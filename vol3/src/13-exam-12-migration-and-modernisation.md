# Exam 12 — Migration and Modernisation

**53 questions · 120 minutes · closed book · answers in the back**

Every scenario in this exam takes place at **Halyard Systems**, whose production service **Keel** has run on Claude for three years and is now being moved off deprecated models and deprecated API surface ahead of a fixed retirement date. Shadow comparison, dual-running, cutover sequencing, and regression detection run through the whole paper.

This is the capstone of Volume III and the hardest tier. A real migration touches every part of the platform, so this exam draws on all eight domains in combination: a question in the Agents section may turn on a caching fact, and a question in the Applications section may turn on a Claude Code setting. A score here is a depth diagnostic, not a predicted exam result.

Unless a question says otherwise, assume the Claude API (not Bedrock or Google Cloud), that today is **18 October 2026**, and current model pricing with default SDK behaviour.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E12.1.** Keel’s largest workload still runs on `claude-sonnet-4-5-20250929`, which was deprecated on 30 September 2026 with a retirement date of 30 November 2026. Halyard’s risk register asks whether Anthropic met its own notice commitment.

How much notice was given, and how does it compare with the documented minimum?

A. 59 days — just under the documented 60-day minimum. B. 61 days — just over the documented 60-day minimum. C. 62 days — counting both endpoints inclusively, comfortably over the 60-day minimum. D. 61 days — but the documented minimum is 90 days, so the notice was short.

------------------------------------------------------------------------

**E12.2.** Halyard’s migration pull request changes the model string from `claude-sonnet-4-5-20250929` to `claude-sonnet-5-5`, updates the pinned SDK to Python v1.0, and leaves the request builder untouched. The builder sets `temperature=0.2` on every call. CI fails before any request reaches the network.

What is the explanation?

A. The request is sent and returns a 400, and the SDK surfaces it as an API error at response time. B. `temperature=0.2` is silently clamped to the model default, and the CI failure is unrelated. C. `temperature` is accepted on 5.5 but requires a beta header the PR does not add. D. The Python SDK v1.0 removed `temperature`, `top_p` and `top_k` entirely, so passing one raises a `TypeError` locally, before a request is constructed.

------------------------------------------------------------------------

**E12.3.** Keel serves 500,000 requests per day. For shadow comparison, Halyard replays a 20% sample of production traffic through the candidate model on Opus 5.5 via the Message Batches API. Each replayed request carries 12,000 input tokens and produces 1,500 output tokens; assume no cache reuse in the shadow path. Opus 5.5 is \$4 per MTok input and \$20 per MTok output.

What does one day of shadow traffic cost?

A. \$3,900 B. \$7,800 C. \$19,500 D. \$1,950

------------------------------------------------------------------------

**E12.4.** Keel’s response formatter has always ended each request with a partial assistant turn containing `{"findings":` so the model continues into valid JSON. After the model string is updated, every request returns a 400.

What is the correct fix?

A. Escape the partial JSON, since unbalanced braces in a prefill are rejected. B. Move the prefill into the system prompt, where prefills are still honoured. C. Remove the prefill — assistant prefill is rejected on 4.6+ — and shape the output with `output_config.format` instead. D. Add the structured-outputs beta header, which re-enables prefill for JSON use cases.

------------------------------------------------------------------------

**E12.5.** Keel’s system prefix is 1,800 tokens. On the model Halyard is leaving, the minimum cacheable prefix was 4,096 tokens, so the prefix never cached; on Opus 5.5 the minimum is 512 tokens, so it now does. Keel makes 2,000,000 requests per month. Assume the prefix is written to cache 720 times a month and read on every other request. Opus 5.5 is \$4 per MTok input, 5-minute cache writes are 1.25× and cache reads are 0.05×.

What do the prefix tokens cost per month after the migration?

A. \$719.74 B. \$726.22 C. \$1,445.96 D. \$14,400.00

------------------------------------------------------------------------

**E12.6.** *(Select TWO)* Keel’s legacy code sets `output_format` on every request and also enables citations so that support agents can trace each statement to a source record. The migration plan is to “rename `output_format` to `output_config.format` and change nothing else.”

Which TWO statements are correct?

A. `output_format` is deprecated in favour of the first-class `output_config.format`. B. `output_config.format` is deprecated in favour of `output_format`, so the rename is backwards. C. `output_config.format` is incompatible with citations, so the combination returns a 400 and the team must choose between them. D. Citations are unaffected by structured output and will continue to work after the rename. E. The rename requires `tool_choice: {"type": "any"}` to take effect. F. `output_config.format` is only available on the Batches API.

------------------------------------------------------------------------

**E12.7.** It is 18 October 2026, and the retirement date for `claude-sonnet-4-5-20250929` is 30 November 2026.

How many days remain before requests to that model begin failing?

A. 43 B. 42 C. 44 D. 13

------------------------------------------------------------------------

**E12.8.** Halyard runs Keel’s primary region on the Claude API and a secondary region on Amazon Bedrock. The migration plan says: “Once we have confirmed the Claude API retirement date for the deprecated model, we will apply the same cutover date to Bedrock.”

What is wrong?

A. Bedrock does not support deprecated models at all, so the secondary region is already failing. B. Bedrock retirement dates are always later, so the plan is merely conservative and costs nothing. C. Bedrock requires a separate contract amendment before any model change. D. Amazon Bedrock and Google Cloud set their own retirement schedules, so the Bedrock date must be confirmed independently and may fall before or after the Claude API date.

------------------------------------------------------------------------

**E12.9.** Halyard wants to replay an archive of 1,400,000 historical requests through the candidate model for regression comparison. Each serialises to approximately 2 KB. A batch may hold at most 100,000 requests and at most 256 MB (take 1 MB as 1,000,000 bytes and 1 KB as 1,000 bytes).

What is the minimum number of batches, and which limit binds?

A. 11 batches; the 256 MB payload limit binds. B. 14 batches; the 256 MB payload limit binds. C. 14 batches; the 100,000-request limit binds. D. 7 batches; the 24-hour expiry allows two batches per day.

------------------------------------------------------------------------

**E12.10.** During a staged cutover, Halyard adds `inference_geo` to every request so that both the old and the new model honour a data-residency constraint. Requests on the new model succeed; requests still routed to the older model return 400.

What is the correct account?

A. `inference_geo` must be set per organisation in the Console, not per request. B. `inference_geo` returns a 400 on pre-4.6 models, so it can only be added to the request path after those routes are retired. C. `inference_geo` conflicts with prompt caching, which the old route uses and the new one does not. D. `inference_geo` requires the Batches API, which the old route does not use.

------------------------------------------------------------------------

**E12.11.** Halyard’s capacity model assumed an average of 40,000 input tokens per request, measured on the model being retired. On the replacement model the same text tokenises to roughly 30% more tokens. Keel handles 300,000 requests per day, and the replacement is Sonnet 5.5 at \$2 per MTok input.

What is the actual daily input cost?

A. \$24,000 B. \$18,461 C. \$7,200 D. \$31,200

------------------------------------------------------------------------

**E12.12.** Halyard’s change-control document states: “We will pin `claude-sonnet-5-5` rather than a dated snapshot, accepting that the alias will roll forward to newer snapshots and give us continuous improvements without further PRs.”

What is wrong with this statement?

A. From 4.6 onward a dateless model ID is a fixed snapshot, not a floating alias; it is the pre-4.6 undated strings that floated. B. Dateless IDs are rejected on the Claude API and only accepted on Bedrock. C. Dateless IDs roll forward, but only within a minor version, so the statement is right about aliasing and wrong about scope. D. Dateless IDs are aliases, but they resolve at account creation time, so an existing account stays pinned.

------------------------------------------------------------------------

**E12.13.** During dual-running, Keel’s production path handles 200 requests per minute at 30,000 fresh input tokens each. The shadow path adds another 200 requests per minute on the candidate model, each reading a 25,000-token cached prefix plus 5,000 fresh tokens; the shadow prefix is written to cache 4 times in that minute and read on the other 196 requests. Cache writes count toward ITPM; cache reads generally do not.

How many input tokens are counted against ITPM in that minute?

A. 6,000,000 B. 7,000,000 C. 7,100,000 D. 12,000,000

------------------------------------------------------------------------

**E12.14.** *(Select THREE)* Keel is moving from `claude-sonnet-4-5-20250929` to `claude-sonnet-5-5`. Which THREE of the following must change in the request path?

A. Non-default `temperature`, `top_p` or `top_k` values must be removed. B. `thinking` with `budget_tokens` must be replaced by `output_config.effort`. C. Forced `tool_choice` (`any` or `tool`) must be replaced by `auto`. D. All `custom_id` fields must be regenerated, since the old namespace is retired with the model. E. The context window must be reduced to 200K, since 1M is reserved for Opus-class models. F. Prompt caching must be disabled, since the minimum cacheable prefix rose.

------------------------------------------------------------------------

**E12.15.** Halyard plans to dual-run for the full 43 days remaining before retirement: a 20% shadow sample for the first 14 days, then a 50% sample for the remaining 29 days. Shadowing 100% of traffic would cost \$19,500 per day.

What is the total shadow cost over the dual-run window?

A. \$167,700 B. \$337,350 C. \$419,250 D. \$838,500

------------------------------------------------------------------------

**E12.16.** An inventory of Keel’s service mesh finds a rarely used reconciliation job still configured for `claude-opus-4-1-20250805`. The job runs quarterly and last ran in July 2026. Its owner says, “It is deprecated but not retired, so we have until its retirement date; I will migrate it in the next quarter’s work.”

What is the correct response?

A. That model retired on 5 August 2026, so the job has been failing since then; this is an incident, not a planned migration. B. The model is deprecated with retirement to be announced, so the owner’s plan is acceptable but should be brought forward. C. The model retires on 30 November 2026 along with the Sonnet 4.5 snapshot, so the next quarter is too late. D. Quarterly jobs are exempt from retirement schedules provided they ran at least once before the deprecation notice.

------------------------------------------------------------------------

**E12.17.** Keel sends scanned 2,000 × 1,500 pixel images. On the retiring model, images were capped at a 1,568-pixel long edge and 1,568 visual tokens per image, and Keel downscaled accordingly. The replacement allows a 2,576-pixel long edge and up to 4,784 visual tokens, and Halyard removes the downscaling step. Image tokens are `ceil(width / 28) * ceil(height / 28)`. Keel handles 50,000 images per day on Sonnet 5.5 at \$2 per MTok input.

What is the additional daily input cost from removing the downscaling?

A. \$0 — image token pricing is unchanged B. \$153.60 C. \$388.80 D. \$232.00

------------------------------------------------------------------------

**E12.18.** Halyard’s gradual rollout routes a growing percentage of traffic to the new model while keeping a single shared cached prefix definition in code “so both paths benefit from the same cache.” At 50/50 split, measured cache hit rates on both paths are far below the single-model baseline and total spend is higher than before the rollout began.

What explains this?

A. Cache entries are evicted when hit rate falls below a threshold, which the split triggered. B. A shared prefix definition cannot be cached because it is referenced from two code paths. C. The cache is keyed per model, so each path maintains its own copy of the prefix and alternating traffic turns reads into writes on whichever path was not last used. D. Cache reads count against ITPM during a rollout, so the rate limiter is throttling reads into misses.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E12.19.** Keel’s bulk classification workload runs 400,000 requests per day, each with 130,000 input tokens and 2,000 output tokens. Halyard is choosing between Sonnet 5.5 (\$2 / \$10 per MTok) and Haiku 5.5 (\$0.10 / \$0.50 per MTok, with input rates multiplied by 5 for any request whose input exceeds 100,000 tokens; output rates are unaffected).

Which is cheaper per day, and by how much?

A. Haiku 5.5, cheaper by \$106,400 B. Haiku 5.5, cheaper by \$85,600 C. Haiku 5.5, cheaper by \$78,000 D. Sonnet 5.5, cheaper by \$18,400

------------------------------------------------------------------------

**E12.20.** Halyard’s migration board asks which model is the documented recommended replacement for `claude-sonnet-4-5-20250929`.

A. `claude-sonnet-5-5` B. `claude-opus-5-5`, because the documented default replaces all deprecated models C. `claude-sonnet-4-6`, because minor-version steps are the documented migration path D. `claude-haiku-5-5`, because the documented path is to re-baseline at the cheapest tier

------------------------------------------------------------------------

**E12.21.** Halyard’s cutover plan includes a line item: “Purchase Priority Tier capacity for Sonnet 5.5 for the dual-run window, so shadow traffic cannot throttle production.”

What is wrong with it?

A. Priority Tier cannot be combined with the Batches API, which the shadow path uses. B. Priority Tier is billed at a premium that exceeds the cost of the shadow traffic itself. C. Priority Tier is closed to new purchase and excludes all current models, so there is nothing to buy for Sonnet 5.5. D. Priority Tier applies per model snapshot, so it would cover only the retiring model.

------------------------------------------------------------------------

**E12.22.** Keel previously ran with `thinking` enabled at `budget_tokens: 8000`. To re-baseline on the replacement, Halyard sweeps three effort levels over 500 evaluation items on Opus 5.5, with a 60,000-token cached prefix. Changing effort restarts the cache, so each level pays one cache write and 499 reads. Opus 5.5 input is \$4 per MTok, 5-minute cache writes 1.25×, cache reads 0.05×.

What does the prefix cost across the sweep?

A. \$18.29 B. \$17.96 C. \$36.83 D. \$18.86

------------------------------------------------------------------------

**E12.23.** *(Select TWO)* Which TWO statements about reasoning effort apply to Halyard’s migration?

A. Effort is set at `output_config.effort` and takes `low`, `medium`, `high`, `xhigh`, `max`. B. Effort is set inside `thinking`, replacing `budget_tokens` in place. C. The default is `medium` on Opus 5.5 and Haiku 5.5, and `high` on the others. D. The default is `low` everywhere, so an explicit setting is always required. E. A `budget_tokens` value maps deterministically onto an effort level, so the sweep can be skipped. F. Effort can only be set once per conversation at the API level and never varies by request.

------------------------------------------------------------------------

**E12.24.** A Keel summarisation job moved from Haiku 4.5 to Haiku 5.5 unchanged. Each request reads a 95,000-token cached prefix and adds 8,000 fresh input tokens, producing 1,200 output tokens; there are 60,000 requests per day. Haiku 5.5 is \$0.10 / \$0.50 per MTok with cache reads at 0.1×, and any request whose input exceeds 100,000 tokens — counting cache reads and writes — has its input rates multiplied by 5. Output rates are unaffected.

What does the job cost per day on Haiku 5.5?

A. \$561.00 B. \$141.00 C. \$705.00 D. \$333.00

------------------------------------------------------------------------

**E12.25.** The Haiku 4.5 → Haiku 5.5 migration above came in roughly four times over budget, and an engineer proposes moving the job to Sonnet 5.5 “because Haiku is clearly not the cheap option any more.”

What is the better first move?

A. Move to Sonnet 5.5, since its flat input rate removes the tiering risk entirely. B. Reduce the per-request input below the 100,000-token threshold — for example by splitting the cached prefix across two requests or trimming it — since the overrun comes from crossing the tier, not from Haiku’s base rate. C. Disable prompt caching, since cache reads count toward the threshold and removing them removes the tier. D. Move to the Batches API, where the tiering multiplier does not apply.

------------------------------------------------------------------------

**E12.26.** Halyard will read a 250,000-token cached prefix 80,000 times during the regression replay and is comparing Sonnet 5.5 (\$2 per MTok input, cache reads 0.05×) with Haiku 5.5 (\$0.10 per MTok input, cache reads 0.1×, input rates multiplied by 5 above 100,000 input tokens per request).

What do the cache reads cost on each?

A. Sonnet 5.5 \$2,000; Haiku 5.5 \$200 B. Sonnet 5.5 \$1,000; Haiku 5.5 \$200 C. Sonnet 5.5 \$4,000; Haiku 5.5 \$1,000 D. Sonnet 5.5 \$2,000; Haiku 5.5 \$1,000

------------------------------------------------------------------------

**E12.27.** An experimental Keel feature runs on `claude-mythos-preview`, which was deprecated on 9 June 2026. The feature owner asks how long they have.

What is the correct answer?

A. Sixty days from the deprecation notice, so the model retired on 8 August 2026. B. Until 30 November 2026, the next scheduled retirement date. C. The retirement date is to be announced, so the feature must be migrated on the assumption that at least 60 days’ notice will arrive at an unpredictable time. D. Preview models are exempt from retirement and can be relied on indefinitely.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E12.28.** Keel’s long-running reconciliation agent passes `compaction_control` to keep its context bounded. The SDK upgrade to Python v1.0 breaks it.

What is the correct migration?

A. Rename it to `output_config.compaction`, which is the v1.0 equivalent. B. Add the compaction beta header, which v1.0 now requires. C. Move the call to the Batches API, where `compaction_control` is still accepted. D. `compaction_control` was removed in v1.0; rebuild the strategy on context editing, with the memory tool where state must outlive the context.

------------------------------------------------------------------------

**E12.29.** Halyard runs a migration canary as an agent with `max_budget_usd` set to \$5.00. Each assistant response in this run costs \$0.90, and the budget is checked after each response arrives.

What is the greatest the canary can spend, and what `ResultMessage.subtype` does it report?

A. \$4.50, with subtype `error_max_budget_usd` B. \$5.40, with subtype `error_max_budget_usd` C. \$5.00, with subtype `success` D. \$5.40, with subtype `error_max_turns`

------------------------------------------------------------------------

**E12.30.** *(Select TWO)* Halyard’s migration dashboard classifies every agent run by `ResultMessage.subtype`. Which TWO are valid values?

A. `success` B. `error_during_execution` C. `error_model_retired` D. `error_cache_miss` E. `error_deprecated_parameter` F. `partial`

------------------------------------------------------------------------

**E12.31.** A Keel agent configured with `max_turns: 10` was expected to terminate quickly during migration testing, but a run with far more than ten exchanges completed normally.

Why?

A. `max_turns` counts tool-use turns only, so exchanges that make no tool call do not advance the counter. B. `max_turns` resets whenever the model changes mid-run. C. `max_turns` applies only to subagents, not to the root agent. D. `max_turns` is measured per minute, not per run.

------------------------------------------------------------------------

**E12.32.** During dual-running, Halyard compares the old and new agents only by final output string equality and reports an 87% match rate. A reviewer points out that several of the 13% mismatches are improvements, and several of the 87% matches reached the same answer by different routes — including one case where the new agent skipped a validation tool the old one called.

What should the comparison measure instead?

A. Semantic similarity of the final strings, scored by a model grader, to absorb harmless wording differences. B. Only the mismatches, since matches by definition carry no regression risk. C. Both the output and the trajectory — which tools were called, in what order, with what arguments — so that a skipped validation step registers as a regression even when the answer matches, and a wording change does not register as one. D. Token-level diff distance between old and new outputs, thresholded at a tuned cutoff.

------------------------------------------------------------------------

**E12.33.** Halyard’s regression harness fans out 150 independent replay subagents, each taking about 25 seconds, with SDK concurrency left at its default.

What is the minimum wall-clock time?

A. 175 seconds B. 200 seconds C. 125 seconds D. 3,750 seconds

------------------------------------------------------------------------

**E12.34.** A Keel agent that requests structured output repeatedly fails validation on the new model and the run ends. Which `ResultMessage.subtype` identifies this case?

A. `error_max_structured_output_retries` B. `error_during_execution` C. `error_schema_validation` D. `error_max_turns`

------------------------------------------------------------------------

**E12.35.** *(Select TWO)* Halyard wants its dual-run comparison to be reproducible enough that a regression found on Tuesday can be re-examined on Friday. Which TWO measures are both technically valid on current models and actually help?

A. Pin the exact model ID and the exact effort level on both arms, since changing either changes behaviour and also restarts the cache. B. Set `temperature: 0` on both arms to remove sampling variance. C. Persist the full trajectory of every run — each tool call, its arguments, and its result — alongside the final output, so a run can be replayed and diffed. D. Set `top_k: 1` on the new arm to force greedy decoding. E. Run both arms through the Batches API, where sampling is disabled. F. Raise effort to `max` on both arms, which removes run-to-run variation.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E12.36.** Keel’s prompts rely on an assistant prefill to force a fixed preamble, a second prefill to force JSON, and a trailing user reminder of the output rules. On the new model, the prefills are rejected.

What is the correct set of replacements?

A. Move every prefill into the final user turn verbatim, which preserves the behaviour exactly. B. Keep the prefills but mark them as system content, which is still accepted. C. Delete the prefills and accept the loss of output shaping, since there is no replacement. D. Shape JSON output with `output_config.format`, move the preamble into the system prompt, and express continuations and reminders as user-turn content.

------------------------------------------------------------------------

**E12.37.** While rewriting prompts for the new model, Halyard’s team reorders a long-context request that currently reads: output rules, then the analyst question, then 300 source records.

What ordering should they move to, and why?

A. Source records first, then the question last — the documented ordering for long context, which the docs’ own tests associate with quality gains of up to roughly 30%, and which also makes the bulk of the prompt a stable cacheable prefix. B. Question first, then records, then rules — so the model knows the task before reading. C. Rules first, then records, then question — because rules constrain how records are read. D. Records split into thirds with the question repeated after each — so each third is scored independently.

------------------------------------------------------------------------

**E12.38.** Keel’s migration agent accumulates 26 tool results of roughly 5,000 tokens each. Context editing with `clear_tool_uses_20250919` runs at its default trigger and default keep setting.

How many results are cleared, and roughly how much context is reclaimed?

A. 20 results, about 100,000 tokens B. 26 results, about 130,000 tokens C. 23 results, about 115,000 tokens D. 3 results, about 15,000 tokens

------------------------------------------------------------------------

**E12.39.** Halyard enables both `clear_thinking_20251015` and `clear_tool_uses_20250919` on the migrated agent. Which statement is correct?

A. Only one clearing strategy may be enabled per request. B. When both are enabled, `clear_thinking_20251015` runs first. C. Tool-result clearing always runs first, because it reclaims more context. D. The two strategies are mutually exclusive on 4.7+ models.

------------------------------------------------------------------------

**E12.40.** *(Select TWO)* After the migration PR adds one new tool definition, Keel’s cache hit rate drops to near zero across all traffic, including requests that never use the new tool. Which TWO statements explain or bound this?

A. Invalidation flows tools → system → messages, so a change to tool definitions invalidates the entire cached prefix that follows, regardless of which tools a given request uses. B. Invalidation flows messages → system → tools, so adding a tool invalidates nothing before the final user turn. C. Cache lookback considers at most 20 blocks. D. Cache lookback considers at most 4 blocks, matching the breakpoint maximum. E. Tool definitions are matched by name, so adding a tool with a new name cannot affect existing cache entries. F. Cache entries survive tool changes for the remainder of their TTL and then expire normally.

------------------------------------------------------------------------

**E12.41.** Keel’s prompts are ported to the new model unchanged, including a `max_tokens` of 4,096 that was tuned when thinking was off by default. After cutover, a growing share of responses are truncated mid-sentence.

What is the most likely cause?

A. The new model’s `max_tokens` ceiling is lower, so 4,096 is being clamped downward. B. The tokenizer change means the same output text needs fewer tokens, which cannot cause truncation. C. Citations now consume output tokens, which they did not before. D. A request with no `thinking` field now runs with thinking enabled, and `max_tokens` covers thinking plus text, so the visible answer is being squeezed.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E12.42.** Keel’s extraction path has always used `tool_choice: {"type": "tool", "name": "emit_record"}` to guarantee a structured call. Every request fails after the model string is updated, and an engineer proposes switching to `tool_choice: {"type": "any"}`.

What is wrong with the proposal, and what should be done instead?

A. Nothing is wrong; `any` is the supported replacement for `tool`. B. `any` is also a forced value and is rejected on current models; use `tool_choice: {"type": "auto"}` with strict tool definitions, state in the prompt when the tool must be called, and validate the result in code. C. `any` is accepted but costs 406 tokens of overhead instead of 286, so it should be avoided on cost grounds alone. D. `any` works only when exactly one tool is defined, so the team should reduce the tool set to one.

------------------------------------------------------------------------

**E12.43.** Halyard’s capacity model budgets tool-use system prompt overhead at 406 tokens per request, the figure for forced `tool_choice`, across 900,000 requests per day on Sonnet 5.5 at \$2 per MTok input.

What is the correct daily figure, and what did the model get wrong?

A. \$514.80 — forced `tool_choice` is rejected on current models, so the applicable overhead is the 286-token `auto`/`none` figure. B. \$730.80 — the 406-token figure is correct and the model simply failed to multiply it out. C. \$514.80 — the 286-token figure applies because `any` is cheaper than `auto`. D. \$216.00 — tool-use overhead is always served from cache and billed at the cache-read rate.

------------------------------------------------------------------------

**E12.44.** Keel talks to two internal MCP servers. One has been updated to the 2026-07-28 revision and the other has not. What distinguishes the updated server?

A. It maintains a long-lived session that survives client restarts. B. It performs an `initialize` handshake before `server/discover`. C. It is stateless, with `server/discover` replacing the `initialize` handshake. D. It requires clients to pin a protocol version in the transport headers.

------------------------------------------------------------------------

**E12.45.** *(Select TWO)* One of Keel’s MCP servers depends on features deprecated in the 2026-07-28 revision and must be restructured. Which TWO features are deprecated?

A. Sampling B. Logging C. Tool definitions D. Per-request `_meta` E. Error responses F. Resource listing

------------------------------------------------------------------------

**E12.46.** After the MCP upgrade, Halyard’s observability team finds that trace identifiers no longer reach the server. The client previously sent them once during connection setup.

What is the correct fix?

A. Re-establish the session on every request so the setup-time identifier is current. B. Send the trace identifier in each request’s `_meta` field, since the revision is stateless and there is no connection-scoped place to put it. C. Encode the trace identifier into each tool’s input schema as a required property. D. Move tracing to the transport layer only, since the revision defines no metadata field.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E12.47.** On cutover night, Keel’s dual-run doubles token consumption and the organisation hits its spend cap. The client’s generic 429 handler enters exponential backoff and the queue stalls for an hour. The response bodies all carry `error.details.error_code == "enforced_spend_limit_reached"`.

What should the handler have done?

A. Backed off longer, since spend-limit 429s clear more slowly than rate-limit 429s. B. Honoured the `retry-after` header on these responses rather than using its own schedule. C. Classified 429s by error code and failed fast on this one — it is never retryable and carries no `retry-after` — so the cutover could be paused deliberately rather than stalling silently. D. Shifted the stalled requests to the Batches API, which is exempt from spend limits.

------------------------------------------------------------------------

**E12.48.** *(Select TWO)* Which TWO controls most reduce the risk of an irreversible mistake during Keel’s cutover?

A. A staged traffic split with an automated rollback trigger bound to a measured regression signal, not to a human noticing. B. Requiring explicit approval for any state-changing action the new path takes that the old path did not, for the duration of the dual run. C. Running the new path at `max` effort throughout, so that it is less likely to make mistakes. D. Disabling logging on the new path to avoid duplicating sensitive data across two systems. E. Raising `max_turns` on the new agent so it has room to self-correct. F. Relying on the model’s refusal behaviour to block unsafe actions on the new path.

------------------------------------------------------------------------

**E12.49.** *(Select TWO)* Halyard’s regression replay re-sends archived production requests, some of which contain customer-supplied free text, through the candidate model, and stores both arms’ outputs in a comparison database that the whole engineering team can read.

Which TWO concerns are legitimate and specific to this design?

A. Archived customer free text may contain prompt-injection payloads that were harmless against the old configuration but reach new tools on the candidate path. B. The comparison database widens access to customer content beyond the systems that originally held it, so it needs the same controls as the source. C. Replaying archived requests is impossible because the Messages API has no idempotency key. D. Batch replay cannot be used for regression testing because results are returned out of order. E. Storing both arms’ outputs doubles token costs, which is a security concern. F. Archived requests cannot be replayed against a different model, because thinking blocks are model-bound.

------------------------------------------------------------------------

**E12.50.** After cutover, Keel’s error rate rises because a small share of responses return `stop_reason: "refusal"` where the old path returned content. The client treats any unexpected stop reason as a 5xx and retries the identical request three times.

What is the correct handling?

A. Stop retrying, classify the refusal from its stop details, and route those requests to a non-automated path — an identical retry cannot change the outcome and triples the cost. B. Retry with a longer `max_tokens`, since refusals are usually truncations. C. Retry on the retiring model until its retirement date, since it does not refuse these requests. D. Strip the system prompt and retry, since system instructions are the usual cause.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E12.51.** Halyard wants every Claude Code session working in the Keel repository to know the migration rules: never reintroduce `temperature`, always use `output_config.effort`, and never pin a dated model ID.

Where do these belong?

A. In the settings file’s `permissions.deny` list, as denied parameter names. B. In `CLAUDE.md` at the repository root, which Claude Code loads as project memory. C. In the MCP server configuration, as server-side instructions. D. In the commit template, so they appear in every commit message.

------------------------------------------------------------------------

**E12.52.** To stop anyone running the legacy deployment script during the migration freeze, an engineer adds `Bash(./deploy-legacy.sh:*)` to the deny list. A colleague then adds `Bash(./deploy-legacy.sh --dry-run)` to the allow list in a more specific settings file, so that dry runs remain possible.

What is the result?

A. The more specific settings file wins, so dry runs are permitted. B. Both rules are dropped as conflicting, and the command prompts interactively. C. Deny takes precedence over allow and allow cannot carve an exception out of a deny rule, so dry runs remain blocked; the deny pattern itself must be narrowed. D. The allow rule applies only to the session that defined it, so dry runs work locally but not in CI.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E12.53.** Halyard’s shadow comparison reports that the candidate model matches the retiring model on 94% of replayed requests. The migration board wants to treat 94% as the go/no-go number.

What is the strongest objection?

A. 94% is too low; a migration should not proceed below 99% agreement. B. Agreement cannot be measured at all across different models, because tokenisation differs. C. The sample is unrepresentative unless it is drawn uniformly at random, which the replay cannot guarantee. D. Agreement with the old model is not the same as correctness: the 6% disagreement contains both regressions and improvements, and the 94% agreement can conceal shared errors — so the disagreements must be adjudicated against a reference standard, and the agreeing cases spot-checked, before any single number is treated as a gate.
