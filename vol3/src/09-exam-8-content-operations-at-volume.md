# Exam 8 — Content Operations at Volume

## Instructions

**53 questions. 120 minutes. Closed book. Answers in the back.**

Work the paper in one sitting, with no documentation and no console. Scratch paper is expected: thirteen items require you to compute something from figures given in the stem, and every figure you need is in the stem.

Where an item is labelled **(Select TWO)** or **(Select THREE)**, exactly that many options are correct. There is no partial credit: score the item only if you selected all of the correct options and none of the incorrect ones.

This paper follows the real exam’s domain blueprint question-for-question. Several items present a design that is plausible but defective and ask what is wrong with it; in those items the options are usually all true statements, and only one of them is the defect that explains the behaviour described. Read for the fault, not for the first true sentence.

Every scenario in this paper sits in one world: a media group running translation, localisation, summarisation, moderation, metadata and archive-processing pipelines at high volume. Moderation questions concern the engineering of the pipeline — thresholds, escalation, measurement — and nothing in this paper requires you to reason about the content being moderated.

All questions assume the current model line-up and current API behaviour.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E8.1.** A metadata-generation service on Claude Sonnet 5.5 must return a parseable JSON record for every archive asset. The team prefills the assistant turn with an opening brace and sets a stop sequence on the matching closing brace. Every request now returns HTTP 400. What fixes the design?

-   A. Remove the assistant prefill and constrain the response with `output_config.format` using a `json_schema`.
-   B. Keep the prefill and add the structured-outputs beta header, which permits prefill on current models.
-   C. Replace the stop sequence with a higher `max_tokens` so the record is never cut short.
-   D. Move the prefill into the final user turn, where the restriction does not apply.

------------------------------------------------------------------------

**E8.2.** A localisation job translates 40,000 articles into six target languages: 240,000 requests on Claude Sonnet 5.5, submitted across three Message Batches so that no batch exceeds the per-batch ceiling. Each request carries a 1,500-token glossary-and-style prefix served from cache, 900 tokens of unique article text, and produces 1,200 output tokens. Assume every request gets a cache hit and ignore the priming requests. What does the work cost?

-   A. \$1,656.00
-   B. \$1,674.00
-   C. \$1,692.00
-   D. \$3,348.00

------------------------------------------------------------------------

**E8.3.** An engineer prepares the same localisation job as a single Message Batches submission of 240,000 requests, reasoning that one submission is simpler to track than three. What is wrong with this?

-   A. Nothing; the ceiling is on payload size rather than request count, and the payload is well under it.
-   B. A batch holds at most 100,000 requests or 256 MB, whichever is reached first, so the submission has to be split.
-   C. A batch holds at most 100,000 requests, but the excess is queued automatically into a follow-on batch, so the only consequence is a longer wall-clock time.
-   D. The ceiling is per organization per day rather than per batch, so the submission succeeds but blocks all other batch work for 24 hours.

------------------------------------------------------------------------

**E8.4.** A summarisation feature must return a JSON object in which each summary field quotes the source paragraph it came from. The team sets `output_config.format` with a `json_schema` and enables citations on the source documents. Every request returns HTTP 400. What is the correct response?

-   A. Raise `max_tokens` so the citation blocks fit alongside the JSON object.
-   B. Add the `structured-outputs-2025-11-13` beta header, which unlocks citations with structured output.
-   C. Move the citation configuration from the document blocks into `output_config`, where the two are reconciled.
-   D. Citations and `output_config.format` cannot be combined; keep one of them and recover the other some other way, for example an uncited structured pass alongside a separate cited free-text pass.

------------------------------------------------------------------------

**E8.5.** **(Select TWO)** An overnight subtitle batch does not finish inside the processing window and the batch expires. Which TWO statements about this outcome are correct?

-   A. Requests that expired are not billed.
-   B. Results for the requests that did complete remain downloadable for 29 days after the batch’s `created_at`.
-   C. Expired requests are automatically resubmitted into a follow-on batch.
-   D. Batches expire after 72 hours rather than 24.
-   E. When a batch expires, any partial results it produced are discarded along with it.

------------------------------------------------------------------------

**E8.6.** An archive-digitisation request to Claude Opus 5.5 carries three scanned stills: 1,960 x 1,102, 616 x 448 and 2,044 x 1,148 pixels. None exceeds the model’s native resolution, so none is downscaled. How many input tokens do the images contribute?

-   A. 5,793
-   B. 6,075
-   C. 6,104
-   D. 6,145

------------------------------------------------------------------------

**E8.7.** The group bills inference back to eleven publishing imprints. An engineer proposes setting `metadata.user_id` to the imprint code on every request and grouping spend by it in the Cost API. What is wrong with this plan?

-   A. Nothing, but imprint codes must be hashed first, because `metadata.user_id` is capped at 512 characters.
-   B. Nothing, but the grouping is only available on usage from the Batches API, and most of the group’s traffic is synchronous.
-   C. `metadata.user_id` feeds abuse detection and is not a grouping dimension in the Usage or Cost APIs; per-imprint attribution needs separate API keys or workspaces.
-   D. `metadata.user_id` forms part of the cached prefix, so a per-imprint value destroys the prompt cache.

------------------------------------------------------------------------

**E8.8.** A transcript-enrichment service runs on Claude Haiku 5.5. Each request carries an 88,000-token cached archive context and 14,000 tokens of fresh transcript, and produces 900 output tokens. What does one request cost?

-   A. \$0.00273
-   B. \$0.01013
-   C. \$0.01365
-   D. \$0.05325

------------------------------------------------------------------------

**E8.9.** A translation worker retries on HTTP 500 using the same `Idempotency-Key` header it sent on the first attempt, expecting the duplicate to be collapsed server-side. Occasionally an article ends up with two stored translations for the same language. What explains this?

-   A. The Messages API has no idempotency key; the header is ignored, so duplicate suppression has to be implemented by the caller against its own key.
-   B. Idempotency keys are honoured but only within a five-minute window, which a long backoff exceeds.
-   C. Idempotency keys are honoured only on requests that carry no `output_config`, and the worker sets one.
-   D. Idempotency keys are honoured per workspace, and the worker pool spans two workspaces.

------------------------------------------------------------------------

**E8.10.** A 36,000-token house style guide is sent as a stable prefix on every request to Claude Sonnet 5.5. The team is considering a five-minute cache breakpoint on it. Counting only the style-guide tokens, at what number of requests inside the TTL does caching first become cheaper in total than sending it uncached every time?

-   A. The 2nd request
-   B. The 3rd request
-   C. The 4th request
-   D. The 5th request

------------------------------------------------------------------------

**E8.11.** A localisation pipeline places a `cache_control` breakpoint on a 410-token per-locale header that opens every request. No error appears, but `cache_read_input_tokens` stays at zero and costs do not move. Why?

-   A. Per-locale content cannot be cached, because the cache key is scoped to the workspace rather than the request.
-   B. The breakpoint is in the wrong level of the prompt, and only message-level breakpoints produce reads.
-   C. The pipeline exceeds four breakpoints, so the first is dropped silently.
-   D. The block is below the 512-token minimum cacheable length on current models, so it is processed without caching and no error is raised.

------------------------------------------------------------------------

**E8.12.** **(Select THREE)** A moderation service runs on Claude Haiku 5.5, where exceeding 100,000 input tokens in a request moves the whole request to the 5x price tier. Which THREE of the following count toward that 100,000-token threshold?

-   A. Tokens read from the prompt cache.
-   B. Tokens written to the prompt cache.
-   C. Fresh uncached input tokens.
-   D. Output tokens produced by the response.
-   E. The `max_tokens` ceiling set on the request.
-   F. Thinking tokens produced during the current turn.

------------------------------------------------------------------------

**E8.13.** To make subtitle segmentation reproducible across reruns, a team sets `temperature: 0` on requests to `claude-haiku-5-5`. Every request returns HTTP 400. What is the correct fix?

-   A. Set `top_p: 1`, which is the supported way to pin sampling on current models.
-   B. Remove `temperature`; sampling parameters are deprecated on Claude 4.7 and later and a non-default value returns 400. Fix the shape of the output with `output_config.format` and hold `output_config.effort` constant instead.
-   C. Keep `temperature` but set it inside `output_config`, where it remains accepted.
-   D. Set `temperature: 1`, the only value still accepted, and rely on a fixed random seed for reproducibility.

------------------------------------------------------------------------

**E8.14.** A localisation agent runs on Claude Opus 5.5 inside the 1M-token context window. The fixed parts are: an 18,000-token system prompt; nine tool definitions averaging 640 tokens each; the tool-use system prompt overhead at the default `tool_choice`; and a 46,000-token running glossary. The team reserves 48,000 tokens of the window for output. Each subtitle segment averages 1,240 tokens. How many complete segments fit in one request?

-   A. 711
-   B. 712
-   C. 748
-   D. 749

------------------------------------------------------------------------

**E8.15.** An archive-reprocessing job retries every HTTP 429 with exponential backoff and unlimited attempts. It stalls for an entire weekend. The 429 bodies carry `error.details.error_code` set to `enforced_spend_limit_reached` and no `retry-after` header. What should the client do differently?

-   A. Fall back to a fixed 60-second retry interval, which is the documented default when `retry-after` is absent.
-   B. Move the job to the Batches API, where workspace spend limits do not apply.
-   C. Classify that error code as terminal and stop: a spend-cap 429 is never retryable, so the job should surface the condition and wait for the cap to be raised.
-   D. Rotate to a second API key in the same workspace, since the cap is enforced per key.

------------------------------------------------------------------------

**E8.16.** A summarisation pipeline runs on Claude Sonnet 5.5 against an input rate limit of 2,000,000 input tokens per minute. In steady state each request reads a 120,000-token cached prefix and sends 9,000 tokens of fresh article text; the prefix is written rarely enough to be ignored. Cache reads generally do not count toward the input rate limit. How many requests per minute can the pipeline sustain?

-   A. 15
-   B. 16
-   C. 222
-   D. 223

------------------------------------------------------------------------

**E8.17.** **(Select TWO)** A localisation pipeline caches its tool definitions, its system prompt — which contains the glossary — and its message history. Which TWO statements are correct?

-   A. Swapping the glossary inside the system prompt invalidates the system and message prefixes but leaves the tool prefix cached.
-   B. Swapping the glossary inside the system prompt invalidates all three cached prefixes.
-   C. Adding a tool to the array invalidates only the tool prefix.
-   D. Appending a new user turn leaves the tool and system prefixes cached.
-   E. Cache reads generally count toward the input-tokens-per-minute rate limit.
-   F. Changing `output_config.format` has no effect on the prompt cache for that thread.

------------------------------------------------------------------------

**E8.18.** A metadata service rotates between forty different schemas depending on asset type, each passed in `output_config.format`. Engineers notice that the first request using any given schema is measurably slower than subsequent ones, and that the effect returns for a schema that has not been used for a day. What explains this?

-   A. A schema is compiled into a grammar on first use and the compiled grammar is cached for 24 hours after it was last used, so a schema that goes a day without traffic is recompiled.
-   B. Schemas are compiled per API key, and the service rotates keys daily.
-   C. The first request with a schema runs without grammar constraint and the response is validated afterwards, which is what costs the extra time.
-   D. Compilation latency scales with the number of distinct schemas in the workspace, so forty schemas make every first request slow.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E8.19.** A summarisation pipeline processes 500,000 articles. Design: Claude Haiku 5.5 on every article at 4,000 input and 600 output tokens; 8% fail a quality gate and are re-run on Claude Opus 5.5 at the same token counts. No caching, no batching, no tier crossing. What is the all-in inference cost?

-   A. \$350.00
-   B. \$1,120.00
-   C. \$1,470.00
-   D. \$14,000.00

------------------------------------------------------------------------

**E8.20.** A team starting a new archive-enrichment project asks which model to build on and when to escalate. Which answer matches the documented guidance?

-   A. Start on Claude Haiku 5.5, which the documentation names the default, and escalate only when latency budgets allow.
-   B. Start on Claude Sonnet 5.5, which the documentation names the recommended default, and escalate to Opus 5.5 when evals plateau.
-   C. Start on Claude Fable 5.1 to fix a quality ceiling, then step down one model at a time until evals break.
-   D. Start on Claude Opus 5.5, which the documentation names the recommended default, and escalate to Fable 5.1 for demanding reasoning and long-horizon agentic work, or when Opus 5.5 at higher effort still falls short on your evals.

------------------------------------------------------------------------

**E8.21.** **(Select TWO)** Which TWO statements about effort control on current models are correct?

-   A. Effort is set through `output_config.effort` and takes one of `low`, `medium`, `high`, `xhigh` or `max`.
-   B. Effort belongs inside the `thinking` object, where it replaces `budget_tokens`.
-   C. Changing effort between two otherwise identical requests restarts the prompt cache.
-   D. Claude Sonnet 5.5 and Claude Fable 5.1 both default to `medium` effort.
-   E. Setting `thinking` with a `budget_tokens` value is the supported way to cap reasoning depth on Claude 4.7 and later.

------------------------------------------------------------------------

**E8.22.** Planning for an awards-season traffic spike, an architect proposes purchasing Priority Tier capacity for the moderation pipeline. What is the objection?

-   A. Priority Tier cannot be combined with the Batches API, and the moderation pipeline is batch-based.
-   B. Priority Tier forfeits prompt caching, which would raise the pipeline’s cost more than the spike justifies.
-   C. Priority Tier is closed to new purchase and excludes all current models, so it cannot be part of a plan built on the current line-up; spike headroom must come from batching, caching and model choice.
-   D. Priority Tier is available only to organizations above a spend threshold that the group does not meet.

------------------------------------------------------------------------

**E8.23.** A summarisation agent on Claude Opus 5.5 sends a 120,000-token prefix with a one-hour cache breakpoint. An experiment alternates `output_config.effort` between `medium` and `high` on consecutive requests, so every request re-writes the prefix instead of reading it. Across 300 requests, how much more do the prefix tokens cost than they would if effort were held constant for the whole run?

-   A. \$7.18
-   B. \$8.14
-   C. \$279.86
-   D. \$288.00

------------------------------------------------------------------------

**E8.24.** A team pins `claude-opus-5-5` in configuration on the understanding that the ID floats forward to whatever the newest Opus is, so upgrades arrive automatically. What is wrong with this understanding?

-   A. Nothing, but a floating ID invalidates the prompt cache whenever the underlying snapshot changes.
-   B. Model IDs without a date are fixed snapshots from Claude 4.6 onward, not aliases; a newer Opus ships under a new ID, and this snapshot will eventually be retired with at least 60 days’ notice.
-   C. The ID is an alias but floats only within a minor version, so a move to 6.0 would need a configuration change.
-   D. The ID is an alias and floats, but aliases are rejected by the Batches API, so batch work would diverge from live traffic.

------------------------------------------------------------------------

**E8.25.** **(Select THREE)** Which THREE statements about the current model line-up are correct?

-   A. Claude Haiku 5.5 is the only current model whose input pricing is tiered by request size.
-   B. Claude Sonnet 5.5 reads cached tokens at 0.05x its base input price.
-   C. All four current models have a reliable knowledge cutoff of June 2026.
-   D. Claude Fable 5.1 reads cached tokens at 0.05x its base input price.
-   E. Claude Opus 5.5 is priced at \$2 per MTok input and \$10 per MTok output.
-   F. Claude Haiku 5.5 has a smaller context window than the rest of the line-up, which is what makes it cheap.

------------------------------------------------------------------------

**E8.26.** A moderation classifier on Claude Haiku 5.5 currently sends one request per asset carrying 140,000 input tokens. An engineer proposes splitting each asset into three requests of 50,000 input tokens each, the growth coming from repeated shared instructions, with no caching in either design. Counting input tokens only, what is the per-asset saving?

-   A. \$0.0150
-   B. \$0.0550
-   C. \$0.0700
-   D. \$0.0850

------------------------------------------------------------------------

**E8.27.** A team proposes running Claude Fable 5.1 across the whole 9-million-item subtitle archive to normalise timecode strings into a single format. Evals put Haiku 5.5 at 99.6% and Fable 5.1 at 99.8% on the task. What is the strongest objection?

-   A. The task is enormous in volume, mechanically specified, and separated by 0.2 points of quality; the efficiency-first path puts it on the cheapest model that clears the bar, and Fable 5.1 is positioned for demanding reasoning and long-horizon agentic work rather than bulk normalisation.
-   B. Fable 5.1 is unavailable through the Batches API, so a 9-million-item job could not take the batch discount.
-   C. Fable 5.1 does not support `output_config.format`, so the timecode format could not be constrained.
-   D. Fable 5.1’s maximum output is too low to return a normalised timecode for every item in a request.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E8.28.** An archive-processing agent runs through the Agent SDK with `max_budget_usd` set to 5.00. After twelve responses the run has spent \$4.88. The thirteenth response costs \$0.46. What is the final spend, and what `ResultMessage.subtype` does the run end with?

-   A. \$4.88, with subtype `success`, because the thirteenth response is cancelled before it is billed.
-   B. \$5.00, with subtype `error_max_budget_usd`, because spend is clamped at the cap.
-   C. \$5.34, with subtype `error_during_execution`, because overspending is an execution fault.
-   D. \$5.34, with subtype `error_max_budget_usd`, because the budget is checked after a response arrives and can therefore be overshot by one response.

------------------------------------------------------------------------

**E8.29.** A localisation agent is configured with `max_turns: 12`. The team expects a hard stop after twelve messages, but transcripts routinely show thirty or more assistant and user messages before the run ends. What explains this?

-   A. `max_turns` applies per subagent rather than to the run as a whole.
-   B. `max_turns` is advisory in the Agent SDK and enforced only in the CLI.
-   C. `max_turns` counts only turns that produced no tool call, so tool-heavy runs are effectively unbounded.
-   D. `max_turns` counts tool-use turns only, so ordinary assistant and user messages do not consume the budget.

------------------------------------------------------------------------

**E8.30.** **(Select TWO)** Which TWO of the following are valid values of `ResultMessage.subtype` in the Agent SDK?

-   A. `error_max_turns`
-   B. `error_quota_exceeded`
-   C. `error_during_execution`
-   D. `error_subagent_depth`
-   E. `error_schema_invalid`

------------------------------------------------------------------------

**E8.31.** An archive-triage orchestrator spawns 45 subagents at once, one per collection, and each of those is written to spawn two further generations below it. Throughput plateaus well short of 45-way parallelism, and the bottom generation never runs at all. Which pair of defaults accounts for both symptoms?

-   A. Concurrency defaults to 10 and depth is unbounded, so the plateau is concurrency and the missing generation is a bug.
-   B. Concurrency is unbounded and depth defaults to 2, so the plateau is rate limiting and the missing generation is depth.
-   C. Concurrency defaults to 20, so only 20 of the 45 run at a time, and depth defaults to 3, so the generation below that is refused.
-   D. Concurrency defaults to 20 and depth defaults to 5, so the missing generation must come from the spend cap rather than from depth.

------------------------------------------------------------------------

**E8.32.** A single moderation-and-metadata agent is wired to four MCP servers exposing 280 tools, roughly 41,000 tokens of definitions, all loaded on every request. Tool selection is unreliable and cost per asset is high. Which change addresses the cause?

-   A. Raise `output_config.effort` to `xhigh` so the model weighs all 280 definitions more carefully.
-   B. Place a `cache_control` breakpoint after the last tool definition, which removes the definitions from the model’s decision space.
-   C. Consolidate the four servers into one, which halves the number of definitions through deduplication.
-   D. Keep a small set of frequently used tools loaded, defer the rest behind tool search, and split the work across subagents whose tool sets match their task — the fault is that the entire catalogue is in context for every decision.

------------------------------------------------------------------------

**E8.33.** An archive agent on Claude Opus 5.5 enables `clear_tool_uses_20250919` with `trigger` set to 60,000 input tokens and `keep` set to 2 tool uses. The system prompt plus tool definitions total 16,000 tokens and never change. Each tool call returns about 9,000 tokens of archive records, and the agent’s own text between calls is negligible. At which tool call does clearing first fire?

-   A. The 4th
-   B. The 5th
-   C. The 6th
-   D. The 7th

------------------------------------------------------------------------

**E8.34.** A long-running archive agent enables both context-editing strategies, listing `clear_tool_uses_20250919` first and `clear_thinking_20251015` second in the `edits` array. Behaviour does not match the documentation. What is wrong?

-   A. When both strategies are used, `clear_thinking_20251015` must be listed first in the `edits` array.
-   B. The two strategies require different beta headers and cannot be sent in one request.
-   C. `clear_tool_uses_20250919` must set `clear_at_least` whenever thinking clearing is also enabled.
-   D. Thinking clearing is incompatible with the memory tool, which this agent also uses.

------------------------------------------------------------------------

**E8.35.** A localisation workflow has four steps per article: source-language detection, terminology extraction, translation, and a back-translation quality check. Detection and terminology extraction are independent of each other; translation needs both; the quality check needs the translation. Which decomposition fits, and why?

-   A. One agent with all four as tools, because a single agent sees the whole article and avoids duplicating input tokens.
-   B. Run detection and terminology extraction in parallel, then chain translation onto their joined output, then chain the quality check onto the translation — the two independent steps gain nothing from being serialised, and each dependent step genuinely needs what precedes it.
-   C. Chain all four in a fixed order, because a chain is easier to cache than a fan-out.
-   D. Run all four in parallel and reconcile afterwards, because parallelisation always wins on latency.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E8.36.** A summarisation prompt is assembled in this order: the article text for this request, then a 28,000-token editorial style guide, then a 9,000-token house glossary, then the instruction block. A cache breakpoint sits at the end of the glossary. Cache hit rates are near zero. What is the fix?

-   A. Move the breakpoint to the very end of the prompt so that it covers the article text as well.
-   B. Switch the breakpoint to a one-hour TTL, which tolerates a prefix that changes between requests.
-   C. Split the style guide across two breakpoints so that a change to the article invalidates only one of them.
-   D. Put the stable content first — style guide, then glossary, then instructions — and the per-request article last, so the cached prefix is byte-identical across requests.

------------------------------------------------------------------------

**E8.37.** A metadata schema constrains `content_rating` to the enum `["GENERAL", "TEEN", "MATURE"]`. In production the field occasionally comes back as `General`. No error is returned and no special `stop_reason` appears. What is the correct handling?

-   A. Add the mixed-case variants to the enum, which is the documented remedy.
-   B. Treat it as a schema-compilation failure and retry with a simplified schema.
-   C. Enum values may differ from the schema in capitalisation only, with no error; compare case-insensitively downstream and avoid enums whose members differ only by case.
-   D. Set `additionalProperties: false` on the containing object, which forces exact enum casing.

------------------------------------------------------------------------

**E8.38.** **(Select THREE)** A metadata schema is being written for `output_config.format`. Which THREE of the following will return 400 because the feature is unsupported?

-   A. `minLength` and `maxLength` on a headline string.
-   B. `minimum` and `maximum` on a numeric duration field.
-   C. A recursive schema for arbitrarily nested chapter structures.
-   D. `anyOf` across two alternative asset shapes.
-   E. `const` pinning a schema-version field to a fixed value.
-   F. A string `format` of `date-time` on a publication timestamp.

------------------------------------------------------------------------

**E8.39.** A moderation-triage service asks Claude to lay out its reasoning step by step inside a structured output, so reviewers can audit borderline decisions. A proportion of responses come back with `stop_reason: "refusal"`. What should the team do?

-   A. Retry those requests with a higher `max_tokens`, since a refusal indicates truncation.
-   B. Remove `additionalProperties: false` so the reasoning fields are permitted.
-   C. Abandon structured output, since auditability and `output_config.format` are mutually exclusive.
-   D. Ask for a short explanation field instead of step-by-step reasoning; a request for extended reasoning inside a constrained output can trigger a reasoning-extraction refusal, and such a response arrives with a 200 status and is billed.

------------------------------------------------------------------------

**E8.40.** A long archive-processing conversation places four `cache_control` breakpoints. The earliest is meant to cover a prefix that sits 27 block positions back, through a stretch of alternating tool uses and tool results. That breakpoint never hits; the other three work. What is the likely cause?

-   A. Four breakpoints exceed the ceiling, so the earliest is silently dropped.
-   B. Tool-result blocks are not cacheable, so any prefix containing one is skipped.
-   C. Breakpoints are evaluated newest-first and only the three most recent are honoured.
-   D. A breakpoint looks back at most 20 block positions, counting itself as the first, so a boundary 27 positions back is out of reach; consecutive tool-use blocks and consecutive tool-result blocks each collapse to a single position, which is why the count is worth doing carefully.

------------------------------------------------------------------------

**E8.41.** A metadata pipeline returns `"runtime": "1h 42m"` for some assets and `"runtime": "102"` for others, even though the schema types `runtime` as an integer and documents it as minutes. The prompt states the convention in prose. What is the most effective change?

-   A. Give two or three worked examples showing the exact normalisation, including one source stated in hours and minutes and one stated in minutes, since the schema already fixes the type and what is missing is a demonstration of the convention.
-   B. Add `minimum: 0` to the field so that only valid integers are accepted.
-   C. Raise `output_config.effort` to `max` on every request.
-   D. Move the convention out of the prompt and into the field’s `description`, which the compiled grammar enforces.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E8.42.** A metadata service must call its `emit_record` tool on every request and never reply in prose. The team sets `tool_choice` to `{"type": "any"}`. Every request returns HTTP 400 on current models. How should the guarantee be obtained?

-   A. Switch to `{"type": "tool", "name": "emit_record"}`, the one forced form still accepted.
-   B. Drop the forced choice and move the guarantee into the output contract: constrain the response with `output_config.format` so the model must return the record directly, leaving `tool_choice` at its default.
-   C. Set `disable_parallel_tool_use: true`, which forces exactly one tool call per turn.
-   D. Keep the forced choice and add the tool-use beta header that re-enables it.

------------------------------------------------------------------------

**E8.43.** **(Select TWO)** An archive-catalogue MCP server is being written against the stateless 2026-07-28 revision. Which TWO statements about that revision are correct?

-   A. `server/discover` replaces `initialize` as the capability-negotiation entry point.
-   B. Per-request context travels in a `_meta` field on each request, rather than in server-side session state.
-   C. Every request must echo a session identifier issued at connection time.
-   D. Sampling and logging become required capabilities that every server must implement.
-   E. Tool definitions move out of the protocol and are registered out of band.

------------------------------------------------------------------------

**E8.44.** A metadata request to Claude Sonnet 5.5 carries a 9,000-token system prompt, eight tool definitions averaging 525 tokens each, a 3,500-token user payload, and `tool_choice` left at its default. How many input tokens does the request consume?

-   A. 16,700
-   B. 16,986
-   C. 17,106
-   D. 17,392

------------------------------------------------------------------------

**E8.45.** An MCP archive server is designed so that, when an asset’s rights status is ambiguous, the server calls back into the client to have the model choose between interpretations, using the sampling capability. Under the stateless revision the callback never fires. What should the design do instead?

-   A. Keep sampling and mark the tool long-running so the client holds the connection open.
-   B. Pin the server to the previous protocol revision, which the client will negotiate automatically.
-   C. Return the candidate interpretations as the tool’s result and let the agent’s next turn choose between them, because sampling is deprecated in the stateless revision.
-   D. Have the server call a model directly using its own credentials, which is the documented replacement for sampling.

------------------------------------------------------------------------

**E8.46.** A `fetch_transcript` tool and a `fetch_captions` tool are frequently confused by the model, which calls one when it should call the other. Both carry a single-line description. Which change most reliably reduces mis-selection?

-   A. Expand each description to say what the tool is for, what it is not for, and when the sibling tool is the right choice, naming that sibling explicitly — the model chooses from the definitions, and one line each gives it no basis for the distinction.
-   B. Reorder the tools array so the more common tool appears first.
-   C. Set `disable_parallel_tool_use: true` so only one of them can be chosen per turn.
-   D. Mark both tools `strict: true`, which validates inputs and so clarifies which tool was intended.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E8.47.** A moderation-triage agent reads user-submitted captions and descriptions, and holds a `publish_asset` tool so it can release items that clear triage. An asset whose description contains text addressed to the assistant is published without review. What is the structural fix?

-   A. Add a system-prompt instruction telling the model to ignore any instructions found inside submitted text.
-   B. Raise `output_config.effort` to `max`, which hardens the model against injected instructions.
-   C. Strip URLs and markup from submitted text before it reaches the model.
-   D. Treat submitted text as untrusted data — labelled explicitly as content to assess rather than instructions to follow — and remove the publishing capability from the component that reads it, so that releasing an asset goes through a separate path with its own authorisation.

------------------------------------------------------------------------

**E8.48.** A moderation pipeline scores each asset from 0 to 1 and routes everything above 0.5 to human review. Reviewers are overwhelmed: 82% of what reaches them is cleared without action, while spot checks of the auto-cleared stream keep surfacing items that should have been escalated. The team proposes raising the threshold to 0.8 to cut reviewer load. What is the sound engineering response?

-   A. Raise the threshold to 0.8 as proposed; reviewer load is the binding constraint and precision is what reviewers experience.
-   B. Lower the threshold to 0.3, since the spot checks prove the classifier is missing cases and recall is always the priority in moderation.
-   C. A single threshold cannot serve both ends: measure precision and recall across the score range on a labelled set, then use two thresholds — auto-clear below the lower one, auto-escalate above the upper one, and send only the band between them to human review — and size that band against reviewer capacity.
-   D. Replace the score with a hard binary output from the model, since a calibrated score is what makes threshold selection arbitrary.

------------------------------------------------------------------------

**E8.49.** **(Select TWO)** Which TWO measures meaningfully reduce the blast radius of an indirect prompt injection reaching a content-operations agent?

-   A. Give the agent only read-only tools and route every state change through a separate service that requires explicit authorisation.
-   B. Validate every proposed action against an allow-list of permitted operations and value ranges before executing it.
-   C. Instruct the model in the system prompt to refuse instructions that appear inside tool output.
-   D. Move to a larger model, which is not susceptible to injection.
-   E. Retain full prompt logs so injections can be found afterwards.
-   F. Wrap untrusted text in a distinctive delimiter the model is told never to cross.

------------------------------------------------------------------------

**E8.50.** To debug moderation disagreements, a team logs the complete request body of every call — including submitted text that sometimes carries names, addresses and account references — and sets `metadata.user_id` to the submitting account’s email address so logs can be correlated. What is the principal problem?

-   A. Both halves put personal data where it does not belong: the logs retain identifiers the moderation task does not need, and `metadata.user_id` is an abuse-detection signal that should carry an opaque identifier rather than directly identifying data.
-   B. The logs will outgrow the 29-day retention window that applies to batch results.
-   C. `metadata.user_id` is capped at 512 characters, so longer addresses truncate and correlation silently breaks.
-   D. Logging request bodies invalidates the prompt cache, because the logging layer mutates the prefix.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E8.51.** A content-tooling repository’s project settings deny `Bash(rm:*)`. A developer adds an allow rule for `Bash(rm -rf ./build:*)` in their user settings, expecting the narrower allow to carve out an exception. The command is still refused. Why?

-   A. User settings never take effect when project settings exist, whatever the rule type.
-   B. Deny takes precedence over allow, and an allow rule cannot carve an exception out of a deny rule; the deny itself must be narrowed.
-   C. Rules are evaluated in file order, and the deny happens to be read first.
-   D. `rm` patterns must name an absolute path, so the allow rule never matches.

------------------------------------------------------------------------

**E8.52.** A media-tooling team wants every Claude Code session in the repository to know the house conventions for subtitle file formats and the rules for touching the archive index, without anyone pasting them each time. What is the right mechanism?

-   A. A `CLAUDE.md` at the project root, which Claude Code loads as project memory for sessions in that repository.
-   B. A custom slash command, which is the only project-scoped configuration Claude Code loads automatically.
-   C. The user-level settings file, so the conventions follow the developer into every repository.
-   D. A hook that injects the text before every tool call, since Claude Code has no declarative project memory.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E8.53.** A moderation classifier is evaluated over 200,000 assets. It flags 4,000, of which human review confirms 3,100 as true violations. A separate stratified audit of the unflagged remainder estimates that 1,350 violations were missed. What are the classifier’s precision and recall?

-   A. Precision 69.7%, recall 77.5%
-   B. Precision 77.5%, recall 69.7%
-   C. Precision 77.5%, recall 77.5%
-   D. Precision 1.6%, recall 69.7%
