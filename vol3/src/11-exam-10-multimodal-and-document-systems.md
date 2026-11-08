# Exam 10 — Multimodal and Document Systems

**Instructions.** This exam contains 53 questions and is timed at 120 minutes. It is a closed-book exam: no documentation, no API console, no calculator beyond pen and paper. Each question has exactly one correct answer unless it is marked **(Select TWO)** or **(Select THREE)**, in which case you must select exactly that many options to earn the mark — there is no partial credit. Answers and full explanations are in the answer key at the back of this volume.

**A note on difficulty.** This is a *hard-tier* exam. It is calibrated so that a well-prepared candidate scores between 50% and 60%. Your score here is a depth diagnostic, not a predicted result on the real CCDV-F exam — use the per-domain table at the end of the answer key to find where your understanding is thin, and do not read a low score as a verdict on your readiness.

Several questions require the visual-token formula. Work it out rather than estimating.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E10.1** A single page image of 1,600 × 1,200 px is sent to Opus 5.5. Neither dimension exceeds the high-resolution tier’s limits, so the image is not resized. How many visual tokens does it cost?

-   A. 2,451
-   B. 2,494
-   C. 2,560
-   D. 4,784

**E10.2** A scanned-archive browser sends 28 page thumbnails in a single request, each 2,400 × 1,800 px. The API returns an `invalid_request_error` mentioning many-image requests. What is wrong?

-   A. Once a request carries more than 20 images, no image may have either dimension above 2,000 px; at 2,400 px wide these are rejected. Downscale the long edge to 2,000 px or under, or split the work into requests of 20 image blocks or fewer.
-   B. The per-request image limit on the Claude API is 20.
-   C. Each image exceeds the 10 MB per-image size limit.
-   D. Images must share identical dimensions when more than 20 are sent in one request.

**E10.3** A 48-page scanned contract set is sent as a PDF. Each page yields roughly 2,400 tokens of extracted text, and each page image is rendered at 1,275 × 1,650 px. Approximately how many input tokens does the document contribute?

-   A. 115,200
-   B. 130,272
-   C. 245,472
-   D. 249,840

**E10.4** A records team wants uploaded scans to disappear automatically six months after upload. What should they do?

-   A. Set `expires_in_seconds` to 15,552,000 on upload.
-   B. Omit `expires_in_seconds`; the default retention is 180 days.
-   C. Set `expires_at` directly on the upload request to a date six months out.
-   D. This cannot be done with a single setting: `expires_in_seconds` accepts 3,600 to 7,776,000 seconds, a 90-day maximum, so six-month retention needs application-side bookkeeping — and expiry is not a guaranteed-deletion control in any case, so an explicit `DELETE` is what actually removes a file.

**E10.5** An overnight job processes 12,000 scanned archive pages through the Message Batches API on Sonnet 5.5. Each page contributes about 5,114 input tokens (2,400 of extracted text plus 2,714 visual) and produces about 600 output tokens. There is no shared cached preamble. What does one night cost?

-   A. \$61.37
-   B. \$97.37
-   C. \$122.74
-   D. \$194.74

**E10.6** An ingestion pipeline uploads a scan to the Files API, processes it, and then calls `GET /v1/files/{file_id}/content` to archive the original into object storage. The call returns 400. Why?

-   A. Uploaded files are never downloadable — `downloadable` is always `false` for them, and the content endpoint returns 400. Only files produced by the code execution tool or by skills can be downloaded, so the pipeline must keep its own copy of anything it uploads.
-   B. The file has already expired, and expired files return 400 on download.
-   C. Downloads require the `files-api-2025-04-14` beta header, which the pipeline does not send.
-   D. Downloads are blocked for files above the 32 MB request-size limit.

**E10.7** Which **TWO** statements about referencing Files API objects from a Messages request are correct? **(Select TWO)**

-   A. A `.docx` file may be referenced directly from a `document` block by its `file_id`.
-   B. An image `file_id` placed in a `document` block is accepted and converted automatically.
-   C. A PDF `file_id` belongs in a `document` block, while a PNG `file_id` belongs in an `image` block.
-   D. A `.csv` must be converted to PDF before it can be referenced at all.
-   E. A `.txt` or `.md` file uploaded with MIME type `text/plain` can be referenced from a `document` block.

**E10.8** A request inlines 14 scanned page images averaging 2.1 MB each as base64, plus a 40 KB prompt. Base64 encoding inflates bytes by roughly 4/3. What happens?

-   A. It succeeds: 29.4 MB of image data is under the 32 MB request limit.
-   B. It succeeds: the relevant limit is 10 MB per image and each is 2.1 MB.
-   C. It fails: base64 inflates 29.4 MB to about 39.2 MB, over the 32 MB request-size limit. Reference the pages by `file_id` from the Files API instead, or split the request.
-   D. It fails: 14 images exceeds the per-request image limit.

**E10.9** A forms pipeline extracts table data, writes it to an `.xlsx`, uploads that to the Files API, and tries to reference it from a `document` block for a second validation pass. What is wrong?

-   A. Spreadsheets must be uploaded with MIME type `text/plain`.
-   B. Spreadsheets are supported in `document` blocks but must be under 10 MB.
-   C. Spreadsheets must always be referenced from a `container_upload` block.
-   D. `.xlsx` and `.docx` are not supported in `document` blocks at all; convert to plain text, or — where visual layout and citations matter — to PDF, which does get built-in image parsing.

**E10.10** A 180-page scanned planning archive is sent as a single PDF to Sonnet 5.5 (1M context). Each page contributes about 5,114 tokens. What happens?

-   A. It is rejected: 180 pages exceeds the 100-page limit.
-   B. It passes the page limit — 600 pages on a 1M-context model — but at about 920,520 tokens the document nearly fills the context window, leaving almost nothing for the system prompt, the question and the output. It has to be split.
-   C. It is accepted with room to spare; 180 pages is comfortably inside both limits.
-   D. It is rejected: the 32 MB request limit is measured in tokens rather than bytes.

**E10.11** Where should images sit relative to text in a mixed request, and what else does the documentation recommend?

-   A. Images before text — Claude performs best with images first — and each image in a multi-image request should be preceded by a short label such as `Image 1:` so it can be referred to by name later.
-   B. Text before images, so that the model knows what it is looking for as it reads them.
-   C. Images interleaved, one immediately after each instruction that refers to it.
-   D. Images in the system prompt and text in the user turn, so the images can be cached.

**E10.12** An invoice service sends 24 page images per request at 1,275 × 1,650 px on Opus 5.5, with negligible accompanying text. What is the visual-token cost and the input cost per request, and is the request valid?

-   A. 2,714 tokens and about \$0.01 — identical images are counted once.
-   B. 65,136 tokens and about \$0.13.
-   C. 65,136 tokens and about \$0.26, but the request is rejected because 24 images exceeds the 20-image maximum.
-   D. 65,136 tokens and about \$0.26, and the request is valid: it carries more than 20 images, but no dimension exceeds 2,000 px.

**E10.13** A document portal has the browser upload scans directly to the Files API and post the returned `file_id` to the backend, which passes it straight into a Messages request. What is the security defect?

-   A. File identifiers expire, so the backend should re-upload rather than reuse them.
-   B. The Files API cannot be called from a browser at all.
-   C. The backend is accepting a `file_id` from an untrusted source. Files are workspace-scoped, so any valid identifier in that workspace resolves regardless of who uploaded it. File IDs must be treated as server-side references, with the user-to-file mapping held in the application and looked up from the authenticated session.
-   D. Uploaded files are not downloadable, so the backend cannot verify what it was handed.

**E10.14** Which **THREE** statements are true of the Message Batches API as used for a scanned-archive job? **(Select THREE)**

-   A. Results are returned in arbitrary order, and `custom_id` is the only reliable key for joining a result back to its page.
-   B. `speed` may be set on individual requests to prioritise urgent pages within a batch.
-   C. A base64-encoded PDF `document` block may be sent inside a batch request.
-   D. A batch does not expire while its results remain unread.
-   E. The batch discount applies to text tokens but not to visual tokens.
-   F. The 50% discount stacks with prompt caching on a shared cached preamble.

**E10.15** A 60-page policy manual is used as a shared cached preamble on Opus 5.5 with the 1-hour TTL. Each page contributes about 5,114 tokens. In one hour the service handles 80 requests: the first writes the cache, the remaining 79 read it. Counting only the manual’s tokens, what does the hour cost?

-   A. \$2.45
-   B. \$7.30
-   C. \$4.85
-   D. \$98.19

**E10.16** To estimate what 5,000 archive pages will cost before committing to the run, an engineer submits them to the Batches API with `max_tokens: 0`. What is the correct approach?

-   A. `max_tokens: 0` is rejected on the Batches API; use the token-counting endpoint, which exists precisely to price content before sending it.
-   B. `max_tokens: 0` is accepted but returns an empty response carrying no usage block.
-   C. Token counting requires the documents to be uploaded to the Files API first.
-   D. Batch requests do not report token usage, so sampling a few pages on the Messages API is the only option.

**E10.17** A `file_id` whose `expires_at` passed yesterday is still being referenced by a scheduled job. What is true?

-   A. The file continues to resolve in Messages requests for a 30-day grace period.
-   B. The metadata is removed immediately and download returns 400.
-   C. Messages requests referencing it fail before inference and download returns 404, but the metadata remains readable for up to 30 days with `expires_at` in the past — so the file still appears in list responses, and callers must filter by comparing `expires_at` to the current time.
-   D. The file is re-materialised from the original upload on first use after expiry.

**E10.18** Which **TWO** Files API limits are stated correctly? **(Select TWO)**

-   A. Maximum file size is 100 MB; a larger file returns 413.
-   B. Maximum file size is 500 MB; a larger file returns 413.
-   C. Total storage is 100 GB per organisation.
-   D. Total storage is 1 TB per organisation, and an upload that would exceed it returns 400.
-   E. There is no rate limit on file operations.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E10.19** A page-classification service runs on Haiku 5.5. Each request carries a 2,000-token system prompt plus N pages at about 5,114 tokens each. At what page count does the request first cross the 100,000-token threshold, and what is the consequence?

-   A. At 25 pages, and the request is rejected above the threshold.
-   B. At 19 pages, and the surcharge applies only to the tokens above 100,000.
-   C. At 20 pages, and the surcharge applies only to the input side of the bill.
-   D. At 20 pages — 104,280 tokens, against 99,166 at 19 pages — and from there the whole request, input and output, is billed at 5×, so adding one page roughly quintuples the cost of that request.

**E10.20** On Opus 5.5, a page image of 1,600 × 1,200 px costs 2,494 visual tokens. What does downsampling it to 800 × 600 px cost, and what is the trade-off?

-   A. 1,247 tokens, exactly half, because tokens scale linearly with each dimension.
-   B. 638 tokens, roughly a quarter, because tokens scale with pixel area; the trade-off is legibility — the documentation warns that resizing can render small text unreadable, which makes this safe for layout classification and risky for field extraction.
-   C. 2,494 tokens; downsampling below the tier limits does not change the token count.
-   D. 638 tokens with no trade-off, since the high-resolution tier re-upscales the image automatically.

**E10.21** A document-extraction service runs on Opus 5.5 and sets no `output_config.effort`. What applies?

-   A. `medium` — Opus 5.5 and Haiku 5.5 default to `medium`, while the others default to `high`; raising it is a deliberate change that will also restart the prompt cache.
-   B. `high` — all current models default to `high`.
-   C. There is no default; effort must be set explicitly or the request returns 400.
-   D. `medium`, and changing it has no effect on the prompt cache.

**E10.22** A team transcribes 12,000 legible scanned pages a night on Fable 5.1 at \$10 / \$50 per MTok, on the grounds that transcription errors are expensive. What is the strongest objection?

-   A. Fable 5.1 does not accept PDF input.
-   B. Fable 5.1’s 0.025× cache-read multiplier is the lowest available, so it is already the cheapest choice for repeated pages.
-   C. Transcribing legible scans sits near the bottom of the difficulty range and this design pays the top of the price range for it with no eval to justify the choice. Price a representative sample on Haiku 5.5 and Sonnet 5.5 against ground truth — and at this volume the Batches API’s 50% discount is worth more than any model decision.
-   D. Fable 5.1’s context window cannot hold 12,000 pages.

**E10.23** Which **TWO** changes genuinely reduce the cost of a high-volume page-image pipeline? **(Select TWO)**

-   A. Downsample page images to the smallest resolution at which the extraction evals still pass, since visual tokens scale with pixel area.
-   B. Send images as base64 rather than by `file_id`, because inline content is not billed as input.
-   C. Set `"oversized_image": "error"` so that oversized images are rejected rather than billed.
-   D. Put the shared instruction preamble and any fixed reference pages behind a cache breakpoint, and route the overnight volume through the Batches API.
-   E. Convert multi-page PDFs to animated GIFs so that only the first frame is billed.

**E10.24** A 300,000-token cached document preamble is read once. Which statement of the read cost across models is correct?

-   A. Opus 5.5 \$0.030 and Sonnet 5.5 \$0.060.
-   B. Fable 5.1 \$0.030 — its 0.025× multiplier is the lowest available.
-   C. Haiku 5.5 \$0.003, because the long-context surcharge does not apply to cache reads.
-   D. Opus 5.5 \$0.060, Sonnet 5.5 \$0.030, Fable 5.1 \$0.075 and Haiku 5.5 \$0.015 — Haiku is cheapest even after the 5× surcharge, which cache reads do count toward.

**E10.25** To make field extraction from forms reproducible, an engineer sets `temperature: 0` and `top_p: 1` on Opus 5.5. The API returns 400. What is the correct reading?

-   A. `temperature` and `top_p` may not both be set on the same request.
-   B. All three sampling parameters — `temperature`, `top_p` and `top_k` — are deprecated on Claude 4.7 and later and return 400. Consistency on extraction has to come from a strict output schema, a pinned model snapshot, and evals that tolerate the residual variation.
-   C. Sampling parameters are accepted only when `output_config.effort` is set to `max`.
-   D. `temperature: 0` is valid but silently ignored when the request contains image content.

**E10.26** 500 scanned claim forms, each about 5,114 input tokens, are processed through the Batches API on Sonnet 5.5. There is no shared preamble. What is the input cost?

-   A. \$2.56
-   B. \$5.11
-   C. \$1.28
-   D. \$12.79

**E10.27** A team wants the high-resolution image tier for dense engineering drawings. How do they get it?

-   A. Request it with the `high-resolution-images` beta header.
-   B. Set `transformations.resolution` to `high` on each image block.
-   C. It is automatic on Claude 4.7 and later and needs no header: the long edge may reach 2,576 px and a single image may cost up to 4,784 visual tokens, roughly three times the standard tier’s ceiling. Anything larger is downscaled to fit.
-   D. It is available only for images referenced through the Files API, not for base64 or URL sources.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E10.28** A document-triage agent sets `max_turns: 4`. It makes four page-fetch tool calls and the run ends without producing a summary. What happened?

-   A. `max_turns` counts every message exchanged, so the summary would have been the fifth.
-   B. `max_turns` counts model invocations including the final answer, so it should be set to 5.
-   C. `max_turns` limits the number of distinct tools, not turns.
-   D. `max_turns` counts tool-use turns only, so four tool calls exhaust it and the run is cut before a text answer can be produced. Raise the limit, or have the agent summarise incrementally so that a partial result survives truncation.

**E10.29** A page-by-page extraction agent sets `max_budget_usd: 25.00`. Each page costs about \$0.42. After 58 pages the run has spent \$24.36. What happens next?

-   A. The run stops at page 58, because page 59 would exceed the budget.
-   B. The run stops after page 59, having spent \$24.78.
-   C. The run continues to the end of the document; the budget is advisory.
-   D. Pages 59 and 60 both run — the budget is checked after a response arrives, so the run crosses \$25.00 at \$25.20 on page 60 and stops there, having overshot by \$0.20.

**E10.30** A workflow spawns one subagent per page across a 400-page archive with subagent concurrency left at its default. The run fails partway through with 429 responses. What is the diagnosis?

-   A. Subagent nesting depth defaults to 3 and the fan-out exceeds it.
-   B. Concurrency defaults to 20, so twenty subagents are issuing image-heavy requests simultaneously; each page carries thousands of visual tokens, so the organisation’s input-token-per-minute limit is reached long before any count-based limit. Lower the concurrency, or batch the pages instead of fanning out.
-   C. The Agent SDK does not permit more than 100 subagents in a single run.
-   D. Image content blocks cannot be passed into subagents.

**E10.31** A long-running archive agent receives page images as tool results and enables `clear_tool_uses_20250919` with its defaults. What is the effect?

-   A. Once the context passes roughly 100,000 tokens, all but the 3 most recent tool-use/tool-result pairs are cleared — which removes the page images and the visual tokens they carry, so anything the agent must retain has to be written down before it is cleared, for instance to the memory tool.
-   B. Image tool results are exempt from clearing, because they cannot be regenerated from the conversation.
-   C. The default trigger is 50% of the context window and the default keep value is 10 pairs.
-   D. Clearing rewrites the cached prefix in place, so there is no cache cost to it.

**E10.32** Which **TWO** statements about context management on an image-heavy agent are correct? **(Select TWO)**

-   A. `clear_tool_uses_20250919` clears tool definitions along with tool results.
-   B. Context editing and prompt caching cannot be used together.
-   C. When `clear_thinking_20251015` is also enabled, thinking blocks are cleared before tool results.
-   D. Image blocks that have been cleared still count toward the more-than-20-images dimension rule.
-   E. The memory tool (`memory_20250818`) gives the agent a store outside the context window, so extracted field values survive the clearing of the page images they were read from.

**E10.33** An archive pipeline spawns an orchestrator, which spawns a per-volume agent, which spawns a per-page agent, which spawns a per-table agent, which spawns a per-cell agent. The per-cell agent never runs. Why?

-   A. Subagent concurrency defaults to 20, which this fan-out exceeds.
-   B. Subagents cannot receive image content, so the per-page agent produces nothing to pass down.
-   C. Subagent nesting depth defaults to 3, so spawning stops below the per-table level: volume is 1, page is 2, table is 3, and the per-cell agent would be a fourth. Flatten the hierarchy or raise the depth deliberately.
-   D. Each nested subagent restarts the parent’s prompt cache, so the run exhausts its budget before reaching the deepest level.

**E10.34** A design spawns one subagent per page across a 900-page archive. Each subagent uploads its page to the Files API and returns a JSON object of extracted fields. Which **TWO** are real problems with this design? **(Select TWO)**

-   A. The Files API cannot hold 900 files.
-   B. Nothing joins the results: subagent outputs arrive in completion order and no per-page identifier is carried through, so an extraction cannot be matched back to the page it came from.
-   C. Subagents are not permitted to call the Files API.
-   D. 900 uploads against a roughly 500-request-per-minute file-operation limit, driven at the default concurrency of 20, will throttle — and the fan-out is the wrong shape regardless: a uniform, asynchronous, high-volume workload is exactly what the Batches API exists for, at half the price.
-   E. Page images must be kept under 2,000 px because the archive as a whole exceeds 20 images.

**E10.35** A multi-session cataloguing project needs the agent to remember which archive volumes it has already processed and the field schema it settled on. What is the right mechanism?

-   A. Keep both in the system prompt and rewrite it at the start of each session.
-   B. Upload both to the Files API and pass the `file_id` on every session.
-   C. Rely on the 1M context window to carry the project history.
-   D. Use the memory tool (`memory_20250818`), which reads and writes a durable store outside the context window and so survives both session boundaries and context editing — unlike Files API objects, which cannot be modified in place and are workspace-scoped rather than project-scoped.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E10.36** A request carries six scanned pages and asks the model to compare the signature block on page 2 with the one on page 5. It keeps referring to the wrong pages. What is the documented fix?

-   A. Send each page in its own request and compare the outputs in the application.
-   B. Precede each image with a short text label — `Image 1:`, `Image 2:` and so on — so the pages can be referred to by name; and for PDFs, use the logical page numbers a viewer shows rather than array indices.
-   C. Put the question before the images so the model knows which pages matter as it reads.
-   D. Raise `output_config.effort` so the model tracks the ordering more carefully.

**E10.37** To force extraction output to begin with `{`, a team appends an assistant turn containing a single `{`. The API returns 400. What is the correct reading?

-   A. Assistant prefill returns 400 on Claude 4.6 and later; for a guaranteed JSON shape, use structured output via `output_config.format` — accepting that this rules out citations on the same call.
-   B. Prefill is permitted but must not be a single character.
-   C. Prefill is incompatible with requests containing image content blocks.
-   D. Prefill is only available for documents referenced through the Files API.

**E10.38** A 300-page scanned archive volume, each page about 5,114 tokens, is sent to a 1M-context model as a single PDF. What happens?

-   A. It fits: 300 pages is well inside the 600-page limit.
-   B. It fits, because PDF pages are billed as extracted text only.
-   C. It does not fit: at roughly 1,534,200 tokens the volume exceeds the 1M context window by more than half a million tokens, even though 300 pages is inside the 600-page limit. The page limit and the context window are separate constraints, and dense scanned pages hit the window first.
-   D. It does not fit, because the per-request page limit is 100.

**E10.39** Which **TWO** practices most directly improve extraction from scanned forms and tables? **(Select TWO)**

-   A. Place the document blocks before the question and put the question last.
-   B. Ask the model to return the table as a rendered image so that the layout is preserved exactly.
-   C. Rotate pages upright before sending and prefer clear, standard fonts, since skewed or heavily compressed pages degrade extraction.
-   D. Raise `max_tokens` so the table is never truncated, which also improves the accuracy of the extracted values.
-   E. Send each table cell as its own image block so the model can attend to one value at a time.

**E10.40** What is the documented ordering for a request mixing page images, supporting text and a question?

-   A. Question first, then images, then supporting text.
-   B. Question first and repeated at the end, with images in between.
-   C. Supporting text, then the question, then the images.
-   D. Images first, then supporting text, then the question last — images perform best before text, and the documentation reports quality gains of up to 30% from query-last placement in its own testing.

**E10.41** A pipeline builds its request by emitting, for each of 40 pages: the question, then the page image, then the question again. Quality is poor and cost is high. What is wrong?

-   A. The repeated question is the dominant cost driver and should be emitted once.
-   B. The ordering fights both documented preferences at once — images belong before text and the question belongs last — and repeating the question 40 times re-frames the model page by page instead of letting it reason over the whole set. Send all images first, then the supporting text, then one question. With more than 20 images, every page must also be under 2,000 px on both dimensions.
-   C. Forty images exceeds the per-request limit of 20.
-   D. Each image needs its own `cache_control` breakpoint for the pages to be cached.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E10.42** To guarantee that every scan produces structured output, a pipeline sets `tool_choice: {"type": "tool", "name": "extract_fields"}`. The API returns 400. What should it do instead?

-   A. Forced tool choice — both `any` and `tool` — returns 400 on current models; for a guaranteed output shape, use structured output via `output_config.format`, or validate and retry in the application.
-   B. `tool_choice` cannot be used on requests that contain image blocks.
-   C. The named tool must also be described in the system prompt for forced choice to resolve.
-   D. Forced tool choice is accepted only on the Batches API.

**E10.43** A scan pipeline makes 20,000 requests a day on Sonnet 5.5. Each request carries the tool-use system overhead for `tool_choice: "auto"` and one page image of 2,714 visual tokens. Where should optimisation effort go?

-   A. Tool overhead about \$114.40 a day against about \$108.56 for the images — the two are comparable.
-   B. Tool overhead about \$11.44 a day against about \$10.86 for the images — the two are comparable.
-   C. Tool overhead about \$11.44 a day against about \$108.56 a day for the page images — the visual tokens are roughly ten times the tool overhead, so downsampling the pages is worth far more than trimming tool definitions.
-   D. Tool overhead about \$16.24 a day against about \$108.56 for the images, since 406 tokens is the overhead for `auto`.

**E10.44** An agent uses a page-cropping tool that returns cropped regions as images inside `tool_result` content. After several turns a request fails with a many-image error, although the current user turn contains only 6 images. What is the explanation?

-   A. Tool results are excluded from the image count, so the failure has another cause.
-   B. Only the images in the current turn are counted toward the limit.
-   C. Cropped images must be sent as base64 rather than referenced by `file_id`.
-   D. Every `image` block counts toward the more-than-20 rule, including images in earlier turns and images inside `tool_result` content; once the total passes 20, all of them must be under 2,000 px on both dimensions.

**E10.45** A document MCP server keeps the current page cursor in session state established at `initialize`, and uses sampling to ask the client’s model which region of a page to crop. What breaks under the stateless 2026-07-28 revision?

-   A. Sampling is fine, but the cursor should be persisted to a database rather than held in memory.
-   B. Both halves break: `server/discover` replaces `initialize` and no session state is carried between requests, so per-request context must travel in `_meta`; and sampling is deprecated, so the crop decision belongs to the client application or to the server’s own logic.
-   C. Cursors must be passed as tool arguments under the new revision, but sampling is retained.
-   D. Session state is retained; only the logging capability is deprecated.

**E10.46** Which **TWO** statements about oversized images are correct? **(Select TWO)**

-   A. Oversized images returned in a `tool_result` are silently downscaled like any other image.
-   B. Screenshots and zoom images returned to the computer-use and browser-use tools are not downscaled, and the API rejects an oversized `tool_result` image with a validation error — so the application must resize before returning it.
-   C. The `transformations` field is used to request a higher resolution tier for an image.
-   D. Images above 8,000 px on a side are downscaled to fit, like any other oversized image.
-   E. Setting `"oversized_image": "error"` makes the API reject an oversized image rather than downscale it, which is useful when silent downscaling would make small print illegible without anyone noticing.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E10.47** A document portal lets a signed-in user paste a `file_id` to re-run extraction on a scan they uploaded earlier. What is the defect?

-   A. A `file_id` must never be accepted from an end user or any untrusted source: files are workspace-scoped, so a valid identifier from anywhere in that workspace resolves regardless of who uploaded it. Keep the user-to-file mapping server-side and resolve the identifier from the authenticated session.
-   B. File identifiers are long enough that guessing one is impractical, so the exposure is acceptable.
-   C. Setting a short `expires_in_seconds` makes pasted identifiers go stale quickly enough to be safe.
-   D. The user should also be required to paste the original filename, as a second factor.

**E10.48** A scanning service onboards 60 customers and must keep their documents isolated from one another. What is the correct design?

-   A. A single workspace with a per-customer filename prefix enforced in the application.
-   B. A single workspace with a per-customer `expires_in_seconds` policy.
-   C. One workspace per tenant, with API keys scoped to it: the workspace is the isolation boundary the Files API provides, and an organisation may have up to 100 workspaces, which covers 60 customers with room to grow.
-   D. A single workspace, relying on the Compliance API activity feed to detect cross-tenant reads after the fact.

**E10.49** A team is building an extraction pipeline over a scanned personnel archive. Which **TWO** measures are sound? **(Select TWO)**

-   A. Instruct the model not to transcribe personal data, which is sufficient to keep it out of the extraction output.
-   B. Ask the model to identify the people appearing in scanned photographs so the records can be indexed by name.
-   C. Treat a transcription as an estimate rather than a record: the documentation states that counting is approximate and that low-quality, rotated or very small images produce errors, so high-stakes fields need verification or human review.
-   D. Redact or exclude sensitive regions before upload rather than after extraction, and remove uploaded scans with an explicit `DELETE` rather than relying on `expires_in_seconds`, which is not a guaranteed-deletion control.
-   E. Use the model to decide whether a scan is an AI-generated forgery before accepting it into the archive.

**E10.50** Which statement correctly reflects the documented limitations of image understanding?

-   A. Claude can reliably determine whether an image is AI-generated, which makes it suitable for forgery screening.
-   B. Claude will name people in photographs when image quality is high enough.
-   C. Object counts are exact when the objects are clearly separated.
-   D. Claude will not name people in images, cannot reliably tell whether an image is AI-generated, and treats counting and coordinate outputs as approximate — none of which should be load-bearing in an archive pipeline.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E10.51** The document-AI team wants every Claude Code session in the ingestion repository to know the page-rendering DPI, the Files API retention policy and the command that runs the extraction evals. Where do these belong?

-   A. In a skill that an engineer invokes by name when they need it.
-   B. In a `CLAUDE.md` at the repository root, which is loaded as project memory for every session in that project and is version-controlled alongside the code.
-   C. In the user-level settings file, so they follow the engineer across projects.
-   D. In a comment block at the top of the pipeline’s entry point.

**E10.52** Project settings deny `Bash(rm:*)`. An engineer adds an allow rule for `Bash(rm ./tmp/pages/*)` so that rendered page images can be cleaned up between runs. What happens?

-   A. Deny takes precedence over allow, and an allow rule cannot carve an exception out of a deny; the deny pattern itself has to be narrowed.
-   B. The more specific allow rule wins and the cleanup is permitted.
-   C. The rules conflict, so Claude Code prompts the user on each invocation.
-   D. User-level settings override project-level settings, so the allow applies.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E10.53** An extraction eval uses 150 born-digital PDFs exported from a single template, scored by exact string match on 12 fields. It passes at 97%. Production, which is roughly 80% scanned paper, fails constantly. What is the central flaw?

-   A. 150 documents is too small a sample to be meaningful.
-   B. Exact string match is too strict and should be replaced with fuzzy matching across all fields.
-   C. The eval set does not resemble production: born-digital PDFs from one template exercise neither the vision path nor the variation scanning introduces — skew, noise, compression artefacts, handwriting, stamps, multi-column layout. Build the set from sampled production scans stratified by quality, keeping exact match where exactness matters and adding tolerance where it does not.
-   D. The eval should be run against Fable 5.1 so that the achievable ceiling is known first.
