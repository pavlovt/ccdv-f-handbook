# Exam 7 — Commerce and Catalogue Systems

## Instructions

**53 questions. 120 minutes. Closed book. Answers in the back.**

Work the paper in one sitting, with no documentation and no console. Scratch paper is expected: fourteen items require you to compute something from figures given in the stem, and every figure you need is in the stem.

Where an item is labelled **(Select TWO)** or **(Select THREE)**, exactly that many options are correct. There is no partial credit: score the item only if you selected all of the correct options and none of the incorrect ones.

This paper follows the real exam’s domain blueprint question-for-question. Several items present a design that is plausible but defective and ask what is wrong with it; in those items the options are usually all true statements, and only one of them is the defect that explains the behaviour described. Read for the fault, not for the first true sentence.

Every scenario in this paper sits in one world: a large online retailer’s catalogue and merchandising platform. All questions assume the current model line-up and current API behaviour.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E7.1.** A catalogue ingestion service on Claude Opus 5.5 sends one request carrying three supplier photographs and a short text block. The images are 1,450 x 1,090, 980 x 784 and 330 x 220 pixels. None exceeds the model’s native resolution, so none is downscaled. How many input tokens do the three images contribute?

-   A. 2,995
-   B. 3,040
-   C. 3,104
-   D. 3,296

------------------------------------------------------------------------

**E7.2.** An attribute-extraction service on Claude Sonnet 5.5 must return parseable JSON for every product. To guarantee this, the team prefills the assistant turn with an opening brace and sets a stop sequence on the closing brace. Every request now returns HTTP 400. Which single change fixes the design?

-   A. Remove the assistant prefill and constrain the response with `output_config.format` using a `json_schema`.
-   B. Keep the prefill but move it into the system prompt, where prefill restrictions do not apply.
-   C. Add stop sequences for the closing brace of each nested object as well as the outermost one.
-   D. Raise `max_tokens` so that a long attribute object is never truncated mid-structure.

------------------------------------------------------------------------

**E7.3.** **(Select TWO)** A merchandising team must generate descriptions for 80,000 SKUs overnight. Their design: one Message Batches submission containing all 80,000 requests; `stream: true` on each request so a progress bar can be driven from the token stream; results joined back to SKUs by the position of each result in the downloaded file; and a `custom_id` scheme that reuses the same SKU identifier in tomorrow’s batch. Which TWO elements of this design are defects?

-   A. `stream: true` is rejected by the Batches API, so every request fails validation.
-   B. Batch results are returned in arbitrary order, so results must be joined on `custom_id` rather than on position.
-   C. 80,000 requests exceeds the per-batch request ceiling, so the submission is rejected outright.
-   D. Reusing the same `custom_id` in a later batch is prohibited, because `custom_id` must be globally unique across an organization.
-   E. `params` are validated synchronously at submission, so a single bad request rejects the whole batch.

------------------------------------------------------------------------

**E7.4.** A description-generation job runs 60,000 SKUs on Claude Sonnet 5.5 through the Message Batches API. Each request carries a 3,200-token shared prefix served from cache, 400 tokens of unique SKU data, and produces 350 output tokens. Assume every request gets a cache hit and ignore the cost of the single priming request that wrote the prefix. What does the batch cost?

-   A. \$129.00
-   B. \$133.80
-   C. \$138.60
-   D. \$277.20

------------------------------------------------------------------------

**E7.5.** A review-summarisation feature must return a JSON object whose fields each quote the review they came from. The team sets `output_config.format` with a `json_schema` and also enables citations on the review documents. Every request returns HTTP 400. What is the correct response?

-   A. Raise `max_tokens` so the citation blocks fit alongside the JSON object.
-   B. Set `output_config.effort` to `high` so Claude emits citation markers inside the JSON string fields.
-   C. Replace `output_config.format` with the deprecated `output_format` parameter, which permits citations.
-   D. Citations and `output_config.format` cannot be combined; keep one of them and recover the other some other way, for example a separate uncited structured pass.

------------------------------------------------------------------------

**E7.6.** A catalogue taxonomy of 24,000 tokens is sent as a stable prefix on every request to Claude Opus 5.5. The team is considering a 1-hour cache breakpoint on it. Counting only the taxonomy tokens, at what number of requests inside the hour does caching first become cheaper in total than sending the taxonomy uncached every time?

-   A. The 2nd request
-   B. The 3rd request
-   C. The 4th request
-   D. The 5th request

------------------------------------------------------------------------

**E7.7.** The platform serves 900 third-party merchants. Finance wants per-merchant inference cost. An engineer proposes setting `metadata.user_id` to the merchant ID on every request and then grouping spend by that field. What is wrong with this plan?

-   A. Nothing, but the merchant ID must be hashed first, because `metadata.user_id` is capped at 512 characters.
-   B. Nothing, but the Usage and Cost APIs group by `metadata.user_id` only for requests submitted through the Batches API.
-   C. `metadata.user_id` feeds abuse detection and is not a grouping dimension in the Usage or Cost APIs; per-merchant attribution needs separate API keys or workspaces.
-   D. `metadata.user_id` is part of the cached prefix, so a per-merchant value destroys the prompt cache on every request.

------------------------------------------------------------------------

**E7.8.** A search-relevance reranker runs on Claude Haiku 5.5. Each request carries a 94,000-token catalogue slice served from cache and 9,000 tokens of fresh query context, and produces 600 output tokens. What does one request cost?

-   A. \$0.00214
-   B. \$0.00694
-   C. \$0.01070
-   D. \$0.05300

------------------------------------------------------------------------

**E7.9.** **(Select THREE)** On a catalogue-extraction request to Claude Sonnet 5.5 that carries tool definitions, which THREE of the following are billed as **input** tokens?

-   A. The tool definitions themselves.
-   B. The tool-use system prompt overhead that is added whenever `tools` is present.
-   C. The thinking tokens Claude produces while working on the current turn.
-   D. The `max_tokens` value, which reserves output capacity and is charged whether or not it is used.
-   E. The `tool_result` content your application sends back to the model.
-   F. The `cache_control` breakpoints, which carry a small per-breakpoint surcharge.

------------------------------------------------------------------------

**E7.10.** A nightly catalogue backfill retries failed requests. On HTTP 500 the client resends the request with the same `Idempotency-Key` header it generated for the first attempt, on the assumption that a duplicate will be collapsed server-side. Occasionally a SKU ends up with two generated descriptions. What explains this?

-   A. The Messages API has no idempotency key; the header is ignored, so duplicate suppression must be implemented by the caller against its own dedup key.
-   B. Idempotency keys are honoured only on the Batches API endpoints, not on individual batch requests.
-   C. The key works but expires after five minutes, so a long exponential backoff defeats it.
-   D. The key works only on requests that carry no `tools`, and the backfill sends tools.

------------------------------------------------------------------------

**E7.11.** A review-clustering request runs on Claude Opus 5.5 and must fit inside the 1M-token context window. The fixed parts are: a 14,000-token system prompt; eleven tool definitions averaging 520 tokens each; the tool-use system prompt overhead at the default `tool_choice`; and a 3,400-token task brief. The team reserves 32,000 tokens of the window for output. Each review averages 1,850 tokens. How many complete reviews fit in one request?

-   A. 504
-   B. 510
-   C. 511
-   D. 540

------------------------------------------------------------------------

**E7.12.** A team places a `cache_control` breakpoint on a 380-token brand-voice block that opens every merchandising-copy request. No error is returned, but `cache_read_input_tokens` is zero on every request and costs do not fall. Why?

-   A. The breakpoint is on a system block, and only message blocks can be cached.
-   B. Brand-voice text changes too often for the five-minute TTL to help.
-   C. A second breakpoint later in the prompt silently supersedes the first.
-   D. The block is below the 512-token minimum cacheable length on current models, so it is processed without caching and no error is raised.

------------------------------------------------------------------------

**E7.13.** A catalogue worker pool runs on Claude Sonnet 5.5 against an input rate limit of 400,000 input tokens per minute. Because an A/B flag changes `output_config.effort` on every call, each request re-writes its 60,000-token prefix to cache instead of reading it, and also sends 2,000 tokens of uncached SKU data. Cache writes count toward the input rate limit. How many requests per minute can the pool sustain?

-   A. 6
-   B. 7
-   C. 66
-   D. 200

------------------------------------------------------------------------

**E7.14.** To make attribute extraction reproducible, a team sets `temperature: 0.2` on requests to `claude-sonnet-5-5`. Every request returns HTTP 400. What is the correct fix?

-   A. Set `top_k: 1` instead, which is the supported way to pin sampling on current models.
-   B. Remove `temperature`; sampling parameters are deprecated on Claude 4.7 and later and a non-default value returns 400. Pin the shape of the answer with `output_config.format` and control depth with `output_config.effort`.
-   C. Keep `temperature` but move it inside `output_config`, where it is still accepted.
-   D. Set `temperature: 0`, which is the one value still accepted on current models.

------------------------------------------------------------------------

**E7.15.** A merchandising request to Claude Sonnet 5.5 carries 24 product images, each 1,120 x 1,120 pixels, plus a negligible text block. What do the images contribute in input tokens, and what do they cost?

-   A. 1,600 tokens, \$0.0032
-   B. 19,200 tokens, \$0.0384
-   C. 32,000 tokens, \$0.0640
-   D. 38,400 tokens, \$0.0768

------------------------------------------------------------------------

**E7.16.** **(Select TWO)** A catalogue agent caches its tool definitions, its system prompt and its message history. Between two requests the team adds one new tool to the array and changes `output_config.effort` from `medium` to `high`. Which TWO statements about the cache are correct?

-   A. Adding a tool invalidates the cached tool, system and message prefixes.
-   B. Adding a tool invalidates only the cached tool prefix; the system and message prefixes survive.
-   C. Changing `output_config.effort` invalidates at least the cached message prefix.
-   D. Changing `output_config.effort` has no effect on the prompt cache, because it governs output rather than input.
-   E. Adding an image to the newest user turn invalidates the cached tool prefix.
-   F. Changing the system prompt invalidates the cached tool prefix as well.

------------------------------------------------------------------------

**E7.17.** A catalogue backfill is wrapped in a generic retry policy: any HTTP 429 is retried with exponential backoff and unlimited attempts. One night the job stops making progress and burns a worker pool for six hours against a wall of 429s. The response bodies carry `error.details.error_code` set to `enforced_spend_limit_reached` and no `retry-after` header. What should the client do differently?

-   A. Treat that error code as terminal: a spend-cap 429 is never retryable, so the job must stop, surface the condition and wait for a human to raise the cap.
-   B. Honour `retry-after` when present and otherwise retry after exactly 60 seconds, which is the documented default for this error.
-   C. Switch the job to the Batches API, where workspace spend limits are not enforced.
-   D. Retry on a different API key in the same workspace, since the cap is per key.

------------------------------------------------------------------------

**E7.18.** A two-stage enrichment pipeline runs per SKU. Stage one extracts attributes on Claude Haiku 5.5: 2,400 input tokens and 500 output tokens, with no cache and no tier crossing. Stage two writes merchandising copy on Claude Sonnet 5.5: 1,800 input tokens and 900 output tokens, no cache. Both stages run through the standard Messages API at full price. What does enriching 150,000 SKUs cost?

-   A. \$1,423.50
-   B. \$1,890.00
-   C. \$1,926.00
-   D. \$1,963.50

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E7.19.** A team compares two designs for 100,000 attribute extractions. Design one: Claude Haiku 5.5 on every SKU at 3,000 input and 400 output tokens; 6% of results fail a validation gate and are re-run on Claude Sonnet 5.5 at the same token counts. Design two: Claude Sonnet 5.5 on every SKU at 3,000 input and 400 output tokens; 1% fail and go to a human reviewer at \$0.40 each. No caching, no batching, no tier crossing. What is the all-in inference-plus-review cost of design one?

-   A. \$50.00
-   B. \$110.00
-   C. \$150.00
-   D. \$1,400.00

------------------------------------------------------------------------

**E7.20.** A new team asks which model to start a catalogue enrichment project on, and when they should move up. Which answer matches the documented guidance?

-   A. Start on Claude Haiku 5.5, because the documentation names it the default for all new projects, and move to Sonnet 5.5 only if latency allows.
-   B. Start on Claude Sonnet 5.5, which the documentation names the recommended default, and move to Fable 5.1 whenever cost permits.
-   C. Start on Claude Fable 5.1 to establish a quality ceiling, then step down one model at a time until evals break.
-   D. Start on Claude Opus 5.5, which the documentation names the recommended default, and move to Fable 5.1 for demanding reasoning and long-horizon agentic work, or when Opus 5.5 at higher effort still falls short on your evals.

------------------------------------------------------------------------

**E7.21.** Ahead of a peak trading season, an architect proposes buying Priority Tier capacity for the catalogue enrichment service so that seasonal traffic is guaranteed served latency. What is wrong with this proposal?

-   A. Priority Tier applies only to the Batches API, which the enrichment service does not use.
-   B. Priority Tier guarantees throughput but forfeits the batch discount, which would cost more than the peak is worth.
-   C. Priority Tier is closed to new purchase and excludes all current models, so it cannot be part of a plan built on the current line-up; peak headroom has to come from batching, caching and model choice instead.
-   D. Priority Tier cannot be combined with prompt caching, so the enrichment service would lose its cache hits.

------------------------------------------------------------------------

**E7.22.** **(Select TWO)** Which TWO statements about effort control on current models are correct?

-   A. Effort is set through `output_config.effort` and takes one of `low`, `medium`, `high`, `xhigh` or `max`.
-   B. Effort is set as a field inside the `thinking` object, alongside the thinking type.
-   C. Claude Opus 5.5 and Claude Haiku 5.5 default to `medium` effort, while the other current models default to `high`.
-   D. Claude Sonnet 5.5 defaults to `low` effort, which is why it is the fastest of the non-Haiku models.
-   E. Changing effort between two otherwise identical requests preserves the prompt cache, because effort is not part of the cached prefix.

------------------------------------------------------------------------

**E7.23.** A catalogue agent on Claude Sonnet 5.5 sends an 80,000-token prefix with a five-minute cache breakpoint. An A/B experiment alternates `output_config.effort` between `medium` and `high` on consecutive requests, so every request re-writes the prefix instead of reading it. Over a run of 500 requests, how much more does the prefix cost than it would if effort were held constant for the whole run?

-   A. \$3.99
-   B. \$4.19
-   C. \$95.81
-   D. \$100.00

------------------------------------------------------------------------

**E7.24.** A team pins `claude-sonnet-5-5` in configuration on the understanding that the ID will float forward to whatever the newest Sonnet is, so they will get upgrades for free. What is wrong with this understanding?

-   A. Nothing, but floating IDs invalidate the prompt cache whenever the underlying snapshot changes.
-   B. Model IDs without a date are fixed snapshots from Claude 4.6 onward, not aliases; a newer Sonnet ships under a new ID, and this snapshot will eventually be retired with at least 60 days’ notice.
-   C. The ID is an alias, but it floats only within a minor version, so a move from 5.5 to 6.0 would need a configuration change.
-   D. The ID is an alias and will float, but aliases are unavailable on the Batches API, so batch jobs would diverge from live traffic.

------------------------------------------------------------------------

**E7.25.** A reranker on Claude Haiku 5.5 currently sends one request per query carrying 120,000 input tokens. An engineer proposes splitting each query into two requests of 62,000 input tokens each — the duplication comes from repeating the shared instructions — with no caching in either design. Counting input tokens only, what is the per-query saving?

-   A. \$0.0124
-   B. \$0.0476
-   C. \$0.0600
-   D. \$0.0724

------------------------------------------------------------------------

**E7.26.** **(Select THREE)** Which THREE statements about the current model line-up are correct?

-   A. All four current models offer a 1M-token context window and up to 128K output tokens.
-   B. Claude Fable 5.1 is priced at \$10 per MTok input and \$50 per MTok output.
-   C. Claude Haiku 5.5 is the only current model with tiered input pricing.
-   D. Claude Opus 5.5 reads cached tokens at 0.1x its base input price.
-   E. Claude Sonnet 5.5 is the documented recommended default for most workloads.
-   F. Claude Haiku 5.5 reads cached tokens at 0.025x its base input price.

------------------------------------------------------------------------

**E7.27.** A team proposes running Claude Fable 5.1 over all 2 million SKUs to normalise unit-of-measure strings into a fixed enum, arguing that the best model will give the best data. Evals show Haiku 5.5 at 99.1% and Fable 5.1 at 99.4% on this task. What is the strongest objection?

-   A. The task is high-volume and tightly specified, with a 0.3-point quality gap; the efficiency-first path puts it on the cheapest model that clears the bar, and Fable 5.1 is positioned for demanding reasoning and long-horizon agentic work rather than bulk normalisation.
-   B. Fable 5.1 cannot be used through the Batches API, so a 2-million-SKU job could not be discounted.
-   C. Fable 5.1 does not support `output_config.format`, so the enum could not be enforced.
-   D. Fable 5.1’s context window is too small to hold the unit-of-measure enum alongside the SKU payload.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E7.28.** A merchandising agent runs through the Agent SDK with `max_budget_usd` set to 2.00. After seven responses the run has spent \$1.94. The eighth response costs \$0.31. What is the final spend, and what `ResultMessage.subtype` does the run end with?

-   A. \$2.25, with subtype `error_max_budget_usd`, because the budget is checked after a response arrives and can therefore be overshot by one response.
-   B. \$1.94, with subtype `success`, because the eighth response is cancelled before it is billed.
-   C. \$2.00, with subtype `error_max_budget_usd`, because spend is clamped at the cap and the remainder is not billed.
-   D. \$2.25, with subtype `error_during_execution`, because exceeding the cap is an execution error rather than a budget outcome.

------------------------------------------------------------------------

**E7.29.** An Agent SDK catalogue agent is configured with `max_turns: 10`. The team expects the run to stop after ten messages of any kind, but runs routinely contain far more than ten assistant and user messages before they end. What explains this?

-   A. `max_turns` counts only the turns in which the agent produced no tool call, so tool-heavy runs are effectively unbounded.
-   B. `max_turns` is advisory on the Agent SDK and only enforced on the CLI.
-   C. `max_turns` counts subagent turns against the parent’s budget, so the parent’s own count never reaches ten.
-   D. `max_turns` counts tool-use turns only, so plain assistant and user messages do not consume the budget.

------------------------------------------------------------------------

**E7.30.** A catalogue-audit plan fans out one subagent per product category. The orchestrator spawns 60 subagents at once and expects all 60 to run concurrently; each of those is written to spawn its own grandchildren, which spawn a further level. Observed behaviour: work proceeds but throughput plateaus, and the deepest level never runs. What are the two defaults at work?

-   A. Subagent concurrency defaults to 10 and depth is unlimited, so the plateau is concurrency and the missing level is a bug.
-   B. Subagent concurrency is unlimited and depth defaults to 2, so the plateau is rate limiting and the missing level is depth.
-   C. Subagent concurrency defaults to 20, so only 20 of the 60 run at a time, and subagent depth defaults to 3, so the fourth level is refused.
-   D. Subagent concurrency defaults to 20 and depth defaults to 5, so the missing level must come from the spend cap rather than depth.

------------------------------------------------------------------------

**E7.31.** **(Select TWO)** Which TWO of the following are valid values of `ResultMessage.subtype` in the Agent SDK?

-   A. `error_max_budget_usd`
-   B. `error_rate_limited`
-   C. `error_max_structured_output_retries`
-   D. `error_tool_denied`
-   E. `error_context_overflow`

------------------------------------------------------------------------

**E7.32.** A single catalogue agent is wired to five MCP servers exposing 320 tools in total, about 48,000 tokens of definitions, all loaded on every request. Tool selection accuracy is poor and cost per task is high. Which change addresses the cause?

-   A. Keep a small set of frequently used tools loaded, defer the rest behind tool search, and split the remaining work across subagents whose tool sets match their task — the fault is that the whole catalogue of tools is in context for every decision.
-   B. Raise `output_config.effort` to `max` so the model reads all 320 definitions more carefully before choosing.
-   C. Place a `cache_control` breakpoint on the last tool definition, which removes the definitions from the model’s decision space.
-   D. Move the tool definitions into the system prompt, where they are not counted against tool-selection confusion.

------------------------------------------------------------------------

**E7.33.** A catalogue agent on Claude Opus 5.5 enables `clear_tool_uses_20250919` with its default `trigger` and default `keep`. The system prompt plus tool definitions come to 22,000 tokens and never change. Each tool call returns a catalogue page of about 12,000 tokens, and the agent’s own text between calls is negligible. At which tool call does clearing first fire?

-   A. The 5th
-   B. The 6th
-   C. The 7th
-   D. The 8th

------------------------------------------------------------------------

**E7.34.** A long-running enrichment agent enables both context-editing strategies. The `edits` array lists `clear_tool_uses_20250919` first and `clear_thinking_20251015` second. The team reports that behaviour is not what the documentation describes. What is wrong?

-   A. The two strategies cannot be combined in one request; one must be applied client-side.
-   B. `clear_thinking_20251015` requires its own beta header, separate from the one `clear_tool_uses_20250919` needs.
-   C. `clear_tool_uses_20250919` must specify `clear_at_least` whenever thinking clearing is also enabled.
-   D. When both are used, `clear_thinking_20251015` must be listed first in the `edits` array.

------------------------------------------------------------------------

**E7.35.** Catalogue enrichment has four independent sub-tasks per SKU — attribute extraction, category assignment, a safety-and-compliance flag, and copy generation — of which only copy generation depends on the others. Which decomposition is the better fit, and why?

-   A. One agent with all four as tools, because a single agent sees the whole SKU and avoids duplicated input tokens.
-   B. Run extraction, category assignment and the compliance flag in parallel, then chain copy generation onto their joined output — the three independent tasks gain nothing from being serialised, and only the dependent step needs the earlier results.
-   C. Chain all four in a fixed sequence, because a chain is easier to cache than a fan-out.
-   D. Run all four in parallel and reconcile conflicts afterwards, because parallelisation always dominates chaining on latency.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E7.36.** A merchandising-copy prompt is assembled in this order: the SKU payload for this request, then the 30,000-token brand style guide, then the 12,000-token category taxonomy, then the instruction block. A cache breakpoint sits at the end of the taxonomy. Cache hit rates are near zero. What is the fix?

-   A. Put the stable content first — style guide, then taxonomy, then instructions — and the per-request SKU payload last, so the cached prefix is identical across requests.
-   B. Move the breakpoint to the very end of the prompt so that it covers the SKU payload too.
-   C. Switch the breakpoint to a one-hour TTL, which tolerates a changing prefix.
-   D. Split the style guide across two breakpoints so that a change to the SKU payload invalidates only one of them.

------------------------------------------------------------------------

**E7.37.** An extraction schema constrains `size_unit` to the enum `["CM", "IN", "MM"]`. In production the field sometimes comes back as `cm`. No error is returned and no special `stop_reason` appears. What is the correct handling?

-   A. Add the lowercase variants to the enum, which is the documented remedy.
-   B. Treat it as a schema-compilation failure and retry the request with a simplified schema.
-   C. Enum values may differ from the schema in capitalisation only, with no error; compare case-insensitively downstream and avoid enums whose members differ only by case.
-   D. Set `additionalProperties: false` on the parent object, which forces exact enum casing.

------------------------------------------------------------------------

**E7.38.** A team wants Claude to explain its reasoning step by step inside the structured output it returns for each SKU, so that merchandisers can audit borderline category assignments. They add a `reasoning_steps` array to the schema and ask for detailed step-by-step reasoning in the prompt. A fraction of requests come back with `stop_reason: "refusal"`. What should they do?

-   A. Retry those requests with a higher `max_tokens`, since a refusal on a structured request indicates truncation.
-   B. Remove `additionalProperties: false` so the extra reasoning fields are permitted.
-   C. Drop structured output entirely; auditability and `output_config.format` are mutually exclusive.
-   D. Ask for a short explanation field rather than step-by-step reasoning; a request for extended reasoning inside a constrained output can trigger a reasoning-extraction refusal, and such a response is returned with a 200 status and billed.

------------------------------------------------------------------------

**E7.39.** **(Select THREE)** A catalogue extraction schema is being written for `output_config.format`. Which THREE of the following features are **not** supported and will return 400?

-   A. `minLength` and `maxLength` on a product-title string.
-   B. `minimum` and `maximum` on a numeric weight field.
-   C. A recursive schema for nested category trees of arbitrary depth.
-   D. `anyOf` across two alternative attribute shapes.
-   E. An internal `$ref` to a definition elsewhere in the same schema.
-   F. `enum` over a fixed list of string values.

------------------------------------------------------------------------

**E7.40.** A long catalogue conversation places four `cache_control` breakpoints, the earliest of which is intended to cover a 26-block prefix of alternating tool uses and tool results. That breakpoint never produces a hit, while the other three work. What is the likely cause?

-   A. Four breakpoints exceed the ceiling, so the earliest is silently dropped.
-   B. A breakpoint looks back at most 20 block positions, so a prefix boundary 26 positions back is out of reach; consecutive tool-use blocks and consecutive tool-result blocks each collapse to one position, which is what makes the arithmetic worth checking.
-   C. Tool-result blocks cannot be cached, so any breakpoint whose prefix contains one is ignored.
-   D. Breakpoints are evaluated newest-first and only the three most recent are honoured.

------------------------------------------------------------------------

**E7.41.** Attribute extraction returns `"weight": "2.5 kg"` for some SKUs and `"weight": "2500 g"` for others, even though the schema types `weight` as a number and `weight_unit` as an enum. The prompt explains the convention in prose. What is the most effective change?

-   A. Give two or three worked examples in the prompt showing the exact normalisation — including one input stated in grams and one in kilograms — since the schema already fixes the types and what is missing is a demonstration of the convention.
-   B. Add `minimum: 0` to the `weight` field so that only valid numbers are accepted.
-   C. Set `output_config.effort` to `max` on every request.
-   D. Move the convention from the prompt into the field’s `description`, which is enforced by the compiled grammar.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E7.42.** A catalogue service must call its `extract_attributes` tool on every request and never answer in prose. The team sets `tool_choice` to `{"type": "tool", "name": "extract_attributes"}`. Every request returns HTTP 400 on the current models. What is the right way to get the same guarantee?

-   A. Set `tool_choice` to `{"type": "any"}`, which is the supported form of forcing on current models.
-   B. Set `disable_parallel_tool_use: true`, which has the side effect of forcing a single tool call.
-   C. Keep `tool_choice` forced and add the tool-use beta header that re-enables it.
-   D. Drop the forced choice and get the guarantee from the output contract instead: constrain the response with `output_config.format` so the model must return the attribute object directly, and leave `tool_choice` at its default.

------------------------------------------------------------------------

**E7.43.** A catalogue request to Claude Sonnet 5.5 carries a 6,000-token system prompt, fourteen tool definitions averaging 410 tokens each, a 2,000-token user brief, and `tool_choice` left at its default. How many input tokens does the request consume?

-   A. 11,740
-   B. 14,026
-   C. 14,146
-   D. 14,432

------------------------------------------------------------------------

**E7.44.** **(Select TWO)** A supplier-inventory MCP server is being written against the stateless 2026-07-28 revision. Which TWO statements about that revision are correct?

-   A. `server/discover` replaces `initialize` as the capability-negotiation entry point.
-   B. Per-request context travels in a `_meta` field on each request, rather than being held in server-side session state.
-   C. The revision introduces a mandatory session identifier that every request must echo.
-   D. Sampling and logging are promoted to required capabilities in this revision.
-   E. The revision removes tool definitions from the protocol in favour of out-of-band registration.

------------------------------------------------------------------------

**E7.45.** An MCP inventory server is designed so that, when a SKU lookup is ambiguous, the server calls back to the client to have the model pick between candidates, using the sampling capability. Under the stateless revision the callback never fires. What should the design do instead?

-   A. Keep sampling but mark the tool as long-running so the client holds the connection open.
-   B. Move the disambiguation into the server’s own logic by calling a model directly from the server.
-   C. Return the candidate set to the client as the tool’s result and let the agent’s own next turn choose between them, because sampling is deprecated in the stateless revision.
-   D. Re-enable sampling by pinning the server to the previous protocol revision, which the client negotiates automatically.

------------------------------------------------------------------------

**E7.46.** A price-lookup tool is mis-selected: the model calls it when it should call the promotions tool. Both tools have one-line descriptions. Which change most reliably reduces mis-selection?

-   A. Rename the tools so the price tool sorts first in the array.
-   B. Expand each description to state what the tool is for, what it is not for, and when to prefer the other tool, naming the sibling explicitly — the model is choosing from the definitions, and one line each gives it no basis for the distinction.
-   C. Set `disable_parallel_tool_use: true` so the model can only pick one.
-   D. Mark both tools `strict: true`, which validates inputs and therefore clarifies intent.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E7.47.** A review-summarisation agent reads seller-supplied product reviews and has access to a `set_price` tool so it can apply approved promotional prices. A review containing instructions addressed to the assistant causes a price change. What is the structural fix?

-   A. Treat all review text as untrusted data: label it explicitly as content to summarise rather than instructions to follow, and remove the write-capable tool from the agent that reads untrusted text, putting price changes behind a separate, human-approved path.
-   B. Add a line to the system prompt instructing the model to ignore any instructions found inside reviews.
-   C. Run the summariser at `output_config.effort: max`, which makes the model less susceptible to injected instructions.
-   D. Strip HTML tags and URLs from reviews before they reach the model.

------------------------------------------------------------------------

**E7.48.** **(Select TWO)** Which TWO measures meaningfully reduce the blast radius of an indirect prompt injection reaching a catalogue agent?

-   A. Give the agent only read-only tools, and route every mutation through a separate service that requires explicit human approval.
-   B. Validate the agent’s proposed actions against an allow-list of permitted operations and value ranges before executing any of them.
-   C. Instruct the model in the system prompt to refuse any instruction that appears in tool output.
-   D. Raise the model tier, since larger models are not susceptible to injection.
-   E. Log the full prompt of every request so injections can be found after the fact.
-   F. Wrap untrusted text in a distinctive delimiter string that the model is told never to cross.

------------------------------------------------------------------------

**E7.49.** Suppliers submit product descriptions as HTML. The team wants to pass that HTML to the model for cleanup and attribute extraction. Which handling is soundest?

-   A. Pass the HTML as-is in the system prompt, since the system prompt is the authoritative channel.
-   B. Concatenate the HTML directly after the instructions with no separator, so the model reads it as one continuous task.
-   C. Let the model execute any embedded scripts in the HTML so that dynamically generated attributes are captured.
-   D. Put the HTML in a user-turn content block with an explicit label marking it as untrusted supplier input to be processed, keep the instructions in the system prompt, and validate the extracted attributes against the schema and against business rules before writing them.

------------------------------------------------------------------------

**E7.50.** To debug extraction failures, a team logs the full request body of every catalogue call, including the review excerpts that sometimes contain customer names and order references, and sets `metadata.user_id` to the reviewing customer’s email address so logs can be correlated. What is the principal problem?

-   A. The log volume will exceed the retention window for batch results.
-   B. `metadata.user_id` is capped at 512 characters, so long email addresses are truncated and correlation breaks.
-   C. Both halves leak personal data into places it does not belong: the logs retain customer identifiers that the task does not need, and `metadata.user_id` is an abuse-detection signal rather than a correlation key and should carry an opaque identifier, not an email address.
-   D. Logging request bodies invalidates the prompt cache, because the logging middleware mutates the prefix.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E7.51.** A catalogue repository’s Claude Code settings deny `Bash(git push:*)` at the project level. A developer adds an allow rule for `Bash(git push origin feature/*:*)` in their user settings, expecting the narrower allow to carve out an exception. Pushes are still refused. Why?

-   A. User settings are always overridden by project settings, whatever the rule type.
-   B. The allow rule’s pattern does not match, because `git push` patterns must name a full ref.
-   C. Permission rules are evaluated in file order, and the deny rule happens to come first.
-   D. Deny takes precedence over allow, and an allow rule cannot carve an exception out of a deny rule; the deny itself has to be narrowed.

------------------------------------------------------------------------

**E7.52.** A catalogue team wants every Claude Code session in the repository to know the SKU schema conventions and the house style for migration scripts, without a developer having to paste them each time. What is the right mechanism?

-   A. Put the conventions in a `CLAUDE.md` at the project root, which Claude Code loads as project memory for sessions in that repository.
-   B. Put them in a custom slash command, which is the only project-scoped configuration Claude Code reads automatically.
-   C. Put them in the user-level settings file, so they apply to every repository the developer opens.
-   D. Put them in a hook that injects the text before each tool call, since there is no declarative project memory.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E7.53.** An attribute-extraction eval reports 97.2% field-level accuracy across a sample of 5,000 SKUs, yet merchandisers keep finding wrong values on exactly the attributes they care about. The sample was drawn uniformly at random from the live catalogue. What is the most likely explanation, and the right fix?

-   A. The sample is too small; raise it to 50,000 SKUs and the discrepancy will resolve.
-   B. Field-level accuracy averaged over a catalogue whose field population is dominated by a few easy attributes hides poor performance on rare but commercially important ones; stratify the eval by attribute and report per-attribute precision and recall, with the commercially important attributes weighted explicitly.
-   C. Accuracy is the wrong metric for extraction; replace it with output-token cost per SKU as a proxy for quality.
-   D. The eval must be run on the same model snapshot as production, and a snapshot mismatch explains the gap.
