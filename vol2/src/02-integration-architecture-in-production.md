# Integration Architecture in Production

Volume I taught you the shape of a request. This chapter is about the fifty thousand of them your service will send tomorrow afternoon, and about the fact that the difference between a working integration and a profitable one is almost entirely arithmetic you have not yet done.

Everything here assumes you know what a content block is, why `max_tokens` is mandatory, and what a cache breakpoint looks like in JSON. Instead we treat the API as one dependency among many and ask what we would ask of any such dependency: what does it cost per unit of work, how does it fail, how do I bound its blast radius, and how do I prove to finance which product line is burning the money.

## 1.1 The request layer as a product surface

A production integration has exactly one place where HTTP happens. If `grep` for `messages.create` returns more than one hit outside the client module, you have no request layer — only a scattering of call sites, each with its own timeout, retry behaviour and logging. The wrapper is not boilerplate; it is where five cross-cutting concerns are decided once:

  -------------------------------------------------------------------------------------------------------------------------------------------------------------
  Concern                 Decided in the wrapper                         Consequence of leaving it to call sites
  ----------------------- ---------------------------------------------- --------------------------------------------------------------------------------------
  Deadline                One budget per logical operation, propagated   Tail latency becomes unbounded; a slow model call holds a web worker for ten minutes

  Retry                   One policy, aware of status semantics          Each site reinvents backoff; 429s get hammered

  Circuit breaking        One shared state per model                     Breakers that never trip because each site sees only its own slice of traffic

  Observability           Uniform span and log schema                    Incidents become archaeology

  Redaction               Content never reaches the log sink             A privacy incident, eventually and inevitably
  -------------------------------------------------------------------------------------------------------------------------------------------------------------

### Deadlines, not timeouts

A timeout is a per-call number; a deadline is an absolute instant that travels with the operation. The distinction matters because one user-facing request may make three model calls, and three ten-second timeouts do not add up to a ten-second experience.

The API pushes in the same direction: non-streaming requests are validated against a ten-minute ceiling, and the SDKs refuse one whose expected generation time would exceed it. Anything that could plausibly run long belongs on the streaming endpoint or in a batch, not behind a hopeful socket timeout. For direct HTTP integrations, TCP keep-alive is not optional — idle intermediaries drop connections that produce no bytes for minutes, and you then see a transport failure with no response body and no request ID to take to support.

### Structured logging that does not log user content

The rule is simple to state and widely violated: the log record describes the request, never its contents. You want the metadata that reconstructs a timeline and reconciles a bill, plus the one identifier that lets Anthropic find the request on their side — the `request-id` response header, surfaced as `message._request_id` in the Python and TypeScript SDKs and present as `request_id` in every error body. Log it unconditionally, on success and on failure. An incident report without it is a guess.

``` {.sourceCode .python}
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import anthropic

log = logging.getLogger("llm.client")

SAFE_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def content_fingerprint(obj: Any) -> str:
    """A stable, non-reversible handle for a prompt, for correlating
    identical requests across logs without storing the text."""
    payload = repr(obj).encode("utf-8", "replace")
    return hashlib.blake2b(payload, digest_size=8).hexdigest()


@dataclass(slots=True)
class CallRecord:
    op: str
    tenant: str
    feature: str
    model: str
    attempt: int
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str | None = None
    status: str = "pending"
    error_type: str | None = None
    latency_ms: int | None = None
    usage: dict[str, int] = field(default_factory=dict)
    prompt_fp: str | None = None

    def emit(self) -> None:
        # Note what is absent: no message text, no system prompt, no tool
        # arguments, no tool results. Only shapes, counts and identifiers.
        log.info("llm_call", extra={"llm": self.__dict__})
```

The fingerprint is the part worth copying. During a cache-miss investigation you need to know whether two requests were byte-identical, from the logs, without a replay harness. Hash the prefix separately from the tail: a prefix fingerprint that changes between consecutive turns is your cache bug, visible in a `GROUP BY`.

### Circuit breaking on the right signal

A breaker that counts all failures equally is worse than no breaker. A 400 from a malformed tool schema is a deterministic bug in one code path, and tripping on it takes down every other feature sharing the model. The signal you want is *capacity* failure: 529, 500, connection resets, read timeouts. Rate limiting is a third category — a 429 means *slow down*, a scheduling instruction rather than a health signal, and belongs in the limiter.

``` {.sourceCode .python}
import threading


class ModelBreaker:
    """One breaker per (model, service tier). Trips on capacity failures only."""

    CAPACITY = {"overloaded_error", "api_error", "timeout_error", "connection_error"}

    def __init__(self, threshold: int = 20, window_s: float = 30.0, cool_s: float = 15.0):
        self._lock = threading.Lock()
        self._failures: list[float] = []
        self._opened_at: float | None = None
        self.threshold = threshold
        self.window_s = window_s
        self.cool_s = cool_s

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at >= self.cool_s:
                # Half-open: let one probe through, keep the breaker armed.
                self._opened_at = time.monotonic()
                self._failures.clear()
                return True
            return False

    def record(self, error_type: str | None) -> None:
        now = time.monotonic()
        with self._lock:
            if error_type is None:
                self._failures.clear()
                self._opened_at = None
                return
            if error_type not in self.CAPACITY:
                return  # deterministic errors do not indicate capacity loss
            self._failures = [t for t in self._failures if now - t < self.window_s]
            self._failures.append(now)
            if len(self._failures) >= self.threshold and self._opened_at is None:
                self._opened_at = now
                log.warning("breaker_open", extra={"failures": len(self._failures)})
```

Note what the breaker does *not* do: a 429 does not count toward opening it, and neither does a 400. Those two decisions are the whole design.

### Concurrency and connection pooling

The SDK clients are built on pooled HTTP clients and are safe to share; constructing one per request pays TLS handshake and connection setup every call. Create the client once per process, size the pool to your intended in-flight concurrency plus headroom, and gate concurrency with a semaphore you own rather than letting the pool queue for you — a pool that queues silently converts a rate-limit problem into a latency problem, which is harder to diagnose.

The right in-flight number is not “as many as the pool allows”. Each streaming request holds a connection for the full generation duration, so concurrency and OTPM interact: a hundred concurrent streams at 40 tokens per second is 100 × 40 × 60 = 240,000 OTPM. Compute that product before you tune the pool.

## 1.2 The economics of prompt caching, worked out

Volume I told you what a breakpoint is. It did not tell you when writing one loses money. Let *P* be the base input price per token for your model; the current multipliers are:

  Operation                             Multiplier on *P*
  ------------------------------------- -------------------
  Five-minute cache write               1.25×
  One-hour cache write                  2.00×
  Cache read, most models               0.10×
  Cache read, Opus 5.5 and Sonnet 5.5   0.05×
  Cache read, Fable 5.1                 0.025×

### Break-even in number of requests

Suppose a prefix of *T* tokens is reused by *N* requests, and every request after the first hits the cache. Write *w* for the write multiplier and *r* for the read multiplier.

-   Uncached cost: *N · T · P*
-   Cached cost: *T · w · P + (N − 1) · T · r · P*

Setting them equal and solving for *N*:

> *N\** = (*w* − *r*) / (1 − *r*)

On Opus 5.5 with a five-minute TTL (*w* = 1.25, *r* = 0.05) that is *N\** ≈ 1.26. Break-even falls between the first and second request, so **two requests are already cheaper than two uncached ones**: 1.25 + 0.05 = 1.30 units against 2.00. One request alone — a write with no read — costs 1.25 units against 1.00, a flat 25% penalty for nothing.

With the one-hour TTL (*w* = 2.00, *r* = 0.05), *N\** ≈ 2.05, just past the second request. Two requests cost 2.00 + 0.05 = 2.05 units against 2.00: still a loss, by 2.5%. Three cost 2.00 + 0.10 = 2.10 against 3.00, a 30% saving. The documented summary — a five-minute write pays off after one read, a one-hour write after two — falls straight out of the algebra.

### Break-even in hit rate

The more useful form asks: given that a fraction *h* of my requests hit and the remaining (1 − *h*) have to re-write the prefix, am I ahead? Expected cost per request, in units of *P · T*:

> *h · r* + (1 − *h*) · *w*

Setting that below 1 and solving:

> *h\** = (*w* − 1) / (*w* − *r*)

  Model                         TTL   *w*    *r*     Break-even hit rate
  ----------------------------- ----- ------ ------- ---------------------
  Opus 5.5 / Sonnet 5.5         5m    1.25   0.05    20.8%
  Opus 5.5 / Sonnet 5.5         1h    2.00   0.05    51.3%
  Fable 5.1                     5m    1.25   0.025   20.4%
  Fable 5.1                     1h    2.00   0.025   50.6%
  Haiku 5.5, Sonnet 5, Opus 5   5m    1.25   0.10    21.7%
  Haiku 5.5, Sonnet 5, Opus 5   1h    2.00   0.10    52.6%

Two conclusions. The five-minute threshold is low enough that you should cache almost any stable prefix over the minimum length: one hit in five pays for the misses. The one-hour threshold, by contrast, is a *majority* requirement — extended TTL is for workloads where you have positive reason to expect most requests to land on the entry, not a generic upgrade. And since the read multiplier barely moves the threshold (20.4% to 21.7% across the whole range), the write multiplier dominates: TTL choice matters far more than model choice when deciding *whether* to cache.

### A worked conversation

Sonnet 5.5, input at \$2.00/MTok. A support assistant carries a 40,000-token stable prefix and a conversation growing by roughly 300 tokens per turn. Twelve turns, all within five minutes.

Uncached input tokens: Σ(40,000 + 300*k*) for *k* = 1…12 = 480,000 + 23,400 = **503,400 tokens**, or **\$1.0068**.

Cached, with one breakpoint at the end of the 40,000-token prefix:

-   Turn 1: write 40,000 at 1.25× → 50,000 billable-equivalent tokens, plus 300 uncached. (An equivalent token is one token billed at the base input price, so 40,000 tokens at 1.25× cost the same as 50,000 plain input tokens. Converting every category to this unit lets you add them up.)
-   Turns 2–12: read 40,000 at 0.05× → 2,000 equivalent each, 22,000 in total, plus 23,100 uncached tail tokens.
-   Total: 50,000 + 22,000 + 23,400 = **95,400 equivalent tokens**, or **\$0.1908**.

An **81% reduction in input spend**. Notice where the remaining cost sits: 23,400 of the 95,400 equivalent tokens — a quarter of the bill — is the growing uncached tail. A second breakpoint, advanced every few turns, converts most of that into reads, and is usually the highest-return change available once the first breakpoint exists.

### The Haiku 5.5 cliff

Haiku 5.5 is the one current model priced by prompt length, and the discontinuity is brutal. At or below 100,000 prompt tokens, input is \$0.10/MTok and a cache read \$0.01/MTok. Above it, input is \$0.50/MTok and a read \$0.05/MTok — a flat **5× step** applied to the whole request, with no proration. A 99,000-token prompt costs **\$0.0099**; a 101,000-token prompt costs **\$0.0505**. Two per cent more input, 5.1× the price.

The trap is that *prompt length for tiering includes cache reads*. A 150,000-token cached corpus on Haiku 5.5 reads at \$0.05/MTok, not \$0.01/MTok, because the request is over the threshold. Compare honestly against Sonnet 5.5 at that point: \$0.0075 against \$0.015 — still cheaper, but the gap you were counting on (10× on cache reads below the threshold, 20× on fresh input) has become 2×, against a considerably stronger model. Workloads just under the threshold should be *engineered* to stay there; workloads comfortably above it should be re-benchmarked against Sonnet.

Haiku is also the family where the ITPM footnote must be checked generation by generation: Haiku 3.5 counted cache reads toward ITPM, and that exception has historically been Haiku-specific. Read the current table rather than assuming.

### Cache hierarchy and the privacy boundary in multi-tenant systems

Caches are never shared across organizations, and on the Claude API they are isolated per *workspace*. That single fact determines your multi-tenant architecture. A sensible hierarchy has three layers, ordered from most stable to least:

1.  **Global prefix** — product system prompt, tool definitions, output conventions. Identical for every tenant. One breakpoint.
2.  **Tenant prefix** — tenant policy, glossary, schema, brand voice. Identical across that tenant’s requests. One breakpoint.
3.  **Session prefix** — the retrieved documents or case file for this conversation. One breakpoint, re-cut as the session grows.

That leaves a fourth breakpoint for the sliding history window. The ordering is not cosmetic: matching is prefix-based, so the least stable content must come last, and an invalidation at any level invalidates everything after it. The documented order is tools, then system, then messages — so a change to the tool list discards the tenant and session layers too.

The privacy question is sharper than it looks. Caching requires a 100% identical prefix including images, and entries hold key-value representations and hashes in memory, never raw prompts. That is a strong guarantee *given correct scoping*, and scoping is the part you own. The rule to enforce in code: **a cache breakpoint must never sit after content belonging to more than one tenant.** If your prefix assembly can interleave tenants, the bug is in the assembly, and caching merely makes it cheaper to repeat.

Where regulatory isolation is required rather than merely desirable, use separate workspaces per tenant and accept the consequence: the global prefix is cached once per workspace, not once globally. With a 6,000-token global prefix and 400 tenants, that is 6,000 × 400 × 1.25 = 3,000,000 equivalent tokens per cold start — \$6.00 on Sonnet 5.5, or \$75.00 on Fable 5.1 at \$10/MTok.

### Pre-warming, concurrency, and the ordering constraint

A cache entry becomes available only once the first response has begun. Fan out fifty requests simultaneously against a cold prefix and you will pay fifty writes, not one write and forty-nine reads. On a 200,000-token prefix on Opus 5.5 at \$4/MTok that error costs 50 × 200,000 × 1.25 × \$4/MTok = **\$50.00**. Done in order, the same work costs one write at \$1.00 plus forty-nine reads at 200,000 × 0.05 × \$4/MTok = \$0.04 each, \$2.96 in total. That is a seventeenfold overrun caused entirely by scheduling.

The fix is a serialisation point: issue one request, wait until its response starts, release the rest. Pre-warming formalises this. Send `max_tokens: 0` with a breakpoint on the shared prefix; the response returns empty content, `stop_reason: "max_tokens"` and a populated usage block, billing the write plus zero output tokens. Three constraints bite:

-   The breakpoint must be on the shared block, not the placeholder user message. Automatic top-level caching puts it on the placeholder, so it cannot pre-warm.
-   Thinking and effort configuration must match the real requests exactly, since both are rendered into the prompt.
-   `max_tokens: 0` is rejected with streaming, extended thinking, `output_config.format`, `tool_choice` of `tool` or `any`, and inside Message Batches.

That last exclusion is why batch pre-warming takes a different shape: submit one ordinary request carrying the shared prefix with a one-hour breakpoint, wait for it to complete, then submit the batch.

``` {.sourceCode .python}
class PrefixWarmer:
    """Serialise the first write, then release the fan-out."""

    def __init__(self, client: anthropic.Anthropic, model: str):
        self._client = client
        self._model = model
        self._done: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def ensure(self, key: str, prefix_blocks: list[dict], ttl: str = "1h") -> None:
        with self._lock:
            event = self._done.get(key)
            if event is None:
                event = self._done[key] = threading.Event()
                owner = True
            else:
                owner = False
        if not owner:
            event.wait(timeout=120)
            return
        try:
            blocks = [dict(b) for b in prefix_blocks]
            blocks[-1]["cache_control"] = {"type": "ephemeral", "ttl": ttl}
            self._client.messages.create(
                model=self._model,
                max_tokens=0,            # rejected with streaming/thinking/format
                system=blocks,
                messages=[{"role": "user", "content": "warm"}],
            )
        finally:
            event.set()
```

### What stacks with what

  --------------------------------------------------------------------------------------------------------------------------------------------------------
  Combination                                        Stacks?                 Note
  -------------------------------------------------- ----------------------- -----------------------------------------------------------------------------
  Caching × Batch (50% off)                          Yes                     Both discounts apply; hits are best-effort because batch order is arbitrary

  Caching × long-context pricing                     Yes                     On Haiku 5.5 cache reads count toward the 100K threshold

  Caching × data residency (`inference_geo: "us"`)   Yes                     1.1× applies to writes and reads too

  Caching × fast mode                                Yes                     Fast mode is not available with batches

  Batch × fast mode                                  No                      Mutually exclusive

  Batch × streaming                                  No                      `stream: true` is rejected in a batch

  Batch × `max_tokens: 0`                            No                      Pre-warm outside the batch

  Caching × `output_config.format` change            No                      Changing the format invalidates the thread’s prompt cache
  --------------------------------------------------------------------------------------------------------------------------------------------------------

The last row catches people: structured output injects an extra system prompt describing the format, so the schema is part of the cached prefix. Switching schemas mid-conversation to “just get one more field” throws away every cached token in the thread.

## 1.3 Choosing streaming, synchronous, or batch

This is a latency-budget decision, not a taste decision. The three modes differ in what they bound.

  -------------------------------------------------------------------------------------------------------------------------------------
                              Synchronous                        Streaming                          Batch
  --------------------------- ---------------------------------- ---------------------------------- -----------------------------------
  Bounds                      Total time to full answer          Time to *first* token              Throughput, not latency

  Practical ceiling           10 minutes; SDK rejects longer     None in practice                   24 hours, then expiry

  Price                       1×                                 1×                                 0.5×

  Partial output on failure   None                               Everything before the break        Per-request results

  Mid-flight errors           HTTP status                        SSE `error` event after HTTP 200   Per-request `errored` result

  Suits                       Short, bounded, machine-consumed   Human-facing, long generations     Backfills, evals, bulk extraction
  -------------------------------------------------------------------------------------------------------------------------------------

A decision table that holds up under review:

  -------------------------------------------------------------------------------------------------------------------------------------
  Latency budget                           Output size       Human waiting?    Choose
  ---------------------------------------- ----------------- ----------------- --------------------------------------------------------
  \< 2 s                                   small             yes               Synchronous, low effort, small model

  \< 2 s to first token, minutes to last   large             yes               **Streaming**

  \< 30 s                                  small/medium      no                Synchronous

  \< 10 min                                any               no                Synchronous if well inside the ceiling, else streaming

  \> 10 min single request                 very large        no                **Streaming** with `get_final_message()`

  Hours, many items                        any               no                **Batch**

  Hours, many items, must be cheapest      any               no                **Batch** + 1h cache on the shared prefix
  -------------------------------------------------------------------------------------------------------------------------------------

Two refinements. Streaming is the correct answer for *long single generations even when nobody is watching*, because it is the only mode that keeps bytes flowing and so avoids idle-connection drops; `client.messages.stream(...)` with `stream.get_final_message()` returns a complete `Message` with none of the incremental handling. And batch is not merely cheaper — it draws on capacity outside your standard pool, with its own limits of 100,000 requests or 256 MB per batch, so moving a backfill into a batch is simultaneously a 50% discount and a way to stop it starving interactive traffic.

## 1.4 Rate-limit engineering

Three limits apply per model class: RPM, ITPM, OTPM. All are enforced with a token bucket that replenishes *continuously*, not a counter that resets on the minute. Four consequences follow, and most client-side limiters get at least two wrong.

**A per-minute average does not protect you.** Capacity is refilled smoothly, so 60 RPM behaves much like one request per second. Firing all sixty at the top of the minute will 429 even though your minutely average is exactly at the limit. A limiter must shape the instantaneous rate, not the minutely total.

**Ramping matters.** Acceleration limits can produce 429s when usage climbs sharply even below the nominal ceiling. A deploy taking a service from 0 to 4,000 RPM in one step is, to the platform, a different event from the same service drifting there over ten minutes. Build a warm-up into your autoscaling.

**ITPM is cache-aware.** This is the single highest-leverage fact in the whole chapter. Input is accounted as:

> total input = `cache_read_input_tokens` + `cache_creation_input_tokens` + `input_tokens`

but **cache writes count toward ITPM and cache reads generally do not** (Haiku 3.5 being the documented exception). So a 200,000-token cached document plus a fifty-token question reports `input_tokens: 50` and consumes essentially nothing from your ITPM bucket on a hit. The documented arithmetic: with a 2,000,000 ITPM limit and an 80% hit rate, you can push roughly 10,000,000 input tokens per minute — 2M uncached plus 8M cached.

That turns caching from a cost optimisation into a *capacity* optimisation: your effective throughput ceiling is a function of your hit rate. A hit-rate regression does not only raise the bill, it can take you from comfortable to rate-limited with no change in traffic. Alert on hit rate as a capacity metric.

**OTPM is not derived from `max_tokens`.** Output is metered in real time, counting only tokens actually generated. Raising `max_tokens` from 4,096 to 64,000 carries no rate-limit penalty whatsoever. ITPM, by contrast, is *estimated* at request start and reconciled during the request against actual input. People routinely get this backwards and cripple their own output quality by shaving `max_tokens` to protect a limit that `max_tokens` does not touch.

### The headers, and the limiter

Every response carries the current state of your buckets:

    anthropic-ratelimit-requests-limit / -remaining / -reset
    anthropic-ratelimit-input-tokens-limit / -remaining / -reset
    anthropic-ratelimit-output-tokens-limit / -remaining / -reset
    anthropic-ratelimit-tokens-limit / -remaining / -reset

Remaining counts are rounded to the nearest thousand, `-reset` values are RFC 3339 timestamps, and the undifferentiated `anthropic-ratelimit-tokens-*` triple reports whichever limit is currently *most restrictive* — workspace values if a workspace limit binds, otherwise the combined input-plus-output total. Treat it as a summary, not a fourth limit. `anthropic-workspace-id` names the workspace charged, which matters when debugging attribution.

A limiter that does not thrash has four properties: continuous-rate shaping rather than a windowed counter; reserve-then-reconcile around each call; `retry-after` treated as authoritative; and self-degrading target rate on repeated 429s instead of retrying into the wall.

``` {.sourceCode .python}
import math
import random


class AdaptiveBucket:
    """Continuous-replenishment shaper with header feedback.

    One instance per (model, limiter kind). Reserve before the call,
    reconcile after. Never busy-waits; callers sleep on the returned delay.
    """

    def __init__(self, rate_per_s: float, burst: float):
        self._lock = threading.Lock()
        self.nominal_rate = rate_per_s
        self.rate = rate_per_s
        self.burst = burst
        self._tokens = burst
        self._last = time.monotonic()
        self._penalty_until = 0.0

    def _refill_locked(self, now: float) -> None:
        self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
        self._last = now

    def acquire(self, cost: float) -> float:
        """Returns seconds the caller must wait before proceeding."""
        with self._lock:
            now = time.monotonic()
            self._refill_locked(now)
            if now < self._penalty_until:
                return self._penalty_until - now
            if self._tokens >= cost:
                self._tokens -= cost
                return 0.0
            deficit = cost - self._tokens
            self._tokens = 0.0
            return deficit / self.rate

    def reconcile(self, estimated: float, actual: float) -> None:
        """Give back over-reservation, charge under-reservation."""
        with self._lock:
            self._refill_locked(time.monotonic())
            self._tokens = max(0.0, min(self.burst, self._tokens + (estimated - actual)))

    def observe_headers(self, headers: dict[str, str], key: str) -> None:
        """Re-anchor to the server's view. Headers are rounded to 1000,
        so treat them as a floor, not a precise count."""
        limit = headers.get(f"anthropic-ratelimit-{key}-limit")
        remaining = headers.get(f"anthropic-ratelimit-{key}-remaining")
        if not (limit and remaining):
            return
        with self._lock:
            self._refill_locked(time.monotonic())
            self._tokens = min(self._tokens, float(remaining))
            self.burst = max(self.burst, float(limit) / 60.0)

    def throttle(self, retry_after_s: float | None) -> None:
        """Called on 429. Halve the target rate and respect retry-after."""
        with self._lock:
            self.rate = max(self.nominal_rate * 0.1, self.rate * 0.5)
            wait = retry_after_s if retry_after_s is not None else 1.0
            self._penalty_until = time.monotonic() + wait + random.uniform(0, 0.25 * wait)
            self._tokens = 0.0
            self._last = time.monotonic()

    def recover(self) -> None:
        """Called on sustained success. Additive increase."""
        with self._lock:
            if self.rate < self.nominal_rate:
                self.rate = min(self.nominal_rate, self.rate + self.nominal_rate * 0.05)
```

Multiplicative decrease on 429, additive increase on success: the same control law that keeps TCP from collapsing, for the same reason. A limiter that restores full rate the instant one request succeeds will oscillate between saturation and starvation, which is worse than running 30% below the limit all day.

One more subtlety. Because ITPM ignores cache reads, the cost you reserve from the input bucket is **not** your prompt’s token count — it is the uncached tail plus any write you expect to perform. Reserving the full prefix every time throttles you to a fraction of your real capacity:

``` {.sourceCode .python}
def itpm_cost(prefix_tokens: int, tail_tokens: int, expect_hit: bool) -> int:
    # Cache reads generally do not draw down ITPM; writes do.
    return tail_tokens if expect_hit else prefix_tokens + tail_tokens
```

Spend-cap 429s are a different animal and must not be retried. They arrive with error type `rate_limit_error` but carry `error.details.error_code == "enforced_spend_limit_reached"`, have no `retry-after`, and keep failing until the month rolls over or the tier is raised. Branch on that field before any backoff loop, or SDK automatic retries will burn budget on requests that cannot succeed. A *user-set* spend limit is different again, arriving as a 400 `invalid_request_error`.

## 1.5 Partial failure in a fan-out

A fan-out over *n* items is the most common production shape and the most commonly mishandled, because “retry the failures” is not a policy. Four rules.

**Classify before you retry.** A 400 on item 37 will 400 forever. Retrying it consumes capacity that successful items need and delays the whole operation. Partition outcomes into *permanent*, *transient*, and *throttled*, and treat only the last two as retryable — with different backoff, since a throttled item is waiting on a bucket and a transient one is waiting on a server.

**Fail the operation on a budget, not on the first error.** Define success as a threshold and make it explicit in the contract. “94 of 100 succeeded” is legitimate for document extraction and catastrophic for financial reconciliation; the helper cannot know which, so it must be told.

**Retries share the concurrency budget.** A retry wave running at full concurrency alongside first attempts converts a partial outage into a self-inflicted thundering herd. Retries belong in the same semaphore, ideally at lower priority.

**Preserve per-item identity across attempts.** Results come back out of order in both a fan-out and a batch; match by a stable `custom_id`, never by position. In a batch that id must be unique and match `^[a-zA-Z0-9_-]{1,64}$`, and results arrive as JSON Lines in arbitrary order.

``` {.sourceCode .python}
from concurrent.futures import ThreadPoolExecutor, as_completed

PERMANENT = {"invalid_request_error", "authentication_error", "permission_error",
             "not_found_error", "request_too_large", "billing_error"}


@dataclass
class ItemResult:
    custom_id: str
    value: Any = None
    error_type: str | None = None
    attempts: int = 0
    request_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.error_type is None


def fan_out(items, call, *, concurrency=8, max_attempts=3,
            min_success_fraction=1.0) -> tuple[list[ItemResult], bool]:
    results: dict[str, ItemResult] = {i.custom_id: ItemResult(i.custom_id) for i in items}
    pending = list(items)

    for attempt in range(1, max_attempts + 1):
        if not pending:
            break
        retry: list = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(call, item): item for item in pending}
            for fut in as_completed(futures):
                item = futures[fut]
                rec = results[item.custom_id]
                rec.attempts = attempt
                try:
                    rec.value, rec.request_id = fut.result()
                    rec.error_type = None
                except anthropic.APIStatusError as exc:
                    rec.error_type = (exc.body or {}).get("error", {}).get("type", "api_error")
                    rec.request_id = getattr(exc, "request_id", None)
                    if rec.error_type not in PERMANENT:
                        retry.append(item)
                except Exception:
                    rec.error_type = "connection_error"
                    retry.append(item)
        pending = retry
        if pending:
            time.sleep(min(30.0, 2 ** attempt) * (0.5 + random.random()))

    succeeded = sum(1 for r in results.values() if r.ok)
    accepted = succeeded >= math.ceil(min_success_fraction * len(items))
    return list(results.values()), accepted
```

In the batch equivalent the taxonomy appears as result types: `succeeded`, `errored`, `canceled`, `expired`, of which only `succeeded` is billed. Within `errored`, an `invalid_request_error` means the body must be fixed before resubmission; anything else is safe to resend as-is. Because each `params` object is validated asynchronously, a malformed request is not rejected at submission — you find it twenty minutes later in the results file, which is an excellent argument for validating locally before submitting 100,000 of them.

## 1.6 Cost attribution

“What did this feature cost last month” is a question your finance team will ask and your logs will answer badly unless you design for it. There are three mechanisms, and only two of them are billing mechanisms.

  -------------------------------------------------------------------------------------------------------------------------------------------
  Mechanism               Granularity                                               Authoritative for billing?
  ----------------------- --------------------------------------------------------- ---------------------------------------------------------
  Workspaces              Per workspace, with per-workspace rate and spend limits   **Yes** — group the Cost API by `workspace_id`

  API keys                Per key                                                   **Yes** for usage — group the Usage API by `api_key_id`

  `metadata.user_id`      Per end user                                              **No** — abuse detection only
  -------------------------------------------------------------------------------------------------------------------------------------------

The third row is the one that catches people. `metadata.user_id` is an opaque external identifier, capped at 512 characters, explicitly documented as being for abuse detection, and explicitly documented as something that must not contain names, e-mail addresses or phone numbers. It is not a billing dimension and does not appear in the Usage or Cost reports. If you need per-user cost, you compute it yourself from response `usage` objects.

The practical architecture, then:

-   **Tenant** → workspace. You get real isolation, real per-tenant rate limits, cache isolation, and authoritative cost reporting grouped by `workspace_id`. Note that usage attributed to the *default* workspace reports `workspace_id: null`.
-   **Feature** → API key within the workspace. The Usage API groups by `api_key_id`, so one key per feature gives you a feature breakdown for free. Console playground usage reports `api_key_id: null`, since it is not tied to a key.
-   **User and request** → your own ledger, written from the response `usage` object at the moment of the call.

The ledger needs care because the `usage` object holds five billable quantities at different prices, so summing tokens is meaningless. Price each category separately:

``` {.sourceCode .python}
PRICES = {  # USD per token
    "claude-opus-5-5":   {"in": 4e-6,   "out": 20e-6,  "w5m": 5e-6,     "w1h": 8e-6,    "read": 0.20e-6},
    "claude-sonnet-5-5": {"in": 2e-6,   "out": 10e-6,  "w5m": 2.5e-6,   "w1h": 4e-6,    "read": 0.10e-6},
    "claude-fable-5-1":  {"in": 10e-6,  "out": 50e-6,  "w5m": 12.5e-6,  "w1h": 20e-6,   "read": 0.25e-6},
    "claude-haiku-5-5":  {"in": 0.10e-6, "out": 0.50e-6, "w5m": 0.125e-6, "w1h": 0.20e-6, "read": 0.01e-6},
}
HAIKU_LONG = {"in": 0.50e-6, "out": 2.50e-6, "w5m": 0.625e-6, "w1h": 1.00e-6, "read": 0.05e-6}


def price_usage(model: str, usage, *, batch: bool = False, geo_us: bool = False) -> float:
    reads = getattr(usage, "cache_read_input_tokens", 0) or 0
    creation = getattr(usage, "cache_creation", None)
    w5 = getattr(creation, "ephemeral_5m_input_tokens", 0) if creation else 0
    w1 = getattr(creation, "ephemeral_1h_input_tokens", 0) if creation else 0
    if not creation:
        w5 = getattr(usage, "cache_creation_input_tokens", 0) or 0
    plain = usage.input_tokens

    p = PRICES[model]
    if model == "claude-haiku-5-5" and (plain + reads + w5 + w1) > 100_000:
        p = HAIKU_LONG  # the whole request steps up, cache reads included

    total = (plain * p["in"] + usage.output_tokens * p["out"]
             + w5 * p["w5m"] + w1 * p["w1h"] + reads * p["read"])
    if batch:
        total *= 0.5
    if geo_us:
        total *= 1.1
    return total
```

Three details there are easy to get wrong and expensive to get wrong: the two write TTLs are priced differently and reported separately under `cache_creation`; the Haiku threshold is evaluated on *total* input including cache reads; and the batch discount and residency multiplier apply to the whole total, not to selected categories.

Reconcile against the Cost API monthly. Data typically appears within about five minutes — daily granularity for cost, down to one-minute buckets for usage — so a nightly job is practical. A persistent discrepancy is nearly always one of three things: streaming usage read from the wrong event, retried requests counted once instead of twice, or a `cache_creation` sub-field ignored.

## 1.7 End to end: a document-processing pipeline

The whole chapter in one system. A legal-tech product ingests contract bundles of 60 to 400 pages and produces, per contract, a structured summary plus answers to 45 standing diligence questions. Roughly 800 bundles a day, arriving unevenly. Results are promised within four hours; one interactive “ask this contract a question” feature promises first token in under two seconds.

**Stage 1 — Ingest.** PDFs go to the Files API once and are referenced by ID thereafter, so the bytes upload once rather than on all 45 questions. Token-count the assembled prefix before committing to a model; the result decides stage 2.

**Stage 2 — Routing.** A per-bundle decision, not a global one.

  -------------------------------------------------------------------------------------------------------------------------------
  Bundle prefix size      Model                                      Reason
  ----------------------- ------------------------------------------ ------------------------------------------------------------
  \< 90,000 tokens        Haiku 5.5, `effort: "medium"`              Comfortably under the 100K cliff; \$0.10/MTok

  90,000–110,000          Sonnet 5.5                                 Too close to the cliff to risk a 5× step on a mis-estimate

  \> 110,000 tokens       Sonnet 5.5, Opus 5.5 for flagged bundles   1M window, flat pricing
  -------------------------------------------------------------------------------------------------------------------------------

The middle row is the interesting one: a bundle estimated at 97,000 tokens whose true count is 101,000 costs 5× what you projected. The margin exists because estimates are estimates.

**Stage 3 — Warm, then fan out.** Per bundle: one pre-warm request with a one-hour breakpoint on the document prefix, awaited to completion, then the 45 questions as a batch. One hour rather than five minutes because break-even is a 51% hit rate and we expect 45 of 46 to hit, while arbitrary batch ordering makes a five-minute window genuinely risky.

Arithmetic for one 200,000-token bundle on Sonnet 5.5:

-   Naive, no cache, no batch: 46 × 200,000 × \$2/MTok = **\$18.40**
-   One-hour cache, no batch: (200,000 × 2.0 + 45 × 200,000 × 0.05) × \$2/MTok = (400,000 + 450,000) × \$2/MTok = **\$1.70**
-   One-hour cache plus batch: **\$0.85**

A 21.6× reduction, of which 10.8× is caching and 2× batching. Across 800 bundles a day that is \$14,720 against \$680 — \$5.4 million a year against \$248,000, running every day. The arithmetic is not an optional appendix.

**Stage 4 — Interactive path.** The same cached prefix serves the interactive feature, but synchronously and streamed, because a human is waiting. Two consequences: the interactive path must never warm a cold prefix, since it would pay a 200,000-token write while the user waits; and it must use the *same* model, effort, tool list and `output_config.format` as the batch path, or it misses. Against a cold bundle, serve uncached and warm asynchronously — paying 1× once beats making the user wait for a write.

**Stage 5 — Rate-limit shaping.** Batch submissions draw on batch limits; interactive traffic draws on standard ITPM and OTPM, so keep two limiters. The interactive one reserves only the uncached tail against ITPM, which is what makes a 200,000-token interactive prefix affordable in capacity terms at all.

**Stage 6 — Accounting.** Each tenant is a workspace; the batch pipeline and the interactive feature hold separate API keys inside it. Every response’s `usage` is priced by the function above into a ledger keyed by tenant, feature, bundle and request ID, reconciled nightly against the Cost API grouped by `workspace_id`.

**Stage 7 — The metrics that matter.** Not request count and p99. These:

  --------------------------------------------------------------------------------------------------------------------------------
  Metric                                 Why                                   Alert on
  -------------------------------------- ------------------------------------- ---------------------------------------------------
  Cache hit rate, by prefix layer        Drives both cost and effective ITPM   10-point drop week over week

  `cache_miss_reason` distribution       Names the regression                  Any `system_changed` or `tools_changed` appearing

  Cost per bundle                        Catches routing regressions           1.5× the trailing median

  Haiku requests over 100K tokens        Silent 5×                             Any sustained non-zero rate

  ITPM headroom from headers             Capacity                              Remaining below 20% of limit

  429 rate split by spend-cap vs. rate   Different responses entirely          Any spend-cap 429 at all
  --------------------------------------------------------------------------------------------------------------------------------

That `cache_miss_reason` row deserves a note, being the newest and most useful debugging surface here. Pass `diagnostics: {"previous_message_id": <previous response id>}` on each turn and the API compares request fingerprints and names *where* two consecutive requests diverged: `model_changed`, `system_changed`, `tools_changed`, `messages_changed`, or the two non-answers `previous_message_not_found` and `unavailable`. The `*_changed` variants carry `cache_missed_input_tokens`, an estimate of lost cacheable prefix derived from byte lengths — a magnitude, not a billing figure. Only the *earliest* divergence is reported, so fix them one at a time. Combine it with `usage.cache_read_input_tokens`: diagnostics answers “did my request change?”, usage answers “did the cache hit?”, and only together do they distinguish a prefix-assembly bug from an expired entry.

Every individual decision above is unremarkable. What makes the pipeline work is that each one was made with a number attached — a break-even hit rate, a 100,000-token threshold, a 51% requirement, a 21.6× total — rather than with an adjective. That habit is the actual subject of this chapter.

## Practice Questions

**V1.1** A service sends 1,000 requests per hour against a 30,000-token stable prefix on Sonnet 5.5 (\$2.00/MTok input). Requests arrive at random intervals, and measurement shows a 35% cache hit rate with a five-minute TTL. Switching to a one-hour TTL raises the measured hit rate to 88%. Which statement is correct?

A. Both configurations are above break-even, and the one-hour configuration is the cheaper of the two. B. The five-minute configuration is already below break-even, and the one-hour configuration is above it. C. Both configurations are above break-even, but the five-minute configuration is cheaper because its write multiplier is lower. D. The one-hour configuration is below break-even because its break-even hit rate exceeds 88%.

**V1.2** Your team reduces `max_tokens` from 64,000 to 4,096 across all requests, hoping to relieve persistent 429 errors that the response body attributes to the output-token limit. What should you expect?

A. OTPM consumption falls immediately, because OTPM is reserved from `max_tokens` at request start. B. OTPM consumption is unchanged, because OTPM counts only tokens actually generated. C. OTPM consumption falls only for streaming requests, where reservation is incremental. D. ITPM consumption falls, because `max_tokens` is included in the input-token estimate.

**V1.3** A 180,000-token corpus is cached on Haiku 5.5 and read by 400 requests, each adding a 500-token question. Which is the most accurate cost statement for a single cache-hit request’s input?

A. 180,000 tokens are billed at \$0.01/MTok and 500 at \$0.10/MTok. B. 180,000 tokens are billed at \$0.01/MTok and 500 at \$0.50/MTok, because the threshold applies only to uncached input. C. All 180,500 tokens are billed at \$0.05/MTok, since cache reads are not separately discounted above the threshold. D. 180,000 tokens are billed at \$0.05/MTok and 500 at \$0.50/MTok.

**V1.4** You fan out 60 requests simultaneously against a 150,000-token prefix that is not yet cached, each with a cache breakpoint on the prefix. What happens?

A. One request writes the cache and the other 59 read it, because the breakpoint is identical. B. The first 20 write and the remaining 40 read, because the lookback window covers 20 positions. C. All 60 requests write the cache, because an entry becomes readable only after the first response begins. D. The requests are serialised server-side so that only one write is billed.

**V1.5** (Select TWO) Which two changes to a mid-conversation request will invalidate a cache breakpoint placed at the end of the top-level `system` field?

A. Reordering the entries in the `tools` array. B. Appending a new user message to the end of `messages`. C. Changing `output_config.format` to add a field to the schema. D. Increasing `max_tokens` from 4,096 to 8,192. E. Changing `metadata.user_id`.

**V1.6** An organization on the Scale tier has 10,000,000 ITPM for Sonnet 5.5. Its workload sends requests whose prefix is a 400,000-token cached document plus a 2,000-token tail, and the cache hit rate is 100%. Ignoring RPM, roughly how many such requests per minute can it sustain before hitting the input limit?

A. 5,000, because each request’s billable input is the 2,000-token tail. B. 25, because each request’s total input is 402,000 tokens. C. Unlimited with respect to ITPM, because cache reads are exempt and the tail is negligible. D. Approximately 24, because the ITPM estimate at request start uses the full prompt.

**V1.7** Which statement about `metadata.user_id` is correct?

A. It is a billing dimension and can be passed to `group_by[]` in the Usage API. B. It is used for abuse detection and is not available as a usage or cost grouping dimension. C. It must contain a stable e-mail address so that per-user limits can be enforced. D. It replaces per-workspace attribution for organizations with more than 100 tenants.

**V1.8** A batch of 20,000 requests shares a 120,000-token prefix. Which submission strategy minimises total cost?

A. Submit all 20,000 at once with a five-minute breakpoint on the prefix. B. Submit all 20,000 at once with a one-hour breakpoint on the prefix. C. Send one ordinary request with a one-hour breakpoint, wait for it to complete, then submit the batch with the same breakpoint. D. Send one batch request with `max_tokens: 0` to pre-warm, then submit the remaining 19,999.

**V1.9** On Opus 5.5, a 50,000-token prefix is written once with a five-minute TTL and then read exactly once before expiring. Relative to sending both requests with no caching at all, what is the cost effect on input tokens?

A. A saving of about 35%. B. A saving of about 65%. C. A penalty of about 25%. D. A saving of about 10%.

**V1.10** (Select TWO) Which two combinations are *not* supported together?

A. Prompt caching and the Message Batches API. B. `max_tokens: 0` pre-warming and `output_config.format`. C. Prompt caching and `inference_geo: "us"`. D. Fast mode and the Message Batches API. E. Structured output and streaming.

**V1.11** Your client-side limiter enforces 5,000 RPM by allowing 5,000 requests in each wall-clock minute, resetting on the minute boundary. You observe 429s in the first few seconds of most minutes and idle capacity at the end. What is the correct diagnosis?

A. The RPM limit is actually lower than 5,000 for your tier. B. `retry-after` is being ignored, which causes the server to reduce your limit. C. The 429s come from ITPM, not RPM, because input is estimated at request start. D. The server uses continuous replenishment, so a windowed counter permits bursts the server rejects.

**V1.12** A request returns 429 with error type `rate_limit_error`, no `retry-after` header, and `error.details.error_code` set to `enforced_spend_limit_reached`. What is the correct handling?

A. Retry with exponential backoff and jitter, up to the usual retry budget. B. Retry immediately against a different model, since the limit is per model class. C. Stop retrying; the condition persists until the monthly cap resets or the tier is raised. D. Treat it as a transient capacity error and open the circuit breaker.

**V1.13** A multi-tenant application serves 300 tenants from a single workspace, with a 5,000-token global prefix and a per-tenant 8,000-token prefix. Which breakpoint layout best balances hit rate against the four-breakpoint limit?

A. One breakpoint at the end of the combined global-plus-tenant prefix. B. One breakpoint after the global prefix, one after the tenant prefix, one after the session documents, leaving one for a sliding history window. C. Four breakpoints spread evenly through the message history, with none in `system`. D. One breakpoint per tenant document, up to four, with the global prefix uncached.

**V1.14** Which statement about the `anthropic-ratelimit-tokens-remaining` header is correct?

A. It is the sum of the input and output remaining values in all cases. B. It is present only on 429 responses. C. It is exact to the token and suitable for precise client-side reservation. D. It reflects whichever limit is currently most restrictive, including a workspace limit.

**V1.15** (Select TWO) A fan-out over 500 items returns 480 successes, 15 failures with `overloaded_error`, and 5 failures with `invalid_request_error`. Which two actions are appropriate?

A. Retry the 15 `overloaded_error` items with exponential backoff within the existing concurrency budget. B. Retry all 20 failures together at full concurrency to finish sooner. C. Surface the 5 `invalid_request_error` items as permanent failures without retrying them. D. Open the circuit breaker on the basis of the 5 `invalid_request_error` items. E. Reduce the concurrency limit permanently to the number of successful items divided by the elapsed seconds.

**V1.16** A 200,000-token bundle is queried 45 times on Sonnet 5.5 (\$2.00/MTok input). Compare (i) no caching and no batch, against (ii) a one-hour cache write plus 45 cache-hit reads, submitted as a batch. Ignoring output and tail tokens, what is the approximate ratio of (i) to (ii)?

A. About 4×. B. About 11×. C. About 21×. D. About 45×.

**V1.17** An interactive feature shares a cached prefix with a batch pipeline but consistently misses the cache. The batch pipeline sets `output_config.effort` to `"medium"`; the interactive path omits it. Both run on Sonnet 5.5. What is the most likely explanation?

A. Effort is not part of the cached prefix, so the cause must be elsewhere. B. Effort is rendered into the prompt, and Sonnet 5.5 defaults to `high`, so the two prefixes differ. C. Interactive requests cannot read entries written by batch requests. D. Streaming requests cannot read cache entries written by non-streaming requests.

**V1.18** Which workload is the strongest candidate for the one-hour cache TTL rather than the five-minute default?

A. A nightly evaluation harness that runs 2,000 prompts against a fixed 90,000-token rubric over 40 minutes. B. A chat product where 20% of sessions send a second message within five minutes. C. A webhook handler that processes one event at a time with no shared prefix. D. A search feature whose prefix changes on every request because it embeds the query.

**V1.19** (Select TWO) You need authoritative monthly cost broken down by tenant and by feature. Which two mechanisms give you that directly from Anthropic’s reporting?

A. `metadata.user_id` set to a tenant identifier, grouped in the Cost API. B. A `stop_sequences` value unique to each feature. C. One workspace per tenant, with the Cost API grouped by `workspace_id`. D. One API key per feature, with the Usage API grouped by `api_key_id`. E. Separate `anthropic-version` headers per feature.

**V1.20** (Select TWO) Which two statements about the `diagnostics` / `cache_miss_reason` mechanism are correct?

A. A `cache_miss_reason` of `previous_message_not_found` indicates that your request’s prefix changed. B. The API stores a fingerprint only for requests that include the `diagnostics` object. C. The response reports every divergence point found, ordered from earliest to latest. D. `cache_missed_input_tokens` is derived from byte lengths and should be read as a magnitude rather than a billing figure. E. Diagnostics can cause the request itself to fail when the comparison is unavailable.
