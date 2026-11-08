# Exam 6 — Scale and Latency

**Instructions.** 53 questions, 120 minutes, closed book. Single-answer questions have four options; multiple-response questions are marked “(Select TWO)” or “(Select THREE)” and are scored all-or-nothing. Answers and worked explanations are in the back of the volume.

Every scenario in this exam is set in consumer-scale, latency-critical engineering: high request rates, strict tail-latency budgets, mobile clients, streaming interfaces, and cost that only matters because it is multiplied by volume.

> **This is the hardest tier in this book.** Exams 5 and 6 are deliberately calibrated above the real exam. A score here is a diagnostic of depth, not a predicted exam result — do not read it as one.

## Section 1 — Applications and Integration

**E6.1.** A consumer chat app has a p99 time-to-first-token budget of 400 ms. The team enables `speed: "fast"` on `claude-opus-5-5` across the whole endpoint to meet it, accepting the higher price. TTFT does not move.

What is wrong?

-   **A.** Fast mode is not available with the Message Batches API, so the streaming path and the background path now behave differently.
-   **B.** Fast mode raises output tokens per second and explicitly does not improve time to first token; TTFT is driven by the uncached prompt the model must process before generating, so the work belongs in cache hit rate, prefix size and model tier.
-   **C.** Fast mode has a dedicated rate limit separate from standard Opus limits, and the endpoint is being throttled against it.
-   **D.** Switching between fast and standard speed invalidates the prompt cache, so the endpoint is paying a cache write it did not pay before.

**E6.2.** A streaming interface must render the first 120 tokens of a response within a p99 budget of 1,800 ms. Measured TTFT on `claude-opus-5-5` is 500 ms and standard output throughput is 60 tokens per second. The team enables `speed: "fast"` and achieves the documented maximum throughput gain.

What is the p99 time to render the first 120 tokens?

-   **A.** 1,000 ms
-   **B.** 2,500 ms
-   **C.** 800 ms
-   **D.** 1,300 ms

**E6.3.** A request-routing layer runs on `claude-haiku-5-5` at 40,000,000 requests per day. A 900-token router prompt sits behind a cache breakpoint and, in steady state, is read on effectively every request. Each request adds 120 uncached input tokens and produces 40 output tokens.

What is the approximate daily cost?

-   **A.** \$1,640.00
-   **B.** \$4,880.00
-   **C.** \$1,280.00
-   **D.** \$8,200.00

**E6.4.** A mobile autocomplete endpoint places its 300-token system prompt behind a `cache_control` marker and reports no cost change at all after the deployment. No error appears in the logs.

What is happening?

-   **A.** The 20-block lookback window cannot reach a breakpoint placed at the start of the system prompt.
-   **B.** A single top-level `cache_control` consumes one of four breakpoint slots, which the endpoint has already used.
-   **C.** 300 tokens is below the 512-token minimum cacheable length on current models, so the prompt is processed without caching and no error is returned; `cache_creation_input_tokens` and `cache_read_input_tokens` will both be 0.
-   **D.** The default 5-minute TTL expires between requests at this endpoint’s arrival rate.

**E6.5.** To create headroom against output-token-per-minute throttling at peak, a team clamps `max_tokens` to 256 on every request across a consumer endpoint. Answers are now truncated and the throttling is unchanged.

What is wrong?

-   **A.** ITPM is estimated when a request starts and adjusted to the actual count during the request, so the clamp affects the wrong limit.
-   **B.** `max_tokens` does not factor into OTPM, which is evaluated in real time against tokens actually produced; the clamp buys no rate-limit headroom and only truncates output.
-   **C.** The `anthropic-ratelimit-*-remaining` token headers are rounded to the nearest thousand, so the measurement that motivated the clamp was too coarse.
-   **D.** The `tokens-*` headers report the most restrictive limit in effect, which may be ITPM rather than OTPM.

**E6.6.** (Select THREE) Which three measures genuinely reduce p99 latency on a high-QPS streaming endpoint?

-   **A.** Keep the uncached suffix after the last breakpoint small, so each request processes fewer new tokens before generation begins.
-   **B.** Stream the response so the client renders progressively rather than waiting for the complete message.
-   **C.** Route the short-answer majority of traffic to `claude-haiku-5-5` and escalate to a larger model only on an application-side signal.
-   **D.** Raise `max_tokens` so the request is never truncated mid-answer.
-   **E.** Set `inference_geo: "us"` so requests are served from closer infrastructure.
-   **F.** Set `temperature: 0` so the model commits to tokens more quickly.

**E6.7.** A consumer endpoint uses `output_config.format`. First use of a schema costs about 600 ms of grammar compilation, and compiled grammars are cached for 24 hours from last use. The endpoint has 50 distinct schemas; those in the long tail are each used about once every 30 hours.

What fraction of long-tail requests pay the compilation cost?

-   **A.** About 2%, since only the first use of each schema compiles.
-   **B.** About 4%.
-   **C.** 0%, since compiled grammars persist once built.
-   **D.** 100%, because the 24-hour grammar cache expires between uses.

**E6.8.** A mobile client sets `output_config.effort: "low"` for short prompts and `"high"` for long ones, switching between them inside a single conversation thread to trade latency against quality. Cache hit rate on the thread collapses.

What explains it?

-   **A.** Changing `output_config.effort` between requests restarts the prompt cache; the `mid-conversation-output-config-2026-07-01` beta preserves it, and otherwise effort should be fixed for the life of a thread.
-   **B.** `claude-sonnet-5-5` defaults to `high` effort, so the `"low"` requests are the ones diverging from the default.
-   **C.** Setting effort explicitly to the model’s own default does not invalidate the cache.
-   **D.** Effort belongs in `output_config` rather than inside `thinking`, and a misplaced value is silently ignored.

**E6.9.** A consumer endpoint has an input-tokens-per-minute limit of 4,000,000. Each request reads 250,000 tokens from cache, writes 1,200 tokens to cache, and carries 800 uncached input tokens. Peak traffic is 1,500 requests per minute.

Is ITPM the binding constraint at peak?

-   **A.** Yes; 378,000,000 tokens per minute far exceeds the limit.
-   **B.** Yes; cache writes alone consume 1,800,000, and reads take the rest.
-   **C.** No; 3,000,000 tokens per minute are consumed, leaving headroom for roughly 500 more requests per minute.
-   **D.** No; only 1,200,000 tokens per minute are consumed, since cache writes do not count.

**E6.10.** A mobile client retries any request that exceeds a 5-second client timeout, on the assumption that a timed-out request did not reach the model. At peak the team sees duplicate charges and, occasionally, two different answers delivered for one user action.

What is wrong?

-   **A.** HTTP 529 `overloaded_error` indicates capacity rather than a rate limit, and the client does not distinguish it.
-   **B.** The Messages API has no idempotency key, so a request that completed server-side after the client gave up is billed and generated again on retry; deduplication must be keyed in the application.
-   **C.** The `retry-after` header must be honoured, and a fixed 5-second client timeout ignores it.
-   **D.** The SDK already retries twice by default, so the client’s retry is the third attempt.

**E6.11.** A nightly recommendation refresh scores 3,000,000 items on `claude-sonnet-5-5`, at 1,500 input tokens and 250 output tokens per item, with no caching. The team is deciding between the synchronous Messages API and the Message Batches API.

What does the batch route change?

-   **A.** It saves \$8,250, and results return in submission order so the existing positional loader can stay.
-   **B.** It saves \$16,500, which is the whole synchronous cost.
-   **C.** It saves \$4,125, a 25% discount on a job of this size.
-   **D.** It saves \$8,250, but results may arrive in any order and only within a 24-hour window, so the loader must join on `custom_id` and the refresh must tolerate that window.

**E6.12.** A mobile session on `claude-opus-5-5` sends requests with `speed: "fast"` and `max_retries=0`, falling back to a standard-speed retry whenever a fast-mode 429 is returned. Sessions that hit the fallback show a large latency and cost spike on the fallback turn and on every turn after it.

What explains it?

-   **A.** Switching between fast and standard speed invalidates the prompt cache, so the fallback turn reprocesses the whole prefix at write prices and the session never recovers its hit rate; pinning one speed per session avoids it.
-   **B.** Fast mode has a dedicated rate limit with its own `anthropic-fast-*` headers, which the client is not reading.
-   **C.** `max_retries=0` also disables retries for transient 5xx and overloaded errors, which must be handled separately.
-   **D.** `usage.speed` reports which speed actually served the request, and the client is not recording it.

**E6.13.** (Select TWO) Which two signals let a client confirm it received fast-mode capacity and how much fast-mode headroom remains?

-   **A.** `usage.speed` in the response body.
-   **B.** `anthropic-fast-output-tokens-remaining`.
-   **C.** `anthropic-ratelimit-output-tokens-remaining`.
-   **D.** `anthropic-priority-output-tokens-remaining`.
-   **E.** `usage.inference_geo`.

**E6.14.** A mobile client uploads camera photographs at their native 3,024 × 4,032 pixels. The team proposes downscaling to 1,008 × 1,344 on device before upload.

Using the documented image token formula, what are the per-image token counts and the reduction factor?

-   **A.** 15,552 → 1,728, a 3x reduction.
-   **B.** 4,320 → 480, a 9x reduction.
-   **C.** 15,552 → 1,728, a 9x reduction.
-   **D.** 15,552 → 5,184, a 3x reduction.

**E6.15.** A streaming mobile endpoint on `claude-opus-5-5` loses connections regularly on cellular networks. On disconnect the client re-sends the original request from the beginning, so users see the answer restart.

What should it do instead?

-   **A.** Prefill an assistant turn with the text already received, so the model continues from that point.
-   **B.** Raise `max_tokens` so the generation has room to complete before the connection drops.
-   **C.** Fall back to a non-streaming request, which completes in one round trip and cannot be interrupted partway.
-   **D.** Resume with a user-message continuation carrying what was already delivered, which is the resumption form for 4.6 and later models — noting that tool-use and thinking blocks are not partially recoverable, so a break inside one must restart from the last complete block.

**E6.16.** A chat endpoint adds a new `cache_control` breakpoint at the end of every turn, “so the tail of the conversation always stays warm”. After a few turns, requests start returning HTTP 400.

What is wrong?

-   **A.** The 20-block lookback window is exceeded once the conversation grows past 20 blocks.
-   **B.** A prompt may carry at most four breakpoints, and a fifth returns 400; a small fixed set of breakpoints plus the 20-block lookback is the intended pattern.
-   **C.** One-hour entries must precede five-minute entries, and turn-by-turn breakpoints interleave them.
-   **D.** Cache writes count toward ITPM, so a breakpoint per turn exhausts the input-token limit.

**E6.17.** A `claude-sonnet-5-5` request mixes cache TTLs. Billing positions resolve as follows: the highest cache hit is at 150,000 tokens, the highest 1-hour breakpoint after it is at 170,000 tokens, and the last breakpoint is at 182,000 tokens.

What does this request’s cache billing come to?

-   **A.** \$0.125
-   **B.** \$0.455
-   **C.** \$0.0182
-   **D.** \$0.113

**E6.18.** (Select THREE) Which three reduce the per-request bill on a 40,000,000-request-per-day `claude-haiku-5-5` endpoint without changing the model?

-   **A.** Keep the total prompt — including cache reads and writes — below 100,000 tokens so the 5x long-context rate never applies.
-   **B.** Move repeated content above the last breakpoint so it bills at the cache-read rate rather than the input rate.
-   **C.** Move the non-interactive share of traffic to the Message Batches API for 50% off, which stacks with caching.
-   **D.** Enable `speed: "fast"` to finish requests sooner and spend less time generating.
-   **E.** Set `inference_geo: "us"` to serve requests from a cheaper geography.
-   **F.** Raise `max_tokens` so requests are not retried after truncation.

## Section 2 — Model Selection and Optimization

**E6.19.** A classifier routes traffic: every request is first sent to `claude-haiku-5-5`, and 5% are escalated to `claude-opus-5-5`, which re-runs the work from scratch. Both models see 2,000 input tokens and produce 150 output tokens. There is no caching.

What is the blended per-request cost?

-   **A.** \$0.000275
-   **B.** \$0.000811
-   **C.** \$0.000825
-   **D.** \$0.011000

**E6.20.** A design review proposes `claude-fable-5-1` for a mobile reply-suggestion endpoint with a 600 ms p99 budget and tens of millions of requests per day, on the grounds that it is the strongest available model.

What must the reviewer say?

-   **A.** Fable 5.1 is the slowest tier, defaults to `high` effort, costs \$10/\$50 per MTok, and fast mode is not available on it; a high-volume, latency-critical suggestion path belongs on Haiku 5.5 or Sonnet 5.5.
-   **B.** All four current models offer a 1M context window and 128K maximum output, so context is not the differentiator here.
-   **C.** Fable 5.1 has adaptive thinking that is always on, which the endpoint cannot disable.
-   **D.** Effort can be lowered to `low`, which narrows the latency gap against the smaller models.

**E6.21.** A team migrates a streaming endpoint from `claude-opus-5-5` to `claude-sonnet-5-5` for the lower per-token price, leaving every other parameter unchanged. p99 latency rises and the bill falls far less than projected.

Which fact explains both observations?

-   **A.** Cache reads are 0.05x of base on both models, so the caching saving the projection assumed does not materialise.
-   **B.** Both models have a 1M context window, so the prompt is processed identically and the difference must lie in the client.
-   **C.** Fast mode is not available on Sonnet 5.5, so the throughput the endpoint previously had is lost.
-   **D.** Sonnet 5.5 defaults to `high` effort while Opus 5.5 defaults to `medium`, so leaving effort unspecified produces more reasoning output on Sonnet 5.5 — more output tokens, billed and generated.

**E6.22.** (Select TWO) Which two statements about `speed: "fast"` are correct for a consumer-scale deployment?

-   **A.** It has a dedicated rate limit separate from standard Opus limits, surfaced through `anthropic-fast-*` response headers.
-   **B.** It is unavailable with the Message Batches API and with a Priority Tier commitment.
-   **C.** It reduces time to first token by up to 2.5x.
-   **D.** It is available on `claude-haiku-5-5`, which is the right pairing for the highest request rates.
-   **E.** Prompt-caching multipliers do not stack with fast-mode pricing, so cached prefixes are billed at standard rates.

**E6.23.** A response on `claude-opus-5-5` consumes 3,000 uncached input tokens and produces 2,500 output tokens. The team compares standard speed with `speed: "fast"`.

What is the cost multiplier, and what does it buy?

-   **A.** 1.6x, buying lower time to first token.
-   **B.** Exactly 2.0x, buying up to 2.5x output tokens per second, with no change to time to first token and no change to model behaviour.
-   **C.** 2.5x, matching the throughput gain.
-   **D.** Exactly 2.0x, buying up to 2.5x output tokens per second together with a proportional reduction in time to first token.

**E6.24.** To improve conversational continuity at peak, a `claude-haiku-5-5` endpoint begins appending the last 40 turns of history to every request. Token volume rises by about 40%; the bill rises by far more, and only on some requests.

What explains it?

-   **A.** Cache reads do not count toward ITPM, so the rate-limit headroom masked the cost increase until it was large.
-   **B.** Context editing could trim the history server-side, which the endpoint is not using.
-   **C.** On some requests the total prompt — including cache reads and writes — crosses 100,000 tokens, and those requests pay 5x on both input and output, with the tier decided per request.
-   **D.** Haiku 5.5 has a 1M context window, so the history fits and the cost increase must come from output.

**E6.25.** (Select THREE) Which three statements about cache-read pricing are correct?

-   **A.** Cache reads are 0.05x of base input price on `claude-opus-5-5` and `claude-sonnet-5-5`.
-   **B.** Cache reads are 0.025x of base input price on `claude-fable-5-1`.
-   **C.** Cache reads are 0.1x of base input price generally, including on `claude-haiku-5-5`.
-   **D.** Cache reads are 0.1x of base input price on all current models.
-   **E.** Cache-read pricing does not stack with the Message Batches discount.
-   **F.** Cache reads count toward ITPM on all current models.

**E6.26.** A latency-critical endpoint must choose between `claude-opus-5-5` at `low` effort and `claude-haiku-5-5` at its default effort. The team’s eval shows the two at quality parity on this task, and prompts stay well under 100,000 tokens.

Which choice is correct and why?

-   **A.** Haiku 5.5, because at parity it is 40x cheaper on both input and output and is the fastest tier; the only caution is to keep prompts below the 100,000-token threshold, which this workload already does.
-   **B.** Opus 5.5 at `low` effort, because a larger model at reduced effort degrades more gracefully under unusual input.
-   **C.** Opus 5.5, because `low` effort reduces output tokens enough to close the price gap.
-   **D.** Haiku 5.5, because it is the only current model on which fast mode is available.

**E6.27.** A service configuration reads `model: "claude-opus-5-5"` with the comment: “alias — picks up the newest snapshot automatically, so no migration work is needed.”

What must the reviewer say?

-   **A.** The Models API exposes a `line` field that should be read rather than parsing the model ID.
-   **B.** Lifecycle status is published on the model deprecations page, which the team should monitor.
-   **C.** Anthropic commits to a minimum of 60 days’ notice before deprecation, which is enough time to react.
-   **D.** Dateless IDs on 4.6 and later are fixed snapshots rather than aliases, so this never auto-upgrades; a migration has to be planned, with the 60-day minimum deprecation notice as the outer bound on reaction time.

## Section 3 — Agents and Workflows

**E6.28.** To cut wall-clock latency on a consumer agent, a design fans out 200 concurrent subagents per user request. Measured latency improves far less than projected, and the service begins hitting its input-token-per-minute limit at a fraction of the expected QPS.

What explains both symptoms?

-   **A.** Default subagent depth is 3, so most of the fan-out never runs.
-   **B.** Default subagent concurrency is 20, so the remaining children queue rather than running in parallel; and each child is a full request, so the fan-out multiplies ITPM consumption per user request.
-   **C.** Subagents inherit the parent’s permission mode, so their tool calls are denied and retried.
-   **D.** `max_turns` counts tool-use turns only, so the subagents exceed their turn budgets.

**E6.29.** An Agent SDK session on `claude-opus-5-5` sets `max_budget_usd: 0.50` and runs until the budget stops it. Each tool-use turn reads 16,000 tokens from cache, carries 2,000 uncached input tokens, and produces 900 output tokens.

When does the budget stop the run, and at what cumulative spend?

-   **A.** After the 17th turn, at \$0.4964.
-   **B.** Exactly at \$0.5000, because the budget is a hard pre-request cap.
-   **C.** After the 18th turn, at \$0.5256, because `max_budget_usd` is checked after a response arrives and therefore overshoots.
-   **D.** After the 18th turn, at \$0.5000, with the excess absorbed rather than billed.

**E6.30.** A consumer shopping agent runs long sessions with `clear_tool_uses_20250919` at its defaults. p99 latency is acceptable most of the time but spikes sharply and periodically, always on a turn following heavy tool use.

What is happening, and what is the fix?

-   **A.** Every clearing event invalidates the cached prefix, so the next request pays a cache write over a very large prefix — that is the spike. Set `clear_at_least` so each clearing recovers enough to be worth the write, and raise the trigger.
-   **B.** The default `keep` of 3 tool uses is discarding results the agent then re-fetches.
-   **C.** `context_management.applied_edits` appears in the final `message_delta`, so the spikes are only visible after the fact.
-   **D.** The token counting endpoint reports `original_input_tokens` alongside `input_tokens`, which the team should use to preview savings.

**E6.31.** (Select TWO) A consumer agent must never block waiting for a human. Which two statements are correct?

-   **A.** `permissionMode: "dontAsk"` converts any call that would otherwise prompt into a denial without invoking `canUseTool`, giving a fixed tool surface and no blocking.
-   **B.** A tool approved by a bare `allowedTools` entry never reaches `canUseTool`, so a check that must run on every call belongs in a `PreToolUse` hook.
-   **C.** `permissionDecision: "defer"` is the right choice, because the deferred call resolves automatically when no reviewer responds.
-   **D.** `permissionMode: "auto"` never blocks and never denies, because a classifier resolves every action.
-   **E.** `allowedTools` constrains `bypassPermissions`, so the two can be combined to get a non-blocking, restricted agent.

**E6.32.** Which statement about `stop_reason: "tool_deferred"` is correct for a latency-critical consumer path?

-   **A.** The turn continues server-side while the approval is pending, so the request’s latency is unbounded.
-   **B.** The deferral is resolved by resending the request with `permissionMode` relaxed.
-   **C.** Deferral adds a fixed, bounded delay and is therefore safe inside a request-scoped budget.
-   **D.** The turn ends and the application must hold the message history and resume later with a `tool_result`, so the wait is unbounded in wall-clock terms; deferral belongs in an asynchronous flow, not on a request with a p99 budget.

**E6.33.** A consumer agent is deployed with no `max_turns` set and a 2-second p99 budget on the user-visible request. Median latency is fine; the tail is terrible and unbounded.

What is wrong?

-   **A.** Without `max_turns`, a single request can run through an arbitrary number of tool-use turns, each a full model round trip, so the tail has no ceiling; cap `max_turns` — which counts tool-use turns only — and degrade gracefully when it is reached.
-   **B.** `max_budget_usd` should be used instead, since it bounds cost and latency together.
-   **C.** Default subagent concurrency is 20, which bounds the fan-out but not the depth.
-   **D.** Permission prompts are blocking, and without a mode the agent will wait for a callback that never answers.

**E6.34.** A consumer agent runs on a path with a 2,000 ms budget. Time to first token is 400 ms per turn. Output throughput is 150 tokens per second. Each tool-use turn emits 120 output tokens and the tool itself takes 150 ms. The closing text-only turn emits 200 output tokens.

How many tool-use turns fit inside the budget?

-   **A.** One, at about 1,750 ms.
-   **B.** One, at exactly 2,000 ms.
-   **C.** Zero — the closing turn alone costs about 1,733 ms, and a single tool-use turn adds 1,350 ms for about 3,083 ms in total.
-   **D.** Two, at about 1,950 ms.

**E6.35.** A consumer agent adds a `PreToolUse` hook that calls an external policy service over the network to authorise each tool call. Correctness improves; p99 latency rises by more than the policy service’s own response time.

What explains it?

-   **A.** Hooks run before every other step in the permission flow and on every tool call, so the hook’s latency lands on the critical path of every turn, multiplied by the number of turns; cache the decision locally and scope the hook to the tools that need it.
-   **B.** A hook that returns `allow` does not skip the deny and ask rules, so each call is evaluated twice.
-   **C.** Hook denies apply even in `bypassPermissions`, which forces the session out of its fast path.
-   **D.** The hook runs in a subprocess whose startup cost exceeds the policy service’s response time.

## Section 4 — Prompt and Context Engineering

**E6.36.** A chat endpoint sends 500 tokens of tool definitions, a 2,000-token system prompt, and a 40-turn history of 300 tokens per turn. Its single `cache_control` breakpoint sits at the end of the system prompt. The team proposes moving the breakpoint to the end of turn 38.

What happens to the ITPM-counted tokens per request in steady state?

-   **A.** 14,500 before, 600 after.
-   **B.** 12,000 before, 2,500 after.
-   **C.** 12,000 before, 13,900 after.
-   **D.** 12,000 before, 600 after — a 20x reduction.

**E6.37.** (Select TWO) Which two measures shrink the uncached suffix on a streaming chat endpoint?

-   **A.** Place the last breakpoint after the stable part of the conversation history, so only genuinely new turns fall outside the cached prefix.
-   **B.** Keep per-request volatile values — timestamp, locale, device model — out of the cached prefix and put them in the first message after the last breakpoint.
-   **C.** Add a fifth `cache_control` breakpoint so more of the prompt is covered.
-   **D.** Set `inference_geo: "us"` so the prefix is cached closer to the client.
-   **E.** Raise `max_tokens` so fewer requests are needed per answer.

**E6.38.** A personalisation feature toggles web search on and off per user within a single conversation thread. The 50,000-token system corpus, which never changes, misses on every toggle.

What explains it?

-   **A.** Toggling web search changes the tool definitions, which invalidates the tools cache and everything after it.
-   **B.** Toggling web search or citations preserves the tools cache but invalidates the system and message caches, because the hierarchy runs tools → system → messages; the toggle must be held constant for the life of a thread.
-   **C.** The corpus exceeds the 20-block lookback window once the history grows.
-   **D.** Web search results are appended above the breakpoint, changing the cached prefix.

**E6.39.** After the last `cache_control` breakpoint, a prompt contains a run of 6 consecutive `tool_use` blocks, a run of 6 consecutive `tool_result` blocks, and 14 text blocks.

How many lookback positions does this consume on the Claude API, and is the breakpoint’s entry still discoverable?

-   **A.** 26 positions, so the entry is not discoverable.
-   **B.** 20 positions, exactly at the limit.
-   **C.** 16 positions, so the entry is still discoverable.
-   **D.** 15 positions, so the entry is still discoverable.

**E6.40.** An A/B test alternates between two `output_config.format` schema variants on the same conversation thread, assigning a variant per request. Quality metrics are clean; cost per conversation rises sharply.

What is wrong?

-   **A.** Changing `output_config.format` invalidates the prompt cache for that thread, so every variant switch pays a cache write; the variants should run on disjoint traffic with sticky assignment.
-   **B.** Compiled grammars are cached for 24 hours from last use, so both variants stay compiled.
-   **C.** Structured output injects an additional system prompt describing the format, which adds input tokens.
-   **D.** Required properties appear first in the output, in schema order, followed by optional ones.

**E6.41.** A long-running consumer agent on `claude-opus-5-5` enables both context-editing strategies and wants to minimise cache churn.

Which statement is correct?

-   **A.** Thinking-block clearing is the main source of cache invalidation and should be disabled.
-   **B.** `clear_at_least` applies to both strategies and should be set on each.
-   **C.** Both strategies invalidate the cache equally, so the trigger should be raised on both.
-   **D.** On Opus 5.5, server-side context management never invalidates thinking blocks, so thinking clearing defaults to keeping all turns there; the cache-invalidating cost comes from tool-result clearing, which is where `clear_at_least` belongs.

## Section 5 — Tools and MCPs

**E6.42.** A consumer endpoint on `claude-haiku-5-5` carries 24 tool definitions totalling 9,600 tokens with `tool_choice: "auto"`, all inside the cached prefix and read on effectively every request, at 40,000,000 requests per day. The team proposes trimming to 8 tools totalling 3,100 tokens.

What is the daily cost of the tool prefix before and after?

-   **A.** \$3,840.00 falling to \$1,240.00.
-   **B.** \$3,954.40 falling to \$1,354.40, a saving of \$2,600.00 per day.
-   **C.** \$39,544.00 falling to \$13,544.00.
-   **D.** \$3,954.40 falling to \$1,354.40, a saving of \$3,954.40 per day.

**E6.43.** (Select TWO) Which two statements about the stateless MCP revision dated 2026-07-28 matter to a high-QPS client?

-   **A.** `server/discover` replaces `initialize`, so there is no per-connection handshake to amortise across requests.
-   **B.** Per-request `_meta` carries what was previously session state, so each request is self-contained.
-   **C.** Sampling lets the server call back into the model, saving the client a round trip.
-   **D.** Server log notifications provide progress reporting for long-running tools.
-   **E.** The revision introduces a persistent session identifier that clients should reuse across requests.

**E6.44.** To avoid a round trip in which the model answers in prose instead of calling a tool, a latency-critical endpoint sets `tool_choice: {"type": "any"}` on `claude-opus-5-5`. Every request returns HTTP 400.

What is wrong?

-   **A.** Forced `tool_choice` raises the injected tool-use system prompt from 286 to 406 tokens.
-   **B.** A `tool_choice` change invalidates the system and message caches.
-   **C.** Forced `tool_choice` — `any` and `tool` alike — returns 400 on current models; where the goal is a guaranteed machine-readable shape, `output_config.format` is the mechanism.
-   **D.** Strict tool use validates the arguments but not whether a tool is called at all.

**E6.45.** An MCP search tool returns 40 results with the full text of each document. The agent usually needs two of them. p99 latency and cost both climb steadily across a session.

What is the principal defect?

-   **A.** Context editing can clear old tool results once the trigger is reached.
-   **B.** A consecutive run of `tool_result` blocks counts as one lookback position.
-   **C.** Haiku 5.5 and the other current models have a 1M context window, so the results fit.
-   **D.** The tool result enters the prompt on the next turn, after the last breakpoint, so it is billed at the full input rate and reprocessed on every subsequent turn; the tool should return identifiers and short snippets, with full text fetched on demand.

**E6.46.** A team wants to auto-approve every tool from one MCP server named `search` and nothing else. Which statement is correct?

-   **A.** Allow rules accept tool-name globs only after a literal `mcp__<server>__` prefix with a glob-free server segment, so `mcp__search__*` works while `mcp__*` is ignored with a startup warning and auto-approves nothing.
-   **B.** `allowed_tools=["mcp__*"]` auto-approves every MCP tool and must be narrowed with a deny rule.
-   **C.** Allow rules do not support globs at all, so each tool must be listed by its full name.
-   **D.** `allowed_tools=["*"]` auto-approves every tool, which is the broader form of the same rule.

## Section 6 — Security and Safety

**E6.47.** A mobile app sends the signed-in user’s email address in `metadata.user_id`, and the backend reads that field from its own request log to scope which conversations a support tool may display.

What is wrong?

-   **A.** `metadata.user_id` is capped at 512 characters, and some email addresses will exceed it.
-   **B.** `metadata.user_id` is an abuse-detection field supplied by the caller and carries no authentication; scoping must come from the server-side session, and the field should carry an opaque stable surrogate rather than an email address.
-   **C.** `metadata.user_id` is not a Usage and Cost API grouping dimension, so per-user cost reporting will not work.
-   **D.** The field is echoed in the response, which widens where the email appears.

**E6.48.** To remove a network hop worth about 80 ms, a proposal has the mobile client call the Messages API directly with an API key embedded in the app binary.

What must the reviewer say?

-   **A.** Client-side calls cannot use streaming, so the perceived-latency gain is lost.
-   **B.** Rate limits are enforced per organization, so a mobile fleet will exhaust them.
-   **C.** An embedded key is extractable from the app, after which any holder can spend against the organization’s limits and quota; the key stays server-side and the hop is accepted, with streaming used to recover perceived latency.
-   **D.** The `anthropic-workspace-id` header would be set by the client, which breaks cost attribution.

**E6.49.** (Select TWO) A consumer agent summarises web pages the user chooses. Which two are sound defences?

-   **A.** Treat fetched page content as untrusted data and bound the agent’s authority with code-level deny rules, so no text in a page can widen what the agent is able to do.
-   **B.** Validate any structured output against an application-side allow-list before acting on it.
-   **C.** Add a system-prompt instruction that the agent must ignore instructions appearing in fetched content.
-   **D.** Set `output_config.effort: "max"` so the agent reasons carefully about what it reads.
-   **E.** Log the full text of every fetched page for later review.

**E6.50.** On the last days of a billing month, a consumer endpoint running at 20,000 requests per minute begins receiving HTTP 429 on every request. The retry layer backs off and retries, and the endpoint stays down.

What should the endpoint do?

-   **A.** Honour `retry-after` and lengthen the backoff, since the limit resets continuously.
-   **B.** Treat the 429 as a 529 `overloaded_error` and shed load until capacity returns.
-   **C.** Raise `max_retries` so transient throttling is absorbed.
-   **D.** Check `error.details.error_code == "enforced_spend_limit_reached"` and, on a match, fail over immediately to a degraded non-model path: that 429 carries no `retry-after` and is never retryable, so retrying it at this request rate only amplifies the outage.

## Section 7 — Claude Code

**E6.51.** A CI job runs an Agent SDK session with `permission_mode="bypassPermissions"` and `allowed_tools=["Read", "Grep"]`, on the understanding that only those two tools can run. The session runs `Bash` and writes files.

What is wrong?

-   **A.** `allowed_tools` does not constrain `bypassPermissions`: unlisted tools match no allow rule, fall through to the permission mode, and are approved there. To block a tool in that mode, put its bare name in `disallowed_tools`, which removes the definition from the request.
-   **B.** `allowed_tools` entries must be scoped, so the bare names are ignored.
-   **C.** `bypassPermissions` refuses to start outside a recognised sandbox, so the session should not have run at all.
-   **D.** Hooks are not executed in `bypassPermissions` mode, so the job’s guard hook never ran.

**E6.52.** A long-running session is in `auto` permission mode. The application calls `setModel()` to switch to a model that auto mode does not support, then switches the model back a few turns later. Permission prompts now reach the `canUseTool` callback on every call.

What happened?

-   **A.** `auto` mode is unavailable in the Agent SDK and was never active.
-   **B.** The session changed to `default` mode when the unsupported model was set, emitting a `system` message with subtype `status`; switching the model back does not restore `auto`, which must be re-set with `setPermissionMode("auto")`.
-   **C.** `setModel()` resets all allow rules, so every call now falls through.
-   **D.** The classifier in `auto` mode is itself a model call, and it failed silently on the unsupported model.

## Section 8 — Eval, Testing, and Debugging

**E6.53.** A team’s latency eval records one number per request — total wall-clock time from request to final token — and reports the mean across a 10,000-request run. A change ships that lowers the mean; user complaints about slow first response increase.

What is wrong with the eval?

-   **A.** 10,000 requests is too small a sample for a p99 measurement.
-   **B.** Wall-clock time includes network time, which the eval cannot attribute.
-   **C.** A mean of an end-to-end number hides the tail the budget is written against, and it collapses two quantities that move independently; time to first token and output tokens per second must be measured separately at p99, because fast mode, cache hit rate, effort and prompt shape each move only one of them.
-   **D.** The eval does not record `usage.speed`, so fast-mode and standard requests are mixed in the same distribution.
