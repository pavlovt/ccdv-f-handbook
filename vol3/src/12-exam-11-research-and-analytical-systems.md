# Exam 11 — Research and Analytical Systems

**53 questions · 120 minutes · closed book · answers in the back**

Every scenario in this exam takes place inside **Polaris Scholar**, a hosted research platform that ingests scientific literature, runs long-context synthesis across large corpora, and drives multi-step analytical agents on behalf of research groups. You do not need any domain science to answer these questions: the science is set dressing, and the engineering is what is being tested.

This is the hardest tier in Volume III. A score here is a depth diagnostic, not a predicted exam result — treat anything you miss as a map of where to read next, not as a forecast.

Unless a question says otherwise, assume the Claude API (not Bedrock or Google Cloud), current model pricing, and default SDK behaviour.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E11.1.** Polaris Scholar screens abstracts overnight. Each request to Claude Haiku 5.5 carries a 12,000-token screening protocol that is identical across the run and marked with a cache breakpoint, plus 800 tokens of abstract text unique to the request, and produces 200 output tokens. Tonight’s run is 40,000 requests, submitted through the Message Batches API. The first request writes the cache with a 5-minute TTL; the remaining 39,999 read it. Haiku 5.5 is priced at \$0.10 per MTok input and \$0.50 per MTok output.

What does the run cost?

A. \$3.60 B. \$12.00 C. \$6.00 D. \$27.60

------------------------------------------------------------------------

**E11.2.** A Polaris Scholar synthesis endpoint runs on Haiku 5.5 for cost reasons. Each request sends a 120,000-token cached methods corpus (read from cache) plus 20,000 tokens of fresh query material, and returns 3,000 output tokens. Haiku 5.5 is the only tiered model: a request whose input exceeds 100,000 tokens is billed at 5× the standard input rates for that request, and cache reads and writes count toward the threshold. Output rates are not multiplied. Base rates are \$0.10 per MTok input, \$0.50 per MTok output, with cache reads at 0.1×.

What do 2,000 such requests cost?

A. \$35.00 B. \$9.40 C. \$25.40 D. \$47.00

------------------------------------------------------------------------

**E11.3.** *(Select TWO)* An engineer describes the nightly reprocessing job: “We submit 60,000 synthesis requests as a single batch. A worker reads the results stream in order and writes row *i* of the results to paper *i* of the input manifest. For the 4,000 requests where we only want a token count and no generation, we set `max_tokens: 0`. We poll until the batch completes, then archive the results.”

Which TWO statements identify real defects in this plan?

A. A single batch may not exceed 100,000 requests, so 60,000 is over the limit and the batch will be rejected. B. Batch results are returned in arbitrary order; `custom_id` is the only reliable join key, so positional matching will mis-assign results. C. `max_tokens: 0` is rejected by the Batches API, so those 4,000 requests cannot be submitted as described. D. Batch results are retained for only 24 hours, so archiving after polling is too late. E. Prompt caching cannot be combined with the Batches API, so the job loses all cache savings. F. A batch that has not completed within 24 hours is cancelled, so polling is pointless.

------------------------------------------------------------------------

**E11.4.** A Polaris Scholar request is assembled as follows: a tool definitions block with a cache breakpoint; a system prompt with a cache breakpoint; three corpus blocks, each with its own cache breakpoint; and the final user turn with a cache breakpoint. The engineer’s reasoning is that finer-grained breakpoints let partial corpus changes reuse more of the prefix.

What is the primary problem?

A. Cache breakpoints placed on tool definitions have no effect, because tools are never cached. B. The request specifies six cache breakpoints, exceeding the maximum of four, so it is rejected. C. Breakpoints on the final user turn are ignored, so the last block is never cached. D. Corpus blocks must be placed after the user turn for the breakpoints to take effect.

------------------------------------------------------------------------

**E11.5.** A Polaris Scholar workspace pins a 180,000-token review corpus into the cache on Claude Opus 5.5 and serves 400 analyst queries against it in one session. The corpus is written once with a 5-minute TTL (refreshed by the reads) and read 400 times — treat it as 1 write and 400 reads. Each query adds 500 fresh input tokens and produces 1,200 output tokens. Opus 5.5 is \$4 per MTok input and \$20 per MTok output; cache writes at the 5-minute TTL are 1.25× the input rate, and cache reads on Opus 5.5 are 0.05× the input rate.

What is the session’s total cost?

A. \$24.80 B. \$25.70 C. \$40.10 D. \$298.40

------------------------------------------------------------------------

**E11.6.** Polaris Scholar’s ingestion worker wraps every call in a retry policy: on any HTTP 429 it waits with exponential backoff and jitter and retries up to eight times. During a month-end crunch the worker spends forty minutes in a retry loop and completes no work, and the on-call engineer finds every response body contains `error.details.error_code == "enforced_spend_limit_reached"`.

What should the retry policy do differently?

A. Honour the `retry-after` header on that response instead of using its own backoff schedule. B. Increase the backoff ceiling, because spend-limit 429s clear on a longer cycle than rate-limit 429s. C. Switch those requests to the Batches API, where spend limits are not enforced. D. Treat a 429 carrying that error code as non-retryable and surface it immediately, because it will never succeed on retry and carries no `retry-after`.

------------------------------------------------------------------------

**E11.7.** A Polaris Scholar figure-extraction step sends every panel of a paper to the model as an image. The current paper has six panels at 1,130 × 870 pixels and two panels at 910 × 1,405 pixels. Image tokens are computed as `ceil(width / 28) * ceil(height / 28)`.

How many image tokens does the paper’s figures consume?

A. 10,786 B. 10,640 C. 10,740 D. 11,238

------------------------------------------------------------------------

**E11.8.** A Polaris Scholar feature produces a full machine-readable extraction of a 400-page monograph in a single response. The design document specifies a streaming request on Sonnet 5.5 with `max_tokens` set to 200,000, on the grounds that the 1M context window makes the output length affordable.

What is wrong?

A. Streaming responses are capped at 64K tokens regardless of `max_tokens`. B. `max_tokens` above 100,000 requires the Batches API. C. The maximum output is 128K tokens, so the request will not accept `max_tokens: 200000`; the extraction must be decomposed into multiple responses. D. The 1M context window is shared between input and output, so a 200,000-token output leaves too little room for the monograph.

------------------------------------------------------------------------

**E11.9.** Polaris Scholar’s job runner submits each analysis step with a UUID in a header, and on a network timeout re-submits the same step with the same UUID, “so the API will de-duplicate it.” Engineers notice duplicate charges and duplicate rows after transient network failures.

What is the correct diagnosis?

A. The UUID must be sent as `custom_id` rather than a header for de-duplication to apply. B. De-duplication only applies within a single 5-minute cache window, which the timeout exceeded. C. De-duplication applies on the Batches API but not on streaming requests. D. The Messages API has no idempotency key, so the re-submission is simply a second billable request; de-duplication must be implemented in the job runner.

------------------------------------------------------------------------

**E11.10.** A one-off reprocessing job must send 260,000 requests through the Message Batches API. Each request serialises to approximately 4 KB. A single batch may contain at most 100,000 requests and at most 256 MB of payload (take 1 MB as 1,000,000 bytes and 1 KB as 1,000 bytes).

What is the minimum number of batches, and which limit binds?

A. 3 batches; the 100,000-request limit binds. B. 5 batches; the 256 MB payload limit binds. C. 3 batches; the 24-hour expiry binds. D. 5 batches; the 100,000-request limit binds.

------------------------------------------------------------------------

**E11.11.** A long-running Polaris Scholar agent accumulates tool results from a citation-graph crawler and eventually exceeds its context budget. The team enables context editing with `clear_tool_uses_20250919` at its defaults.

Which statement correctly describes what the defaults do?

A. Clearing is triggered once the context reaches 100,000 tokens, and the three most recent tool uses are kept. B. Clearing runs on every turn, keeping the three largest tool results. C. Clearing is triggered at 100,000 tokens and keeps the three *oldest* tool uses, since early results anchor the trajectory. D. Clearing is triggered when `max_tokens` is reached and retains the last tool use only.

------------------------------------------------------------------------

**E11.12.** *(Select TWO)* Polaris Scholar wants every synthesis response to be a strict JSON object conforming to a published schema, and also wants each claim in the response to carry a citation pointing at the source passage. The team plans to set `output_config.format` to the schema and enable citations on the source documents in the same request.

Which TWO statements are correct?

A. `output_config.format` and citations are incompatible; combining them returns a 400. B. `output_format` is the current first-class field and `output_config.format` is the deprecated alias. C. `output_config.format` is the first-class field; `output_format` is deprecated in favour of it. D. Citations are only available on the Batches API, so the combination is impossible in synchronous requests. E. Setting `output_config.format` silently disables citations and returns a 200. F. Structured output and citations can be combined if `tool_choice` is set to `any`.

------------------------------------------------------------------------

**E11.13.** Polaris Scholar’s organisation has an input-tokens-per-minute (ITPM) limit. During the busiest minute, the platform issues 40 requests. Each request reads a 180,000-token cached corpus and adds 6,000 fresh input tokens. Separately, during that same minute the corpus prefix is re-written to the cache three times, at 180,000 tokens each. Cache writes count toward ITPM; cache reads generally do not.

How many input tokens are counted against the ITPM limit in that minute?

A. 240,000 B. 780,000 C. 7,200,000 D. 7,980,000

------------------------------------------------------------------------

**E11.14.** A Polaris Scholar “whole field” request assembles 1,180,000 tokens of full-text papers plus a 40,000-token system prompt and asks for a 20,000-token synthesis. The architect argues that because the model’s context window is 1M tokens and the output limit is 128K, the request fits.

What is wrong with the reasoning?

A. The output limit counts against the context window, so the 20,000-token output is the binding constraint. B. System prompts are not counted toward the context window, but the papers alone still fit. C. The input alone is 1,220,000 tokens, which exceeds the 1M context window; the corpus must be reduced or the synthesis staged. D. Context windows are measured in characters, not tokens, so the request is well within limits.

------------------------------------------------------------------------

**E11.15.** A Polaris Scholar workspace holds a 250,000-token corpus and serves 20 analyst queries spread across one hour, with gaps between queries that always exceed five minutes. On Opus 5.5 — \$4 per MTok input, 5-minute cache writes at 1.25×, 1-hour cache writes at 2×, cache reads at 0.05× — the team compares two configurations: a 1-hour TTL (1 write plus 19 reads) and a 5-minute TTL (every query is a fresh write, 20 writes and no reads).

How much does the 1-hour TTL save on prefix costs over that hour?

A. \$22.05 B. \$23.00 C. \$22.80 D. \$12.50

------------------------------------------------------------------------

**E11.16.** An engineer proposes shipping all overnight work through the Batches API and relying on the service to hold results until the quarterly archival job runs six weeks later.

What is the defect?

A. Batch results cannot be downloaded more than once, so archival must happen inline. B. Batch results are retained for 24 hours, so even a daily archival cycle is too slow. C. Batches expire after 29 days of processing, so long batches never complete. D. Batch results are retained for 29 days, so a six-week archival cycle will lose them.

------------------------------------------------------------------------

**E11.17.** *(Select THREE)* Which THREE statements about the Message Batches API are correct for Polaris Scholar’s nightly workload?

A. Batch requests receive a 50% discount, and this stacks with prompt caching discounts. B. A batch is limited to 100,000 requests and 256 MB. C. Requests inside a batch may set `stream: true` to receive incremental results. D. Results may be returned in any order, and `custom_id` is the only reliable way to match a result to its request. E. Batch processing bypasses the organisation’s spend limits. F. A batch’s 50% discount replaces prompt caching discounts rather than stacking with them.

------------------------------------------------------------------------

**E11.18.** Polaris Scholar runs an effort sweep on Sonnet 5.5 over a fixed 400,000-token cached corpus: 60 requests, 30 at `medium` effort and 30 at `high`. The first implementation alternates effort on every request; the proposed fix groups all 30 `medium` requests, then all 30 `high`. Changing the effort level restarts the cache. Sonnet 5.5 input is \$2 per MTok, 5-minute cache writes are 1.25× and cache reads are 0.05×.

How much does grouping save on the corpus prefix?

A. \$55.68 B. \$58.00 C. \$56.68 D. \$0.00 — effort does not affect the cache

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E11.19.** A Polaris Scholar synthesis job makes 150 requests. Each reads a 300,000-token cached corpus, adds 2,000 fresh input tokens, and produces 5,000 output tokens. Ignore the one-off cache write. The team compares Fable 5.1 (\$10 / \$50 per MTok, cache reads 0.025×) against Opus 5.5 (\$4 / \$20 per MTok, cache reads 0.05×).

How much more does Fable 5.1 cost for this job?

A. \$22.50 B. \$24.30 C. \$26.55 D. \$51.30

------------------------------------------------------------------------

**E11.20.** A Polaris Scholar design review asks which model the team should start from for a new, not-yet-characterised analytical workload, absent any benchmark data of their own.

Which answer reflects the documented guidance?

A. Haiku 5.5, because starting from the cheapest model and escalating is always the documented path. B. Opus 5.5, which is documented as the recommended default. C. Fable 5.1, because the most capable model always produces the best baseline against which to measure downgrades. D. Sonnet 5.5, because it is the mid-tier model and mid-tier is the documented default.

------------------------------------------------------------------------

**E11.21.** Polaris Scholar routes 10,000 analysis requests. 30% of them carry 160,000 input tokens; the other 70% carry 40,000. Every request produces 2,000 output tokens. On Haiku 5.5 (\$0.10 / \$0.50 per MTok) a request whose input exceeds 100,000 tokens is billed at 5× the input rates for that request; output rates are unaffected.

What does running the whole workload on Haiku 5.5 cost?

A. \$86.00 B. \$278.00 C. \$290.00 D. \$390.00

------------------------------------------------------------------------

**E11.22.** A capacity plan for Polaris Scholar’s peak season reads: “To guarantee throughput during the submission deadline, we will purchase Priority Tier capacity for Opus 5.5 and Sonnet 5.5 and route all deadline traffic through it.”

What is wrong with this plan?

A. Priority Tier is available only for Haiku-class models, so Opus 5.5 cannot be covered. B. Priority Tier requires a minimum 12-month commitment that will not complete before the deadline. C. Priority Tier capacity cannot be combined with prompt caching, which would raise costs beyond the benefit. D. Priority Tier is closed to new purchase and excludes all current models, so no such capacity can be bought for Opus 5.5 or Sonnet 5.5.

------------------------------------------------------------------------

**E11.23.** *(Select TWO)* Which TWO statements about reasoning effort on current models are correct?

A. Effort is configured through `output_config.effort`, with values `low`, `medium`, `high`, `xhigh`, and `max`. B. Effort is configured as `thinking.effort`, replacing `thinking.budget_tokens`. C. The default effort is `medium` on Opus 5.5 and Haiku 5.5, and `high` on the others. D. The default effort is `high` on every current model. E. Setting `thinking` with `budget_tokens` on a 4.7+ model silently downgrades to the nearest effort level. F. Effort values map deterministically onto fixed thinking-token budgets, so a sweep is unnecessary.

------------------------------------------------------------------------

**E11.24.** Polaris Scholar runs an effort sweep over a fixed 500,000-token cached prefix on Sonnet 5.5: three effort levels on each of two model configurations, 120 requests per combination (720 requests in total). Within a combination the prefix is written once and read thereafter; changing model or effort restarts the cache. Sonnet 5.5 input is \$2 per MTok, 5-minute cache writes 1.25×, cache reads 0.05×.

What do the prefix tokens cost across the whole sweep?

A. \$37.20 B. \$43.20 C. \$78.90 D. \$900.00

------------------------------------------------------------------------

**E11.25.** A Polaris Scholar product manager asks why the assistant keeps describing a late-2026 methodological debate as “recent work” when the team’s internal wiki covers it in detail. No retrieval is wired into that endpoint.

What is the correct explanation?

A. The model’s training is continuously refreshed, so the wiki will be absorbed within a few weeks. B. Reliable knowledge extends to June 2026; later material must be supplied in context, and the endpoint supplies none. C. The model is hallucinating because effort is set too low; raising effort to `max` will recover the missing material. D. Internal wikis are excluded from training by policy, but public late-2026 literature is included.

------------------------------------------------------------------------

**E11.26.** Polaris Scholar will read a 400,000-token cached prefix 1,000 times during a synthesis campaign and is choosing between Fable 5.1 (\$10 per MTok input, cache reads 0.025×), Opus 5.5 (\$4, 0.05×), and Sonnet 5.5 (\$2, 0.05×).

Which model has the lowest absolute cache-read cost for the campaign, and what is it?

A. Fable 5.1, \$10.00 B. Opus 5.5, \$80.00 C. Sonnet 5.5, \$40.00 D. Sonnet 5.5, \$20.00

------------------------------------------------------------------------

**E11.27.** Polaris Scholar routes each query to Haiku 5.5, Sonnet 5.5, or Opus 5.5 based on a predicted difficulty score, and shares a single 300,000-token cached corpus prefix across all three routes. Cache hit rates are far below the modelled figure and costs are triple the forecast.

What is the most likely cause?

A. The cache is per-model, so routing across three models means each model maintains its own prefix and a route switch is a cache write rather than a read. B. A 300,000-token prefix exceeds the maximum cacheable prefix length, so nothing is cached at all. C. Cache reads are counted against ITPM, so the rate limiter is evicting entries. D. Cache entries are invalidated whenever the user turn changes, so a shared prefix can never be reused.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E11.28.** A Polaris Scholar analytical agent is configured with `max_turns: 12`. In testing, a run that the team counts as “twenty-one turns” of back-and-forth completes successfully without hitting the limit.

Why?

A. `max_turns` applies per subagent, and the parent’s turns are not counted. B. `max_turns` counts only turns in which the model produced text, not tool calls. C. `max_turns` is advisory and only logs a warning when exceeded. D. `max_turns` counts tool-use turns only, so conversational turns that make no tool call do not advance the counter.

------------------------------------------------------------------------

**E11.29.** A Polaris Scholar agent is launched with `max_budget_usd` set to \$2.00. In this run every assistant response costs \$0.35, and the budget is checked after each response arrives.

What is the greatest amount the run can spend, and what `ResultMessage.subtype` will it report?

A. \$1.75, with subtype `error_max_budget_usd` B. \$2.10, with subtype `error_max_budget_usd` C. \$2.00, with subtype `success` D. \$2.10, with subtype `error_during_execution`

------------------------------------------------------------------------

**E11.30.** *(Select TWO)* Polaris Scholar’s orchestrator must branch on how an agent run ended. Which TWO of the following are valid `ResultMessage.subtype` values?

A. `error_max_turns` B. `error_max_structured_output_retries` C. `error_context_window_exceeded` D. `error_rate_limited` E. `timeout` F. `error_max_depth`

------------------------------------------------------------------------

**E11.31.** A Polaris Scholar orchestrator spawns a literature-triage subagent, which spawns a per-journal subagent, which spawns a per-paper extraction subagent, which attempts to spawn a per-figure subagent. The last spawn fails. The team has changed no SDK defaults.

What is the explanation?

A. Subagent concurrency defaults to 20 and the fan-out has exceeded it. B. Subagents cannot spawn subagents at all; only the orchestrator may. C. Subagent nesting depth defaults to 3, and the per-figure subagent would be the fourth level. D. The default `max_turns` of the root agent is consumed by the nested spawns.

------------------------------------------------------------------------

**E11.32.** A Polaris Scholar evaluation harness scores a multi-step analytical agent purely on whether the final numeric answer matches a reference value. Scores are high, but reviewers repeatedly find that the agent reached correct answers by reading a cached summary table rather than by running the analysis it was asked to run, and the same prompt produces a wrong answer when the cached table is stale.

What is the right correction to the harness?

A. Score the trajectory as well as the answer — assert on which tools were called, in what order, and on what inputs — because an unverified path makes a correct answer uninformative. B. Raise effort to `max` so the agent stops taking shortcuts. C. Replace exact-match scoring with a model-graded rubric on the final answer. D. Increase the number of reference values so that coincidental matches become unlikely.

------------------------------------------------------------------------

**E11.33.** A Polaris Scholar orchestrator fans out 90 independent extraction subagents. Each takes approximately 40 seconds, and the SDK’s concurrency default is unchanged.

What is the minimum wall-clock time for the fan-out?

A. 180 seconds B. 200 seconds C. 120 seconds D. 3,600 seconds

------------------------------------------------------------------------

**E11.34.** A Polaris Scholar service pinned to Python SDK v0.x is being upgraded to v1.0. Its agent loop passes `compaction_control` to manage long-running context, and the upgrade fails at import-time validation.

What is the correct account of the failure?

A. `compaction_control` was renamed to `output_config.compaction` and the old name now raises a deprecation warning only. B. `compaction_control` now requires a beta header that the service does not send. C. `compaction_control` is only valid with the Batches API in v1.0. D. `compaction_control` was removed from the Python SDK in v1.0, so the call must be rewritten around context editing and the memory tool.

------------------------------------------------------------------------

**E11.35.** *(Select TWO)* A Polaris Scholar reviewer complains that re-running the same analytical agent on the same inputs produces different intermediate steps and sometimes a different conclusion, and asks the team to “make it deterministic.”

Which TWO responses are technically sound?

A. Pin the exact model snapshot ID and the exact effort level, since changing either changes behaviour and also restarts the cache. B. Set `temperature: 0` on the agent’s requests, which makes current models deterministic. C. Record and replay the full trajectory — every tool call, its arguments, and its result — so a run can be audited and compared even though it cannot be made bit-identical. D. Move the agent to the Batches API, where sampling is disabled. E. Set `top_k: 1`, which restricts the model to the single highest-probability token. F. Raise effort to `max`, which eliminates run-to-run variation.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E11.36.** Polaris Scholar’s synthesis prompt currently places the analyst’s question first, followed by forty papers, followed by output-format instructions. A reviewer proposes reordering.

Which ordering matches the documented guidance, and why?

A. Documents first, then the question last — the documented ordering, with quality gains of up to roughly 30% reported in the docs’ own long-context tests. B. Question first, then documents — so the model knows what to look for while reading. C. Documents interleaved with per-document questions, so each is scored independently. D. Output-format instructions first, documents second, question third, because format constrains reading.

------------------------------------------------------------------------

**E11.37.** A Polaris Scholar agent enables both thinking-block clearing and tool-result clearing on a long trajectory.

What is the correct configuration?

A. Only one clearing strategy may be active per request; combining them returns a 400. B. Tool-result clearing must run first, because tool results dominate the context. C. When both are combined, `clear_thinking_20251015` runs first. D. The order is determined by whichever strategy’s trigger threshold is reached first.

------------------------------------------------------------------------

**E11.38.** A Polaris Scholar crawler agent has accumulated 18 tool results, each approximately 8,000 tokens, and context editing with `clear_tool_uses_20250919` fires at its default trigger with its default keep setting.

How many tool results are cleared, and roughly how many tokens does that reclaim?

A. 15 results, about 120,000 tokens B. 18 results, about 144,000 tokens C. 3 results, about 24,000 tokens D. 12 results, about 96,000 tokens

------------------------------------------------------------------------

**E11.39.** Polaris Scholar wants an agent to carry durable notes about a research programme across sessions, beyond what fits in a single context window.

Which mechanism is designed for this?

A. `compaction_control`, which persists a rolling summary server-side. B. The memory tool, `memory_20250818`. C. A 1-hour cache TTL, refreshed on every session start. D. `clear_tool_uses_20250919` with `keep` set to a high value.

------------------------------------------------------------------------

**E11.40.** *(Select TWO)* Polaris Scholar’s cache hit rate collapses whenever the team ships a prompt change. Which TWO statements about cache invalidation are correct?

A. Invalidation flows tools → system → messages: changing tool definitions invalidates the system prompt and messages that follow. B. Invalidation flows messages → system → tools: changing the last user turn invalidates everything before it. C. Changing the system prompt invalidates cached message blocks that come after it but not the cached tool definitions before it. D. Cache lookback considers at most 20 blocks. E. Cache lookback considers at most 4 blocks, matching the breakpoint maximum. F. Reordering tool definitions is safe, because tools are matched by name rather than by position.

------------------------------------------------------------------------

**E11.41.** A Polaris Scholar prompt places the 600,000-token corpus last, immediately before the model’s turn, and the analyst’s question at the very top of the user message, followed by instructions. The team reports both weak long-context recall and a cache hit rate near zero across a session of related questions.

Which single change addresses both symptoms?

A. Reduce the corpus to 200,000 tokens so that recall improves and the prefix becomes cacheable. B. Move the instructions into the system prompt and leave the rest unchanged. C. Add a cache breakpoint after the question so the question is cached. D. Put the stable corpus at the front of the prompt with a cache breakpoint after it, and move the varying question to the end.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E11.42.** Polaris Scholar connects to an internal MCP server exposing a corpus index. The team is updating its client to the 2026-07-28 revision.

What is the key structural change?

A. The protocol gained a persistent websocket session that replaces per-request HTTP. B. Tool discovery moved from `server/discover` to the `initialize` handshake. C. The protocol became stateless: `server/discover` replaces the `initialize` handshake. D. Servers must now maintain per-client session state to support resumable tool calls.

------------------------------------------------------------------------

**E11.43.** Under the 2026-07-28 MCP revision, where does per-request metadata such as a trace identifier belong?

A. In a per-request `_meta` field. B. In the `initialize` handshake, once per session. C. In a `session` object negotiated at connection time. D. In the transport’s HTTP headers only; the protocol defines no metadata field.

------------------------------------------------------------------------

**E11.44.** *(Select TWO)* A Polaris Scholar MCP server was written against an older revision. Which TWO of its features are deprecated under the 2026-07-28 revision?

A. Sampling B. Logging C. Tool definitions D. Resource listing E. Prompt templates F. Error responses

------------------------------------------------------------------------

**E11.45.** Polaris Scholar is budgeting token overhead for a 50,000-request extraction run on Sonnet 5.5 (\$2 per MTok input). The design document says: “Each request carries tool definitions; with `tool_choice` set to `any` the tool-use system prompt overhead is 406 tokens, so we budget 406 × 50,000 tokens.” The team’s tool definitions are otherwise unchanged.

What is the correct budget, and what did the design miss?

A. \$28.60 — forced `tool_choice` values (`any` or `tool`) return 400 on current models, so the 406-token path is unavailable and the applicable overhead is 286 tokens per request. B. \$40.60 — the 406-token figure is correct; the design’s only error is omitting the cost calculation. C. \$28.60 — the 286-token figure applies because `any` is cheaper than `auto`, not because forced choice is rejected. D. \$0.00 — the tool-use system prompt is always cached and therefore free.

------------------------------------------------------------------------

**E11.46.** To guarantee that an extraction step always emits structured data, a Polaris Scholar engineer sets `tool_choice: {"type": "tool", "name": "record_extraction"}` on a current model. Every request fails.

What is the correct remedy?

A. Add the `tool_choice` beta header, which re-enables forced tool use. B. Rename the tool, since `tool_choice.name` must match a reserved namespace. C. Set `tool_choice: {"type": "any"}` instead, which is still supported. D. Use `tool_choice: {"type": "auto"}` with strict tool definitions, and state in the prompt when the tool must be called.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E11.47.** A Polaris Scholar agent crawls preprint full texts and feeds them directly into a loop that has access to a `write_report` tool and a `send_email` tool. A reviewer warns that a preprint’s body text is untrusted input.

What is the strongest mitigation?

A. Instruct the model in the system prompt never to follow instructions found in paper text. B. Lower effort so the model is less likely to act on elaborate embedded instructions. C. Treat retrieved document text as untrusted data — isolate it from the instruction channel, and gate state-changing tools such as `send_email` behind validation or human approval rather than relying on prompt-level instructions alone. D. Strip all imperative sentences from retrieved text before it enters the context.

------------------------------------------------------------------------

**E11.48.** *(Select TWO)* Which TWO practices meaningfully reduce the blast radius of a prompt-injection attempt against Polaris Scholar’s analytical agent?

A. Give each tool the narrowest capability that satisfies its purpose, so that a hijacked turn cannot reach destructive operations. B. Require human approval for irreversible or outbound actions, independent of what the model decides. C. Place the untrusted document text at the very end of the prompt, since later text has less influence. D. Disable thinking, since embedded instructions are most often acted on during reasoning. E. Raise `max_turns`, so the agent has room to recover from a hijacked turn. F. Rely on the model’s refusal behaviour as the primary control.

------------------------------------------------------------------------

**E11.49.** A Polaris Scholar response includes a quoted passage attributed to a source paper, but the citation points at a different document in the corpus. The pipeline builds citations by asking the model to emit a source filename in its JSON output.

What is the structural problem?

A. The filename field should be an integer index into the corpus, which is less error-prone. B. Attribution produced as free-form model output is unverified; citations should come from the citations mechanism, which binds a quoted span to the document block it came from. C. The corpus should be reduced so that only one document is ever in context. D. Citations should be generated in a second pass by a smaller model.

------------------------------------------------------------------------

**E11.50.** A Polaris Scholar endpoint receives a response whose `stop_reason` is `refusal`. The client currently treats any non-`end_turn` stop reason as a transport error and retries three times with the identical request.

What should it do instead?

A. Retry with `max_tokens` increased, since refusals usually indicate truncation. B. Retry with a different model, since refusal behaviour is model-specific and the retry will usually succeed. C. Strip the system prompt and retry, since refusals are usually triggered by system instructions. D. Stop retrying, inspect the refusal’s stop details to classify it, and route the request to a non-automated path — an identical retry will not change the outcome.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E11.51.** Polaris Scholar’s repository contains conventions that every Claude Code session should follow — the analysis directory layout, the statistics library to prefer, and the rule that generated figures are never committed.

Where do these belong?

A. In `CLAUDE.md` at the project root, which Claude Code loads as project memory. B. In the settings file’s `permissions.allow` list. C. In a comment block at the top of the main entry-point file. D. In an MCP server that the session queries for conventions.

------------------------------------------------------------------------

**E11.52.** A Polaris Scholar engineer adds `Bash(rm:*)` to the deny list, and then, to let a cleanup script run, adds `Bash(rm -rf ./build)` to the allow list in a more specific settings file.

What happens?

A. The more specific settings file wins, so the cleanup command is permitted. B. The allow entry is invalid syntax and is ignored, but the deny entry is also dropped. C. Deny takes precedence over allow, and an allow entry cannot carve an exception out of a deny rule, so the command remains blocked. D. The two rules conflict, so Claude Code prompts the user interactively on each invocation.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E11.53.** Polaris Scholar must evaluate a synthesis feature whose “correct” output is genuinely contested: three domain experts disagree about how strongly a body of evidence supports a conclusion, and their disagreement is stable rather than careless. The team’s current eval scores model output against a single expert’s labels and reports 61% accuracy.

What is the soundest way to build an eval here?

A. Pick the most senior expert’s labels as ground truth and treat the others’ as noise. B. Replace the eval with a model-graded rubric, since human disagreement makes human labels unusable. C. Report only inter-model agreement, since absolute correctness is unknowable. D. Measure the model against the distribution of expert judgements — establish inter-rater agreement first, score against the consensus where one exists, and report performance separately on the contested subset rather than collapsing it into a single accuracy figure.
