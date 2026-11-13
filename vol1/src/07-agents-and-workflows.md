# Agents and Workflows

The word “agent” has been stretched to cover everything from a two-step prompt chain to an autonomous system that runs for hours against a production codebase. That looseness causes real engineering harm, because the two ends of that range have different failure modes, different cost profiles, and different testing strategies. A system whose control flow you wrote is debuggable by reading code. A system whose control flow the model decides at runtime is debuggable only through traces, budgets, and guardrails you built in advance.

This chapter draws that line precisely, then works through what you need on each side of it: the mechanics of the tool-use loop, the workflow patterns that cover most production needs without autonomy, the termination and budget controls that keep an autonomous loop from running away, context management for runs that outlive the window, and the failure modes that show up in every agent system eventually. It closes on the Claude Agent SDK and an honest account of what it gives you over writing the loop yourself.

## Workflow or agent: the distinction that matters

Anthropic’s framing is clean and worth adopting verbatim as terminology:

-   A **workflow** is a system where language models and tools are orchestrated through **predefined code paths**. You decide the sequence. The model fills in steps.
-   An **agent** is a system where the model **directs its own control flow** — deciding which tools to call, in what order, how many times, and when the task is done.

The distinction is not about sophistication. A three-model workflow with retrieval, validation, and a retry path can be far more sophisticated than a naive agent loop. The distinction is about **who decides what happens next**: your code, or the model.

That one difference propagates into everything:

  -----------------------------------------------------------------------------------------------------
  Property                 Workflow                             Agent
  ------------------------ ------------------------------------ ---------------------------------------
  Control flow             Written by you, visible in code      Decided by the model at runtime

  Cost predictability      Bounded by construction              Unbounded without explicit caps

  Latency predictability   Roughly known in advance             Varies by an order of magnitude

  Testability              Each step testable in isolation      Requires end-to-end traces and evals

  Debugging a failure      Read the code path                   Read the transcript

  Right for                Tasks you can decompose in advance   Tasks whose steps cannot be predicted
  -----------------------------------------------------------------------------------------------------

The default should be the simplest thing that works, and the documented guidance is explicit: start with the simplest solution and add complexity only when it demonstrably improves outcomes. Often a single well-constructed call with good retrieval and in-context examples is enough, and no agentic system is needed at all. The step from “one call” to “workflow” should be forced by a task that genuinely has stages. The step from “workflow” to “agent” should be forced by a task where you cannot enumerate the stages in advance.

The signal that you need an agent is specific: **the number and nature of the steps depends on what the earlier steps discover.** “Find and fix the bug causing these test failures” is agentic, because which files need reading depends on what the test output says, and which edits are needed depends on what the files contain. “Summarize this document, then translate the summary, then check the translation against a glossary” is a workflow, because you knew all three steps before you saw the document.

Choosing an agent when a workflow would do buys you nondeterminism, unbounded cost, and a debugging story that requires transcript archaeology — in exchange for flexibility you are not using.

## The core agent loop

Everything agentic on the Claude API reduces to one loop. Understanding it in detail is worth more than any framework, because when a framework misbehaves this is the layer you debug at.

The mechanics:

1.  You send a request with a `tools` array.
2.  You inspect `stop_reason`. If it is `"tool_use"`, the response contains one or more `tool_use` content blocks, each with an `id`, a `name`, and an `input` object.
3.  You execute each requested tool in your own code.
4.  You append the assistant message to the history, then append a **user** message containing one `tool_result` block per `tool_use`, each referencing the original `tool_use_id`.
5.  You send the request again and repeat until `stop_reason` is something other than `"tool_use"`.

A complete loop, with the error handling and caps a production implementation needs:

``` {.sourceCode .python}
import json
import time
import anthropic

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "search_orders",
        "description": "Search orders by customer email. Returns at most 20 matches.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Customer email address"},
                "status": {
                    "type": "string",
                    "enum": ["open", "shipped", "cancelled"],
                    "description": "Optional status filter",
                },
            },
            "required": ["email"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Issue a refund for an order. Irreversible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount_cents": {"type": "integer", "minimum": 1},
            },
            "required": ["order_id", "amount_cents"],
        },
    },
]


class ToolBudgetExceeded(Exception):
    pass


def dispatch(name, tool_input):
    """Execute a tool. Raises on bad input so the caller can report is_error."""
    if name == "search_orders":
        return json.dumps(order_store.search(**tool_input))
    if name == "issue_refund":
        return json.dumps(payments.refund(**tool_input))
    raise ValueError(f"unknown tool: {name}")


def run_agent(
    user_request: str,
    *,
    max_turns: int = 20,
    max_tokens_total: int = 400_000,
    deadline_seconds: float = 120.0,
    model: str = "claude-sonnet-5-5",
):
    messages = [{"role": "user", "content": user_request}]
    turns = 0
    tokens_used = 0
    started = time.monotonic()
    consecutive_errors = 0

    while True:
        # --- Budget checks before every model call -----------------------
        if turns >= max_turns:
            return Outcome("turn_budget_exhausted", messages, tokens_used, turns)
        if tokens_used >= max_tokens_total:
            return Outcome("token_budget_exhausted", messages, tokens_used, turns)
        if time.monotonic() - started > deadline_seconds:
            return Outcome("deadline_exceeded", messages, tokens_used, turns)

        response = client.messages.create(
            model=model,
            max_tokens=8192,
            tools=TOOLS,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
        )
        turns += 1
        usage = response.usage
        tokens_used += (
            usage.input_tokens
            + usage.output_tokens
            + getattr(usage, "cache_read_input_tokens", 0)
            + getattr(usage, "cache_creation_input_tokens", 0)
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "max_tokens":
            # The final content block may be a truncated tool_use. Do not execute it.
            return Outcome("output_truncated", messages, tokens_used, turns)

        if response.stop_reason == "pause_turn":
            continue    # a server tool paused; resending the history resumes it

        if response.stop_reason != "tool_use":
            # end_turn on success; refusal and others are reported as they are
            return Outcome(response.stop_reason, messages, tokens_used, turns)

        # --- Execute every requested tool; parallel calls are normal -----
        results = []
        turn_had_error = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                content = dispatch(block.name, block.input)
                is_error = False
            except Exception as exc:
                content = f"{type(exc).__name__}: {exc}"
                is_error = True
                turn_had_error = True
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })

        consecutive_errors = consecutive_errors + 1 if turn_had_error else 0
        if consecutive_errors >= 3:
            return Outcome("repeated_tool_failure", messages, tokens_used, turns)

        messages.append({"role": "user", "content": results})
```

Several details in that loop are the difference between a demo and a production system. (One thing it deliberately leaves out is an approval gate in front of the irreversible `issue_refund`; that is added in the human-in-the-loop section below.)

**Append the assistant message before executing anything.** The conversation must contain Claude’s `tool_use` blocks before the matching `tool_result` blocks, or the next request is malformed.

**Handle every `tool_use` block in the response, not just the first.** Claude can issue several tool calls in one turn, and every one needs a `tool_result` keyed to its `tool_use_id`. If you only answer one, the request is invalid. You can set `tool_choice: {"type": "auto", "disable_parallel_tool_use": True}` to force one call per turn, which simplifies the loop at the cost of more round trips.

**Check for `stop_reason: "max_tokens"` before executing.** When output is truncated, a trailing `tool_use` block may be incomplete — partial JSON in `input`. Executing it is how agents delete the wrong file. Treat truncation as a terminal condition or retry with a higher `max_tokens`, never as a tool call.

**Report tool errors back to the model rather than raising.** Set `is_error: true` with the error text as content. Claude will typically adjust and try a different approach, which is the entire value of the loop. Raising out of the loop on a transient failure throws away the run.

**Count tokens from `usage` on every response.** You cannot enforce a token budget you are not measuring, and the cache fields matter: they are real context occupancy even when they are cheap.

Server tools are a partial exception to all of this. Tools like web search, web fetch, and code execution run on Anthropic’s infrastructure and their results come back in the response directly — you write no execution code for them. The mixed case, where Claude calls a server tool in the same parallel group as a client tool, has its own handling rules worth reading before you rely on it.

## Termination conditions and budget caps

An agent loop without an exit condition is an unbounded bill. There are three independent budgets, and you need all three, because each catches a different failure.

**Turn cap.** The simplest and most important. Bounds the number of model round trips. Catches the loop that oscillates between two tools forever. Set it from measured data: if your p99 successful task completes in 14 turns, a cap of 25 is generous without being open-ended.

**Token cap.** Catches the run that makes few turns but enormous ones — an agent that reads a 300K-token file on turn 2 and then keeps the whole thing in context for the next fifteen turns. Turn count looks fine; cost does not. Accumulate from `usage` across the run.

**Wall-clock deadline.** Catches the slow run that is neither making many turns nor burning many tokens, because it is stuck waiting on a tool. In any request-scoped context — an HTTP handler, a queue consumer with a visibility timeout — the deadline is what keeps the agent inside its allotted time.

Beyond budgets, the natural termination conditions:

  ----------------------------------------------------------------------------------------------------------------------
  Condition                     Meaning                                    Handling
  ----------------------------- ------------------------------------------ ---------------------------------------------
  `stop_reason: "end_turn"`     Model finished; no tool calls              Normal success path

  `stop_reason: "tool_use"`     Model wants a tool executed                Continue the loop

  `stop_reason: "max_tokens"`   Output truncated mid-generation            Terminal; do not execute trailing tool\_use

  `stop_reason: "refusal"`      Model declined the request                 Terminal; surface to the caller

  `stop_reason: "pause_turn"`   Long-running server tool turn unfinished   Continue the turn in a follow-up request

  Turn / token / time cap       Your budget hit                            Terminal; return partial state

  Repeated tool failure         Same tool erroring N times running         Terminal; the environment is broken
  ----------------------------------------------------------------------------------------------------------------------

Two design rules about budget exhaustion. First, **return the partial state, not an exception** — the conversation history up to that point is valuable for diagnosis and for resumption. Second, **distinguish the exhaustion reason in your telemetry.** “Agent failed” is not actionable. “Agent hit the turn cap on 12% of refund requests, all of which first called `search_orders` with a malformed email” is a bug report.

A subtlety about budget enforcement worth internalizing: a cost cap can only be checked after a response arrives, because the cost comes from the usage the API returns with that response. The response that crosses the cap still completes and still bills. So actual spend can exceed a cost cap by up to the cost of one full response — more if parallel work was in flight. Leave headroom.

## Workflow patterns

Most production systems described as “agents” are better built as workflows. Five patterns cover the great majority of real cases.

### Prompt chaining

Decompose a task into a fixed sequence where each call consumes the previous call’s output, with programmatic checks between steps. Trades latency for accuracy by giving each call a narrower job.

Use it when the decomposition is stable and known in advance: draft an outline, verify it meets structural criteria, then write the document against it. The gate between steps is the real value — you catch a bad outline before paying for a document built on it.

### Routing

Classify the input, then dispatch to a specialized handler. Two distinct payoffs: handling categories that genuinely need different prompts or tools, and sending easy inputs to cheaper models.

Use it when categories are distinguishable with high accuracy and benefit from different treatment. The failure mode is a miscalibrated classifier silently sending hard requests down the cheap path; measure per-category quality, not just aggregate.

### Parallelization

Two variants with different purposes.

**Sectioning** splits a task into independent subtasks run concurrently, then aggregates. Latency becomes the slowest branch rather than the sum. Classic shape: answer the user’s question on one branch while screening the input for policy violations on another.

**Voting** runs the same task several times, with varied prompts, and combines the results. Buys confidence rather than speed — several independent passes looking for security vulnerabilities in a diff catch more than one pass, and agreement across passes is a usable signal.

### Orchestrator-workers

A central model decomposes the task at runtime, delegates pieces to workers, and synthesizes the results. This is where the workflow/agent line genuinely blurs: the decomposition is model-decided, but the overall structure is fixed.

Use it when **you cannot predict the subtasks**, only their shape. A change that must be applied across an unknown number of files, or a research question requiring search across sources you cannot enumerate in advance. If you can enumerate the subtasks, sectioning is cheaper and more predictable.

### Evaluator-optimizer

One call generates, another evaluates against criteria and returns feedback, and the loop repeats until the evaluation passes or a cap is hit.

Use it when the evaluation criteria are articulable and iteration measurably helps — literary translation refined through critique, or a search strategy improved over rounds. It requires a hard iteration cap and a tolerance for the evaluator converging on “good enough” by exhaustion rather than merit. If your criteria are machine-checkable (tests pass, schema validates), use the checker directly instead of a model evaluator — it is cheaper and more reliable.

  ------------------------------------------------------------------------------------------------------
  Pattern                        Who decides steps        Use when
  ------------------------------ ------------------------ ----------------------------------------------
  Prompt chaining                You                      Fixed decomposition, gates between stages

  Routing                        You (model classifies)   Categories need different handling or models

  Parallelization — sectioning   You                      Independent subtasks; latency matters

  Parallelization — voting       You                      Confidence matters more than cost

  Orchestrator-workers           Model decomposes         Subtasks unpredictable in advance

  Evaluator-optimizer            You (loop structure)     Clear criteria, iteration demonstrably helps
  ------------------------------------------------------------------------------------------------------

## Subagents and context isolation

A subagent is a separate agent instance spawned to handle a focused subtask. The benefit that matters most is **context isolation**: the subagent runs in its own conversation, its intermediate tool calls and results stay inside it, and only its final message returns to the parent.

The economics are compelling for exploratory work. A subagent that reads forty files to answer “where is authentication handled in this codebase” might consume 200,000 tokens doing so. Run inline, that 200,000 tokens becomes permanent context in the main conversation, re-sent and re-billed on every subsequent turn. Run as a subagent, the parent’s context grows by a two-paragraph summary.

Three other benefits follow from separation: **parallelization** (independent subtasks finish in the time of the slowest rather than the sum), **specialized instructions** (a migration specialist can carry detailed SQL and rollback knowledge that would be noise in the main prompt), and **tool restriction** (a documentation reviewer given only read tools cannot modify anything, by construction rather than by instruction).

The cost is the thing engineers consistently underestimate: **a subagent starts with no knowledge of the parent conversation.** Unless it is an explicit fork, the only content crossing the boundary is the prompt string the parent passes. It does not receive the parent’s history, tool results, or system prompt. If the subagent needs a file path, an error message, or a decision made three turns ago, that must be written into the prompt. A vaguely briefed subagent re-derives context that the parent already had, which is slower and worse than not delegating.

Use subagents when the subtask is **high-volume and low-yield**: it reads or searches a lot and reports a little. Skip them when the subtask needs most of the parent’s context to make sense, because you will spend the savings reconstructing it.

Subagents also introduce a structural risk: they can spawn subagents of their own, so one prompt can become a tree. Cap the depth, the concurrency, and the total spend. In the Agent SDK those are `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (default 3 layers), `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20), and `max_budget_usd`, which counts subagent spend toward the total and refuses further spawns at the cap. Models vary in how readily they delegate — Opus 5 delegates more eagerly than earlier models — so these limits matter more on some models than others, and prompting alone is not a substitute for enforcing them.

## Context management across a long run

Context accumulates monotonically within a session: system prompt, tool definitions, every tool input, every tool output, every assistant message. Tool outputs dominate. One verbose command or one large file read can add thousands of tokens in a single turn, and that content is then re-sent on every subsequent turn.

Three server-side mechanisms address this, and they are complementary rather than alternatives.

**Compaction** is the recommended default for long-running work. When the conversation crosses a token threshold (default 100,000 tokens), Claude writes a structured summary of it, and that summary replaces the earlier history. The default summary covers task overview, current state, important discoveries, next steps, and context to preserve. On the API, server-side compaction is enabled by passing the `compact_20260112` edit in `context_management`. The older client-side mechanism, the SDK’s `compaction_control` parameter, checked usage after each response and injected the summary prompt itself; it is deprecated in TypeScript and Ruby and removed from the Python SDK in v1.0.

Compaction’s limitation is inherent: it is lossy, so it is a poor fit for tasks requiring exact recall of early details. Instructions placed only in the initial prompt may not survive. The fix is to put persistent rules somewhere re-injected on every request — a `CLAUDE.md` in the SDK — rather than in the opening message.

**Context editing** clears content rather than summarizing it, with finer control. Enabled with the `context-management-2025-06-27` beta header. The `clear_tool_uses_20250919` strategy removes the oldest tool results once input exceeds a threshold, replacing each with placeholder text telling Claude it was removed:

``` {.sourceCode .python}
response = client.beta.messages.create(
    model="claude-opus-5-5",
    max_tokens=8192,
    tools=TOOLS,
    messages=messages,
    betas=["context-management-2025-06-27"],
    context_management={
        "edits": [{
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "input_tokens", "value": 120_000},
            "keep": {"type": "tool_uses", "value": 5},
            "clear_at_least": {"type": "input_tokens", "value": 20_000},
            "exclude_tools": ["read_policy_document"],
        }]
    },
)
```

The defaults are a 100,000-input-token trigger and 3 recent tool uses kept. `clear_at_least` matters more than it looks: clearing changes the prompt prefix and therefore invalidates the cache from that point, so you want each clear to free enough context to justify the cache write. `exclude_tools` protects results that must never be cleared. A companion strategy, `clear_thinking_20251015`, manages prior turns’ thinking blocks; when combining strategies it must be listed first. Applied edits are reported in `context_management.applied_edits`, and `count_tokens` returns both the post-edit `input_tokens` and the pre-edit `original_input_tokens` so you can preview the effect.

A valuable property of context editing: your client keeps the full unmodified history. The editing happens server-side before the prompt reaches the model, so there is nothing to sync.

**The memory tool** (`memory_20250818`) lets Claude write information to persistent files. Paired with either mechanism, it closes the loss problem: Claude receives an automatic warning as the clearing threshold approaches and can save what matters before it is removed, then read it back on demand. This is the right answer when a run must preserve specific findings across compaction.

What happens when the window fills mid-loop depends on whether you configured these mechanisms. With none of them, an over-long prompt is simply rejected with a 400 “prompt is too long” (Chapter 2), and the loop has no clean way to recover. With them, the window should never fill: context editing clears before the model sees an oversized prompt, compaction summarizes once the threshold is crossed, and the memory tool warns Claude in advance. If compaction triggers while a tool use is pending, that tool use block is removed before summarizing, and Claude re-issues the call after resuming if it still needs it. Your job is to configure these mechanisms with thresholds that leave headroom, rather than to write a recovery handler for a window-full error.

One caveat with server tools: `cache_read_input_tokens` can include reads from internal calls, so the SDK may overcount and compact earlier than necessary. Use the token counting endpoint when you need an accurate context length.

## State and memory between turns

Distinguish three kinds of persistence, because conflating them is a common design error.

**Conversation state** is the message history. It is what makes the loop coherent. It lives in your process for a hand-rolled loop, or in a session for the SDK. It is the thing compaction compresses.

**Task state** is the work product: files written, rows updated, a plan being executed. It should live outside the conversation. An agent whose only record of what it has done is the transcript loses that record to compaction. An agent that writes a progress file, or updates a task tracker, keeps its state in a place that survives summarization and that you can inspect while the run is in flight. This is the single most effective structural defense against compaction loss.

**Cross-session memory** is what persists between runs. The memory tool provides this on the API. In the SDK, sessions can be resumed by session ID, restoring full prior context — files read, analysis performed, actions taken — and can also be forked to branch into a different approach without disturbing the original.

A design heuristic: **the conversation should be the model’s working memory, not your database.** If losing the transcript would lose work, the architecture is wrong.

## Human-in-the-loop checkpoints

Autonomy is a spectrum, and the useful question is not “should a human approve” but “which actions are expensive to undo.”

Three placements for a checkpoint:

**Before an irreversible tool call.** The highest-value checkpoint by a wide margin. Issuing a refund, sending an email, deleting a record, merging a branch, running a destructive migration. The implementation is a gate in your dispatch function: reversible tools execute, irreversible tools return a pending state and the loop suspends.

**At a plan boundary.** Let the agent propose a plan, have a human approve it, then let the agent execute. This front-loads the review into a single legible decision rather than dozens of approval prompts, and it is why plan-then-execute modes exist.

**On an escalation signal.** When the agent reports low confidence, hits a budget cap, or encounters an error it cannot resolve, hand off to a human rather than letting it keep trying.

In a hand-rolled loop, the natural implementation classifies tools and suspends the run:

``` {.sourceCode .python}
IRREVERSIBLE = {"issue_refund", "send_email", "delete_record"}

def dispatch_with_gate(name, tool_input, approvals):
    if name in IRREVERSIBLE:
        key = approval_key(name, tool_input)
        decision = approvals.get(key)
        if decision is None:
            raise AwaitingApproval(key, name, tool_input)
        if decision == "denied":
            # Report as a tool error so the model can adapt.
            return "Denied by human reviewer. Do not retry this action."
    return dispatch(name, tool_input)
```

Note the denial path: a rejected tool call is reported back as a result, not raised. Claude will typically try a different approach or explain that it cannot proceed, which is usually what you want.

The Agent SDK provides this as permission modes and a `canUseTool` callback: `default` routes calls needing approval to your callback, `acceptEdits` auto-approves file edits and common filesystem commands while still gating other shell commands, `plan` lets Claude explore and plan without editing source files, `dontAsk` denies anything that would prompt, `auto` uses a model classifier to review actions like shell commands and network requests, and `bypassPermissions` runs everything allowed — appropriate only for CI and isolated containers. Hooks give a complementary mechanism: a `PreToolUse` hook can validate or block a call before it executes, and hooks run in your process rather than in the agent’s context window, so they cost no tokens.

The failure mode to avoid is approval fatigue. A system that asks about every file read trains its operators to approve reflexively, which is worse than no checkpoint, because it manufactures the appearance of oversight. Gate the irreversible operations and let the rest run.

## Failure modes

Four failures appear in essentially every agent system that runs long enough. Each has a structural fix, and in each case prompt adjustment is the weaker remedy.

### Loops that never terminate

The agent oscillates: search, get an unhelpful result, search again with a trivially different query, repeat. Or it re-reads the same file every few turns because it has lost track of having read it.

The fix is layered. A turn cap bounds the damage unconditionally. Detecting repetition — the same tool called with the same arguments three times — lets you intervene with a targeted message rather than just dying at the cap. And a task-state file the agent updates as it works gives it an external record of progress, which is the most robust defense because it addresses the cause rather than the symptom.

### Runaway cost

Distinct from non-termination, and sneakier. The agent terminates fine but each run costs ten times what you projected: large tool outputs accumulating in context, high effort levels on turns that do not need reasoning, a subagent tree that fanned out wider than expected, cache misses from a prompt prefix that changes per request.

The fixes are measurement and caps. Log the full `usage` object per turn, including cache fields and `output_tokens_details.thinking_tokens`. Set a cost cap, with headroom for the overshoot described earlier. Cap subagent depth and concurrency. Truncate large tool outputs at the dispatch boundary — a tool that can return a 400K-token file read should return the first N tokens plus a note, with pagination available, rather than the whole thing. And check whether your cache is actually hitting: a per-request timestamp placed before a cache breakpoint silently defeats caching for the entire run.

### A tool that errors repeatedly

A database is down, a credential expired, a tool schema is wrong. Claude receives `is_error` results and keeps trying, sometimes with creative variations that make it worse.

Track consecutive failures and terminate the run when a threshold is crossed. The loop above does the simplest version, counting consecutive turns in which any tool failed; a counter per tool name is finer-grained and does not end the run because two different tools failed once each. The reasoning: if a tool has failed three times in a row, the problem is the environment, not the model’s approach, and further turns are pure cost. Distinguish retryable failures (timeout, rate limit) from permanent ones (authentication, schema validation) and do not feed permanent failures back as though retry might help — a 401 should end the run, not generate five more attempts.

### Hallucinated tool arguments

The model invents an order ID, passes a string where an integer belongs, references a file path that does not exist, or supplies an enum value outside the allowed set. This is the failure most often misdiagnosed as a model quality problem when it is a schema quality problem.

The structural fixes, in order of effectiveness:

1.  **Validate every tool input against its schema in your dispatch layer**, before executing. Never trust `block.input` to conform just because you declared a schema. Return validation failures as `is_error` results with the specific problem named; Claude corrects well when told exactly what was wrong.
2.  **Write schemas that constrain.** Use `enum` for closed sets, `minimum`/`maximum` for numbers, `required` honestly. (Numeric bounds are allowed on non-strict tools and documented to the model; strict mode does not support them, so your dispatch-layer validation is what enforces them.) A parameter described as “the status” invites invention; one declared as `enum: ["open", "shipped", "cancelled"]` does not.
3.  **Describe tools precisely, including limits and side effects.** The `description` is the model’s only documentation. “Search orders by customer email. Returns at most 20 matches. Requires a full email address, not a partial string” prevents a class of errors that no amount of system prompting will.
4.  **Never execute a tool call from a response with `stop_reason: "max_tokens"`.** Truncated `input` JSON can parse as valid-looking partial arguments.

## The Claude Agent SDK

The Agent SDK packages the agent loop that powers Claude Code as a library for Python and TypeScript. Both SDKs bundle a native Claude Code binary, so most installations need no separate Claude Code install. For other languages, you can drive the same loop by running the CLI as a subprocess with `-p` and `--output-format json`.

It sits in a spectrum of options worth being clear about:

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------
  Option                          Who runs it             What you get
  ------------------------------- ----------------------- ---------------------------------------------------------------------------------------------------------
  Client SDK, hand-rolled loop    You                     Full control; you write everything in this chapter

  Client SDK tool runner (beta)   You                     Loop automation with `max_iterations`, schema generation from type hints, automatic `is_error` wrapping

  Agent SDK                       You                     Claude Code’s loop, built-in tools, permissions, hooks, subagents, sessions, compaction

  Managed Agents                  Anthropic               Hosted harness with sessions in a managed or self-hosted sandbox
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------

What the Agent SDK provides over a hand-rolled loop:

-   **Built-in tools**: `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `WebSearch`, `WebFetch`, `ToolSearch` for on-demand tool loading, and orchestration tools including `Agent`, `Skill`, and `AskUserQuestion`. These are implemented, hardened, and maintained. Reimplementing a correct file-edit tool is a week of work you can skip.
-   **Permission system**: the modes described earlier, plus `allowed_tools` and `disallowed_tools` lists and scoped rules like `"Bash(npm *)"`, evaluated in a documented order.
-   **Hooks**: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStart`/`SubagentStop`, `PreCompact`. They run in your process, not in the context window, and can short-circuit the loop.
-   **Subagents**: defined programmatically via `agents`, or as markdown files in `.claude/agents/`, with per-subagent model, effort, tool set, `maxTurns`, and memory source.
-   **Automatic compaction**, with a `compact_boundary` system message emitted when it happens and a `PreCompact` hook if you need to archive the transcript first.
-   **Sessions**: capture `session_id` from the result and resume with full prior context, or fork to branch.
-   **Budget enforcement**: `max_turns` (counting tool-use turns) and `max_budget_usd`, with the cap covering subagent spend.
-   **Structured results**: a `ResultMessage` whose `subtype` distinguishes `success`, `error_max_turns`, `error_max_budget_usd`, `error_during_execution`, and `error_max_structured_output_retries`, and which carries `total_cost_usd`, `usage`, `num_turns`, and `session_id` even on error paths.

``` {.sourceCode .python}
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def fix_failing_tests():
    async for message in query(
        prompt="Find and fix the bug causing test failures in the auth module",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "Glob", "Grep"],
            setting_sources=["project"],   # load CLAUDE.md, skills, hooks
            max_turns=30,
            max_budget_usd=2.0,
            effort="high",
        ),
    ):
        if isinstance(message, ResultMessage):
            if message.subtype == "success":
                print(message.result)
            elif message.subtype == "error_max_turns":
                print(f"Turn limit hit. Resume session {message.session_id}.")
            else:
                print(f"Stopped: {message.subtype}")
            if message.total_cost_usd is not None:
                print(f"Cost: ${message.total_cost_usd:.4f}")


asyncio.run(fix_failing_tests())
```

One behavioral detail that catches people: when a single-shot `query()` run ends on a limit or error (such as `error_max_turns`), it yields the final result message and *then* raises, so wrap the loop in a try block if your code needs to continue past a limit. A streaming-input session stays alive instead.

When should you not use it? When your tools are entirely your own domain operations and you need none of the built-in file and shell tooling, the Agent SDK’s surface is weight you are not using — the client SDK’s tool runner may fit better. When you need control flow the SDK does not express, a hand-rolled loop is the honest choice. And when the task is actually a workflow, none of this applies: write the code path.

The argument for the Agent SDK is not that the loop is hard to write. The loop is about forty lines, and you have seen them. The argument is that *everything around* the loop — permissions, compaction, subagent isolation, hooks, session resumption, cost accounting across an agent tree — is a substantial system, and it is the part that determines whether your agent is safe to run unattended.

## Practice Questions

**Q7.1** A team is building a feature that takes a customer support email, classifies it into one of six categories, and then runs a category-specific extraction prompt. An engineer proposes implementing it as an agent with a classification tool and six extraction tools, letting Claude decide which to call. What is the strongest objection?

A. The steps are fully known in advance, so a routing workflow gives the same result with predictable cost, latency, and testability B. The model cannot reliably choose between six similar tools, so classification accuracy will drop C. Agents cannot call more than one tool per turn, so the pipeline would need six round trips D. Tool definitions for six extractors would exceed the context window

**Q7.2** Your agent loop occasionally executes a tool call with malformed arguments that corrupt a record. Reviewing transcripts, you find that in each case the preceding response had `stop_reason: "max_tokens"`. What is the correct fix?

A. Lower the effort level so the model produces shorter responses B. Validate arguments against the tool schema and retry with corrected values C. Treat `max_tokens` as a terminal condition and never execute a trailing `tool_use` block from a truncated response D. Set `disable_parallel_tool_use` so only one tool call can be truncated per turn

**Q7.3** An agent run shows 11 turns, well under its 30-turn cap, but costs roughly 15x the median run. Token totals are enormous. Which diagnosis best fits?

A. A tool returned a very large output early in the run, and that content was re-sent as input on every subsequent turn B. The turn cap is set too high, allowing excessive round trips C. The wall-clock deadline was too generous, letting the run accumulate cost D. Thinking tokens are billed at a premium rate on agentic turns

**Q7.4** You delegate codebase exploration to a subagent. It consistently produces worse answers than the same work done inline in the main conversation, and often re-reads files the parent had already examined. What is the most likely cause?

A. The parent’s conversation history and tool results do not cross into the subagent, so anything it needs must be written into the prompt it receives B. Subagents run on a cheaper model by default, reducing quality C. Subagent context is compacted more aggressively than the parent’s D. Subagents cannot use read tools unless explicitly granted the Agent tool

**Q7.5** A long-running agent must remember a specific API version constraint stated in the opening user message. Partway through the run, it begins making calls that violate the constraint. Compaction fired earlier in the run. What is the best structural fix?

A. Raise the compaction threshold so compaction never fires B. Repeat the constraint in every tool description C. Put the constraint somewhere re-injected on every request, such as a CLAUDE.md, rather than only in the initial prompt D. Switch from compaction to `clear_tool_uses_20250919`, which never removes user messages

**Q7.6** Your agent calls a payments tool that has been returning authentication errors since a credential expired. The agent receives `is_error` results and keeps retrying with variations, burning the full turn budget on every request. Which change most directly addresses this?

A. Track consecutive failures per tool and terminate the run once a threshold is crossed, distinguishing permanent failures from retryable ones B. Remove `is_error` from the tool result so the model does not see the failure C. Lower the turn cap so the damage per run is smaller D. Move the payments tool behind a human approval checkpoint

**Q7.7** You are designing human oversight for an agent that can read files, run tests, edit code, and open pull requests. Which checkpoint placement best balances safety against approval fatigue?

A. Require approval for every tool call so nothing happens unreviewed B. Require approval for the first call of each tool type, then auto-approve that type C. Require approval after the run completes, before results are shown D. Require approval only before irreversible actions such as opening the pull request, and let reads, tests, and local edits run

**Q7.8** A code-review system runs three independent checks on each diff: style, security, and test coverage. Currently they run sequentially and p95 latency is unacceptable. Which pattern fits?

A. Prompt chaining, so each check builds on the previous one’s findings B. Parallelization by sectioning, running the three checks concurrently and aggregating C. Evaluator-optimizer, with one model generating findings and another critiquing them D. Orchestrator-workers, letting a central model decide which checks to run

**Q7.9** A task requires applying a consistent refactor across files, but you cannot know in advance which files need changing or how many there will be. Which pattern fits best?

A. Prompt chaining with one step per file B. Routing, classifying each file and dispatching to a handler C. Orchestrator-workers, where a central model discovers the work and delegates pieces D. Parallelization by voting, running the refactor several times and taking the consensus

**Q7.10** An agent you deployed with `max_budget_usd=10` produced a run that cost \$11.40. Your finance team asks whether the cap is broken. What is the correct explanation?

A. The cap applies only to the main agent and excludes subagent spend B. Cache read tokens are excluded from the cap calculation C. The cap is advisory and only triggers a warning D. Spend is compared against the cap after each response arrives, so the response that crosses the cap still completes and bills, and in-flight subagents can add more before stopping

**Q7.11** You are configuring `clear_tool_uses_20250919` for an agent whose cache hit rate matters. An engineer sets a low trigger and omits `clear_at_least`. What problem should you anticipate?

A. Clearing will remove the system prompt, which is never cacheable B. Frequent small clears will repeatedly invalidate the cache prefix without freeing much context, so you pay cache writes for little benefit C. The agent will lose access to all tool results, including recent ones D. Context editing requires `clear_at_least` and the request will be rejected

**Q7.12** Your agent repeatedly calls `search_documents` with nearly identical queries, getting the same results, until it hits the turn cap. The cap prevents cost disaster but the task never completes. Beyond the cap, which addition most directly attacks the cause?

A. Increase the turn cap so the agent has more attempts to find a path B. Raise the effort level so the model reasons more carefully about each query C. Have the agent maintain a task-state record of what it has tried and found, outside the conversation, and detect repeated identical tool calls D. Switch to a larger model, which oscillates less

**Q7.13** A team is choosing between the client SDK’s beta tool runner and the Claude Agent SDK for an agent that operates on a local repository: reading files, editing them, and running the test suite. Which consideration most favors the Agent SDK?

A. The tool runner cannot execute more than one tool per turn B. The Agent SDK is the only option that can call the Claude API with tools C. The tool runner does not support bounding the loop D. The Agent SDK provides hardened built-in file and shell tools plus a permission system, rather than requiring you to implement and secure them

**Q7.14** You define a tool with a parameter described as “the order status” and no further constraints. The agent frequently passes values like `"pending_review"` that your system does not recognize, and the calls fail. What is the most effective fix?

A. Add instructions to the system prompt listing the valid statuses B. Declare the parameter as an `enum` with the allowed values in the tool’s input schema, and validate inputs in your dispatch layer C. Raise the effort level so the model reasons more carefully about parameter values D. Catch the failures and retry the same call, since the model usually self-corrects

**Q7.15** You are reviewing a design for an autonomous agent that will run unattended on a schedule against production infrastructure. Which combination of controls best matches the guidance in this chapter?

A. A high turn cap, a model classifier reviewing shell commands, and transcript logging B. Turn, token, and wall-clock caps; per-tool consecutive-failure termination; schema validation in dispatch; approval gates on irreversible actions; task state written outside the conversation; and per-turn usage logging C. A generous cost cap and `bypassPermissions`, since no human is present to approve anything D. Compaction with a low threshold and subagents for every subtask, to keep context small and costs predictable
