# Exam 5 — Regulated and High-Assurance Systems

**Instructions.** 53 questions, 120 minutes, closed book. Single-answer questions have four options; multiple-response questions are marked “(Select TWO)” or “(Select THREE)” and are scored all-or-nothing. Answers and worked explanations are in the back of the volume.

Every scenario in this exam is set in financial-services or healthcare engineering. Audit, residency, retention, PII-handling and approval requirements appear in the stems as *given system requirements*: your task is to engineer against them, not to evaluate them.

> **This is the hardest tier in this book.** Exams 5 and 6 are deliberately calibrated above the real exam. A score here is a diagnostic of depth, not a predicted exam result — do not read it as one.

## Section 1 — Applications and Integration

**E5.1.** A claims-adjudication service runs on `claude-opus-5-5` with `inference_geo: "us"` on every request. A 40,000-token adjudication rulebook sits in the system prompt behind a single `cache_control` breakpoint with `ttl: "1h"`. Each request adds 1,200 tokens of uncached claim detail after the last breakpoint and produces 800 output tokens. The service handles 2,000 requests per day spread evenly across 24 hours, and in practice the cached prefix is written once per hour and read on every other request.

What is the approximate daily cost?

-   **A.** \$65.09
-   **B.** \$68.43
-   **C.** \$71.60
-   **D.** \$88.99

**E5.2.** A bank’s platform team must attribute Claude spend to the five business units that use a shared internal gateway. Their design sets `metadata.user_id` to a string of the form `bu-<unit>-<employee-hash>` on every request, and a nightly job pulls the Usage and Cost API grouped by that field to produce the chargeback report. The report comes back empty.

Which statement identifies the defect?

-   **A.** The Usage and Cost API does not group by `metadata.user_id`; its grouping dimensions are api key, workspace, model, service tier, context window, `inference_geo` and `speed`, so per-unit attribution has to be carried by separate API keys or workspaces.
-   **B.** `metadata.user_id` is capped at 512 characters, and the composite string will be truncated for some units.
-   **C.** The Messages API has no idempotency key, so a retried request can be counted twice in any spend attribution scheme.
-   **D.** Cache reads are billed at a reduced multiplier, so a chargeback report that sums raw token counts will overstate the cost of cache-heavy units.

**E5.3.** A de-identification pre-pass runs on `claude-haiku-5-5`. A 60,000-token handling-policy block is cached with the default 5-minute TTL and, in steady state, is read rather than written on effectively every request. Each request appends one patient record after the last breakpoint and produces 500 output tokens.

Daily volume is 10,000 requests: 6,000 carry a 30,000-token record and 4,000 carry a 50,000-token record.

What is the approximate daily cost?

-   **A.** \$46.50
-   **B.** \$136.10
-   **C.** \$117.00
-   **D.** \$140.10

**E5.4.** (Select TWO) A payments team is building an Agent SDK workflow in which any transfer above a threshold must be approved by a named reviewer before it executes. Which two statements about implementing that gate are correct?

-   **A.** A `canUseTool` callback that returns `permissionDecision: "defer"` ends the turn with `stop_reason: "tool_deferred"`, so the application can hold the pending call, obtain the reviewer’s decision out of band, and resume.
-   **B.** A tool approved by a bare `allowedTools` entry, or by `bypassPermissions` mode, never reaches `canUseTool`, so a gate that lives only in the callback is silently bypassed for those tools; a `PreToolUse` hook runs before every other step and is the right place for a check that must always run.
-   **C.** Setting `permissionMode: "dontAsk"` defers calls that would otherwise prompt, which is the recommended way to queue them for review.
-   **D.** A `PreToolUse` hook that returns `allow` short-circuits the deny and ask rules, so the reviewer’s approval can be expressed as a hook allow.
-   **E.** `max_turns` bounds the number of tool calls an agent can make, so setting it to 1 is equivalent to requiring approval for each call.

**E5.5.** A clinical-coding endpoint is built like this: tool definitions carry `strict: true`; `output_config.format` supplies a JSON schema whose every property is required and whose `additionalProperties` is `false`; `enum` values list the permitted diagnosis codes for the encounter; and citations are enabled so each extracted code can be traced to a line in the chart. The request returns HTTP 400.

What causes the 400?

-   **A.** Placing clinical values in `enum` entries is disallowed, because the compiled schema is cached outside the message-content retention protections.
-   **B.** Citations cannot be combined with `output_config.format`; enabling both returns 400.
-   **C.** The schema exceeds the limit on optional parameters across all strict and JSON schemas.
-   **D.** `strict: true` on tool definitions cannot be combined with `output_config.format` in the same request.

**E5.6.** An overnight job reclassifies documents against a retention schedule. It runs on `claude-sonnet-5-5` through the Message Batches API. A 20,000-token retention rubric is attached with an identical `cache_control` block carrying `ttl: "1h"` on every request; over the run the prefix is written 40 times and read on every other request. Each of the 120,000 documents contributes 3,000 input tokens after the last breakpoint and 400 output tokens.

What is the approximate total cost of the run?

-   **A.** \$1,443.12
-   **B.** \$843.12
-   **C.** \$721.56
-   **D.** \$600.00

**E5.7.** A brokerage wraps every Claude call in a retry helper: on HTTP 429 it sleeps with exponential backoff and retries up to eight times, logging a warning each time. During the last week of a month the trading-surveillance service goes dark for six hours; every request fails after eight attempts and the log is full of identical warnings.

What is wrong with the design?

-   **A.** A 429 raised by the organization’s monthly spend cap carries `error.details.error_code == "enforced_spend_limit_reached"`, has no `retry-after` header, and is never retryable; the helper must detect that code and fail fast to an alert rather than burning six hours of retries.
-   **B.** HTTP 529 `overloaded_error` indicates capacity rather than a rate limit, and the helper does not distinguish it from 429.
-   **C.** The SDK already retries 429 twice by default, so the helper’s eight attempts multiply into sixteen.
-   **D.** The `retry-after` header is expressed in seconds, and exponential backoff that ignores it will retry earlier than permitted and fail again.

**E5.8.** A claims intake pipeline sends scanned forms to Claude. Each claim comprises eight page images, every page rasterised at 1,700 × 2,200 pixels, together with 1,500 tokens of structured claim metadata as text.

Using the documented image token formula, what is the input token count for one claim?

-   **A.** 38,940
-   **B.** 38,552
-   **C.** 41,393
-   **D.** 40,052

**E5.9.** An audit-report generator on `claude-opus-5-5` streams a narrative of roughly 90,000 output tokens. The connection drops partway through. The recovery path re-sends the original request with an assistant turn prefilled with the text received so far, so the model “continues where it left off”. Every recovery attempt returns HTTP 400.

What is wrong?

-   **A.** The report exceeds the model’s maximum output, so the generation cannot complete regardless of recovery strategy.
-   **B.** Assistant prefill returns 400 on 4.6 and later models; on those models an interrupted generation is resumed with a user-message continuation, not a prefill.
-   **C.** Tool-use and thinking blocks are not partially recoverable, so a break inside one of them invalidates the recovery.
-   **D.** Non-streaming requests are subject to a 10-minute ceiling, which a generation of this length will exceed.

**E5.10.** A dispute-resolution service posts each Claude-produced summary to an immutable ledger. To protect against double-posting when a request times out and the client retries, the design sends an `Idempotency-Key` header on the Messages API request and treats a repeated key as proof the model was called only once.

What is wrong?

-   **A.** The Messages API has no idempotency key; a header it does not recognise provides no deduplication, so the retry must be keyed in the application’s own layer — a request id recorded before the call and checked before the ledger write.
-   **B.** The key must be a UUID, and a non-UUID value is silently ignored.
-   **C.** Idempotency applies only to the Message Batches API, where `custom_id` fills that role.
-   **D.** The header works, but it does not cover streaming requests, which is the case that actually times out.

**E5.11.** (Select THREE) A team is investigating why a long-lived cached prefix on a prior-authorisation service misses intermittently. Which three statements are correct?

-   **A.** Sending `diagnostics.previous_message_id` on a request asks the API to compare it with that earlier message and report `diagnostics.cache_miss_reason`.
-   **B.** `cache_miss_reason` takes values including `model_changed`, `system_changed`, `tools_changed`, `messages_changed`, `previous_message_not_found` and `unavailable`.
-   **C.** The invalidation hierarchy runs tools → system → messages, so a change to the tool definitions invalidates the system and message caches as well.
-   **D.** `cache_read_input_tokens` of 0 establishes that the prefix was shorter than the model’s minimum cacheable length.
-   **E.** The diagnostics response reports the index of the first content block at which the two prefixes diverged.
-   **F.** A `cache_miss_reason` of `unavailable` means the entry’s TTL elapsed before the request arrived.

**E5.12.** A trading-surveillance service has an input-tokens-per-minute limit of 2,000,000. Each request reads 180,000 tokens from cache, writes 8,000 tokens to cache, and carries 2,000 uncached input tokens after the last breakpoint.

What throughput does the ITPM limit permit, and why?

-   **A.** About 10 requests per minute, because cache reads count toward ITPM.
-   **B.** About 11 requests per minute, because the entire 190,000-token prompt counts toward ITPM.
-   **C.** About 200 requests per minute, because only the 8,000 cache-write tokens and the 2,000 uncached input tokens count toward ITPM.
-   **D.** About 1,000 requests per minute, because only the 2,000 uncached input tokens count toward ITPM.

**E5.13.** A nightly PII-redaction job submits 48,000 records to the Message Batches API. The loader builds a list of records, submits them in that order, then streams the results file and writes result *i* back to record *i* of the list. Spot checks show redacted text attached to the wrong patients.

What is wrong?

-   **A.** Batch results are available for 29 days from creation, and the loader reads them too late.
-   **B.** Batch results can arrive in any order; `custom_id` is the only join key, and the positional write is unsound.
-   **C.** Batch usage is billed at 50% of standard prices, so the cost model, not the correctness, is what the loader has wrong.
-   **D.** Requests that expire after 24 hours are not billed, so the result file is shorter than the input list.

**E5.14.** A wealth-advisory console runs interactively on `claude-opus-5-5` with `speed: "fast"` and `inference_geo: "us"`. Each advisory session reads a 25,000-token cached client-policy prefix, adds 1,500 uncached input tokens after the last breakpoint, and produces 3,000 output tokens. There are 4,000 sessions per day, and in steady state the prefix is read rather than written.

What is the approximate daily cost?

-   **A.** \$568.00
-   **B.** \$312.40
-   **C.** \$1,460.80
-   **D.** \$624.80

**E5.15.** A suitability-review service must attach a disclosure record to every advisory interaction. To guarantee the model always emits one, the design sets `tool_choice: {"type": "tool", "name": "file_disclosure"}` on every request to `claude-opus-5-5`. Every request returns HTTP 400.

What is wrong?

-   **A.** Forced `tool_choice` — both `any` and `tool` — returns 400 on current models; a guaranteed machine-readable shape should come from `output_config.format` instead.
-   **B.** Forced `tool_choice` raises the injected tool-use system prompt from 286 to 406 tokens, which pushes the prefix past a limit.
-   **C.** A tool used under `strict: true` counts against the limit of 20 strict tools per request.
-   **D.** Changing `tool_choice` invalidates the system and message caches, so every request is a cache miss.

**E5.16.** A health insurer runs two workloads through one workspace. One must execute inference only on US-based infrastructure and sets `inference_geo: "us"`; the other has no such requirement and omits the parameter. The auditors ask for a monthly report that demonstrates the first workload’s inference actually ran under the restriction.

Which Usage and Cost API grouping dimension answers the question?

-   **A.** api key
-   **B.** `speed`
-   **C.** `inference_geo`
-   **D.** context window

**E5.17.** (Select TWO) A validated clinical-decision-support workflow must not change model behaviour without a revalidation cycle. The configuration pins `model: "claude-opus-5-5"`. Which two statements are correct?

-   **A.** Dateless model IDs on 4.6 and later are fixed snapshots rather than moving aliases, so this configuration already pins a single, stable set of weights.
-   **B.** Anthropic commits to a minimum of 60 days’ notice before a model is deprecated, which is the window the revalidation plan has to fit inside.
-   **C.** A dateless ID on current models resolves to the newest snapshot in its line, so a date suffix must be appended to pin the configuration.
-   **D.** A Priority Tier commitment keeps a deprecated model available past its retirement date for committed customers.
-   **E.** Because the pin is stable, no migration plan is required; the configuration can be left unchanged indefinitely.

**E5.18.** To satisfy an audit requirement that every automated clinical determination be reconstructable, a team logs the full JSON request body and the full response body — including thinking blocks — into the organization’s general-purpose searchable log index, which is readable by the whole support organization.

What is the principal defect?

-   **A.** Thinking blocks are preserved by default on current models, so logging them duplicates content the API already retains.
-   **B.** The log store now holds the same patient data as the prompt, in a system whose access population is far wider than the application’s; reconstructability should be carried by `request_id`, model, usage, the determination itself, and references to content held in the system of record.
-   **C.** Full-body logs grow faster than the retention schedule permits, so the index will exceed its storage budget.
-   **D.** Zero-data-retention processing means the API keeps no copy, so the log is the only record and must therefore be complete.

## Section 2 — Model Selection and Optimization

**E5.19.** An eligibility-determination step sends a 120,000-token member history with no caching and produces 600 output tokens. The team is pricing it on `claude-haiku-5-5`.

What is the per-request cost?

-   **A.** \$0.0123
-   **B.** \$0.0603
-   **C.** \$0.2460
-   **D.** \$0.0615

**E5.20.** A triage service holds a multi-request conversation per case. It sends the first turn at the model default effort and, when a rules engine flags the case as complex, sets `output_config.effort: "high"` on the next turn in the same thread. Cache hit rate collapses on flagged cases.

What explains it, and what is the remedy?

-   **A.** `output_config.effort` on `claude-opus-5-5` defaults to `medium`, so the first turn was already below `high`.
-   **B.** Changing effort between requests restarts the prompt cache; the `mid-conversation-output-config-2026-07-01` beta preserves it across such a change.
-   **C.** Effort belongs in `output_config`, not inside `thinking`; a `thinking` block carrying `budget_tokens` returns 400 on 4.7 and later.
-   **D.** Setting effort explicitly to the model’s own default does not invalidate the cache, so only non-default values matter.

**E5.21.** (Select TWO) Which two statements about sampling and reasoning controls on current models are correct?

-   **A.** `temperature`, `top_p` and `top_k` are deprecated on 4.7 and later models and return 400.
-   **B.** A `thinking` object carrying `budget_tokens` returns 400 on 4.7 and later; reasoning depth is set with `output_config.effort`.
-   **C.** `output_config.effort` accepts only `low`, `medium` and `high`.
-   **D.** `temperature: 0` remains accepted on current models as the documented way to obtain deterministic output for regulated workflows.
-   **E.** The default effort on `claude-opus-5-5` is `high`.

**E5.22.** A nightly batch sets `inference_geo: "us"` on every request. Most requests succeed, but the subset routed to a pinned `claude-opus-4-5` snapshot used by a legacy validated workflow returns HTTP 400.

What is the cause?

-   **A.** `inference_geo` is supported on 4.6 and later models and returns 400 on earlier ones, including the pinned Opus 4.5 snapshot.
-   **B.** `inference_geo` cannot be set per request inside a batch; it must be set once on the batch.
-   **C.** The workspace’s `allowed_inference_geos` excludes `us`, which fails only for models that enforce it.
-   **D.** `inference_geo: "us"` is a 1.1x price modifier and is rejected when it would carry the request past the workspace spend limit.

**E5.23.** A loan-underwriting desk sends an 80,000-token underwriting rulebook as a cached prefix on `claude-opus-5-5`. Work arrives in bursts of 6 requests, and bursts start every 20 minutes across an 8-hour day. With the default 5-minute TTL the prefix is written once per burst; with `ttl: "1h"` it is written once per hour.

How much does the 1-hour TTL save per day?

-   **A.** \$8.59
-   **B.** \$6.14
-   **C.** \$4.22
-   **D.** \$4.48

**E5.24.** A design document for a new claims-decision path states: “To meet the 2-second p99 commitment we will purchase Priority Tier capacity for `claude-opus-5-5` and run the interactive path on it, falling back to standard service tier only on overflow.”

What must the reviewer say?

-   **A.** Fast mode cannot be combined with a Priority Tier commitment, so the latency plan and the capacity plan conflict.
-   **B.** Priority Tier responses carry `anthropic-priority-*-tokens-*` headers, which the fallback logic must read to detect overflow.
-   **C.** Each token consumed with `inference_geo: "us"` draws down 1.1 tokens of committed throughput, which the capacity sizing omits.
-   **D.** Priority Tier is closed to new purchase and excludes all current models, so this is not an available option and the committed-capacity plan has to be replaced.

**E5.25.** A transaction-categorisation step on `claude-opus-5-5` sends a 1,100-token prompt and produces about 100 tokens of final answer per request, but is billed for several times that many output tokens. The team’s eval shows no accuracy difference between `low` effort and the model default. The workload is interactive and the prompt is distinct on every request.

Which single change cuts cost the most without changing the model?

-   **A.** Enable `speed: "fast"`, which raises output tokens per second.
-   **B.** Set `output_config.effort: "low"`, which reduces the reasoning tokens billed as output.
-   **C.** Move the 1,100-token prompt behind a `ttl: "1h"` cache breakpoint.
-   **D.** Move the workload to the Message Batches API for the 50% discount.

**E5.26.** (Select THREE) A health system is budgeting a `claude-haiku-5-5` workload whose prompt length varies. Which three statements are correct?

-   **A.** Haiku 5.5 is the only current model priced by prompt length, paying 5x above 100,000 input tokens.
-   **B.** The 100,000-token threshold is evaluated on the total prompt, counting cache read and cache write tokens as well as uncached input.
-   **C.** The tier is decided per request, so a workload with mixed prompt sizes pays both rates on the same day.
-   **D.** Above the threshold the 5x multiplier applies to input tokens only; output stays at the base rate.
-   **E.** The threshold is evaluated on the `input_tokens` field alone, so a large cached prefix never triggers it.
-   **F.** Submitting the long-prompt share through the Message Batches API avoids the long-context rate.

**E5.27.** A regulatory-research assistant keeps a 400,000-token corpus as a cached prefix. Each query reads the whole prefix from cache, adds 1,000 uncached input tokens, and produces 2,500 output tokens. The team is comparing `claude-fable-5-1` with `claude-opus-5-5`.

By approximately what factor is Fable 5.1 more expensive per request?

-   **A.** 1.75x
-   **B.** 2.50x
-   **C.** 1.25x
-   **D.** 2.00x

## Section 3 — Agents and Workflows

**E5.28.** An Agent SDK workflow that files regulatory reports sets `max_budget_usd: 2.00`. The design document records this as a hard guarantee that no single filing run can cost more than \$2.00, and the finance control that was going to sit in front of the service is removed on that basis.

What is wrong?

-   **A.** `max_turns` counts tool-use turns only, so the budget can be exhausted by a single long text turn that `max_turns` does not bound.
-   **B.** Default subagent concurrency is 20, so a fan-out multiplies the budget by the number of concurrent children.
-   **C.** `max_budget_usd` is checked after a response arrives, so a single expensive turn can carry the run past the cap; a genuine ceiling needs a pre-request bound such as a smaller `max_tokens` and a lower effort, in addition to the budget.
-   **D.** `max_budget_usd` applies per session, and a filing run that spans sessions is not covered by one value.

**E5.29.** An Agent SDK workflow must, for one submission: read three evidence files, run a validator once per file, and write a single summary. The agent issues the three reads as three parallel `tool_use` blocks in one assistant turn. Each validator call needs the preceding validator’s output, so the three validator calls are sequential. The write is one call. The run ends with a text-only assistant message containing the summary.

How many tool-use turns does the run take, and is `max_turns: 5` sufficient?

-   **A.** 7 tool-use turns; `max_turns` must be at least 7.
-   **B.** 6 tool-use turns, because the closing text message counts as a turn.
-   **C.** 5 tool-use turns, but `max_turns: 5` will be exceeded because the closing assistant message counts as a turn.
-   **D.** 5 tool-use turns; `max_turns: 5` is exactly sufficient, because the closing text-only turn is not counted.

**E5.30.** (Select TWO) A pharmacy agent may propose a drug-interaction override but the override must be enforced by the application, never by the model’s cooperation. Which two controls enforce that in code?

-   **A.** A `PreToolUse` hook, which runs before every other step in the permission flow and whose deny applies even in `bypassPermissions` mode.
-   **B.** A scoped deny rule such as `disallowed_tools=["Bash(psql *)"]`, which blocks matching calls in every permission mode.
-   **C.** A system-prompt instruction that the agent must always ask a pharmacist before applying an override.
-   **D.** Listing only safe tools in `allowed_tools` while running the session in `bypassPermissions` mode.
-   **E.** Running the session in `acceptEdits` mode, which auto-approves only file operations and therefore leaves the override gated.

**E5.31.** A multi-jurisdiction review orchestrator is built as four nested levels: a top-level coordinator spawns one subagent per jurisdiction, each of which spawns one per product line, each of which spawns one per rule family. The deepest level never runs and the parent reports a refusal.

What is wrong?

-   **A.** Default subagent concurrency is 20, and the fan-out exceeds it at the third level.
-   **B.** Default subagent depth is 3, so the fourth level is refused; the hierarchy has to be flattened or the depth limit raised.
-   **C.** Subagents inherit the parent’s permission mode, and the deepest level inherits a mode that denies its tools.
-   **D.** Each subagent has its own context window, so the deepest level receives no instructions from the coordinator.

**E5.32.** A compliance-monitoring agent runs headless and unattended against a fixed set of read-only tools. No human is available to answer a prompt. The team wants any call outside the sanctioned set to fail loudly rather than depend on the absence of a callback.

Which configuration expresses that?

-   **A.** `allowedTools` listing the sanctioned tools together with `permissionMode: "dontAsk"`, so listed calls run and anything that would prompt is denied without `canUseTool` being called.
-   **B.** `permissionMode: "plan"`, so the agent explores read-only and never edits.
-   **C.** `permissionMode: "default"` with no `canUseTool` callback, so unresolved calls fall through and are dropped.
-   **D.** `permissionMode: "bypassPermissions"` with `allowedTools` listing the sanctioned tools, so only those are approved.

**E5.33.** An orchestrator runs in `bypassPermissions` so it can operate on the build host unattended. One of its subagents processes third-party submissions, so its `AgentDefinition` sets `permissionMode: "default"` to sandbox it. Review finds the subagent running unrestricted.

What is wrong?

-   **A.** Deny rules are evaluated before the permission mode and therefore still apply in `bypassPermissions`, so the sandbox should have used deny rules — but the subagent’s mode was applied correctly.
-   **B.** Hooks still execute in `bypassPermissions` mode, so the subagent’s mode is irrelevant and a hook was required.
-   **C.** A subagent runs in `bypassPermissions` whenever the parent session does; a per-subagent `permissionMode` is applied only when the parent is in `default`, `dontAsk` or `plan`, so the sandboxing never took effect.
-   **D.** `bypassPermissions` refuses to start as root outside a recognised sandbox, so the orchestrator itself should have failed before the subagent ran.

**E5.34.** A case-review agent runs long sessions with heavy tool use. Its configuration enables context editing with both strategies:

    "context_management": {"edits": [
      {"type": "clear_tool_uses_20250919"},
      {"type": "clear_thinking_20251015"}
    ]}

What is the defect?

-   **A.** The default `trigger` of 100,000 input tokens fires earlier than this agent needs, discarding results it still uses.
-   **B.** The default `keep` of 3 tool uses is too small for a review that cross-references many documents.
-   **C.** Clearing tool results invalidates the cached prefix, so `clear_at_least` should be set to make each clearing worth the cache write.
-   **D.** When both strategies are used, `clear_thinking_20251015` must be listed first in the `edits` array.

**E5.35.** A turn ends with `stop_reason: "tool_deferred"`. A reviewer later approves the pending action. What must the application send to continue?

-   **A.** A new session seeded with a summary of the deferred decision.
-   **B.** The same message history, extended with a `tool_result` block carrying the deferred `tool_use` id, in a new request.
-   **C.** The same history with an assistant turn prefilled with the approved tool call.
-   **D.** The same request with `permissionMode` changed to `bypassPermissions` so the pending call is approved on replay.

## Section 4 — Prompt and Context Engineering

**E5.36.** A prior-authorisation prompt is assembled from one instruction block followed by 26 policy blocks. The builder places explicit `cache_control` markers on four of the policy blocks and, “for safety”, also sets a single top-level `cache_control` on the request. The request returns HTTP 400.

What is the cause?

-   **A.** A top-level `cache_control` consumes one of the four available breakpoint slots, so combining it with four explicit markers exceeds the limit and returns 400.
-   **B.** The instruction block is shorter than the 512-token minimum cacheable length on current models.
-   **C.** The lookback window is 20 blocks per breakpoint, so markers beyond the twentieth block cannot be discovered.
-   **D.** The invalidation hierarchy runs tools → system → messages, so markers inside the system prompt are invalidated by any message change.

**E5.37.** A de-identification prompt on `claude-haiku-5-5` places its entire 380-token system block behind a `cache_control` marker. Responses report both `cache_creation_input_tokens` and `cache_read_input_tokens` as 0, and no error is returned.

How many additional tokens must the cached prefix carry, at minimum, for caching to take effect?

-   **A.** 644
-   **B.** 1,668
-   **C.** 132
-   **D.** 0 — there is no minimum, and the cause lies elsewhere.

**E5.38.** (Select THREE) A requirement states that direct patient identifiers must not leave the application tier. Which three are sound engineering practices for prompt construction under that requirement?

-   **A.** Replace each identifier with a per-request surrogate token before the request is built, and re-hydrate from the mapping after the response returns.
-   **B.** Keep identifiers out of JSON-schema property names, `enum` values, `const` values and regex patterns, because the compiled schema is cached for up to 24 hours outside the message-content retention protections.
-   **C.** Validate the response against the allow-list of surrogate tokens actually sent, rather than relying on the model to echo only supplied values.
-   **D.** Instruct the model in the system prompt never to repeat an identifier in its output.
-   **E.** Carry the identifier out of band in `metadata.user_id` so it never appears in the message content.
-   **F.** Enable citations so every identifier in the output is attributed to the source chart line it came from.

**E5.39.** A cached system prefix on an adjudication service ends with a block containing the current date and the requesting adjuster’s name, “so the model has the context it needs”. Cache hit rate is effectively zero.

What is wrong?

-   **A.** A change in the system prompt invalidates the message cache as well, so the adjuster’s name should be in the tool definitions instead.
-   **B.** Date and name are a handful of tokens, so the cost of the miss is negligible and the real problem is elsewhere.
-   **C.** The 5-minute TTL is refreshed at no cost on each read, so a 1-hour TTL would not change the hit rate.
-   **D.** Per-request values placed inside the cached prefix change the prefix on every request and invalidate it; they belong in the first message after the last breakpoint.

**E5.40.** A response on a prior-authorisation request reports:

    "usage": {
      "input_tokens": 1400,
      "cache_read_input_tokens": 96000,
      "cache_creation_input_tokens": 4000,
      "cache_creation": {"ephemeral_5m_input_tokens": 1000, "ephemeral_1h_input_tokens": 3000}
    }

What is the total input for this request, and how many of those tokens count toward ITPM?

-   **A.** 101,400 total; 101,400 counted toward ITPM.
-   **B.** 101,400 total; 5,400 counted toward ITPM.
-   **C.** 97,400 total; 1,400 counted toward ITPM.
-   **D.** 1,400 total; 1,400 counted toward ITPM.

**E5.41.** A regulatory assistant carries a 60,000-token corpus that never changes, and exposes a different set of tools depending on the case type. Hit rate on the corpus is poor even though the corpus itself is identical on every request.

Which arrangement fixes it?

-   **A.** Place the corpus ahead of the tool definitions so it is cached before any tool change can affect it.
-   **B.** Hold one superset tool list constant across case types and gate tool availability in application code, so the tools level stays stable and the system-level corpus stays cached.
-   **C.** Switch the corpus breakpoint to `ttl: "1h"`, so the entry survives long enough to be reused across case types.
-   **D.** Move the corpus into the first user message so it sits in the messages level, which is not affected by tool changes.

## Section 5 — Tools and MCPs

**E5.42.** A prior-authorisation request carries 11 tool definitions totalling 3,900 tokens, a 7,100-token system prompt, and `tool_choice: "auto"`.

How many tokens does the tools-and-system portion of the prompt contribute?

-   **A.** 11,000
-   **B.** 11,406
-   **C.** 7,386
-   **D.** 11,286

**E5.43.** A client is written against the stateless MCP revision dated 2026-07-28. It opens a connection, calls `initialize`, caches the returned capability list for the life of the process, and subscribes to server log notifications to surface progress to an audit console. Neither the handshake nor the notifications work.

What is wrong?

-   **A.** In that revision `server/discover` replaces `initialize`, and sampling and logging are deprecated; per-request `_meta` carries what used to be session state.
-   **B.** Tool definitions must be re-declared on every request, so caching the capability list is the defect.
-   **C.** MCP tool names are exposed as `mcp__<server>__<tool>`, and the client is subscribing under the unprefixed name.
-   **D.** Connector tools that the organization has set to `ask` always fall through to the approval callback, which suppresses the notifications.

**E5.44.** (Select TWO) An MCP server exposes a tool that can move money between customer accounts. Which two choices apply least privilege at the right layer?

-   **A.** Mark the transfer tool with `_meta["anthropic/requiresUserInteraction"]`, so it always falls through to the approval callback and no allow rule can auto-approve it.
-   **B.** Enforce the per-account limit inside the MCP server, against the calling identity’s own entitlements, rather than stating the limit in the tool description.
-   **C.** State in the tool description that transfers above \$500 are not permitted, so the model will not request them.
-   **D.** Run the session in `dontAsk` mode so the transfer tool always prompts for approval before executing.
-   **E.** Set `strict: true` on the transfer tool’s schema, so the server can rely on the arguments being authorised.

**E5.45.** An agent retrieves a patient’s allergy list through an MCP tool. The returned text contains a passage that reads like a new set of instructions addressed to the model. Which engineering response is correct?

-   **A.** Reduce `output_config.effort`, so the model follows the system prompt more literally and is less likely to act on the passage.
-   **B.** Treat every tool result as untrusted data: validate it against the expected schema in the application, and bound the agent’s authority with code-level deny rules so no text in a result can widen what the agent is able to do.
-   **C.** Add a system-prompt instruction that text inside tool results is data and must never be followed.
-   **D.** Enable strict tool use, so the tool’s arguments and results are both schema-validated.

**E5.46.** A claims workflow flips `tool_choice` between `"auto"` during evidence gathering and `"none"` during the final write-up, within one conversation thread. Cache diagnostics report `system_changed` on every transition.

What explains it?

-   **A.** A change to the tool definitions invalidates the tools, system and message caches.
-   **B.** Adding or removing images preserves the tools cache but invalidates the system and message caches.
-   **C.** A `tool_choice` change preserves the tools cache but invalidates the system and message caches; holding `tool_choice` constant and gating in application code avoids it.
-   **D.** Switching `speed` preserves the tools cache but invalidates everything after it.

## Section 6 — Security and Safety

**E5.47.** A record-retrieval service builds a prompt containing the requested patient chart plus the requesting clinician’s role and care-team membership, and asks the model to answer “may this clinician see this record?” before summarising. The application acts on the model’s answer.

What is the principal defect?

-   **A.** The decision should be returned through `output_config.format` so the application can parse it reliably.
-   **B.** A confirmation gate should be added so the clinician approves the disclosure before the summary is produced.
-   **C.** The decision should be logged with the `request_id` so it can be reconstructed during an audit.
-   **D.** Authorisation must be decided in code against the identity store before the prompt is built; a record the caller is not entitled to see should never enter the prompt at all, so the model is never the access-control decision point.

**E5.48.** (Select TWO) A servicing assistant summarises correspondence received from third parties, and the same session also exposes a tool that can initiate a payment. Which two measures are sound defensive engineering?

-   **A.** Remove the payment tool’s definition from requests that process third-party content, using a bare-name deny entry so the tool is not in the request at all and cannot be attempted.
-   **B.** Require a `PreToolUse` hook that re-derives the payee and amount from the application’s own record of the servicing request, and denies the call when the model’s arguments disagree.
-   **C.** Add a system-prompt instruction that the assistant must disregard any payment instruction appearing in correspondence.
-   **D.** List the payment tool in `allowedTools` so every use of it is attributed in the permission audit trail.
-   **E.** Set `temperature: 0` so the assistant’s behaviour on adversarial input is deterministic and testable.

**E5.49.** An audit requirement says a stable identifier must link each model interaction to a patient record, while a data requirement says the identifier itself must not be written to the application’s log store. Which approach satisfies both?

-   **A.** Derive a stable surrogate key at the point the request is constructed, use the surrogate in both the prompt and the log, and keep the surrogate-to-identifier mapping in the system of record — because a request/response log written after the call necessarily contains whatever was sent.
-   **B.** Log the full request and response, then run a scheduled redaction job over the index.
-   **C.** Log the identifier but restrict the log index with field-level access control.
-   **D.** Place the identifier in `metadata.user_id`, which is not written to the response body and therefore not logged.

**E5.50.** An agent that can close a customer’s account is designed so the model writes “This will permanently close account \#\#\#\#. Shall I proceed?” and continues when the next user message is affirmative.

What is wrong?

-   **A.** The prompt should state the consequences more precisely so the user’s consent is informed.
-   **B.** The confirmation should be returned as structured output so the application can detect it reliably.
-   **C.** The confirmation lives inside the model’s turn, so it is advisory: nothing prevents the closing call being emitted in the same turn or on a later one without it. The gate has to sit in the permission layer, where the application rather than the model decides.
-   **D.** An affirmative reply can arrive from a different user in a shared session, so the session must be bound to one identity.

## Section 7 — Claude Code

**E5.51.** To keep an Agent SDK session out of a credentials directory, a team passes `disallowed_tools=["Edit(/secrets/**)"]`. Writes under `/secrets` on disk still succeed.

What is wrong?

-   **A.** `Edit(path)` rules govern only the `Edit` tool, so `Write` and `NotebookEdit` are unaffected.
-   **B.** With a single leading slash the rule anchors at the rule’s source — for rules passed through `disallowed_tools`, the session’s working directory — so it does not match `/secrets` on disk; `Edit(//secrets/**)` is the absolute form.
-   **C.** A `Write(path)` rule is never matched by the file permission checks, so the rule had to name `Write` explicitly.
-   **D.** Deny rules are not evaluated in `bypassPermissions` mode, which is the mode the session was running in.

**E5.52.** Which statement correctly contrasts the two deny-rule forms?

-   **A.** Both forms remove the tool definition from the request; the scoped form additionally logs the blocked pattern.
-   **B.** Both forms leave the tool available and block matching calls; the bare form matches every call to the tool.
-   **C.** The bare form blocks matching calls in every permission mode; the scoped form is advisory and can be overridden by an allow rule.
-   **D.** `disallowed_tools=["Bash"]` removes the `Bash` tool definition from the request, so Claude cannot attempt it. `disallowed_tools=["Bash(rm *)"]` leaves `Bash` available and denies only calls matching `rm *` as written, so a call written as `/bin/rm` falls through to the permission mode.

## Section 8 — Eval, Testing, and Debugging

**E5.53.** A team validates a new overnight retention-classification job by submitting a 2,000-request batch to the Message Batches API in a staging workspace and checking that the batch is accepted. The batch is accepted, and the next morning most results are `errored` with `invalid_request_error`.

What is wrong with the test?

-   **A.** Validation of each request’s `params` happens asynchronously, so shape errors surface only after the batch ends; request shapes must be tested against the synchronous Messages API first.
-   **B.** A batch holds up to 100,000 requests or 256 MB, and a 2,000-request batch is too small to be representative.
-   **C.** `errored` results are not billed, so the test is cheap but tells you nothing about cost.
-   **D.** Batch results are downloadable for 29 days from `created_at`, so the morning check is within the window and the failures must have another cause.
