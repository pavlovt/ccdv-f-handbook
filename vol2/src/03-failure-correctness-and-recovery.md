# Failure, Correctness, and Recovery

There are two kinds of integration engineer. The first has a `try/except` around `messages.create` that logs and returns `None`. The second has a taxonomy, a retry budget, an idempotency design, and four post-mortems in a wiki. This chapter is about becoming the second kind.

Volume I listed the error codes and the stop reasons; we will not list them again. What Volume I could not teach, treating each feature in isolation, is that in production the hard part is never knowing what `529` means — it is working out, from one ambiguous symptom at 03:00, which of four layers is broken, then recovering without making it worse.

## 2.1 A taxonomy by layer

Every failure in a Claude integration lives in exactly one of four layers, and each has a different detection signal, retry policy and owner.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Layer                   Example                                                                                                                Retryable?                          Owner
  ----------------------- ---------------------------------------------------------------------------------------------------------------------- ----------------------------------- ------------------------------------
  **Transport**           Connection reset, TLS failure, read timeout, proxy 502, DNS failure                                                    Yes, blindly, with backoff          Your infrastructure or the network

  **API**                 400, 401, 403, 404, 409, 413, 429, 500, 504, 529                                                                       Depends entirely on the code        Split between you and the platform

  **Model output**        `stop_reason: max_tokens`, `refusal`, `model_context_window_exceeded`, schema-invalid JSON, hallucinated field value   Sometimes, with a changed request   You

  **Application logic**   Correct response, wrong downstream handling; mismatched `tool_result`; lost conversation state                         No — retrying reproduces it         You
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The subtlety that makes this hard is that **layers 3 and 4 both return HTTP 200**. A refusal is a successful response; so is a truncated answer; so is a response that fills the context window. Monitoring that equates “200” with “healthy” is blind to the entire lower half of the table, which is where the expensive incidents live.

### Telling them apart from one symptom

The symptom you get is usually one of five.

**Symptom: “the API is returning errors.”** Read the error `type`, not the message string: types are stable and extensible, messages are prose and will change under you. The SDKs raise typed exceptions for exactly this reason, caught most-specific-first. If the error body is absent entirely and there is no `request_id`, you never reached the API — that is transport, and the proxy logs are the next stop.

**Symptom: “responses are truncated.”** Three distinct causes, distinguished by one field:

  ------------------------------------------------------------------------------------------------------------------------------------
  Observation                                      Cause                   Fix
  ------------------------------------------------ ----------------------- -----------------------------------------------------------
  `stop_reason: "max_tokens"`                      Your ceiling            Raise `max_tokens`, or continue in a new request

  `stop_reason: "model_context_window_exceeded"`   The model’s ceiling     Compact or trim history; raising `max_tokens` cannot help

  Stream ended with no `message_stop`              Transport               Reconnect and resume
  ------------------------------------------------------------------------------------------------------------------------------------

The second row is the one people misdiagnose. `model_context_window_exceeded` is not an HTTP error — it arrives on a 200 with a normal `usage` block. On Claude 4.5 and newer, a request whose input plus `max_tokens` exceeds the window is *accepted*, and you learn the window was binding only when generation runs into it. If input *alone* exceeds the window you get a 400 `invalid_request_error`, on every model. So: 400 means the prompt was too long before generation started, and the stop reason means generation ran out of room. Raising `max_tokens` addresses the first and is irrelevant to the second.

**Symptom: “it returned text instead of JSON.”** With `output_config.format` set, schema compliance is guaranteed in most cases, which makes the exceptions worth memorising, because each has a different response:

-   `stop_reason: "refusal"` — HTTP 200, you are billed, and the refusal text may not conform to the schema at all. Check `stop_details` for the policy category. Asking for chain-of-thought inside a structured response can trigger a `reasoning_extraction` refusal specifically; ask for a short explanation field instead.
-   `stop_reason: "max_tokens"` — the JSON is simply cut off. Retry with a higher ceiling.
-   Enum and `const` casing drift — values differ only in capitalisation, with no error and no special stop reason. Compare case-insensitively, and never define enum members that differ only by case.
-   HTTP 400 with “Schema is too complex for compilation”, or a 400 naming an unsupported schema feature — a deployment-time bug, not a runtime one. A 180-second compilation timeout also applies.

**Symptom: “it worked yesterday.”** Check model ID first. Routers, A/B splits and fallback paths silently change models, and a model change invalidates the prompt cache, changes default effort, and can change which parameters are legal at all. Opus 5.5 defaults to `medium` effort where Opus 5 defaulted to `high`, so a model bump alone makes responses shallower with no code change.

**Symptom: “quality dropped but nothing is failing.”** This is layer 3 with no error signal at all. Section 2.7 is about detecting it.

## 2.2 A retry policy that is actually correct

Most retry code is wrong in one of three ways: it retries what cannot succeed; it retries correctly but without a budget, so a partial outage becomes a self-inflicted one; or it retries a non-idempotent operation and produces duplicates.

### Which codes are retryable

  -----------------------------------------------------------------------------------------------------------------------------------------
  Status            Type                                 Retry?                              Backoff
  ----------------- ------------------------------------ ----------------------------------- ----------------------------------------------
  400               `invalid_request_error`              No                                  —

  401               `authentication_error`               No                                  —

  402               `billing_error`                      No                                  —

  403               `permission_error`                   No                                  —

  404               `not_found_error`                    No                                  —

  409               `conflict_error`                     Only after resolving the conflict   —

  413               `request_too_large`                  No — shrink the request             —

  429               `rate_limit_error`                   Yes, *unless* spend-cap             Honour `retry-after`; otherwise bucket-aware

  500               `api_error`                          Yes                                 Exponential with jitter

  504               `timeout_error`                      Yes, but reconsider the mode        Exponential; prefer streaming or batch

  529               `overloaded_error`                   Yes                                 Exponential with jitter, longer base

  —                 Connection error / reset / timeout   Yes                                 Exponential with jitter
  -----------------------------------------------------------------------------------------------------------------------------------------

The one trap there is 429 with `error.details.error_code == "enforced_spend_limit_reached"`. It carries the retryable status code and the retryable error type, no `retry-after`, and fails every time until the month rolls over or the tier is raised. Branch on that field *before* entering backoff; the SDK’s own retries will not.

### Why 429 and 529 need different backoff

They are different physics.

A **429** means *you* exceeded a quota whose refill rate is known and often stated in `retry-after`. The optimal wait is exactly the stated interval: less is guaranteed to fail, more wastes capacity you are paying for. There is no contention with other clients, so jitter is nearly pointless — the bucket is yours. What you need instead is rate *adaptation*: repeated 429s mean your target rate is wrong, and a correct client lowers it rather than retrying into the wall at the same speed.

A **529** means the platform is overloaded across all users. Every client hears this simultaneously, and clients retrying on the same schedule synchronise into a thundering herd that keeps the overload alive. Here jitter is essential, the base delay should be longer because recovery is measured in seconds, and the correct behaviour is to *shed load* — fail fast on low-priority work, open a breaker — rather than queue it.

As policy:

                         429 (rate)                529 (overload)
  ---------------------- ------------------------- --------------------------
  Honour `retry-after`   Always, exactly           Rarely present
  Base delay             From header, else \~1 s   2–4 s
  Jitter                 Small (\~10–25%)          Full jitter, essential
  Max attempts           3–4                       2–3
  Side effect            Lower the target rate     Trip the circuit breaker
  Caller-visible         Queue, degrade            Fail fast, shed

### Jitter strategy

Three options, in increasing order of correctness for the 529 case:

-   **No jitter**: `delay = base * 2**n`. Synchronises clients. Never use for shared-capacity failures.
-   **Equal jitter**: `delay = base * 2**n * (0.5 + random()/2)`. Keeps a floor under the delay. Reasonable default.
-   **Full jitter**: `delay = random() * base * 2**n`. Best decorrelation, lowest expected delay for the same ceiling.

Full jitter for 529 and connection errors; equal jitter for 500; `retry-after` plus small jitter for 429.

### Retry budgets

A retry multiplies load exactly when load is the problem. The defence is a *budget*: a cap on retries as a fraction of successful traffic, measured over a window and shared process-wide. Ten per cent is a common start — if more than one request in ten is a retry, something systemic is wrong and more retries make it worse, so the budget exhausts and retries stop until it refills.

The official SDKs retry twice by default, honouring `retry-after`, configurable through `max_retries`. If you build your own policy layer, **turn the SDK’s retries off** or you get the product of the two: three of your attempts times three of theirs is nine requests for one logical call, and your budget accounting is wrong by a factor of three.

``` {.sourceCode .python}
import random
import threading
import time
from dataclasses import dataclass

import anthropic

PERMANENT = {
    "invalid_request_error", "authentication_error", "billing_error",
    "permission_error", "not_found_error", "request_too_large",
}


class RetryBudget:
    """Token bucket over retries, expressed as a fraction of successes."""

    def __init__(self, ratio: float = 0.1, min_per_s: float = 1.0, burst: float = 20.0):
        self._lock = threading.Lock()
        self.ratio, self.min_per_s, self.burst = ratio, min_per_s, burst
        self._tokens = burst
        self._last = time.monotonic()
        self._success_rate = 0.0

    def _refill(self) -> None:
        now = time.monotonic()
        allowance = max(self.min_per_s, self._success_rate * self.ratio)
        self._tokens = min(self.burst, self._tokens + (now - self._last) * allowance)
        self._last = now

    def record_success(self) -> None:
        with self._lock:
            self._success_rate = 0.95 * self._success_rate + 0.05 * 10.0

    def try_withdraw(self) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    delay_s: float = 0.0
    reason: str = ""


def classify(exc: BaseException, attempt: int, budget: RetryBudget) -> RetryDecision:
    if isinstance(exc, anthropic.APIStatusError):
        body = exc.body if isinstance(exc.body, dict) else {}
        err = body.get("error", {}) or {}
        etype = err.get("type", "api_error")
        details = err.get("details", {}) or {}

        if details.get("error_code") == "enforced_spend_limit_reached":
            return RetryDecision(False, reason="spend_cap")
        if etype in PERMANENT:
            return RetryDecision(False, reason=etype)

        if exc.status_code == 429:
            if attempt >= 4 or not budget.try_withdraw():
                return RetryDecision(False, reason="budget_or_attempts")
            header = (exc.response.headers or {}).get("retry-after")
            base = float(header) if header else 1.0 * (2 ** (attempt - 1))
            return RetryDecision(True, base + random.uniform(0, 0.25 * base), "rate_limit")

        if exc.status_code == 529:
            if attempt >= 3 or not budget.try_withdraw():
                return RetryDecision(False, reason="budget_or_attempts")
            # Full jitter: decorrelate from every other client seeing 529.
            return RetryDecision(True, random.uniform(0, 3.0 * (2 ** (attempt - 1))), "overloaded")

        if exc.status_code in (500, 504):
            if attempt >= 3 or not budget.try_withdraw():
                return RetryDecision(False, reason="budget_or_attempts")
            base = 1.0 * (2 ** (attempt - 1))
            return RetryDecision(True, base * (0.5 + random.random() / 2), "server_error")

        return RetryDecision(False, reason=f"status_{exc.status_code}")

    if isinstance(exc, (anthropic.APIConnectionError, TimeoutError)):
        if attempt >= 3 or not budget.try_withdraw():
            return RetryDecision(False, reason="budget_or_attempts")
        return RetryDecision(True, random.uniform(0, 2.0 * (2 ** (attempt - 1))), "transport")

    return RetryDecision(False, reason="unknown")
```

### Why retries without idempotency are dangerous

The Messages API has **no idempotency key**. There is no request header you can set that makes the platform recognise a retry as a duplicate and return the original response. This is the single most consequential fact in this chapter, and it has a nasty corollary: a retry after a *timeout* may duplicate work that actually succeeded.

Consider the sequence. You send a request. The model generates a full response. The connection drops before the body reaches you. You see a read timeout, classify it as transport, and retry. The platform has now generated two responses, billed both, and — if tool use executed, or your handler writes on success — performed the work twice.

For a pure completion that is a cost problem. For anything with side effects it is a correctness problem. And it is not rare: timeouts near the ten-minute non-streaming ceiling, or on long generations without streaming, are exactly the conditions under which the response most likely did complete.

## 2.3 Designing idempotency around the absence of a key

Since the platform will not deduplicate for you, you must. Three workable designs.

**Design A — Idempotent sink.** Make the *consumer* of the response idempotent rather than the call: derive a deterministic key from the request and have the write path upsert on it, so two identical responses collapse into one row. The cheapest design and the right default. It prevents double *effect*, not double *billing*.

**Design B — Intent ledger.** Before calling, write an attempt row with a deterministic operation ID and status `in_flight`; on success transition it to `complete` with the response and request ID. A retry reads the ledger first and, finding a `complete` row, returns the stored response without calling. This prevents double billing across processes and crashes and gives an audit trail keyed by request ID, at the cost of a write before every call.

**Design C — Deduplicate by effect.** For tool-using agents, make each *tool* idempotent rather than the conversation. Most real APIs do support idempotency keys, so a replayed tool call is harmless. This is the only design that survives mid-loop retries.

Most production systems need A plus B; agents need all three.

``` {.sourceCode .python}
import hashlib
import json
from typing import Protocol


class Ledger(Protocol):
    def get(self, op_id: str) -> dict | None: ...
    def put_in_flight(self, op_id: str, meta: dict) -> bool: ...
    def complete(self, op_id: str, payload: dict) -> None: ...


def operation_id(*, tenant: str, feature: str, model: str, request_body: dict) -> str:
    """Deterministic across retries and processes. Any field that changes
    between a call and its retry must be excluded, or dedup silently breaks."""
    canonical = json.dumps(request_body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{tenant}|{feature}|{model}|{canonical}".encode()).hexdigest()
    return digest[:40]


def call_once(client, ledger: Ledger, *, tenant: str, feature: str,
              model: str, body: dict, budget: RetryBudget) -> dict:
    op_id = operation_id(tenant=tenant, feature=feature, model=model, request_body=body)

    existing = ledger.get(op_id)
    if existing and existing["status"] == "complete":
        return existing["payload"]          # no API call: dedup achieved

    if not ledger.put_in_flight(op_id, {"model": model, "feature": feature}):
        # Another worker owns this operation. Wait for it rather than racing.
        for _ in range(60):
            time.sleep(0.5)
            row = ledger.get(op_id)
            if row and row["status"] == "complete":
                return row["payload"]
        raise TimeoutError(f"operation {op_id} still in flight")

    attempt = 0
    while True:
        attempt += 1
        try:
            msg = client.messages.create(model=model, **body)
            payload = {
                "request_id": msg._request_id,
                "stop_reason": msg.stop_reason,
                "content": [b.model_dump() for b in msg.content],
                "usage": msg.usage.model_dump(),
            }
            ledger.complete(op_id, payload)
            budget.record_success()
            return payload
        except BaseException as exc:
            decision = classify(exc, attempt, budget)
            log.warning("llm_retry", extra={"op": op_id, "attempt": attempt,
                                            "retry": decision.retry,
                                            "reason": decision.reason})
            if not decision.retry:
                raise
            time.sleep(decision.delay_s)
```

The comment on `operation_id` is the part people get wrong. If any part of the body varies between the original call and its retry — a timestamp in the system prompt, a fresh UUID, a reordered tool list — the operation ID differs and deduplication silently does nothing. That is the same discipline that makes prompt caching work: the prefix stability you need for cache hits is the prefix stability you need for idempotency.

## 2.4 `max_tokens` and `model_context_window_exceeded` as distinct recoveries

Both truncate. The recoveries are opposites.

**`stop_reason: "max_tokens"`** means your ceiling bound the response. Three recoveries, in order of preference:

1.  Raise `max_tokens` and resend. Costs nothing in rate-limit terms, since OTPM counts generated tokens only. Almost always right when output is well under the context window.
2.  Continue: append the partial assistant content and a user message asking it to resume, preserving work already paid for.
3.  Reduce scope: ask for less, or lower effort so the model is terser.

One special case has a hard rule: if the final content block is an *incomplete* `tool_use`, you cannot continue and cannot use the partial arguments. Retry with a higher `max_tokens`. Partially-streamed `input_json_delta` is not recoverable JSON.

**`stop_reason: "model_context_window_exceeded"`** means the *window* bound the response, so raising `max_tokens` is useless — the ceiling is not yours. Recoveries:

1.  Compact. Server-side compaction summarises earlier turns so the conversation continues past the limit, and is the intended strategy for long agentic runs.
2.  Context editing: clear old tool results, or earlier thinking blocks.
3.  Trim history yourself — but editing earlier messages destroys the prompt cache and, on recent models, the validity of replayed thinking blocks, which can turn a recoverable truncation into a 400.
4.  Treat the response as truncated and say so.

A dispatcher that gets this right:

``` {.sourceCode .python}
MAX_CONTINUATIONS = 3


def resolve(client, model: str, body: dict, msg) -> tuple[str, dict]:
    """Returns (action, next_body). Actions: 'done', 'retry', 'compact', 'escalate'."""
    reason = msg.stop_reason

    if reason in ("end_turn", "stop_sequence"):
        if not msg.content:
            # Documented edge case: do not resend an empty assistant turn.
            nxt = dict(body)
            nxt["messages"] = body["messages"] + [{"role": "user", "content": "Please continue"}]
            return "retry", nxt
        return "done", body

    if reason == "max_tokens":
        last = msg.content[-1] if msg.content else None
        if last is not None and getattr(last, "type", None) == "tool_use":
            # Incomplete tool call: the arguments are unusable. Only a bigger
            # ceiling helps; never attempt to patch partial JSON.
            nxt = dict(body)
            nxt["max_tokens"] = min(128_000, body["max_tokens"] * 4)
            return "retry", nxt
        nxt = dict(body)
        nxt["messages"] = body["messages"] + [
            {"role": "assistant", "content": msg.content},
            {"role": "user", "content": "Please continue from where you left off."},
        ]
        return "retry", nxt

    if reason == "model_context_window_exceeded":
        # Raising max_tokens cannot help: the window, not the ceiling, bound us.
        return "compact", body

    if reason == "refusal":
        category = getattr(msg, "stop_details", None)
        log.warning("refusal", extra={"category": getattr(category, "type", None),
                                      "request_id": msg._request_id})
        return "escalate", body      # retry on a fallback model, or rephrase

    if reason == "pause_turn":
        nxt = dict(body)
        nxt["messages"] = body["messages"] + [{"role": "assistant", "content": msg.content}]
        return "retry", nxt          # resend assistant content unchanged

    if reason == "tool_use":
        return "done", body          # the tool loop, not this function, owns it

    log.error("unknown_stop_reason", extra={"stop_reason": reason})
    return "escalate", body
```

Two details. `pause_turn` arrives when a server-tool loop hits its iteration limit (ten by default), and the recovery is to send the assistant content back *unchanged* — but cap the continuations, or a pathological loop runs forever at full price. And `refusal` is a billed 200; on most current models the documented recovery is a retry on a different model, though Haiku 5.5 has no server-side fallback, so that retry must live in your client.

## 2.5 Validating structured output: repair, retry, or escalate

Even with a schema-constrained format, boundary validation is not optional — the documented exceptions exist, and *schema-valid* is not *semantically correct*. A response can satisfy every constraint and still assert that an invoice total is negative. So validate in two stages and route failures differently.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Stage             Checks                                                       Typical failure                                        Action
  ----------------- ------------------------------------------------------------ ------------------------------------------------------ ---------------------------------------------------
  **Structural**    Parses; matches schema                                       Truncated JSON, refusal text                           Retry (higher ceiling) or escalate

  **Semantic**      Business invariants, cross-field consistency, value ranges   Negative total, date out of range, enum casing drift   Repair if deterministic, else retry with feedback
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The choice comes down to one question: *is the fix deterministic from information you already have?*

-   **Repair** when the transformation is total and unambiguous: case-normalising an enum whose intended value is unique under case folding, trimming whitespace, coercing `"42"` to `42` where the schema says integer. Safe because there is exactly one correct answer and you can compute it.
-   **Retry with feedback** when the content is wrong but the request is sound. Send the invalid output back naming the failed invariant. One retry; a second rarely helps and a third never does.
-   **Escalate** on a refusal, after two failed retries, or whenever repair would require *guessing*. Silent guessing is the worst outcome available, being indistinguishable from success downstream.

Note the constraints you cannot delegate. The supported JSON Schema subset excludes numeric bounds (`minimum`, `maximum`, `multipleOf`), string length bounds, recursive schemas, and `minItems` other than 0 or 1. So “amount must be positive” is *your* check every time. SDK helpers that validate responses do re-check your original constraints after the schema is simplified, which is a good reason to use them rather than hand-rolling.

``` {.sourceCode .python}
from typing import Callable

import pydantic


class Invalid(Exception):
    def __init__(self, stage: str, detail: str):
        super().__init__(f"{stage}: {detail}")
        self.stage, self.detail = stage, detail


def normalise_enums(obj, enums: dict[str, set[str]]):
    """Deterministic repair: case-fold enum values whose intent is unambiguous."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            allowed = enums.get(k)
            if allowed and isinstance(v, str):
                matches = [a for a in allowed if a.casefold() == v.casefold()]
                out[k] = matches[0] if len(matches) == 1 else v
            else:
                out[k] = normalise_enums(v, enums)
        return out
    if isinstance(obj, list):
        return [normalise_enums(v, enums) for v in obj]
    return obj


def extract_validated(client, model: str, body: dict, Model: type[pydantic.BaseModel],
                      *, enums: dict[str, set[str]],
                      invariants: Callable[[pydantic.BaseModel], None],
                      max_feedback_rounds: int = 1):
    messages = list(body["messages"])
    for round_ in range(max_feedback_rounds + 1):
        msg = client.messages.create(model=model, **{**body, "messages": messages})

        if msg.stop_reason == "refusal":
            raise Invalid("refusal", getattr(getattr(msg, "stop_details", None), "type", "unknown"))
        if msg.stop_reason == "max_tokens":
            body = {**body, "max_tokens": min(128_000, body["max_tokens"] * 4)}
            continue  # structural failure with a deterministic fix

        raw = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            data = normalise_enums(json.loads(raw), enums)
            parsed = Model.model_validate(data)
        except (json.JSONDecodeError, pydantic.ValidationError) as exc:
            if round_ >= max_feedback_rounds:
                raise Invalid("structural", str(exc)[:400]) from exc
            messages = messages + [
                {"role": "assistant", "content": msg.content},
                {"role": "user", "content": f"That output failed validation: {exc}. "
                                            f"Return only corrected JSON."},
            ]
            continue

        try:
            invariants(parsed)          # bounds, cross-field logic: not in the grammar
        except Invalid as exc:
            if round_ >= max_feedback_rounds:
                raise
            messages = messages + [
                {"role": "assistant", "content": msg.content},
                {"role": "user", "content": f"The values are inconsistent: {exc.detail}. "
                                            f"Re-extract and return corrected JSON."},
            ]
            continue

        return parsed, msg
    raise Invalid("exhausted", "validation did not converge")
```

One operational note: each feedback round appends to the conversation, so the retried request is strictly larger and more expensive, with a different prefix beyond the breakpoint. A request that needs one feedback round costs roughly 2.2× a single call: the original call, plus a retry about 20% larger because it carries the failed output and the feedback. If 20% of requests need a round, the average cost per request is about 1 + 0.2 × 1.2 = 1.24× the single-call cost. Budget for that, and alert if the rate climbs — a rising repair rate is usually a prompt or schema regression, not a model problem.

## 2.6 Streaming failure and resumption

Streaming moves failures past the HTTP status line, which breaks every assumption your retry layer makes. The sequence is `message_start`, then per block `content_block_start` / `content_block_delta`× / `content_block_stop`, then one or more `message_delta` carrying cumulative usage and the `stop_reason`, then `message_stop`. `ping` events may appear anywhere and must be ignored, and unknown event types may be added, so unrecognised types must be tolerated rather than raising. Three things can go wrong, and only the first looks like an error.

**An `error` event mid-stream.** You already got HTTP 200. The error arrives as `event: error` with a normal error body — `overloaded_error` is the documented example, which in a non-streaming request would have been a 529. Standard retry handling does not apply, because your HTTP layer saw success. Your stream consumer must inspect event types for `error`, not only the connection state.

**The connection dies silently.** No `error` event, no `message_stop` — the iterator simply ends. This is indistinguishable, at the transport layer, from a completed stream whose terminal event was lost. The only reliable detector is a state machine that knows it never saw `message_stop`.

**You never see `message_stop` but did see a `stop_reason`.** Partially complete. You have a usable answer and incomplete accounting.

Which means: **track completion explicitly.** A stream is complete if and only if you observed `message_stop`. Anything else is a partial, and partials need a resumption decision.

### Resumption

Resumption is model-generation dependent, and the generations differ in a way that matters.

-   **Claude 4.5 and earlier**: save the partial text and send a new request including it as the start of a new assistant message — prefill-style continuation.
-   **Claude 4.6 and later**: prefilling the assistant turn is rejected. Send a *user* message instead, along the lines of “your previous response was interrupted and ended with …; continue from where you left off.”

Since prefill returns a 400 on current models, only the second form is available on anything current — a good illustration of why a resumption helper must branch on model generation rather than assume one shape.

Hard limits: **tool use and thinking blocks cannot be partially recovered.** You can resume from the most recent complete text block and nothing else. A stream that dies mid-`tool_use` must be re-run from the last stable turn; reconstructing the JSON from accumulated `input_json_delta` fragments is a bug waiting to be shipped.

Decision table for a dead stream:

  -------------------------------------------------------------------------------------------------------------------------
  Observed                                  Tokens so far           Action
  ----------------------------------------- ----------------------- -------------------------------------------------------
  Died in `message_start`                   \~0                     Retry the whole request; nothing lost

  Died mid text block, \< 15% of expected   small                   Retry whole; resumption overhead exceeds the saving

  Died mid text block, \> 15% of expected   large                   Resume with a continuation user message

  Died mid `tool_use`                       any                     Re-run from the last stable turn; no partial recovery

  Died mid `thinking`                       any                     Re-run; thinking blocks are not partially recoverable

  `error` event received                    any                     Classify the error body; retry per its type

  Saw `stop_reason` but no `message_stop`   full                    Accept the content; mark usage as estimated
  -------------------------------------------------------------------------------------------------------------------------

``` {.sourceCode .python}
class StreamOutcome:
    def __init__(self):
        self.text_parts: list[str] = []
        self.saw_message_stop = False
        self.stop_reason: str | None = None
        self.error_type: str | None = None
        self.open_block_type: str | None = None
        self.usage: dict = {}
        self.request_id: str | None = None

    @property
    def complete(self) -> bool:
        return self.saw_message_stop and self.error_type is None

    @property
    def resumable(self) -> bool:
        # Only a text block can be resumed from. Tool and thinking blocks cannot.
        return (not self.complete
                and self.error_type is None
                and self.open_block_type in (None, "text")
                and sum(len(p) for p in self.text_parts) > 0)


def consume(client, model: str, body: dict) -> StreamOutcome:
    out = StreamOutcome()
    with client.messages.stream(model=model, **body) as stream:
        for event in stream:
            etype = getattr(event, "type", None)
            if etype == "ping":
                continue
            if etype == "error":
                out.error_type = getattr(getattr(event, "error", None), "type", "unknown")
                break
            if etype == "message_start":
                out.request_id = getattr(event.message, "_request_id", None)
            elif etype == "content_block_start":
                out.open_block_type = getattr(event.content_block, "type", None)
            elif etype == "content_block_delta":
                delta = event.delta
                if getattr(delta, "type", None) == "text_delta":
                    out.text_parts.append(delta.text)
            elif etype == "content_block_stop":
                out.open_block_type = None
            elif etype == "message_delta":
                out.stop_reason = getattr(event.delta, "stop_reason", None) or out.stop_reason
                if getattr(event, "usage", None):          # cumulative, not incremental
                    out.usage = event.usage.model_dump()
            elif etype == "message_stop":
                out.saw_message_stop = True
            # Unknown event types fall through deliberately.
    return out


def resume(client, model: str, body: dict, out: StreamOutcome) -> StreamOutcome:
    """Current models reject assistant prefill; continue with a user turn."""
    tail = "".join(out.text_parts)[-600:]
    nxt = dict(body)
    nxt["messages"] = body["messages"] + [{
        "role": "user",
        "content": ("Your previous response was interrupted. It ended with:\n\n"
                    f"{tail}\n\nContinue from exactly that point. Do not repeat it."),
    }]
    return consume(client, model, nxt)
```

Two accounting notes. Usage in `message_delta` is **cumulative**, so accumulating it additively double-counts; take the last value, do not sum. And after a resumption, the two halves are two billed requests — if your ledger records one logical operation, it must sum two usage objects or it will under-report.

## 2.7 Observability: what to log, trace, and alert on

The goal is that any incident can be reconstructed from telemetry alone, without a reproduction.

### Log

Per call, exactly once, on success and on failure:

  ----------------------------------------------------------------------------------------------------------------
  Field                                               Why
  --------------------------------------------------- ------------------------------------------------------------
  `request_id`                                        The only identifier Anthropic can look up. Non-negotiable.

  Model ID, as sent                                   Routers lie; record what left the process

  `stop_reason` and `stop_details`                    Layer-3 failures are invisible otherwise

  Full `usage` object, all five fields                Cost, cache efficiency, truncation signals

  HTTP status and error `type`                        Classification, never the message string

  Attempt number and retry reason                     Distinguishes one failing call from ten

  Latency, split into time-to-first-token and total   Two different problems

  Prefix fingerprint and tail fingerprint             Cache-miss forensics without storing content

  Tenant, feature, operation ID                       Attribution and dedup

  `anthropic-workspace-id`                            Which workspace was actually charged

  Rate-limit headers                                  Headroom at the moment of the call
  ----------------------------------------------------------------------------------------------------------------

And exactly one thing you must *not* log: content. No prompts, no completions, no tool arguments, no tool results. Fingerprints and counts give you the diagnostic power without the liability, and a log pipeline that has never contained user content cannot leak it.

### Trace

The platform emits OpenTelemetry spans in beta, and the attribute names are worth knowing because they let you join your traces to the platform’s view. The span for a message creation is `anthropic.messages.create`, and the attributes include `anthropic.request.id`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.request.max_tokens`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`, `gen_ai.usage.reasoning.output_tokens`, `gen_ai.response.time_to_first_chunk`, `anthropic.message.stop_reason`, `error.type`, `http.response.status_code`, and `http.request.resend_count`.

Two of those are quietly excellent. `http.request.resend_count` is the SDK’s own retry counter, which lets you detect double-retry layering — if your attempt counter says 1 and the resend count says 3, the SDK is retrying underneath you. And `gen_ai.usage.reasoning.output_tokens` separates thinking from visible output, which is the only way to see an effort regression in the cost data.

Span structure that works: one span per logical operation, one child span per attempt, one child per tool invocation. Attempts as children of the operation, not siblings — otherwise you cannot tell four separate failures from one call retried four times, which is precisely the distinction an incident turns on.

### Alert

  ------------------------------------------------------------------------------------------------------------------
  Alert                                  Threshold shape             Catches
  -------------------------------------- --------------------------- -----------------------------------------------
  Error rate by `type`                   Per-type, not aggregate     A 400 spike hidden inside a healthy aggregate

  Spend-cap 429 count                    Any non-zero                Billing cliff; retries cannot help

  Cache hit rate by prefix layer         10-point drop               Cost and ITPM capacity regression

  `cache_miss_reason` by type            Any `*_changed` appearing   Prefix instability, named precisely

  `stop_reason: max_tokens` rate         2× trailing median          Silent truncation

  `model_context_window_exceeded` rate   Any sustained non-zero      Compaction not keeping up

  Refusal rate                           2× trailing median          Prompt regression or input shift

  Validation failure rate                1.5× trailing median        Schema or prompt drift

  Time-to-first-token p95                Absolute SLO                Streaming UX

  Retry budget exhaustion                Any occurrence              Systemic failure already in progress

  Model ID distribution                  Any unexpected value        Router or fallback misconfiguration
  ------------------------------------------------------------------------------------------------------------------

The last row is the one people add after their first incident rather than before it.

## 2.8 Detecting silent quality regressions

Hard errors announce themselves. A model that starts producing plausible, well-formed, subtly worse answers announces nothing, and it is the failure mode most likely to reach your customers before it reaches your dashboard.

Five signals, in increasing order of cost to implement.

**1. Output token distribution.** The cheapest canary available. Response length is remarkably stable for a fixed prompt distribution, and a 30% shift in median output tokens with no deploy means something changed: a model default, an effort level, a prompt edit, or a change in the inputs. Opus 5.5 defaulting to `medium` effort where Opus 5 defaulted to `high` is exactly the kind of change that shows up here first and nowhere else.

**2. Reasoning token share.** With `gen_ai.usage.reasoning.output_tokens` you can track thinking as a fraction of output. A sudden collapse in that fraction on a hard task class is an effort regression; a sudden expansion is a cost regression. Neither raises an error.

**3. Validation and repair rates as quality proxies.** Your structural and semantic validators already run on every response. Their failure rate is a free quality metric with no labelling cost. A rising semantic-invariant failure rate, with structural failures flat, is the clearest available signal of degraded reasoning.

**4. Golden-set replay.** A fixed set of 100–300 inputs with known-good outputs, replayed on every deploy and on a schedule. Score with exact match where you can, a rubric-graded model judge where you cannot. Hold the judge model *pinned* — if you upgrade judge and subject together you cannot attribute the change. Run the golden set through the batch API: it is 50% cheaper, it is not latency-sensitive, and it draws on capacity outside your interactive pool.

**5. Shadow comparison.** Mirror a small sampled fraction of production traffic to a candidate configuration and compare distributions — output length, validation rate, judge score, cost per request — without ever serving the candidate’s output. Expensive, and the only honest way to qualify a model change on real traffic.

``` {.sourceCode .python}
import statistics
from collections import deque


class QualityCanary:
    """Distribution drift detector over a rolling baseline. One per
    (feature, model, effort) combination; a change to any of those
    resets the baseline, because it is a different population."""

    def __init__(self, window: int = 500, tolerance: float = 0.30):
        self.baseline: deque[float] = deque(maxlen=window)
        self.current: deque[float] = deque(maxlen=100)
        self.tolerance = tolerance

    def observe(self, output_tokens: int) -> None:
        self.current.append(float(output_tokens))
        if len(self.baseline) < self.baseline.maxlen:
            self.baseline.append(float(output_tokens))

    def drifted(self) -> tuple[bool, float]:
        if len(self.current) < 50 or len(self.baseline) < 200:
            return False, 0.0
        base = statistics.median(self.baseline)
        now = statistics.median(self.current)
        if base == 0:
            return False, 0.0
        ratio = now / base
        return abs(ratio - 1.0) > self.tolerance, ratio
```

Medians, not means: a single 128,000-token response moves a mean by enough to mask or fabricate a regression.

## 2.9 Four post-mortems

### Case 1 — The \$41,000 Tuesday

**Symptom.** Cloud cost alert fires on a Tuesday afternoon: Claude API spend for the day is already 6.2× the trailing median. No error-rate change, no latency change, no customer complaints, no deploy.

**Investigation.** Usage API grouped by model shows volume flat and token counts flat. Grouped by `context_window` and model, the picture resolves: Haiku 5.5 requests in the over-100K bucket have gone from 3% of traffic to 71%. The deploy log shows nothing that day — but a *content* change the previous evening added two new sections to a shared retrieval template, lifting the median assembled prefix from 94,000 tokens to 103,000.

**Root cause.** Haiku 5.5 is priced by prompt length with a hard step at 100,000 tokens: \$0.10 → \$0.50 per MTok input, with cache reads counted toward the threshold and stepping up too. A 9.5% increase in prompt size produced a 5× increase in unit price, applied to the whole request. Nothing failed; the bill simply quintupled.

**Fix.** Immediate: cap retrieval so assembled prefixes stay under 92,000 tokens, with a hard assertion at request-build time. Structural: route by measured prefix size, sending anything above 90,000 tokens to Sonnet 5.5, where pricing is flat across the whole 1M window and quality is higher anyway. Permanent: an alert on the fraction of Haiku requests over 100K tokens, which is now the single most valuable cost alert in the system. A margin was deliberately left between the 92,000-token cap and the 100,000-token threshold because token counts are estimates until the request is sent.

### Case 2 — The retry storm that was a cache bug

**Symptom.** 429 rate climbs from near zero to 18% over three days. Request volume unchanged. The team requests a tier increase.

**Investigation.** Rate-limit headers show input-token remaining collapsing within seconds of each minute, while output-token remaining stays comfortable — so ITPM, not RPM or OTPM, is binding. Average `input_tokens` in the logs has risen 11× while `cache_read_input_tokens` has fallen to zero. Enabling `diagnostics` with `previous_message_id` returns `system_changed` with `cache_missed_input_tokens` around 38,000 on nearly every turn. A commit from the previous week had added a freshly rendered timestamp to the system prompt for “better log correlation”.

**Root cause.** The timestamp made every system prompt unique, so no cache ever hit. Because **cache reads generally do not count toward ITPM but uncached input does**, the hit-rate collapse converted a comfortable ITPM position into a saturated one with no change in traffic. The 429s were a *symptom* of a caching bug, and the requested tier increase would have papered over it at roughly 10× the necessary cost.

**Fix.** Move the timestamp out of the system prompt into the first user message after the breakpoint. Hit rate returns to 94%, ITPM consumption drops by about an order of magnitude, 429s go to zero, and the tier request is withdrawn. Permanent: `diagnostics` enabled on a 1% traffic sample, with an alert on any `*_changed` reason appearing at all, plus a prefix-fingerprint cardinality check in CI that fails the build if a system prompt is not byte-stable across two renders.

### Case 3 — Duplicate refunds

**Symptom.** Finance reports 41 duplicate refund approvals over two weeks. Each pair is identical in amount and reason, minutes apart. The approval service’s logs show one approval per case.

**Investigation.** The refund agent uses a tool loop; the tool that issues a refund is called once per case according to its own logs — but the *approval* records come in pairs. Correlating by request ID shows that each duplicated case has two distinct Claude request IDs, minutes apart, and the first of each pair coincides with a read timeout in the client. The client’s retry layer classified the timeout as transport and retried.

**Root cause.** The Messages API has no idempotency key. The original request had completed server-side — the model generated the full response including the `tool_use` block — but the response body never reached the client. The retry produced a second, equivalent response, and the tool loop executed the refund tool a second time. The refund tool itself was idempotent on its own key, so the money moved once; the *approval record* was written by the agent’s handler on each successful tool result, and that write was not idempotent.

**Fix.** Three layers, all of them necessary. (a) An intent ledger: a deterministic operation ID per case, written `in_flight` before the call and `complete` after, so a retry in any process returns the stored response instead of calling again. (b) The approval write becomes an upsert keyed on the operation ID. (c) The retry policy stops treating read timeouts on non-streaming requests as freely retryable: such requests move to streaming, where a partial response is visible and a completed-but-undelivered response is far less likely. Permanent: a test that asserts the operation ID is byte-stable across two renders of the same logical request, because the entire design collapses if any field varies between a call and its retry.

### Case 4 — The quiet summariser

**Symptom.** None, for eleven days. Then a customer escalation: document summaries have been “much less useful lately”. Error rate zero. Validation failure rate zero. Latency improved by 22%.

**Investigation.** Latency *improving* with no deploy is the clue. Output token medians for the summarisation feature had dropped from 780 to 410 over a single day, eleven days earlier. Model ID distribution shows the feature moved from `claude-opus-5` to `claude-opus-5-5` on that date — a planned migration whose only change was the model string. Opus 5 defaults to `high` effort; Opus 5.5 defaults to `medium`. The migration had silently lowered effort by one level, and because effort affects all output tokens, summaries got shorter and shallower while remaining perfectly well-formed and schema-valid.

**Root cause.** A default changed across a model boundary. Nothing in the error, latency or validation telemetry could possibly have caught it; all three moved in the “good” direction.

**Fix.** Set `output_config.effort` explicitly on every request, so a default change can never move behaviour. Re-run the golden set against both `medium` and `high` on Opus 5.5 to choose deliberately rather than inheriting. Permanent: output-token distribution monitoring per (feature, model, effort) with a 30% drift alert, and a rule that any model ID change requires a golden-set run before rollout — which would have caught this in under an hour.

The pattern across all four is the same. Every one was invisible to the obvious dashboard. Three had no errors at all, and one had errors that pointed at the wrong layer entirely. The telemetry that caught them — prompt-size distribution by model, cache hit rate as a capacity metric, request IDs correlated with timeouts, and output-token medians per configuration — is cheap, and none of it is on by default. Add it before you need it.

## Practice Questions

**V2.1** A non-streaming request times out at the client after nine minutes. Your retry layer resends it and the second attempt succeeds. The request’s tool loop writes to a payments ledger. What is the most significant risk?

A. The first request may have completed server-side, so the work may be performed twice and billed twice. B. None; a timeout means the request never reached the model. C. The retry will be rejected as a duplicate because the Messages API deduplicates by request body. D. The retry will fail with 409 `conflict_error` because the original is still in flight.

**V2.2** A response returns HTTP 200 with `stop_reason: "model_context_window_exceeded"`. Which action is most likely to resolve it?

A. Raise `max_tokens` so generation has more room. B. Compact or trim the conversation history, then resend. C. Retry unchanged with exponential backoff. D. Lower `output_config.effort` so fewer tokens are generated.

**V2.3** You receive a 429 whose body includes `error.details.error_code` of `enforced_spend_limit_reached` and no `retry-after` header. Which handling is correct?

A. Retry with full jitter up to three attempts, then escalate. B. Open the circuit breaker and retry on a different model. C. Reduce the client’s target rate by half and retry after one second. D. Treat it as permanent for the current billing period; do not retry.

**V2.4** (Select TWO) Which two differences between 429 and 529 handling are justified?

A. 529 warrants full jitter because all clients receive it simultaneously; 429 does not, because the bucket is per-organization. B. 429 warrants tripping the circuit breaker; 529 does not. C. 429 should honour `retry-after` exactly when present; 529 rarely carries one and needs a longer synthetic base delay. D. 529 should cause the client to lower its sustained target rate; 429 should not. E. Neither should ever be retried more than once.

**V2.5** A stream ends without a `message_stop` event, after 6,000 characters of text across one text block that is still open. Which response is best?

A. Treat the output as complete, since a `stop_reason` is not required. B. Retry the entire request from scratch to guarantee consistency. C. Resume with a user message quoting the tail and asking the model to continue. D. Prefill a new assistant turn with the partial text and continue from there.

**V2.6** A stream dies while a `tool_use` block is open, with roughly 80% of the tool arguments received as `input_json_delta` fragments. What should you do?

A. Parse the accumulated fragments with a lenient JSON parser and execute the tool. B. Resume with a continuation message asking the model to finish the JSON. C. Re-run from the last stable turn; partial tool use is not recoverable. D. Return a `tool_result` with an error and let the model retry the call.

**V2.7** Structured output is configured with `output_config.format`, and a response arrives with `stop_reason: "refusal"`. Which statement is correct?

A. The request failed with a non-2xx status and was not billed. B. The response is HTTP 200, you are billed, and the text may not match the schema. C. The schema is still enforced, so the refusal text will be valid JSON. D. The refusal is a rate-limit condition and should be retried after the stated interval.

**V2.8** (Select TWO) Which two validation failures are appropriate for deterministic repair rather than a retry?

A. A numeric field reported as `-250.00` where the business rule requires a positive amount. B. A missing required object that the schema declares. C. An enum value returned as `"In Progress"` where the schema declares `"in_progress"`, with no other member matching case-insensitively. D. Trailing whitespace on a string field. E. A date three years outside the plausible range for the document.

**V2.9** Your retry layer allows three attempts, and you also leave the SDK’s default `max_retries` in place. What is the worst-case number of requests sent for one logical call?

A. Three. B. Five. C. Nine. D. Six.

**V2.10** A response arrives with `stop_reason: "max_tokens"` and the final content block is an incomplete `tool_use`. Which recovery is correct?

A. Append the partial assistant content and a user message asking it to continue. B. Switch to `tool_choice: "none"` and resend. C. Execute the tool with the partial arguments and return a `tool_result`. D. Retry with a higher `max_tokens`; the partial tool arguments cannot be used.

**V2.11** You observe `stop_reason: "pause_turn"` on a server-tool request. What is the documented recovery, and what safeguard does it require?

A. Retry the original request unchanged; cap the number of retries. B. Send the assistant’s content back unchanged to continue; cap the number of continuations. C. Raise `max_tokens` and resend; no safeguard needed. D. Treat it as a refusal and fall back to another model.

**V2.12** (Select TWO) Which two signals would detect a silent quality regression caused by a model’s default effort level dropping, with no errors and no latency degradation?

A. Median output tokens per (feature, model) falling sharply with no deploy. B. `gen_ai.usage.reasoning.output_tokens` as a share of output tokens collapsing. C. Aggregate HTTP error rate by status code. D. The `cache_miss_reason` distribution. E. The p99 of `anthropic-ratelimit-requests-remaining`.

**V2.13** Latency for a feature *improves* by 25% overnight with no deploy, no error-rate change, and no validation-failure change. What is the most useful next check?

A. Compare the model ID distribution and output-token medians against the previous week. B. Scale down the connection pool, since latency has improved. C. Raise `max_tokens`, since responses may be truncating early. D. Nothing; improved latency is not an incident.

**V2.14** Which single field most reliably distinguishes “the prompt was too long before generation started” from “generation ran out of context window”?

A. The HTTP status code: 400 for the former, 200 with a stop reason for the latter. B. `usage.input_tokens` compared against the model’s window. C. The presence of a `retry-after` header. D. Whether `max_tokens` was explicitly set.

**V2.15** You are designing idempotency with no platform idempotency key available. Your operation ID is a SHA-256 of the canonicalised request body. Which detail most threatens the design?

A. SHA-256 collisions at production volume. B. The need to include `max_tokens` in the hash. C. The ID being too long to store as a database key. D. Any per-request value inside the body — a timestamp, a UUID, a reordered tool list — making the ID differ between a call and its retry.

**V2.16** (Select TWO) Which two items must never appear in your application logs for a Claude call, while the rest of the record remains useful?

A. The `request-id` response header. B. The text of the system prompt. C. The full `usage` object. D. Tool result payloads returned by your own tools. E. The error `type` from the response body.

**V2.17** `message_delta` events carry a `usage` object during a stream. How should it be accumulated?

A. Summed across all `message_delta` events, since each reports an increment. B. Taken from the last `message_delta` observed, since the values are cumulative. C. Ignored; only the `message_start` event carries authoritative usage. D. Averaged across events to smooth out partial counts.

**V2.18** A golden-set replay shows scores dropping after you upgraded both the subject model and the model used as a judge in the same release. What is the primary problem?

A. The judge is now too strict, so the scores are simply wrong. B. Golden sets cannot be used with model judges at all. C. The change is unattributable: either model could account for the movement. D. The replay should have run synchronously rather than as a batch.

**V2.19** (Select TWO) Which two conditions return HTTP 200 and therefore evade monitoring that treats non-2xx as the only failure signal?

A. 413 `request_too_large`. B. `stop_reason: "refusal"`. C. 529 `overloaded_error` on a non-streaming request. D. An `error` event delivered mid-stream after headers were sent. E. 400 for an unsupported JSON Schema feature.

**V2.20** A circuit breaker opens repeatedly during a deploy that introduced a malformed tool schema, taking down unrelated features that share the same model. What is the design error?

A. The breaker counts deterministic 400 errors as capacity failures, so a code bug trips it. B. The breaker’s failure threshold is too low for the traffic volume. C. The breaker should be per-feature rather than per-model, regardless of failure type. D. The breaker should never half-open; it should require a manual reset.
