# Answer Key: Chapters 3–5

## Chapter 3 — The Messages API

**Q3.1 — A.** The API enforces strict user/assistant alternation, so two consecutive `user` turns are rejected. Merging them into a single turn with two text blocks (or one concatenated string) satisfies the invariant while preserving both messages. B is wrong because an empty assistant turn is itself invalid content and misrepresents the conversation; there is no `allow_consecutive_roles` parameter, and discarding a response wastes a billed generation.

**Q3.2 — C.** `content` is always an array of typed blocks, and with extended thinking the `thinking` block typically precedes the text block, so index 0 no longer has a `.text` attribute. The fix is to filter on `block.type == "text"` rather than index. A is wrong: `content` remains an array; enabling thinking does not change the container type, only which block types appear in it.

**Q3.3 — D.** A response truncated at the `max_tokens` ceiling returns HTTP 200 with a well-formed `Message` and `stop_reason: "max_tokens"` — no exception is raised, so only an explicit check catches it. B is the attractive distractor because context overflow is a real failure, but that produces `model_context_window_exceeded`, and comparing input tokens to the window would not detect output truncation at all.

**Q3.4 — B.** `max_tokens` is a hard ceiling, not a length target: the model does not compress to fit, it simply stops, leaving `stop_reason: "max_tokens"` and a cut-off answer. A and D both assume the model adapts its plan to the budget, which it does not. To get shorter summaries you must change the prompt, not the cap.

**Q3.5 — A.** Non-streaming requests hold an idle connection for the whole generation, and long generations exceed what proxies and the SDK’s ten-minute validation tolerate, producing failures with no HTTP response at all. The documented remedy is streaming or the Batches API. B is wrong because `max_tokens` does not consume OTPM — only tokens actually generated do.

**Q3.6 — D.** Appending a flattened text string in place of `response.content` discards the `tool_use` blocks, so the `tool_result` blocks you subsequently send reference ids that no longer appear in the history, and the request is rejected. The fix is to round-trip `response.content` verbatim. B is wrong because the API is stateless and holds no tool state; all of it lives in the array you send.

**Q3.7 — B.** In the Messages API the system prompt is a top-level `system` parameter, accepting either a string or an array of content blocks. A describes the convention of other chat APIs and is the most attractive wrong answer precisely because it is so common elsewhere; there is no system entry at the head of `messages`.

**Q3.8 — C.** The cached prefix must be byte-identical across requests, so the large static block goes first with `cache_control` on it, and the volatile timestamp goes after the breakpoint. B inverts this: placing the changing timestamp inside the cached prefix guarantees a fresh write on every request and never a hit. D is simply false — `system` blocks are cacheable.

**Q3.9 — A.** `pause_turn` is a cooperative yield from a long server-side operation, not an error; resending the conversation with the paused assistant turn appended resumes the work already done. B is the attractive wrong answer because the status looks transient, but restarting from scratch discards completed work and re-bills it.

**Q3.10 — D.** Stop sequences match any occurrence in generated output, so `}` fires on the first closing brace — including one closing a nested object — truncating the JSON. A is wrong because stop sequences are evaluated against output only; a brace in your input has no effect. Constrained structured output is the correct modern tool here.

**Q3.11 — C.** Token counting accepts images and documents only with `base64` sources; `url` and `file` sources return `invalid_request_error`. B is attractive because silent partial counting would be a plausible design, but the endpoint rejects the request outright rather than ignoring the file. For Files API references, read `usage` from the real response instead.

**Q3.12 — B.** Newer models use a different tokenizer that yields substantially more tokens for the same text — on the order of 30% more — so counts are not portable between model generations. A is the natural guess but the wrong mechanism; the window did not shrink, the same text simply measures larger. Always recount against the model you will call.

**Q3.13 — D.** The versioning policy explicitly reserves the right to add new output fields and new enum variants within a version without a version bump, so clients must tolerate unknown fields rather than rejecting them. C is wrong because versions never change automatically — `anthropic-version` is pinned by you and does not expire.

**Q3.14 — A.** The `request-id` response header (mirrored as `request_id` in error bodies) is the only identifier that correlates your observation with server-side records, and it is the first thing a support investigation asks for. B is useless for identifying one call, since the version header is the same constant on every request you make.

**Q3.15 — C.** Automatic retries with backoff that honor `retry-after`, plus streaming accumulation helpers like `text_stream` and `get_final_message()`, are SDK conveniences over the same HTTP protocol. A and B are available over raw REST like everything else — the SDK adds no capability the API lacks. D is false in any client: the API is stateless and always requires you to resend history.

## Chapter 4 — Streaming, Caching, and Batching

**Q4.1 — C.** Long non-streaming generations hold an idle connection past what the ten-minute validation and intermediate network equipment tolerate, which is why the documentation directs you to streaming or batching for them. D is the attractive wrong answer: retrying a request that takes minutes to fail wastes a full billed generation each attempt and does not address the cause.

**Q4.2 — A.** `input_json_delta` payloads are fragments of a JSON string — `{"location": "San Fra` is a legitimate delta — so they are individually unparseable by design. Accumulate the fragments and parse once at `content_block_stop`, where `tool_use.input` is guaranteed to be a complete object. C confuses the delta types; tool input never streams as `text_delta`.

**Q4.3 — B.** The `usage` carried on `message_delta` is cumulative, not incremental, so summing across events multiplies the real count. Take the final `message_delta` value instead. C is wrong in the opposite direction: `message_start` carries a placeholder `output_tokens` of 1, which is not a usable final figure.

**Q4.4 — D.** SDK retry logic keys off HTTP status codes and connection faults, and a mid-stream error arrives inside an already-successful 200 response, so no retryable condition is ever observed. A is wrong because `overloaded_error` is generally retryable — the issue is purely that automatic machinery cannot see it, leaving the retry decision to your stream consumer.

**Q4.5 — C.** A stream that simply ends without `message_stop` produces no exception and no error event, so the only reliable detection is a flag set on `message_stop` and checked after the loop exits. A is wrong because `message_start` always carries `stop_reason: null`; the terminal reason arrives later, in `message_delta`.

**Q4.6 — A.** Prompts below the model’s minimum cacheable length are processed without caching and return no error, which is exactly why both cache usage fields reading zero is the diagnostic. C is the plausible-sounding distractor, but prompt caching no longer requires a beta header; if it did, you would get an error rather than silence.

**Q4.7 — D.** Cache matching requires a byte-identical prefix, so a timestamp placed before the breakpoint makes every request unique, producing a write at 1.25× every time and a hit never. C is attractive but misdiagnoses it: even with a one-hour TTL the prefix would still differ on every call. Move volatile content after the breakpoint.

**Q4.8 — B.** `usage.input_tokens` counts only tokens after the last cache breakpoint, so total input is `cache_read_input_tokens + cache_creation_input_tokens + input_tokens`. A is the trap, and it is dangerous because it makes a large workload look nearly free in your own dashboard while the invoice reflects reality.

**Q4.9 — C.** The cached prefix is assembled as tools, then system, then messages, and a change at one level invalidates that level and everything after it — so any edit to a tool definition, including a description, invalidates the entire cache. B is the intuitive but wrong answer: descriptions are part of the hashed prefix, not inert metadata.

**Q4.10 — A.** A cache entry becomes readable only once the first response has begun, so twenty simultaneous cold requests all miss and all write. The fix is to send one request, wait for it to start responding, then release the rest — or pre-warm with `max_tokens: 0`. D is wrong because no entry existed to expire.

**Q4.11 — B.** A twenty-minute reuse interval falls outside the five-minute default window but well inside an hour, which is precisely the case the one-hour TTL exists for: pay 2× to write once instead of rewriting on every run. A guarantees expiry between calls, so you would pay the 1.25× write every night and never read.

**Q4.12 — D.** Batch request params are validated asynchronously and errors surface only after the entire batch ends, so a single smoke test against the synchronous Messages API catches a systematic mistake before you commit 50,000 requests. C changes nothing, because the errors do not exist until the batch has ended regardless of how often you poll.

**Q4.13 — A.** Batch result order is explicitly not guaranteed, which is why `custom_id` is required and unique — it is the only correct correlation key. C identifies a real symptom but the wrong mechanism: errored results do appear in the file, and positional matching would be unsafe even if they did not.

**Q4.14 — C.** `expired` means the 24-hour processing window closed before those requests reached the model; they are not billed and are safe to resubmit. B conflates expiry with the separate 29-day result retention window, and gets the billing backwards — unprocessed requests incur no charge.

**Q4.15 — B.** `stream: true` is a validation error inside a batch request, because batch results are delivered as a single file rather than an event stream; the two features are opposite answers to the same latency-versus-cost question. D invents a parameter — the discount comes from using the Batches API, not from a flag on a synchronous call.

## Chapter 5 — Structured Output, Multimodal Input, and Failure Handling

**Q5.1 — D.** Constrained decoding via `output_config.format` makes schema-invalid output unproducible, which removes the failure class rather than mitigating it. A is the path of least resistance and the wrong one: regex-plus-retry scales your cost and latency with your error rate while leaving schema drift unaddressed. Note that temperature is not available on newer models anyway.

**Q5.2 — B.** Numeric constraints such as `minimum` and `maximum` are outside the supported schema subset and return 400 when sent raw. C describes what the *SDK helper* does — strip the constraint, move it into the description, and validate client-side — but that transformation only happens if you go through the helper or `transform_schema()`.

**Q5.3 — A.** A refusal returns HTTP 200, is billed for generated tokens, and its message can override schema compliance, so `stop_reason` must be checked before parsing. D is the attractive wrong answer because truncation produces similar-looking invalid output, but truncation reports `max_tokens`, not `refusal`, and raising the limit would not change a refusal.

**Q5.4 — C.** The limit is 20 strict tools per request and non-strict tools do not count toward it, so marking only the critical tools `strict` is the documented first remedy. A moves in the wrong direction on reliability for no benefit to the binding constraint, and D is not something you can configure — the 180-second timeout is a backstop, not a tunable.

**Q5.5 — B.** Citations and `output_config.format` are explicitly incompatible and return 400 together, so a forced tool call is the way to get a schema-constrained object alongside citations. A is wrong because that beta header applies to the deprecated `output_format` parameter and does nothing to resolve the citations conflict.

**Q5.6 — D.** Prefilling a trailing assistant turn is unsupported on newer models and returns 400; the documented replacements are structured outputs or system prompt instructions. C invents a rule — assistant content may be a string or a block array on any model — and the failure has nothing to do with the brace’s encoding.

**Q5.7 — A.** A standard-tier model downscales anything above a 1568 px long edge, so a 3840×2160 screenshot becomes roughly 1456 px wide before processing: you pay the upload bandwidth and receive 1456-px detail. B is wrong because oversized images are downscaled by default, not rejected — rejection requires explicitly setting `oversized_image: "error"`.

**Q5.8 — C.** Because the API is stateless, every turn resends the full history, so a 6 MB base64 image is retransmitted on each call until the accumulated payload crosses the 32 MB Messages limit and returns 413. The Files API fixes it by replacing the inline data with a short `file_id`. B invents an expiry rule that does not exist.

**Q5.9 — B.** Any request containing more than 20 images requires every image to have no dimension above 2000 px, so 45 images at 3000×2000 violates the rule even though each is well under the 8000 px per-image maximum. A states a limit that applies to claude.ai messages, not to API requests, where the ceiling is 100 or 600 images.

**Q5.10 — D.** Each PDF page is processed twice — rendered as an image and supplied as extracted text — so cost is roughly 1,500–3,000 text tokens per page plus the visual-token cost of the page image. A is the common underestimate and will understate a large document’s cost by a wide margin, which is why dense PDFs exhaust the context window well below the 600-page limit.

**Q5.11 — A.** Uploaded files are scoped to the entire workspace rather than to a user or session, so any valid `file_id` accepted from a client lets one tenant reference another tenant’s file. Keep the user-to-file mapping server-side and consider one workspace per tenant. B is a real operational concern but not the security flaw being flagged.

**Q5.12 — C.** A spend-cap 429 carries no `retry-after` and is identified by `error.details.error_code == "enforced_spend_limit_reached"`; retrying cannot clear it until access resumes at the start of the next month or the tier is raised. B would not help, since the distinguishing feature is the absence of the header altogether, not its value.

**Q5.13 — B.** Pure exponential backoff keeps a fleet that failed together synchronized, so all 200 workers retry at the same instant at each doubling and re-overload the service. Jitter decorrelates the retries, and a circuit breaker stops contributing to the overload entirely. D is wrong: 529 is a transient capacity signal and is retryable.

**Q5.14 — A.** The Messages API has no idempotency-key header, so a retry after a timeout is a second billed generation and can double-apply side effects; the mitigation must live in your layer. B invents the header. C is worse than it looks — disabling retries converts a recoverable transient fault into a hard user-visible failure.

**Q5.15 — D.** HTTP 200 with a `stop_reason` other than `end_turn` or `tool_use` is a model-layer event that HTTP-focused dashboards cannot see, and `max_tokens` truncation is the classic cause of intermittent parse errors. The flat error-rate graph is the clue: nothing failed at the transport layer, so TLS and header problems are ruled out by the 200 itself.
