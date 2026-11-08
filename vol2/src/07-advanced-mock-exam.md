# Advanced Mock Exam

## Instructions

**60 questions. 135 minutes suggested. Closed book. Answers in the back.**

Work through the paper in one sitting, with no documentation, no console and no calculator beyond simple arithmetic. Scratch paper is expected: roughly a third of this exam requires you to compute something from figures given in the stem, and every figure you need is in the stem.

Mark your answer for each item. Where an item is labelled **(Select TWO)** or **(Select THREE)**, exactly that many options are correct and partial credit is not available: score the item only if you selected all of the correct options and none of the incorrect ones.

### Read this before you score yourself

**This mock is deliberately harder and narrower than the real CCDV-F exam.** Three things make it unrepresentative, and you need to hold all three in mind when you interpret your score:

1.  **It omits five domains entirely.** The real blueprint spreads across eight domains. This paper covers only Applications and Integration (26 questions), Model Selection and Optimization (18 questions) and Agents and Workflows (16 questions) — the three heaviest domains, which together decide roughly 65% of the real exam.
2.  **It over-weights calculation.** Eighteen items require arithmetic. The real exam asks for far less of it, and asks for simpler arithmetic when it does.
3.  **It is pitched above the real exam’s difficulty on purpose.** Multi-step inference, options that are all individually true, and design-critique items appear here at a density you will not meet on exam day.

So the number you get out of this paper is **a diagnostic of your depth in three domains, not a predicted exam score.** Treat it that way in both directions:

-   **Below 75%** means the heavy domains still need work. Use the per-domain scoring guide at the end of the answer key to find which of the three is weakest, and re-read the material it points to before you sit the real exam.
-   **Above 75% is not readiness.** A high score here tells you nothing about the five domains this paper skips. Do not read it as clearance for the full blueprint; go back and check your coverage of the remaining domains before you book.

The Volume I mock, which mirrors the real blueprint question-for-question across all eight domains, is the paper whose score you should treat as predictive. This one is the one that makes the real thing feel easy.

All questions assume the current model line-up and current API behaviour.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**A1.** A service on Claude Opus 5.5 sends one request containing three images and a short text block. The images are 1130 x 845, 700 x 560 and 340 x 250 pixels. None of them exceeds the model’s native resolution, so none is downscaled. How many input tokens do the three images contribute?

-   A. 1,796
-   B. 1,827
-   C. 1,888
-   D. 2,048

------------------------------------------------------------------------

**A2.** An extraction service runs on Claude Opus 5.5. To guarantee that the response is parseable JSON, the team prefills the assistant turn with an opening brace and sets a stop sequence on the closing brace. Every request now returns HTTP 400. Which single change fixes the design?

-   A. Remove the assistant prefill and constrain the response with `output_config.format` using a `json_schema`.
-   B. Set `output_config.effort` to `low` so the model is less inclined to wrap the JSON in commentary.
-   C. Add a stop sequence for the closing brace of each nested object as well as the outermost one.
-   D. Raise `max_tokens` so a long JSON object is never truncated mid-structure.

------------------------------------------------------------------------

**A3.** **(Select TWO)** A team aggregates five MCP servers into one agent: 320 tools, about 48,000 tokens of definitions. They include the regex tool search tool, set `defer_loading: true` on all 320 catalogue tools, and place a `cache_control` breakpoint on the last of the deferred tools to hold the catalogue in cache. Every request returns HTTP 400. Which TWO changes are required?

-   A. Reduce the catalogue below the ceiling on deferred tools per request.
-   B. Move the `cache_control` breakpoint onto a non-deferred tool, since a deferred tool cannot carry one.
-   C. Set `defer_loading: true` on the tool search tool as well, so it does not occupy context.
-   D. Leave at least one tool non-deferred, since a request in which every tool is deferred is rejected.
-   E. Raise the search `limit` above its default so that all five servers are represented in each result set.

------------------------------------------------------------------------

**A4.** A classification job runs on Claude Sonnet 5.5 through the Message Batches API. There are 10,000 requests. Each request carries a 2,400-token shared prefix that is served from cache, 150 tokens of unique input, and produces 200 output tokens. Assume every request gets a cache hit and ignore the cost of the single priming request that wrote the prefix. What does the batch cost?

-   A. \$11.50
-   B. \$13.90
-   C. \$25.40
-   D. \$12.70

------------------------------------------------------------------------

**A5.** A multi-tenant document product uploads customer files through the Files API and stores the returned `file_id` in the browser. The client sends the `file_id` back on each question so the server can reference it in a Messages request. What is the significant defect in this design?

-   A. Files carry a maximum expiry of 90 days, so long-lived client-held references eventually break.
-   B. Files are workspace-scoped rather than user-scoped, so a caller who supplies another tenant’s `file_id` can read that tenant’s file; keep the user-to-file mapping server side and use one workspace per tenant.
-   C. Uploaded files are not downloadable, so the client cannot verify that the `file_id` it holds is still valid.
-   D. The Files API is limited to roughly 500 file-related requests per minute, which a per-question flow will exceed.

------------------------------------------------------------------------

**A6.** An agent uses the server-side web search tool. Its loop reads `stop_reason`, and when the value is neither `end_turn` nor `tool_use` it returns whatever text it has to the user. Users report answers that stop mid-investigation. Logs show `stop_reason: "pause_turn"` on those requests. What is the correct handling?

-   A. Append the assistant’s content to `messages` and call the API again so Claude can continue its server-tool loop.
-   B. Retry the original request with a higher `max_tokens`, since `pause_turn` signals output truncation.
-   C. Return a `tool_result` for the pending `server_tool_use` block and resend the conversation.
-   D. Stop streaming the request, since `stop_reason` is only reliable in a non-streamed message body.

------------------------------------------------------------------------

**A7.** Which of the following JSON Schema constructs is supported by `output_config.format`?

-   A. `minimum` and `maximum` constraints on numeric properties.
-   B. `maxLength` on string properties.
-   C. `anyOf` composition that resolves through a local `$ref`.
-   D. A recursive schema in which a `$def` references itself.

------------------------------------------------------------------------

**A8.** **(Select THREE)** Which THREE of the following are billed as input tokens on a Messages request?

-   A. The tool definitions in the `tools` array.
-   B. The value of `max_tokens`.
-   C. The tool-use system prompt overhead that is added when `tools` is present.
-   D. Thinking tokens produced in the response being billed.
-   E. The content of `tool_result` blocks sent back to the model.
-   F. The `cache_control` breakpoint markers themselves.

------------------------------------------------------------------------

**A9.** A system prompt of 18,000 tokens is reused across requests on Claude Opus 5.5 with a 1-hour cache TTL. Assume one cache write followed by reads, and ignore every other part of the request. How many requests must share the prefix inside the TTL window before caching costs less in total than sending the prefix uncached each time?

-   A. 2
-   B. 3
-   C. 4
-   D. 6

------------------------------------------------------------------------

**A10.** A streaming client accumulates text deltas correctly but crashes on tool calls. The code calls `json.loads` on `delta.partial_json` as each `input_json_delta` event arrives. What is the fix?

-   A. Disable eager input streaming so each tool input arrives as a single whole value.
-   B. Read the completed tool input from the final `message_delta` event, which carries it.
-   C. Set `disable_parallel_tool_use` so that only one `tool_use` block streams at a time.
-   D. Accumulate the `partial_json` fragments into a buffer and parse once, at `content_block_stop`.

------------------------------------------------------------------------

**A11.** An agent on Claude Sonnet 5.5 must stay inside a 200,000-token working context. The fixed overhead is a 12,000-token system prompt, 9 tool definitions averaging 450 tokens each, and the tool-use system prompt overhead for `tool_choice: "auto"`. Each tool-use round trip adds about 3,100 tokens of call plus result to the history, and the conversation starts with a 2,400-token user brief. How many round trips fit before the context is full?

-   A. 58
-   B. 62
-   C. 59
-   D. 60

------------------------------------------------------------------------

**A12.** **(Select TWO)** Which TWO `stop_reason` values mean the generated content may be cut off mid-structure, and therefore must not be parsed as a complete response?

-   A. `pause_turn`
-   B. `max_tokens`
-   C. `end_turn`
-   D. `tool_use`
-   E. `model_context_window_exceeded`
-   F. `refusal`

------------------------------------------------------------------------

**A13.** A production client receives HTTP 429 with `error.details.error_code` set to `enforced_spend_limit_reached` and no `retry-after` header. What should the client do?

-   A. Retry with exponential backoff; the SDK’s default retries will clear the condition.
-   B. Honour the `retry-after` header before retrying, as with any other 429.
-   C. Stop retrying and surface the condition, because this 429 persists until the limit is raised or the monthly window resets.
-   D. Treat it as a malformed request and correct the request body, since spend conditions surface as 400.

------------------------------------------------------------------------

**A14.** A research product passes a PDF as a `document` block with citations enabled, and also sets `output_config.format` so the answer arrives as structured JSON with a `claims` array. The request returns HTTP 400. Which statement describes the constraint and the right design?

-   A. Citations require the Files API beta header, which the request omitted.
-   B. Citations and `output_config.format` cannot be combined in one request; get the cited prose from one call and structure it in a second.
-   C. Citations are incompatible with `strict: true` on tool definitions; drop strict mode from the tools.
-   D. Citations require a `document` block whose source is base64 rather than a `file_id`.

------------------------------------------------------------------------

**A15.** A chat service caches at three levels: a stable `tools` array, a system prompt, and the conversation history. Someone adds the current date and time to the end of the system prompt so the model knows “now”. Which statement is correct about the effect on caching?

-   A. Only the system block’s entry is invalidated; message-level entries continue to hit.
-   B. The system change invalidates the system level and everything after it, so message-level entries miss as well, while the tools prefix still hits.
-   C. Nothing is invalidated, because cache matching normalises whitespace and timestamps.
-   D. The entire cache, tool definitions included, is invalidated on every request.

------------------------------------------------------------------------

**A16.** A catalogue service sends one request containing 26 product photographs, each 2,400 x 1,800 pixels, to Claude Opus 5.5. What happens?

-   A. It fails: once a request carries more than 20 images, every image must be at most 2,000 pixels on each side, so the 2,400-pixel width is rejected.
-   B. It fails: the API permits at most 20 images per request.
-   C. It succeeds: images above the model’s native resolution are downscaled automatically, so 2,400 pixels is fine.
-   D. It fails: the 8,000 x 8,000 maximum applies to the aggregate of all images in a request.

------------------------------------------------------------------------

**A17.** A request to Claude Opus 5.5 carries 14 tool definitions averaging 320 tokens each, `tool_choice` left at its default, a 900-token system prompt and a 400-token user message. Nothing is cached. Approximately how many input tokens does the request consume?

-   A. 5,780
-   B. 6,186
-   C. 6,066
-   D. 6,277

------------------------------------------------------------------------

**A18.** **(Select THREE)** A request has cached prefixes at the tools, system and messages levels. Which THREE of the following changes invalidate the cached **system**-level prefix?

-   A. Adding a new tool to the `tools` array.
-   B. Changing `tool_choice` from `auto` to `none`.
-   C. Switching `speed` between fast and standard.
-   D. Turning citations on.
-   E. Adding an image to the most recent user message.
-   F. Setting `output_config.effort` explicitly to the value that is already the model’s default.

------------------------------------------------------------------------

**A19.** A team on Claude Sonnet 5.5 wants a guaranteed tool call with schema-valid arguments, so they set `tool_choice` to `{"type": "any"}` and `strict: true` on each tool. The request returns HTTP 400. What is the correct replacement design?

-   A. Name the tool explicitly with `{"type": "tool", "name": ...}`, which is accepted where `any` is not.
-   B. Keep `tool_choice` at `auto`, keep `strict: true`, and use `output_config.format` for the final response shape, because forced tool choice returns 400 on Sonnet 5.5.
-   C. Enable manual extended thinking, under which forced tool use is permitted.
-   D. Add the interleaved-thinking beta header, which re-enables forced choice.

------------------------------------------------------------------------

**A20.** A support assistant caches aggressively. The team sets one `cache_control` breakpoint, on the final content block of the conversation — the incoming user message — reasoning that this caches the longest possible prefix. In production, `cache_creation_input_tokens` is non-zero on every request and `cache_read_input_tokens` is always zero. What is wrong?

-   A. The cached prefix is below the minimum cacheable length, so nothing is stored.
-   B. The conversation is long enough that the breakpoint’s lookback window never reaches a stored entry.
-   C. The 5-minute TTL expires before the next request arrives, so each request writes a fresh entry.
-   D. The breakpoint sits on a block whose content changes every request, so no earlier request ever wrote that exact prefix; it belongs on the last block that is identical across requests.

------------------------------------------------------------------------

**A21.** Which parameter causes a request inside a Message Batches submission to fail validation?

-   A. `stream: true`
-   B. A `tools` array in which a tool sets `strict: true`
-   C. `output_config.format`
-   D. `context_management.edits`

------------------------------------------------------------------------

**A22.** A retrieval-augmented endpoint has a 4,000 ms p95 budget end to end. Measured components: 350 ms of network and application overhead, a 600 ms retrieval call, 480 ms to first token from the model, and generation at 90 output tokens per second. The response is capped at 180 output tokens. Does the design fit the budget?

-   A. Yes, with about 1,050 ms of slack.
-   B. Yes, with about 1,170 ms of slack.
-   C. Yes, with about 570 ms of slack.
-   D. No; it exceeds the budget by about 570 ms.

------------------------------------------------------------------------

**A23.** A long-running agent enables context editing with the `clear_tool_uses_20250919` strategy, leaving `trigger` and `keep` at their defaults and setting no `clear_at_least`. Throughput is fine, but the cache hit rate collapses and input spend rises. Which explanation is correct?

-   A. Clearing removes tool calls as well as tool results by default, so Claude repeats work it has already done.
-   B. The default `keep` of 3 is too small for a tool-heavy workflow, so Claude re-fetches context.
-   C. Context editing requires a beta header that the request omitted, so the strategy silently does nothing.
-   D. Each clear rewrites the prompt prefix and invalidates the cached prefix, so without `clear_at_least` the agent pays cache-write costs again and again for small clears.

------------------------------------------------------------------------

**A24.** **(Select TWO)** Which TWO statements about the Message Batches API are correct?

-   A. A batch that has not finished within 1 hour expires.
-   B. Requests that end as `expired` or `canceled` are billed at the batch rate.
-   C. Results become available when every request has finished, or after 24 hours, whichever comes first.
-   D. A single batch may contain at most 10,000 Message requests.
-   E. Results remain downloadable for 29 days counted from the batch’s creation time.

------------------------------------------------------------------------

**A25.** A nightly pipeline uploads source documents through the Files API with `expires_in_seconds` set to 3600, then stores the `file_id` values in a queue that a morning job drains eight hours later. The morning job’s Messages requests fail. Which statement describes the behaviour and the fix?

-   A. The Messages request succeeds, because file metadata is retained for 30 days after expiry.
-   B. The Messages request fails before inference; `expires_in_seconds` accepts values from 3,600 to 7,776,000 and cannot be changed after upload, so re-upload with a longer value.
-   C. The file is transparently re-fetched from the original upload, so the failure must have another cause.
-   D. Downloads return 404 after expiry but Messages references keep working for 30 days.

------------------------------------------------------------------------

**A26.** A workload on Claude Sonnet 5.5 has an input-token-per-minute limit of 2,000,000. Prompt caching serves 85% of its input tokens from cache. Approximately how many total input tokens per minute can the workload process before it hits the limit?

-   A. About 13,300,000
-   B. About 2,000,000
-   C. About 2,350,000
-   D. About 11,300,000

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**A27.** A support product routes every ticket to Claude Haiku 5.5 first, at \$0.0020 per ticket. Tickets the first pass cannot resolve are escalated to Claude Opus 5.5 at \$0.0400 per ticket; an escalated ticket pays both charges. The budget is \$0.0160 per ticket, averaged across all tickets. What is the highest escalation rate that stays inside budget?

-   A. 30%
-   B. 35%
-   C. 33%
-   D. 40%

------------------------------------------------------------------------

**A28.** A team migrates an analysis service from Claude Opus 5 to Claude Opus 5.5 without changing any request parameters. Cost per request falls, but quality on the hardest reasoning items drops noticeably. What explains it?

-   A. Opus 5.5 has a smaller context window than Opus 5, so long inputs are now truncated.
-   B. `output_config.effort` is not supported on Opus 5.5; thinking depth must be set with `thinking.budget_tokens` instead.
-   C. Opus 5.5 defaults to `low` effort, which the service never overrides.
-   D. Opus 5.5 defaults to `medium` effort while Opus 5 defaults to `high`, so omitting `effort` now runs one level lower; set `effort` to `high` or above.

------------------------------------------------------------------------

**A29.** **(Select THREE)** Which THREE statements about `output_config.effort` are correct?

-   A. Effort raises `max_tokens` when the task needs more room to finish.
-   B. Effort applies to all output tokens, including tool calls and their arguments, and thinking when it is active.
-   C. `adaptive` is a valid effort value for long-horizon agentic work.
-   D. Both `max` and `xhigh` are available on Claude Opus 5.5.
-   E. Lower effort levels make more tool calls, to compensate for shallower reasoning per call.
-   F. Setting effort explicitly to the model’s own default does not invalidate the prompt cache.

------------------------------------------------------------------------

**A30.** A workload sends 200,000 requests per month, each with 40,000 input tokens and 3,000 output tokens, with no caching. It currently runs entirely on Claude Opus 5.5. An evaluation shows that 70% of the traffic can be served by Claude Haiku 5.5 with acceptable quality, leaving 30% on Opus 5.5. What is the monthly saving from that split?

-   A. \$13,970
-   B. \$30,800
-   C. \$30,030
-   D. \$22,000

------------------------------------------------------------------------

**A31.** A latency-sensitive endpoint on Claude Opus 5.5 uses fast mode. The team wants to reuse the same request shape for an overnight reprocessing job on the Message Batches API, and the batch requests fail validation. Which statement is correct?

-   A. The `speed` parameter is rejected in batch requests; fast mode runs only on the synchronous Messages API, where Opus 5.5 bills at \$8 input and \$40 output per MTok.
-   B. Fast mode requires a beta header, which the batch requests omitted.
-   C. Fast mode is supported in batches, but the 50% batch discount does not apply to fast-mode tokens.
-   D. Fast mode is available only on Claude Sonnet 5.5 and Claude Haiku 5.5, not Opus 5.5.

------------------------------------------------------------------------

**A32.** A content service on Claude Sonnet 5.5 serves 500,000 requests per month. Each carries a 6,000-token system prefix that is always a cache hit. At `effort: "high"` responses average 2,800 output tokens; at `effort: "medium"` they average 1,700 output tokens and evaluations still pass. What is the monthly saving from dropping to `medium`?

-   A. \$2,750
-   B. \$5,500
-   C. \$8,500
-   D. \$14,000

------------------------------------------------------------------------

**A33.** **(Select TWO)** Which TWO statements about Claude Haiku 5.5’s tiered pricing are correct?

-   A. The threshold is 100,000 prompt tokens, and prompt length counts cache reads and cache writes along with uncached input.
-   B. Haiku 5.5 bills its full 1M-token window at one flat rate, as the other current models do.
-   C. The tier affects input prices only; output stays at the lower rate.
-   D. The tier is decided per request, so a request above the threshold pays the higher rate even on the part of its input that was a cache hit.
-   E. Output tokens count toward the 100,000-token threshold.

------------------------------------------------------------------------

**A34.** A classifier is being migrated from Claude Sonnet 4.5 to Claude Sonnet 5.5. The request sets `temperature: 0`, `top_p: 0.9` and `thinking: {"type": "enabled", "budget_tokens": 4000}`. It now returns HTTP 400. Which statement identifies the problems and the correct migration?

-   A. Only `top_p` is rejected; `temperature` and the thinking block remain valid on Sonnet 5.5.
-   B. The thinking block is accepted but deprecated; removing `temperature` and `top_p` is sufficient.
-   C. All three parameters are valid; the 400 comes from omitting `max_tokens`.
-   D. `temperature` and `top_p` are rejected on 4.7 and later, and `thinking.type: "enabled"` returns 400; replace the thinking block with `output_config.effort` and rely on a schema or the prompt for consistent output.

------------------------------------------------------------------------

**A35.** A prompt measured 12,000 input tokens on Claude Sonnet 4.6, which bills input at \$3 per MTok. The team moves it unchanged to Claude Sonnet 5.5, which bills input at \$2 per MTok but uses the newer tokenizer that produces roughly 30% more tokens for the same text. What happens to the input cost per request?

-   A. It rises by about 30%, because the tokenizer change dominates.
-   B. It is unchanged, because the per-token price is what changed, not the text.
-   C. It falls from about \$0.0360 to about \$0.0312, roughly 13% lower, because the lower per-token price more than offsets the token inflation.
-   D. It falls from \$0.0360 to \$0.0240, a third lower, since \$2 is two-thirds of \$3.

------------------------------------------------------------------------

**A36.** An agent on Claude Opus 5.5 holds a 180,000-token prefix in cache with a 1-hour TTL. It makes 400 requests in that hour: one writes the prefix and 399 read it. Counting only the prefix, what does the hour cost?

-   A. \$15.80
-   B. \$14.36
-   C. \$30.17
-   D. \$15.26

------------------------------------------------------------------------

**A37.** **(Select TWO)** A high-volume extraction job must get cheaper, and the team has been told not to change models. Which TWO levers actually reduce cost?

-   A. Change the cache TTL from 5 minutes to 1 hour, which lowers the cache write multiplier.
-   B. Raise `max_tokens` so that responses are never truncated and retried.
-   C. Lower `output_config.effort` from `high` to `medium`.
-   D. Set `inference_geo: "us"` so inference stays in one region.
-   E. Move the job to the Message Batches API.
-   F. Enable fast mode so each request occupies the service for less time.

------------------------------------------------------------------------

**A38.** A team needs an agent that runs multi-hour research sessions and carries the analysis through to a finished document. Their evaluation suite still falls short with Claude Opus 5.5 at `xhigh` effort. What does the documented selection path say to do next?

-   A. Keep Opus 5.5 and raise `max_tokens` to 300,000 using the extended-output beta.
-   B. Move to Claude Fable 5.1, which is positioned for demanding reasoning and long-horizon agentic work once Opus 5.5 at `xhigh` or `max` is not enough.
-   C. Move to Claude Mythos 5.1, which is the higher-capability sibling of Fable 5.1.
-   D. Keep Opus 5.5 as an orchestrator and split the session across parallel Claude Haiku 5.5 subagents.

------------------------------------------------------------------------

**A39.** A classification step runs 100,000 times a month. Claude Haiku 5.5 is 91% accurate at \$0.0015 per request; Claude Opus 5.5 is 98.5% accurate at \$0.0300 per request. Every misclassification costs \$4.00 in manual rework. Which option is cheaper all-in, and by how much per month?

-   A. Haiku 5.5, by about \$2,850
-   B. Opus 5.5, by about \$30,000
-   C. Haiku 5.5, by about \$35,000
-   D. Opus 5.5, by about \$27,150

------------------------------------------------------------------------

**A40.** A service on Claude Haiku 5.5 sets `cache_control` on a 460-token system prompt. In production, both `cache_creation_input_tokens` and `cache_read_input_tokens` are always 0, and no error is returned. Why?

-   A. Claude Haiku 5.5 does not support prompt caching.
-   B. The breakpoint must sit on the last system block, and it was placed on the first.
-   C. The prefix is below the 512-token minimum cacheable length for Haiku 5.5, so the request is processed without caching and no error is raised.
-   D. The minimum cacheable length on Haiku 5.5 is 4,096 tokens, so a 460-token prefix is far short of it.

------------------------------------------------------------------------

**A41.** **(Select THREE)** Which THREE statements about using prompt caching to reduce cost are correct?

-   A. The breakpoint belongs on the last block whose prefix is byte-identical across requests.
-   B. Cache read tokens count toward the input-tokens-per-minute limit on all current models.
-   C. A request may carry up to 8 explicit `cache_control` breakpoints.
-   D. Blocks with a 1-hour TTL must appear before blocks with a shorter TTL in the prompt.
-   E. The batch discount stacks on top of the cache write and read multipliers.
-   F. A cache entry’s TTL clock starts when the response that wrote it finishes streaming.

------------------------------------------------------------------------

**A42.** A model’s output-tokens-per-minute limit is 400,000. Requests set `max_tokens` to 64,000 as a safety ceiling, but actual responses average 650 output tokens. Approximately how many requests per minute can the output limit sustain?

-   A. About 615
-   B. About 6
-   C. About 1,230
-   D. The output limit does not bound request rate; only the requests-per-minute limit does.

------------------------------------------------------------------------

**A43.** A summarizer runs on Claude Haiku 5.5. Requests average 96,000 input tokens and 1,200 output tokens. Product wants to add a 6,000-token style guide to the system prompt. What is the cost per 1,000 requests after the change, and by what factor does it rise?

-   A. \$54.00, about 5.3x
-   B. \$10.84, about 1.06x
-   C. \$51.60, about 5.1x
-   D. \$13.20, about 1.3x

------------------------------------------------------------------------

**A44.** A batch job on Claude Haiku 5.5 submits 20,000 requests. Each carries a 108,000-token shared prefix served from cache, 900 tokens of unique input, and produces 300 output tokens. What does the batch cost?

-   A. \$13.20
-   B. \$54.00
-   C. \$132.00
-   D. \$66.00

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**A45.** An Agent SDK run proceeds as follows: turn 1 calls `Bash`; turn 2 calls `Read` twice; turn 3 calls `Edit` and then `Bash`; a final turn produces text with no tool calls. The run is configured with `max_turns=2`. What happens?

-   A. All four turns run, because `max_turns` counts only subagent spawns, not tool-use turns.
-   B. Two tool-use turns run plus the final text-only turn, and the run returns the `success` subtype.
-   C. The loop stops after two tool-use turns and returns a `ResultMessage` with subtype `error_max_turns` and no `result` field.
-   D. The loop stops after two tool-use turns and returns the `success` subtype with a partial `result`.

------------------------------------------------------------------------

**A46.** **(Select THREE)** Which THREE things does Claude Code do when a query reaches its `max_budget_usd` cap?

-   A. Rolls back the cost of the response that crossed the cap, so the reported total lands on the cap.
-   B. Stops background subagents that are still running.
-   C. Ends the query with the `error_max_budget_usd` result subtype.
-   D. Resets the budget counter so that later messages in the same conversation can continue.
-   E. Drops the remaining turns to the `low` effort level to stretch the remaining budget.
-   F. Refuses to spawn further subagents, returning `Budget limit reached`.

------------------------------------------------------------------------

**A47.** An Agent SDK run sets `max_budget_usd` to \$5.00. Accumulated spend is \$4.85 when a model response costing \$0.70 arrives. Two background subagents are mid-flight at that moment and spend a further \$0.18 and \$0.11 before they are stopped. What does the run report?

-   A. \$5.84 and the subtype `error_max_budget_usd`
-   B. \$5.00 and the subtype `error_max_budget_usd`, since the cap is enforced exactly
-   C. \$5.55 and the subtype `error_max_budget_usd`, since subagent spend is tracked separately
-   D. \$5.84 and the subtype `success`, since the response that crossed the cap completed normally

------------------------------------------------------------------------

**A48.** Which statement correctly describes what a non-fork subagent starts with in its context?

-   A. The parent’s conversation history, but not the parent’s tool results.
-   B. The parent’s system prompt, so that shared conventions carry over.
-   C. Any skill content the parent had preloaded, so the two agents stay aligned.
-   D. Its own `prompt`, the Agent tool’s prompt string, project CLAUDE.md and its tool definitions, but none of the parent’s history, tool results or system prompt.

------------------------------------------------------------------------

**A49.** An Agent SDK application runs on Claude Opus 5 with no limits configured. A single prompt grows into dozens of concurrently running agents and the run’s cost far exceeds what the team expected. Which set of controls actually bounds the growth?

-   A. `max_turns`, which caps the total number of subagents a run may spawn.
-   B. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (default 3) and `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20) as environment variables, plus `max_budget_usd`, whose cap counts subagent spend.
-   C. Adding `Agent` to `disallowedTools`, which is the only supported control over delegation.
-   D. Setting `permissionMode` to `plan`, which prevents subagent spawning.

------------------------------------------------------------------------

**A50.** **(Select TWO)** Which TWO statements about capping subagent growth are correct?

-   A. The default spawn depth is 3 layers of subagents below the main agent, and setting it to 1 stops your subagents from spawning any of their own.
-   B. `max_budget_usd` counts only the main agent’s own requests, which is why subagent fan-out escapes it.
-   C. Depth and concurrency are set as `query()` options, in the same way as `max_budget_usd`.
-   D. The default concurrency limit is 3 subagents running at once.
-   E. At the concurrency limit, Claude receives a `tool_result` carrying `Concurrent subagent limit reached`, and can spawn again once the running count drops.

------------------------------------------------------------------------

**A51.** A long-running agent enables `clear_tool_uses_20250919`. The team’s concern is that findings discovered early in the run disappear when old tool results are cleared. Which design preserves what the agent needs?

-   A. Set `clear_tool_inputs: true`, so that the agent keeps the results and loses only the calls.
-   B. Raise `keep` to 50 so that nothing important is ever in the cleared range.
-   C. Give the agent the memory tool so it can write findings to memory files before clearing, and name the tools whose results must survive in `exclude_tools`.
-   D. Lower `trigger` to 10,000 input tokens so that clearing happens before any findings accumulate.

------------------------------------------------------------------------

**A52.** A headless CI agent must be restricted to a fixed, explicit tool surface. Anything not pre-approved should be hard-denied rather than silently allowed because no approval callback is registered. Which permission mode fits?

-   A. `dontAsk`
-   B. `default`
-   C. `bypassPermissions`
-   D. `acceptEdits`

------------------------------------------------------------------------

**A53.** A main agent on Claude Opus 5.5 holds 85,000 tokens of context. A research subtask would read 14 files averaging 9,000 tokens each. Done inline, all of that tool output lands in the main agent’s context; delegated to a subagent, only the subagent’s 1,800-token final report does. Treating the added context as uncached input on the main agent’s next request, roughly how much does each subsequent main-agent request cost extra if the work is done inline instead of delegated?

-   A. About \$0.05
-   B. About \$0.25
-   C. About \$0.84
-   D. About \$0.50

------------------------------------------------------------------------

**A54.** **(Select TWO)** A reviewer is handed this subagent definition: a `doc-auditor` agent with `tools` omitted, `model: "inherit"`, no `maxTurns`, and a prompt instructing it never to modify files. Which TWO are real defects?

-   A. `model: "inherit"` is not a valid value; a subagent must name a concrete model alias or model ID.
-   B. Project CLAUDE.md is never loaded into a subagent’s context, so the agent cannot follow the project’s documentation conventions.
-   C. Omitting `tools` gives the subagent every tool available to subagents, so the no-modification rule rests on prompting alone; scope it to read-only tools instead.
-   D. With no `maxTurns`, the subagent runs until it decides it is finished, so an open-ended audit can run long; set a limit and resume the agent if its output comes back marked partial.
-   E. A programmatic subagent cannot be given a `prompt`; only filesystem-defined agents can.
-   F. Subagents always run in the foreground, so a long audit blocks the parent agent.

------------------------------------------------------------------------

**A55.** An application reads `message.result` as soon as it sees a `ResultMessage`. It crashes on runs that end with subtype `error_max_turns`. Which statement is correct?

-   A. `result` is present on every subtype; the crash must come from a null `total_cost_usd`.
-   B. `result` is present only on the `success` subtype, so the subtype must be checked first; `total_cost_usd`, `usage`, `num_turns` and `session_id` are carried on every subtype.
-   C. `error_max_turns` is not a result subtype; hitting the turn limit raises instead of yielding a result.
-   D. Reading `result` is safe, but `session_id` is absent on error subtypes, so such a run cannot be resumed.

------------------------------------------------------------------------

**A56.** An agent is given hard operating rules in its initial prompt. Long runs work well until a `compact_boundary` message appears in the stream, after which the agent stops honouring several of the rules. What is the correct fix?

-   A. Compaction is off by default; turning it on will preserve the rules in the summary.
-   B. Raise `autoCompactWindow` to 1,000,000 so that compaction never fires.
-   C. Compaction replaces older messages with a summary, so early instructions can be lost; persistent rules belong in CLAUDE.md loaded through `settingSources`, because that content is re-injected on every request.
-   D. Use a `PreCompact` hook to re-send the rules as a user message, which is the only supported mechanism for persisting them.

------------------------------------------------------------------------

**A57.** Which statement about Agent SDK hooks is correct?

-   A. Hooks run in your application process rather than inside the agent’s context window, so they consume no context; a `PreToolUse` hook that rejects a call prevents execution and Claude receives the rejection as the tool result.
-   B. Hooks run inside the model’s context, and their output is billed as input tokens on the next request.
-   C. `PostToolUse` is the hook to use for blocking a dangerous command before it runs.
-   D. Hooks are available only in the Python SDK; the TypeScript SDK exposes permission callbacks instead.

------------------------------------------------------------------------

**A58.** Claude requests five tool calls in a single turn: three `Read` calls, one `Edit` and one `Bash`. How does the Agent SDK execute them?

-   A. All five run concurrently, since they were requested in one turn.
-   B. All five run sequentially; concurrency requires setting `disable_parallel_tool_use` to false.
-   C. Custom tools run in parallel by default while built-in tools run sequentially, so the mix runs sequentially.
-   D. The read-only calls can run concurrently while the state-changing `Edit` and `Bash` calls run sequentially; a custom tool is sequential unless it declares `readOnlyHint`.

------------------------------------------------------------------------

**A59.** A streaming-input session has `maxTurns` set. A user message is queued at the moment a turn ends by hitting the turn limit. What happens to that message?

-   A. It is appended to that turn’s final model call, so the turn limit is effectively exceeded by one message.
-   B. It stays queued and begins a new turn with the max-turns count starting over, while the budget total keeps accumulating across messages.
-   C. It is discarded and the session ends with `error_max_turns`.
-   D. Both the turn count and the budget total start over for the new message.

------------------------------------------------------------------------

**A60.** An agent must finish inside a 90-second wall-clock budget. Each tool-use turn averages 5.4 s of model time plus 1.9 s of tool execution. The final text-only turn takes 6.0 s and has no tool execution. What is the largest `max_turns` value that fits the budget?

-   A. 15
-   B. 16
-   C. 11
-   D. 12

------------------------------------------------------------------------

*End of exam. Answers begin in the answer key.*
