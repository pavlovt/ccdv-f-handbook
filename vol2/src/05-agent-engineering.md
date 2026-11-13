# Agent Engineering

Volume I established the shape of an agent: a loop that emits `tool_use`, executes, returns `tool_result`, and repeats until the model stops asking for tools or a cap fires. It also established that you should not build an agent when a workflow will do, and it catalogued the workflow patterns — chaining, routing, parallelization, orchestrator-worker, evaluator-optimizer — along with subagents, compaction, checkpoints and the Agent SDK.

This chapter assumes all of that and asks a different question: what has to be true for such a loop to run unattended, on someone else’s money, against systems that fail?

The gap between a working agent and a production agent is almost entirely about bounded resources and recoverable failure. A demo agent gets three turns and a cooperative API. A production agent gets forty turns, a tool that times out on the eleventh call, a context window that fills at turn twenty-five, a user who closes the browser at turn thirty, and a finance team that wants to know why Tuesday cost \$900. Everything below is a response to one of those facts.

## 4.1 The run controller

Begin with the thing most tutorials omit: a controller that owns the run, not just the loop. The loop decides what to call next. The controller decides whether the run may continue at all, what the run is allowed to spend, and what it reports when it stops.

Four observations shape its design.

**Budget is checked after the fact, not before.** You cannot know a response’s cost until the response arrives with its usage numbers. Any budget cap is therefore an overshoot cap: in the Agent SDK, `max_budget_usd` is compared with accumulated spend once a response lands, so a run can pass the cap by up to the cost of that one response, plus whatever still-running subagents spend before they are stopped. Set the cap below the number you actually cannot exceed.

**Turn limits and budget limits fail differently.** `max_turns` counts tool-use round trips only — the final text-only response is not a turn. A run that stops on turns usually stopped mid-task on a tractable problem. A run that stops on budget usually stopped because context grew, which is a different diagnosis and a different remedy.

**Timeouts belong to the tool, not the run.** A single hung tool call will consume a run’s wall-clock budget without consuming a single token. Each tool needs its own deadline, and the deadline needs to become a `tool_result` the model can read, not an exception that kills the process.

**Cancellation must be cooperative.** If a user abandons the run, you want the in-flight tool to stop, the loop to exit, and the partial result to be reported — not a process killed between an API charge and a database write.

The controller below drives the Messages API directly rather than the Agent SDK, because writing it once is the only way to understand what the SDK is doing for you. It is complete: budget enforcement, turn limits, per-tool timeouts, an error policy, cancellation, and a structured result.

``` {.sourceCode .python}
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

import anthropic

# Opus 5.5 list prices, USD per million tokens.
PRICE = {
    "input": 4.00,
    "output": 20.00,
    "cache_write_5m": 5.00,
    "cache_read": 0.20,
}


class Outcome(str, Enum):
    COMPLETED = "completed"
    TURN_LIMIT = "turn_limit"
    BUDGET_LIMIT = "budget_limit"
    CANCELLED = "cancelled"
    TOOL_CIRCUIT_OPEN = "tool_circuit_open"
    NO_PROGRESS = "no_progress"
    MODEL_ERROR = "model_error"


@dataclass
class ToolSpec:
    schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[str]]
    timeout_s: float = 30.0
    max_consecutive_failures: int = 3
    retryable: bool = True


@dataclass
class RunResult:
    outcome: Outcome
    answer: str | None
    turns: int
    cost_usd: float
    wall_clock_s: float
    tool_calls: int
    tool_failures: int
    transcript: list[dict[str, Any]]
    notes: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.outcome is Outcome.COMPLETED and bool(self.answer)


def response_cost(usage: Any) -> float:
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    plain = usage.input_tokens or 0
    out = usage.output_tokens or 0
    return (
        plain * PRICE["input"]
        + write * PRICE["cache_write_5m"]
        + read * PRICE["cache_read"]
        + out * PRICE["output"]
    ) / 1_000_000


class AgentRun:
    """One bounded agent run with its own budget, limits and failure policy."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        system: str,
        tools: dict[str, ToolSpec],
        *,
        max_turns: int = 30,
        budget_usd: float = 2.00,
        wall_clock_s: float = 600.0,
        loop_window: int = 4,
    ) -> None:
        self.client = client
        self.model = model
        self.system = system
        self.tools = tools
        self.max_turns = max_turns
        self.budget_usd = budget_usd
        self.wall_clock_s = wall_clock_s
        self.loop_window = loop_window

        self.cost = 0.0
        self.turns = 0
        self.tool_calls = 0
        self.tool_failures = 0
        self.consecutive_failures: dict[str, int] = {}
        self.call_fingerprints: list[str] = []
        self.notes: list[str] = []

    # -- guards -----------------------------------------------------------

    def _stop_reason(self, started: float) -> Outcome | None:
        if self.cost >= self.budget_usd:
            return Outcome.BUDGET_LIMIT
        if self.turns >= self.max_turns:
            return Outcome.TURN_LIMIT
        if time.monotonic() - started >= self.wall_clock_s:
            return Outcome.CANCELLED
        return None

    def _is_looping(self) -> bool:
        """A repeated identical call with no new information is a loop."""
        w = self.loop_window
        if len(self.call_fingerprints) < w:
            return False
        tail = self.call_fingerprints[-w:]
        return len(set(tail)) == 1

    # -- tool execution ---------------------------------------------------

    async def _run_tool(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        spec = self.tools.get(name)
        if spec is None:
            return (
                f"No tool named {name!r}. Available tools: "
                f"{', '.join(sorted(self.tools))}.",
                True,
            )

        if self.consecutive_failures.get(name, 0) >= spec.max_consecutive_failures:
            return (
                f"The {name} tool has failed "
                f"{spec.max_consecutive_failures} times in a row and is now "
                "disabled for this run. Do not call it again. Either reach the "
                "goal with the other tools or report what is missing.",
                True,
            )

        try:
            out = await asyncio.wait_for(spec.handler(args), timeout=spec.timeout_s)
        except asyncio.TimeoutError:
            self.consecutive_failures[name] = self.consecutive_failures.get(name, 0) + 1
            self.tool_failures += 1
            return (
                f"{name} did not return within {spec.timeout_s:.0f}s. The call was "
                "abandoned; nothing was changed. Narrow the request (fewer rows, "
                "a smaller date range) and try once more.",
                True,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # the tool's own failure, reported to the model
            self.consecutive_failures[name] = self.consecutive_failures.get(name, 0) + 1
            self.tool_failures += 1
            hint = "" if spec.retryable else " This failure is not retryable."
            return (f"{type(exc).__name__}: {exc}.{hint}", True)

        self.consecutive_failures[name] = 0
        return out, False

    # -- the loop ---------------------------------------------------------

    async def execute(self, prompt: str) -> RunResult:
        started = time.monotonic()
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        answer: str | None = None
        outcome = Outcome.COMPLETED

        try:
            while True:
                stop = self._stop_reason(started)
                if stop is not None:
                    outcome = stop
                    break

                try:
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        system=[
                            {
                                "type": "text",
                                "text": self.system,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                        tools=[spec.schema for spec in self.tools.values()],
                        messages=messages,
                    )
                except anthropic.APIStatusError as exc:
                    if exc.status_code in (429, 500, 502, 503, 529):
                        await asyncio.sleep(2.0)
                        self.notes.append(f"retried after HTTP {exc.status_code}")
                        continue
                    self.notes.append(f"fatal API error {exc.status_code}")
                    outcome = Outcome.MODEL_ERROR
                    break

                self.cost += response_cost(response.usage)
                messages.append(
                    {"role": "assistant", "content": response.content}
                )

                calls = [b for b in response.content if b.type == "tool_use"]
                if not calls:
                    answer = "".join(
                        b.text for b in response.content if b.type == "text"
                    )
                    outcome = Outcome.COMPLETED
                    break

                self.turns += 1
                for call in calls:
                    self.call_fingerprints.append(
                        f"{call.name}:{json.dumps(call.input, sort_keys=True)}"
                    )
                if self._is_looping():
                    outcome = Outcome.NO_PROGRESS
                    break

                results = await asyncio.gather(
                    *(self._run_tool(c.name, c.input) for c in calls)
                )
                self.tool_calls += len(calls)

                blocks: list[dict[str, Any]] = []
                for call, (content, is_error) in zip(calls, results):
                    blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": content,
                            "is_error": is_error,
                        }
                    )
                messages.append({"role": "user", "content": blocks})

                if all(
                    self.consecutive_failures.get(n, 0)
                    >= self.tools[n].max_consecutive_failures
                    for n in self.tools
                ):
                    outcome = Outcome.TOOL_CIRCUIT_OPEN
                    break

        except asyncio.CancelledError:
            outcome = Outcome.CANCELLED
            self.notes.append("cancelled by caller; partial transcript retained")

        return RunResult(
            outcome=outcome,
            answer=answer,
            turns=self.turns,
            cost_usd=round(self.cost, 6),
            wall_clock_s=round(time.monotonic() - started, 2),
            tool_calls=self.tool_calls,
            tool_failures=self.tool_failures,
            transcript=messages,
            notes=self.notes,
        )
```

Three details in that code are load-bearing and easy to get wrong.

The tool’s failure becomes a `tool_result` with `is_error: true`, never an exception that escapes the loop. The model is the recovery mechanism for a recoverable failure; denying it the information denies it the recovery. Volume I covered the mechanics of returning errors — what matters here is that the error *text* is written for a reader who will act on it.

`asyncio.CancelledError` is re-raised inside `_run_tool` and caught only at the top of `execute`. If you swallow cancellation in the tool layer, a cancelled run keeps making API calls on a task nobody is waiting for.

The loop exits on `NO_PROGRESS` before executing a repeated call, not after. Detecting the loop is worth nothing if you pay for the fourth identical query first.

## 4.2 The economics of a run

Agent cost does not grow linearly with turns, and the reason is structural rather than incidental. Context accumulates. Every turn re-sends everything that came before it.

Let `P` be the fixed prefix (system prompt plus tool definitions), `g` the tokens one turn appends (the `tool_use` block plus its `tool_result`), and `o` the output tokens per response. Turn *n* sends `P + (n-1)·g` input tokens. Across `N` turns:

    total_input  = N·P + g·N(N-1)/2
    total_output = N·o

The input term is quadratic in `N`. Take `P = 12,000`, `g = 2,500`, `o = 600`, and Opus 5.5 list prices.

  --------------------------------------------------------------------------------------------------------
  Turns       Input tokens   Output tokens   Cost, no cache   Cost, cached prefix   Avg \$/turn (cached)
  ----------- -------------- --------------- ---------------- --------------------- ----------------------
  10          232,500        6,000           \$1.05           \$0.33                \$0.033

  20          715,000        12,000          \$3.10           \$0.67                \$0.034

  40          2,430,000      24,000          \$10.20          \$1.49                \$0.037

  80          8,860,000      48,000          \$36.40          \$3.74                \$0.047
  --------------------------------------------------------------------------------------------------------

Doubling the turn count from 20 to 40 multiplies the uncached cost by 3.3, not 2. Prompt caching changes the constant dramatically — the cached column assumes a breakpoint at the end of every request, so everything sent on earlier turns is read back at \$0.20/MTok instead of \$4.00, and only the new material is written at \$5.00 (the 12,000-token prefix once, then each turn’s 2,500 new tokens) — but it does not change the exponent. The curve is still superlinear, and the average cost per turn still rises monotonically: a turn late in a run costs more than a turn early in it, for identical work.

Three consequences follow, and they are the quantitative justification for most of the rest of this chapter.

**A budget cap is a context cap in disguise.** If the thing that ends your runs is spend, the lever is tokens per turn, not turns. Halving `g` from 2,500 to 1,250 — by truncating tool output, by paginating, by returning summaries instead of raw payloads — cuts the quadratic term in half. That is a larger win at turn 40 than removing ten turns.

**Delegation is a cost structure, not just a tidiness measure.** A worker that spends fifteen turns in its own context and returns an 800-token brief adds 800 tokens to the parent’s prefix. Inlining the same fifteen turns would have added roughly `15 × 2,500 = 37,500` tokens to every subsequent parent turn. At turn 40, that difference is most of the bill.

**Cheap models are cheap twice.** A worker on Haiku 5.5 at \$0.10/\$0.50 per MTok, running the same fifteen turns, costs roughly a fortieth of the same work on Opus — and because its transcript never enters the parent, it also avoids inflating the parent’s quadratic term. Match the model to the subtask; this is the single highest-leverage cost decision in an agent system.

## 4.3 Context strategy across a long run

A long run will exceed its context window. You have three real options, and they are not interchangeable.

**Compaction** replaces older history with a model-written summary. In the Agent SDK this happens automatically as the window fills, emitting a `compact_boundary` system message; on the API you can request it server-side with a `compact_20260112` edit in `context_management`. Compaction is the cheapest to adopt and the most lossy in an unpredictable direction: the summariser decides what mattered, and specific early instructions can vanish. This is why durable rules belong in a file that is re-injected every request (`CLAUDE.md` via setting sources) rather than in the opening user message.

**Context editing** clears tool results rather than summarising them. The `clear_tool_uses_20250919` edit, under the `context-management-2025-06-27` beta header, clears the oldest tool results once input passes `trigger` (default 100,000 tokens), keeping the most recent `keep` pairs (default 3), with `clear_at_least` to make a clear worth the cache invalidation it causes and `exclude_tools` to protect results you cannot lose. `clear_tool_inputs` extends it to the arguments. When combined with `clear_thinking_20251015`, the thinking edit must be listed first.

``` {.sourceCode .python}
context_management = {
    "edits": [
        {"type": "clear_thinking_20251015", "keep": {"type": "thinking_turns", "value": 2}},
        {
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "input_tokens", "value": 60_000},
            "keep": {"type": "tool_uses", "value": 4},
            "clear_at_least": {"type": "input_tokens", "value": 8_000},
            "exclude_tools": ["write_findings", "read_findings"],
        },
    ]
}
```

Note the `exclude_tools` choice: the agent’s own notes survive clearing while its raw searches do not. That combination — clear the evidence, keep the conclusions — is the pattern worth remembering, and it is why context editing pairs naturally with the memory tool (`memory_20250818`), which lets the model write what it wants to keep to a file before the clear arrives.

**Handoff** ends the run and starts a fresh one with a distilled brief. This is the only option that resets the quadratic term to zero, and the only one where *you* control what survives, because you write the brief. It is also the only one that loses the model’s implicit state — half-formed hypotheses, the feel of which sources were unreliable.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Strategy                 Who decides what survives               Cache impact                                       Cost effect                         Fails when
  ------------------------ --------------------------------------- -------------------------------------------------- ----------------------------------- ------------------------------------------
  Auto-compaction          The summarising model                   Invalidates at the boundary                        Resets growth, keeps prefix         Early constraints must be obeyed exactly

  Tool-result clearing     Your config (`keep`, `exclude_tools`)   Invalidates cleared prefix; use `clear_at_least`   Cuts `g` retroactively              The agent must re-read what was cleared

  Memory tool + clearing   The model, deliberately                 Same as clearing                                   Adds tool calls, removes re-reads   The model writes vague notes

  Fresh run with a brief   You                                     New prefix, cold cache                             Resets quadratic term to zero       The task needs continuous reasoning
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The practical rule: clear tool results while the task is still the same task, and hand off when the *phase* changes. A research agent that has finished gathering and is now writing should hand off. An agent that is still gathering should clear.

## 4.4 Designing the orchestrator-worker split

Volume I introduced orchestrator-worker as a pattern. The engineering question is where to put the boundary, and the answer is determined by one number: how many tokens the worker returns relative to how many it consumed.

A worker exists to convert many tokens into few. If a worker reads 40,000 tokens of code and returns 35,000 tokens of quoted code, it has achieved nothing except moving the cost around. The compression ratio is the design metric.

Three rules follow.

**The worker returns findings, not transcripts.** State this in the worker’s system prompt, in output-shaped terms, not as a plea for brevity. “Be concise” produces a shorter transcript. A required output schema produces a finding.

``` {.sourceCode .python}
WORKER_PROMPT = """You investigate one question and report findings.

Your reply is the ONLY thing the orchestrator sees. Your tool calls and their
results are discarded. Reply with exactly this structure and nothing else:

CLAIM: one sentence answering the question, or "UNRESOLVED".
CONFIDENCE: high | medium | low
EVIDENCE: up to three bullets. Each names its source and gives the single
  number, quote (<=25 words) or file:line that supports the claim.
GAPS: what you could not determine, or "none".

Hard limits: 200 words total. Never paste a file, a page or a query result.
If the question turns out to be two questions, answer the one you were asked
and name the other under GAPS."""
```

**Everything the worker needs goes in the invocation prompt.** A non-fork subagent inherits no parent history. Its context contains its own system prompt, project-level instruction files, tool definitions, and the prompt string you handed it — nothing else. A worker asked to “check the thing we discussed” has no way to know what that was. Pass file paths, error text, prior decisions and the exact question verbatim.

**The orchestrator holds the plan; the workers hold the evidence.** The orchestrator’s context should contain the objective, the task list with status, and the returned briefs. It should not contain a single raw tool result that a worker could have produced instead. When you find raw payloads in the orchestrator’s transcript, a worker boundary is missing.

A fourth rule is about the cap itself: `AgentDefinition.maxTurns` bounds a worker, and when a worker hits it, its output comes back marked partial, with an `agentId` you can use to resume it rather than restart it. Budget a worker tightly and resume the ones that need more, instead of budgeting every worker for the worst case.

## 4.5 Fan-out, concurrency and conflicting results

Independent subtasks should run concurrently: the wall clock becomes the slowest worker rather than the sum. Two limits bound that. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (default 3) caps how deeply workers may spawn workers of their own; setting it to `1` stops your workers from delegating at all. `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20) caps simultaneous workers, and an attempt past it comes back to the model as a tool result reading `Concurrent subagent limit reached` rather than an exception. The spend cap is separate and sits on the query: `max_budget_usd` counts subagent spend, refuses new spawns past the cap, and stops background workers that are still running.

``` {.sourceCode .python}
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Grep", "Glob", "Agent"],
    env={
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
        "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "6",
    },
    max_budget_usd=4.0,
    max_turns=40,
)
```

Depth `1` plus a concurrency of 6 is a good default for a fan-out orchestrator: it keeps the agent tree a tree of height one, which is the only shape whose cost you can predict before the run.

Concurrency raises a problem that sequential agents never face: two workers return incompatible findings. The orchestrator cannot simply concatenate them, and it must not silently prefer whichever arrived last.

The merge policy should be explicit, and the orchestrator should be told what it is:

1.  **Agreement** — findings consistent, confidences compatible: merge and raise confidence.
2.  **One abstains** — one worker returned `UNRESOLVED`: take the other, keep its confidence unchanged. Absence of evidence is not disagreement.
3.  **Specificity gap** — one claim cites a number or `file:line`, the other is general: prefer the specific one, and record the general one as a caveat.
4.  **Genuine contradiction** — both specific, both confident, mutually exclusive: do not pick. Spawn one adjudicating worker whose only job is to resolve the two cited pieces of evidence against each other, and if it cannot, report the conflict to the user. An agent that reports “sources disagree, here is each” is more useful than one that guesses correctly 70% of the time.

That last case is where most multi-agent systems quietly lose their reliability. The failure is not that workers disagree; it is that the merge step was never designed, so disagreement resolves by accident.

## 4.6 Memory and state that survive a run

Three kinds of state have three different homes, and conflating them is a common design error.

**Conversational state** — what has been tried, what the model currently believes — lives in the transcript and dies with it, unless you persist the session. Capture `ResultMessage.session_id` and you can `resume` the run later with its full context restored, or `fork_session=True` to branch without disturbing the original. For hosts that do not keep local disk, a `session_store` adapter mirrors transcripts to your own backend so a different process can resume them.

**Task state** — the objective, the task list, what is done — should not live only in the transcript, because compaction can paraphrase it away. Keep it in a store you own, inject the current version into every turn, and have the model update it through a tool. The run then becomes resumable by reconstruction rather than by replay: a fresh agent reading the task record can continue without the old transcript.

**Durable knowledge** — findings that outlive the run — belongs in files or a database. The memory tool (`memory_20250818`) gives the model a filesystem it can write to and read back on demand, which is what makes it the natural partner for context editing: warned that a clear is approaching, the model can save what matters before the raw results disappear.

``` {.sourceCode .python}
import json
from pathlib import Path


class RunState:
    """Task state the agent mutates through a tool, persisted outside context."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = (
            json.loads(path.read_text())
            if path.exists()
            else {"objective": None, "tasks": [], "findings": [], "blocked": []}
        )

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)  # atomic: a crash mid-write never truncates state

    def brief(self) -> str:
        """The handoff document. Everything a fresh run needs, nothing else."""
        done = [t for t in self.data["tasks"] if t["status"] == "done"]
        open_ = [t for t in self.data["tasks"] if t["status"] != "done"]
        lines = [f"OBJECTIVE: {self.data['objective']}", ""]
        lines.append(f"COMPLETED ({len(done)}):")
        lines += [f"  - {t['title']}: {t.get('result', '')[:200]}" for t in done]
        lines.append(f"REMAINING ({len(open_)}):")
        lines += [f"  - {t['title']}" for t in open_]
        if self.data["blocked"]:
            lines.append("DO NOT RETRY:")
            lines += [f"  - {b}" for b in self.data["blocked"]]
        if self.data["findings"]:
            lines.append("ESTABLISHED FINDINGS:")
            lines += [f"  - {f}" for f in self.data["findings"]]
        return "\n".join(lines)
```

The `blocked` list is the part people leave out and then regret. A fresh run with no memory of what already failed will cheerfully re-attempt the broken endpoint, pay for the timeout again, and reach the same dead end. Carrying forward negative knowledge is as valuable as carrying forward positive knowledge, and it is cheaper to write down.

## 4.7 Repeated tool failure without burning the budget

A tool that fails once is information. A tool that fails five times is a budget leak, because each failure costs a full turn: the model’s reasoning about the failure, plus the whole accumulated context re-sent.

At turn 25 of the example in §4.2, one wasted turn costs roughly \$0.04 cached and \$0.30 uncached. Five of them on the same broken tool is real money for zero progress, and the transcript now contains five near-identical failures that will be re-sent on every remaining turn — so the waste compounds.

The policy that works has three tiers.

**Tier 1 — retry inside the tool, invisibly.** Transient faults (HTTP 429, 503, a connection reset) should be retried with backoff inside the handler, before the model ever sees them. These cost milliseconds, not turns. The model should never be asked to reason about a rate limit it could not have anticipated.

**Tier 2 — report to the model with steering.** A failure the model can do something about — bad arguments, a result set too large, a resource that does not exist — comes back as a `tool_result` with `is_error: true` and a message naming the corrective action. One such failure is productive; the model usually fixes its arguments on the next call.

**Tier 3 — open the circuit.** After *n* consecutive failures of the same tool (three is a reasonable default), stop executing it. Return a result that says the tool is disabled for the rest of the run, instructs the model not to call it again, and tells it to proceed with the remaining tools or report what is missing. The `_run_tool` method in §4.1 implements exactly this, and resets the counter on any success so that an intermittent tool is not permanently banned.

The subtlety is which counter you keep. Count consecutive failures per tool *name*, not per tool call and not globally. A global counter disables healthy tools because one tool is broken; a per-call counter never trips, because every call has slightly different arguments.

When every tool has tripped, the run is over. The controller returns `TOOL_CIRCUIT_OPEN`, which is a far more actionable outcome than letting the run burn to its turn cap and report `turn_limit`.

## 4.8 Detecting and breaking non-terminating loops

Agents do not usually hang. They do something worse: they make progress-shaped motions indefinitely. Four patterns cover nearly all of it.

**Identical repetition.** The same tool with the same arguments, repeatedly. Detect by hashing `(name, canonical_json(args))` and watching for a window of identical fingerprints — the `_is_looping` check in §4.1. Canonicalisation matters: `sort_keys=True` is what makes `{"a":1,"b":2}` and `{"b":2,"a":1}` the same fingerprint.

**Cycling.** A → B → A → B. Detect by looking for a repeated subsequence in the fingerprint list rather than a repeated element. A cheap, effective version: if the last six fingerprints contain only two distinct values, the agent is cycling.

**Oscillating edits.** The agent writes a file, decides it was wrong, reverts, decides the first version was right. Detect on content: hash the post-write state of each path, and flag a hash that recurs after changing. This one is invisible to fingerprint checks, because every call has genuinely different arguments.

**Plan churn.** No tool repeats, nothing contradicts, and yet the task list never shrinks. Detect by tracking completions, not calls: if `k` consecutive turns close no task and add no finding, the agent has stopped converging. This is the only one of the four that needs your task state, which is a further reason to keep it.

What to do on detection matters as much as detection. Killing the run throws away work. The better escalation is graduated:

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Signal                                First response                                                                             If it recurs
  ------------------------------------- ------------------------------------------------------------------------------------------ ------------------------------------------------------------
  Identical repetition (3 in window)    Inject the observation as a tool result naming the repeated call                           End the run with `NO_PROGRESS`

  Cycling between two states            Inject: name both states, require a decision with a reason                                 End the run; report both options to the user

  Oscillating writes                    Freeze the file, return its current content, require justification before the next write   End the run; leave the file in the last state

  Plan churn (4 turns, 0 completions)   Require the next turn to close a task or mark it blocked                                   Hand off with a brief; the context is probably the problem
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Injecting the observation is remarkably effective, because the model usually cannot see the pattern — its own repetition reads as reasonable from inside the transcript. A result that says “you have now called `search_docs` with exactly these arguments three times and received the same result; it will not change; choose a different approach or report the gap” breaks most loops on the first try.

## 4.9 Evaluating an agent

Evaluating a single completion compares an output to a reference. Evaluating an agent cannot work that way, for three reasons: the output depends on the environment’s state at the time; many different trajectories reach the same correct answer; and an agent can reach the right answer by an unacceptable route.

So you grade two things separately.

**Outcome grading** asks whether the final state is correct. It is cheap, objective where the task has a checkable end state, and the only grade that matters to the user. It is also blind: it cannot distinguish an agent that solved the problem from one that deleted the test file.

**Trajectory grading** asks whether the path was acceptable. It catches dangerous shortcuts, wasted spend, tool misuse and lucky guesses. It is expensive and partly subjective, which is why it should be reduced to mechanical checks wherever possible.

  ------------------------------------------------------------------------------------------
  Dimension                     Outcome grading               Trajectory grading
  ----------------------------- ----------------------------- ------------------------------
  What it measures              Final state correctness       How the state was reached

  Cost per case                 Low — one assertion           High — inspect every turn

  Objectivity                   High where a checker exists   Mixed; needs rubric or rules

  Catches a lucky guess         No                            Yes

  Catches a destructive route   Only if the check covers it   Yes

  Catches cost regressions      No                            Yes

  Good as a release gate        Yes                           Yes, as hard rules only
  ------------------------------------------------------------------------------------------

The practical construction is a per-case record with mechanical assertions over the trajectory plus one outcome assertion, and a rubric grade reserved for the cases the assertions cannot express:

``` {.sourceCode .python}
@dataclass
class EvalCase:
    name: str
    prompt: str
    setup: Callable[[], None]
    check_outcome: Callable[[], bool]          # final state assertion
    forbidden_tools: set[str] = field(default_factory=set)
    required_tools: set[str] = field(default_factory=set)
    max_turns: int = 20
    max_cost_usd: float = 0.75


def grade(case: EvalCase, result: RunResult) -> dict[str, Any]:
    used = {
        b.name                       # assistant content holds SDK block objects
        for m in result.transcript
        if m["role"] == "assistant"
        for b in (m["content"] if isinstance(m["content"], list) else [])
        if getattr(b, "type", None) == "tool_use"
    }
    checks = {
        "outcome": case.check_outcome(),
        "no_forbidden_tool": not (used & case.forbidden_tools),
        "used_required_tools": case.required_tools <= used,
        "within_turns": result.turns <= case.max_turns,
        "within_cost": result.cost_usd <= case.max_cost_usd,
        "terminated_cleanly": result.outcome is Outcome.COMPLETED,
        "no_error_spiral": result.tool_failures <= 2,
    }
    return {
        "case": case.name,
        "pass": all(checks.values()),
        "checks": checks,
        "cost_usd": result.cost_usd,
        "turns": result.turns,
    }
```

Four points about running this.

Agents are stochastic, so a single pass is not a measurement. Run each case `k` times (three to five) and report pass rate, median turns and p90 cost. A case that passes 3/5 is a flaky agent, not a passing one, and it will be a production incident.

The cost assertion is as important as the correctness assertion. Agents regress on efficiency silently: a prompt change that adds eight turns to every run passes every correctness test and triples the bill.

Set up and tear down real state. An agent evaluated against mocks that always succeed is evaluated against a world that does not exist; the error paths — the ones §4.7 exists for — are never exercised.

Keep a counterfactual set: cases where the correct behaviour is to refuse, to ask, or to report that the task is impossible. Agents that cannot fail gracefully score well on happy-path suites and badly in production.

## 4.10 Human-in-the-loop that does not destroy throughput

The naive design — approve every tool call — turns an agent into a slow, expensive manual tool. Each approval adds human latency to a loop that otherwise runs at API speed, and the human, asked thirty times, starts approving without reading. That is worse than no approval at all, because it manufactures the appearance of oversight.

Four techniques make oversight compatible with throughput.

**Gate on consequence, not on action.** Reads, searches and analysis run freely; only irreversible or externally visible effects need a human. The Agent SDK’s permission modes encode exactly this gradient: `acceptEdits` auto-approves file edits and common filesystem commands while other Bash calls still follow the rules; `plan` lets the agent explore and propose without touching source; `dontAsk` gives a headless agent a fixed approved surface and hard-denies anything that would otherwise prompt; `auto` runs a classifier over shell commands and network requests; `bypassPermissions` belongs only in disposable environments. A `PreToolUse` hook gives you the same control programmatically, returning `permissionDecision` of `allow`, `deny`, `ask` or `defer`.

**Batch the approvals.** Let the agent plan in `plan` mode, present the whole plan once, approve it, then run the plan unattended. One decision over twelve actions beats twelve decisions, and the human reviewing a plan sees the shape of the work — which is where the real errors are.

**Make the ask cheap to answer.** An approval request should carry the action, the reason, the blast radius and the reversal path, in four lines. If the human has to read the transcript to decide, the design has failed.

**Defer rather than block.** A `PreToolUse` hook that returns `defer` ends the turn with `stop_reason` of `tool_deferred`, so the run yields instead of holding a process open waiting for a human. The pending call is resumed later. This is the difference between an agent fleet that scales and one that is bounded by how many approvals are open at once.

  -----------------------------------------------------------------------------------------------------------------------------
  Design                          Human decisions per run   Throughput     Catches a bad action   Decays into rubber-stamping
  ------------------------------- ------------------------- -------------- ---------------------- -----------------------------
  Approve every call              20–40                     Very low       Almost always          Yes, quickly

  Approve plan, then run          1                         High           Usually                Rarely

  Gate by consequence class       2–4                       High           For gated classes      Rarely

  Post-hoc review with rollback   0 during run              Highest        After the fact         N/A

  Classifier-gated (`auto`)       0–2                       High           Mostly                 No
  -----------------------------------------------------------------------------------------------------------------------------

The last row is worth its own sentence: for a large class of actions, the right reviewer is another model with a rule, not a person. Reserve the person for decisions that are genuinely about judgement or liability.

## 4.11 Worked example: a multi-step research agent

Everything above now assembles into one system. The task: answer a research question that requires several independent lines of investigation, with a hard budget, a written answer, and an audit trail.

The architecture is deliberately flat. An orchestrator decomposes the question, fans out to workers at depth 1, merges briefs under an explicit conflict policy, and writes the answer. State lives in a file, not in the transcript. Each worker is capped tightly and resumed if it runs out of turns.

``` {.sourceCode .python}
import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    HookMatcher,
)

RESEARCHER = AgentDefinition(
    description=(
        "Investigates ONE specific factual question using web search and file "
        "reads. Use for every independent sub-question. Returns findings only."
    ),
    prompt=WORKER_PROMPT,          # the structured-output prompt from §4.4
    tools=["WebSearch", "WebFetch", "Read", "Grep"],
    model="sonnet",                # workers rarely need the frontier model
    maxTurns=12,                   # tight; resume the ones that need more
)

ADJUDICATOR = AgentDefinition(
    description=(
        "Resolves two contradictory findings. Use ONLY when two researchers "
        "returned specific, confident, mutually exclusive claims."
    ),
    prompt=(
        "You are given two contradictory claims with their cited evidence. "
        "Check each citation against its source. Reply with: WINNER (claim A, "
        "claim B, or NEITHER), REASON (one sentence naming the deciding "
        "evidence), and RESIDUAL_DOUBT. Never invent a third claim."
    ),
    tools=["WebFetch", "Read"],
    model="sonnet",
    maxTurns=8,
)

ORCHESTRATOR_PROMPT = """You answer a research question by delegating.

Procedure, in order:
1. Decompose the question into 3-6 independent sub-questions. Independent
   means a researcher can answer one without knowing another's answer.
2. Spawn one `researcher` per sub-question, in a single batch so they run
   concurrently. Put everything the researcher needs in its prompt: it sees
   none of this conversation.
3. Record every returned brief with `record_finding` before you reason about
   it. State you have not recorded does not survive compaction.
4. Merge the briefs under this policy:
   - consistent claims: merge, raise confidence
   - one UNRESOLVED: take the other, keep its confidence
   - one specific (number / quote / file:line), one general: prefer specific,
     record the general as a caveat
   - both specific, both confident, mutually exclusive: spawn `adjudicator`
     once. If it returns NEITHER, report the conflict. Never pick silently.
5. If a sub-question is still unresolved after one researcher and the budget
   allows, respawn it ONCE with a narrower prompt. Never a third time.
6. Write the answer: the claim, the evidence per claim with sources, then an
   explicit list of what remains unknown.

You never call WebSearch, WebFetch or Read yourself. Raw source text must not
enter this conversation. If you catch yourself wanting to read a page, that is
a sub-question: delegate it."""


async def research(question: str, state_path: Path, budget_usd: float = 6.0):
    state = RunState(state_path)
    state.data["objective"] = question
    state.save()

    async def audit(input_data, tool_use_id, context):
        """Durable audit trail; runs in our process, costs no context."""
        if input_data.get("tool_name") in ("Agent", "Task"):
            state.data.setdefault("spawns", []).append(
                {"id": tool_use_id, "input": input_data.get("tool_input")}
            )
            state.save()
        return {}

    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        agents={"researcher": RESEARCHER, "adjudicator": ADJUDICATOR},
        allowed_tools=["Agent", "record_finding", "read_state"],
        disallowed_tools=["WebSearch", "WebFetch", "Write", "Edit"],
        env={
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
            "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "6",
        },
        max_budget_usd=budget_usd,
        max_turns=40,
        permission_mode="dontAsk",
        hooks={"PreToolUse": [HookMatcher(matcher="Agent|Task", hooks=[audit])]},
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(f"{state.brief()}\n\nResearch question: {question}")
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                state.data["result"] = {
                    "subtype": message.subtype,
                    "cost_usd": message.total_cost_usd,
                    "turns": message.num_turns,
                    "session_id": message.session_id,
                }
                state.save()

                if message.subtype == "success":
                    return message.result
                if message.subtype == "error_max_budget_usd":
                    return (
                        "Budget exhausted. Findings so far:\n"
                        + state.brief()
                        + f"\n\nResume: session {message.session_id}"
                    )
                if message.subtype == "error_max_turns":
                    return (
                        "Turn limit reached before completion. Resume session "
                        f"{message.session_id} with a higher cap.\n\n"
                        + state.brief()
                    )
                return f"Stopped: {message.subtype}\n\n{state.brief()}"
```

Six design choices in that code deserve naming, because each one is a response to a specific failure this chapter has described.

`disallowed_tools` removes the search tools from the orchestrator entirely. Instructing it not to read pages is a suggestion; removing the tool is a guarantee. Without this, the orchestrator reads one page “just to check”, and 15,000 tokens of raw HTML enter the context that every subsequent turn re-sends.

Depth is pinned to `1`. Workers cannot spawn workers, so the cost of the run is bounded by the orchestrator’s turns times the per-worker cap — a number you can compute before you press go. Allowing nesting makes that number unbounded in practice.

Workers run on Sonnet and the orchestrator on the default frontier model. Decomposition and merging are the hard reasoning; searching and extracting a number are not. This single split typically halves the bill.

The audit hook writes to state, not to context. Hooks run in your process and consume no context window, which makes them the correct place for all observability. Logging through a tool would have cost tokens on every turn for the rest of the run.

Every error subtype returns the brief rather than an apology. A run that hit its budget at 85% completion has produced most of its value; returning `state.brief()` plus a resumable `session_id` makes that value collectible. Returning “the run failed” discards it.

The respawn rule is capped at one retry, in the prompt. Without an explicit cap, “try a narrower prompt” is an invitation to the plan-churn loop from §4.8 — each retry is a genuinely new call, so no fingerprint check will catch it.

## 4.12 What to take away

A production agent is a bounded resource manager that happens to contain a language model. The model picks the next action; your controller decides whether there is room for another action at all, what happens when the action fails, and what the run reports when it stops early — which it often will.

The quantitative core is §4.2: cost is quadratic in turns because context accumulates. Almost every engineering technique in this chapter is a way of attacking either the coefficient (truncate, paginate, clear, summarise) or the exponent (delegate, hand off, reset). Techniques that reduce turn count without reducing tokens per turn are the weaker lever.

And the operational core is that early termination is normal. Budget caps fire. Tools break. Users cancel. An agent that returns a structured partial result, a list of what already failed, and a session it can be resumed from is a system you can run. One that returns a stack trace is a demo.

## Practice Questions

**V4.1** An agent run is configured with `max_budget_usd=5.00`. Monitoring shows a completed run with `subtype` of `error_max_budget_usd` and `total_cost_usd` of \$5.74. What is the most likely explanation?

A. The budget cap applies only to the main agent, and subagent spend is excluded from it B. `total_cost_usd` includes cache-write tokens that are excluded from the cap comparison C. The cap is evaluated once per turn rather than once per response, so a multi-tool turn can exceed it D. Spend is compared with the cap after a response arrives, so the response that crossed the cap still completed and was billed, plus any subagent spend before those agents stopped

**V4.2** Using the model from §4.2 — fixed prefix `P` of 12,000 tokens, `g` of 2,500 tokens appended per turn, 600 output tokens per response — approximately how many total input tokens does a 30-turn run send, before caching?

A. 435,000 B. 720,000 C. 1,447,500 D. 2,250,000

**V4.3** A worker subagent is told “be concise” and consistently returns 4,000-token replies containing long quoted passages from the files it read. Which change most reliably fixes this?

A. Replace the brevity instruction with a required output structure that caps total words and forbids pasting source text B. Lower the worker’s `maxTurns` so it has less material to quote C. Switch the worker to a smaller model, which produces shorter outputs D. Enable tool-result clearing in the worker so the quoted material is no longer in its context

**V4.4** Your orchestrator’s transcript contains full 12,000-token web pages. The orchestrator’s prompt says it should delegate all reading to researchers. Which fix is strongest?

A. Add `WebFetch` to `disallowed_tools` on the orchestrator so the tool is not available to it at all B. Add a stronger instruction with an example of what not to do C. Reduce the orchestrator’s `max_turns` so there is less opportunity to fetch D. Enable auto-compaction so the pages are summarised away

**V4.5** A tool has failed with the same connection error on four consecutive calls. The run has 22 turns and \$3.10 of budget remaining. What is the correct controller behaviour?

A. Keep returning the error to the model; it may find a different approach eventually B. Raise the exception so the run ends immediately and the operator is alerted C. Stop executing that tool, return a result stating it is disabled for the run and instructing the model to continue with other tools or report what is missing, and reset the counter only on a later success D. Retry the tool with exponential backoff until the budget is exhausted

**V4.6** An agent calls `search_index` with `{"q": "latency", "limit": 50}`, then `{"limit": 50, "q": "latency"}`, then `{"q": "latency", "limit": 50}`. A fingerprint-based loop detector does not trigger. What is the most likely cause?

A. The detector’s window is larger than three calls B. Loop detection cannot see tool calls made in the same turn C. The detector resets on any successful tool result D. The detector hashes the arguments without canonicalising key order, so the second call produces a different fingerprint

**V4.7** Which statement about `max_turns` in the Agent SDK is correct?

A. It counts every assistant response, including the final text-only one B. It counts tool-use round trips only; the final text-only response is not a turn C. It counts individual tool calls, so a turn with three parallel calls consumes three turns D. It counts turns across the whole session and cannot be reset by starting a new message

**V4.8** Two researchers return contradictory findings. Researcher A says the p99 latency is 840 ms, citing a named dashboard panel. Researcher B says latency is “well within target”, citing a product page. Under the merge policy in §4.5, what should the orchestrator do?

A. Prefer A and record B as a caveat, because A’s claim is specific and B’s is general B. Spawn an adjudicator, because the claims are mutually exclusive C. Report the conflict to the user without resolving it D. Average the two confidences and report medium confidence

**V4.9** You are deciding between enabling `clear_tool_uses_20250919` and ending the run to hand off to a fresh agent with a written brief. The agent has finished gathering evidence and is now composing a long written report. Which is the better choice, and why?

A. Clearing, because the report needs the gathered evidence still in context B. Clearing, because a handoff loses the session and cannot be resumed C. Handoff, because the phase has changed: the writing phase needs the distilled findings, not the raw evidence, and a handoff resets the accumulated context entirely D. Neither; auto-compaction handles phase changes correctly without configuration

**V4.10** An eval suite of 40 cases reports 100% pass on correctness after a prompt change. Production spend rises 2.6x the following week. What was most likely missing from the suite?

A. Trajectory assertions on forbidden tools B. Per-case assertions on turns and cost, run over multiple repetitions C. Counterfactual cases where the agent should refuse D. Real environment setup instead of mocks

**V4.11** A `PreToolUse` hook returns `permissionDecision` of `defer`. What happens?

A. The tool runs and its result is withheld from the model until a human approves it B. The tool call is denied and the model receives a rejection message C. The call is queued and executed automatically when the next turn begins D. The turn ends with `stop_reason` of `tool_deferred`, and the pending call can be resumed later

**V4.12** Using the cached-prefix column of the table in §4.2, roughly what fraction of a 40-turn run’s cost is attributable to cache reads of the accumulated prefix rather than to new writes and output?

A. About one twentieth B. About one third C. About two thirds D. Essentially all of it

**V4.13** An orchestrator spawns 14 researchers in one batch. Several come back with a tool result reading `Concurrent subagent limit reached`. What is happening, and what is the correct response?

A. The budget cap was reached; raise `max_budget_usd` B. The spawn depth limit was reached; raise `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` C. `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` is set below 14; either raise it or have the orchestrator fan out in smaller batches D. The model exceeded the parallel tool call limit; disable parallel tool use

**V4.14** Which piece of state is most at risk of being silently lost to auto-compaction, and therefore most needs to live outside the transcript?

A. The task list with per-task status, and the record of approaches that already failed B. The raw text of tool results from early turns C. The model’s reasoning about which sources were unreliable D. The system prompt and tool definitions

**V4.15** A run ends with `error_max_turns` at what you estimate is 80% completion. Which response preserves the most value?

A. Report the failure and start a new run from the original prompt B. Return the persisted task-state brief plus the `session_id`, so the run can be resumed or reconstructed C. Raise the turn cap and automatically re-run the same prompt D. Switch to a larger model and re-run

**V4.16** (Select TWO) Which two changes reduce the *quadratic* growth term in an agent run’s cost, as opposed to only reducing its constant factor?

A. Enabling prompt caching on the system prompt and tool definitions B. Delegating a 15-turn investigation to a subagent that returns an 800-token brief C. Truncating each tool result from 2,500 to 1,250 tokens D. Ending the run and starting a fresh one with a distilled brief E. Moving the workers from Opus to Haiku

**V4.17** (Select TWO) Which two signals indicate plan churn rather than simple tool repetition?

A. The same tool is called with identical canonicalised arguments four times B. The agent alternates between two tools in an A-B-A-B pattern C. A file’s content hash recurs after having changed D. Four consecutive turns close no task and add no finding, while every tool call is distinct E. The task list length is unchanged across six turns despite continuous tool activity

**V4.18** (Select TWO) Which two statements about the memory tool combined with context editing are correct?

A. `clear_tool_uses_20250919` must be listed before `clear_thinking_20251015` when both are used B. The memory tool automatically persists all tool results before they are cleared C. Context editing clears content from the server-side history before the prompt reaches the model, while your client keeps the full transcript D. `exclude_tools` can protect the memory tool’s own calls, so the agent’s saved notes survive clearing E. Tool-result clearing preserves cached prefixes, which is why `clear_at_least` is unnecessary

**V4.19** (Select TWO) An agent fleet runs 400 autonomous tasks per hour. Which two human-in-the-loop designs preserve throughput while retaining meaningful oversight?

A. Running in `plan` mode, having a human approve the whole plan once, then executing unattended B. Approving every tool call through a synchronous callback C. Gating only irreversible or externally visible actions, and letting reads and searches run freely D. Setting `permission_mode` to `bypassPermissions` and reviewing transcripts weekly E. Requiring approval for the first three tool calls of every run

**V4.20** (Select TWO) Which two pairs of run outcomes should a controller keep distinct, rather than collapsing into a single “failed” status, because each member of the pair implies a different remedy?

A. `turn_limit` and `budget_limit` B. `completed` and `cancelled` C. `model_error` and `completed` D. `turn_limit` and `completed` E. `tool_circuit_open` and `no_progress`
