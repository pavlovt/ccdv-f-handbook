# Exam 9 — Enterprise Knowledge and Retrieval

**Instructions.** This exam contains 53 questions and is timed at 120 minutes. It is a closed-book exam: no documentation, no API console, no calculator beyond pen and paper. Each question has exactly one correct answer unless it is marked **(Select TWO)** or **(Select THREE)**, in which case you must select exactly that many options to earn the mark — there is no partial credit. Answers and full explanations are in the answer key at the back of this volume.

**A note on difficulty.** This is a *hard-tier* exam. It is calibrated so that a well-prepared candidate scores between 50% and 60%. Your score here is a depth diagnostic, not a predicted result on the real CCDV-F exam — use the per-domain table at the end of the answer key to find where your understanding is thin, and do not read a low score as a verdict on your readiness.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E9.1** An onboarding assistant runs on Sonnet 5.5 (\$2 / \$10 per MTok). A single cache breakpoint with the 5-minute TTL covers a 120,000-token prefix holding the stable runbook corpus. In steady state the service handles 400 requests per hour, evenly spaced; the first request of each hour writes the cache and the remaining 399 read it. Every request also carries 2,000 tokens of freshly retrieved, uncached material and produces 500 output tokens. What is the approximate cost of one steady-state hour?

-   A. \$6.69
-   B. \$13.48
-   C. \$8.69
-   D. \$99.60

**E9.2** A team places the 120,000-token runbook corpus at the top of the system prompt, appends the current user’s retrieved chunks immediately after it, sets a single `cache_control` breakpoint after the retrieved chunks, and puts the question last. Cache hit rate in production is close to zero. What is wrong?

-   A. The 5-minute TTL expires between requests; switching to the 1-hour TTL would raise the hit rate.
-   B. The breakpoint sits after per-user content, so the cached prefix includes material that differs on every request and nothing ahead of the breakpoint is stable across users.
-   C. Prompt caching has a 20-block lookback, and the corpus spans more content blocks than that.
-   D. Cache writes count toward the input-tokens-per-minute limit, so the writes are being throttled.

**E9.3** A wiki assistant runs on Haiku 5.5 (base \$0.10 / \$0.50 per MTok). Each request is served with 95,000 tokens as a cache read, 8,000 uncached tokens of retrieved context and question, and 1,200 output tokens. What do 1,000 such requests cost?

-   A. \$2.35
-   B. \$9.38
-   C. \$7.95
-   D. \$11.75

**E9.4** To make citation output reproducible across runs, an engineer sets `temperature: 0` on a Sonnet 5.5 request. The API returns 400. What is the correct reading?

-   A. `temperature` is deprecated on Claude 4.7 and later and returns 400; determinism is not an exposed control on these models, and reproducibility has to come from pinning the model snapshot and holding the prompt fixed.
-   B. `output_config.effort` defaults to `high` on Sonnet 5.5, and high effort rejects sampling parameters.
-   C. Citations and `temperature` are mutually exclusive on all models.
-   D. Sampling parameters are only accepted when the model ID is a dated snapshot.

**E9.5** A knowledge assistant layers its prompt as (1) tool definitions, (2) a 40,000-token policy handbook, (3) a 90,000-token runbook corpus, (4) rotating per-user retrieval. Which **TWO** statements correctly constrain how prompt-cache breakpoints can be used here? **(Select TWO)**

-   A. Breakpoints may be placed only in the system prompt, not on tool definitions or on message content.
-   B. At most four cache breakpoints may be set on a request, so layers 1 through 3 can each carry one with one to spare.
-   C. Changing the tool definitions invalidates only the tools segment, leaving the handbook and corpus caches intact.
-   D. Cache lookup walks back at most 20 content blocks from a breakpoint, so a prefix split into many small blocks may not be matched.
-   E. Each cache breakpoint must cover at least 5,000 tokens on current models.

**E9.6** A retrieval service targets a 1M-context model. Its system prompt is 3,000 tokens. It defines four tools used with `tool_choice: "auto"`, whose schemas total 1,900 tokens on top of the tool-use system overhead. A cached corpus occupies 180,000 tokens and conversation history 60,000. The team wants to reserve the full 128,000-token maximum output. How many tokens remain for retrieved documents?

-   A. 627,100
-   B. 626,694
-   C. 626,814
-   D. 754,814

**E9.7** A grounding requirement says every answer must cite the wiki page it came from. A separate downstream consumer needs the answer as a JSON object with fixed fields. The team enables `citations` on each document block and sets `output_config.format` to a JSON schema. The API returns 400. What is the correct resolution?

-   A. Citations and structured output via `output_config.format` are mutually exclusive; the design must choose — emit citations and parse the response in the application, or drop citations and use the schema.
-   B. Citations require the document blocks to be in the system prompt, where `output_config.format` does not apply.
-   C. The JSON schema must declare a `citations` property for the two features to coexist.
-   D. Citations are available only on `document` blocks sourced from the Files API, and these are inline.

**E9.8** A nightly job re-summarises 4,000 runbooks through the Message Batches API on Sonnet 5.5. Each runbook averages 3,200 input tokens and 400 output tokens. There is no shared cached prefix. What does one night cost?

-   A. \$12.80
-   B. \$16.00
-   C. \$41.60
-   D. \$20.80

**E9.9** A platform team uploads each department’s wiki export to the Files API and hands the resulting `file_id` to that department’s assistant, treating the opaque identifier as the access control. What is the flaw?

-   A. Files expire after at most 90 days, so the identifiers will eventually stop resolving and access will fail open.
-   B. Files are scoped to the workspace, not to a user or a session: any API key with access to that workspace can read any file in it, so the `file_id` is not a secret and isolation must come from one workspace per department.
-   C. The Files API requires the `files-api-2025-04-14` beta header, which the assistants are not sending.
-   D. Uploaded files are never downloadable, so departments cannot verify what they were given.

**E9.10** Runbooks go stale faster than they are retired. The assistant confidently walks a new hire through a decommissioned failover procedure, citing it correctly. What is the most direct fix?

-   A. Raise `output_config.effort` to `max` so the model reasons harder about whether a procedure is current.
-   B. Add a system-prompt line stating that the model’s knowledge cutoff is June 2026 and that anything newer may be missing.
-   C. Carry each document’s last-reviewed date into the context alongside its text, instruct the model to surface it, and exclude documents past their review date at retrieval time.
-   D. Move to Opus 5.5, whose greater capability reduces hallucination on procedural content.

**E9.11** A 150,000-token corpus is cached on Sonnet 5.5. Traffic is 12 requests per hour, evenly spaced five minutes apart — so with the 5-minute TTL every request arrives at the expiry boundary and pays a write. Counting only the corpus tokens, what does one steady-state hour cost under each TTL?

-   A. \$3.60 with the 5-minute TTL; \$0.77 with the 1-hour TTL.
-   B. \$4.50 with the 5-minute TTL; \$0.77 with the 1-hour TTL.
-   C. \$4.50 with the 5-minute TTL; \$0.60 with the 1-hour TTL.
-   D. \$4.50 with the 5-minute TTL; \$0.93 with the 1-hour TTL.

**E9.12** Cache hit rate collapsed after a deploy and nobody knows which layer changed. Which **TWO** steps use the documented cache diagnostics correctly? **(Select TWO)**

-   A. Send `diagnostics.previous_message_id` on the follow-up request and read `diagnostics.cache_miss_reason` on the response.
-   B. Read `usage.cache_miss_reason`, which is present on every response whether or not diagnostics were requested.
-   C. A `cache_miss_reason` of `tools_changed` points at an edited tool definition, which invalidates everything below the tools segment.
-   D. A `cache_miss_reason` of `model_changed` can be ruled out, because changing `output_config.effort` is not a model change and does not restart the cache.
-   E. Set `diagnostics.cache_debug: true` to have the API return the cached prefix it matched against.

**E9.13** An API gateway retries Messages API calls on 529 with an identical payload. The audit log begins showing duplicate answers against single user questions. What is the correct fix?

-   A. The Messages API has no idempotency key, so a retried request is simply a new request; deduplication must happen in the caller, for example by keying the audit write on a client-generated request identifier carried through the retry.
-   B. Set `stream: false` on retries so the gateway can detect duplicate completions.
-   C. Supply the Batches API `custom_id` on the Messages API call so the service deduplicates.
-   D. Pin `output_config.effort` so responses are deterministic and duplicates are harmless.

**E9.14** A request to a 1M-context model carries a 940,000-token prompt and sets `max_tokens: 128000`. What happens?

-   A. It succeeds: 128,000 is the documented maximum output and is budgeted separately from the context window.
-   B. It succeeds, but generation stops at 60,000 tokens with `stop_reason: "max_tokens"`.
-   C. It fails: 940,000 exceeds the per-request input limit of 900,000 tokens.
-   D. It fails: input plus `max_tokens` must fit inside the 1M context window, which leaves room for roughly 60,000 output tokens here.

**E9.15** A team A/B tests `output_config.effort: low` against `high` by alternating the setting request by request against the same cached 200,000-token corpus. Hit rate is near zero. Why?

-   A. `effort` must be set inside the `thinking` block, and setting it at the top level silently disables caching.
-   B. Alternating effort does not affect the cache, but it does double output tokens, which is what the cost graph is actually showing.
-   C. Changing `output_config.effort` between requests restarts the prompt cache, so each alternation pays a write; the arms should be run as separate cohorts rather than interleaved.
-   D. `low` effort disables prompt caching entirely.

**E9.16** Production pins `claude-sonnet-5-5`. The team believes this floats to the newest Sonnet release. What is the correct understanding?

-   A. Dateless identifiers are aliases and do float to the newest snapshot, so no action is needed.
-   B. On Claude 4.6 and later a dateless identifier is a fixed snapshot, not a floating alias; moving to a new model is an explicit change, and deprecation of a snapshot carries at least 60 days’ notice.
-   C. Aliases exist but resolve only within a major version, so the pin floats across 5.x but not into 6.x.
-   D. The model identifier is ignored whenever a matching cached prefix is present.

**E9.17** Capacity planning for a Monday-morning onboarding surge. Someone proposes buying Priority Tier capacity. What should the team do?

-   A. Priority Tier is closed to new purchase and covers no current model, so it is not available; smooth the surge with the Batches API for anything that can run asynchronously, and with prompt caching plus retry-with-backoff on the interactive path.
-   B. Purchase Priority Tier per workspace and attach it to the onboarding workspace only.
-   C. Priority Tier is granted automatically above an organisation spend threshold, so confirm the threshold.
-   D. Priority Tier applies automatically to requests that hit a warm prompt cache.

**E9.18** Which **THREE** statements are true of the Message Batches API as used for the nightly runbook summarisation job? **(Select THREE)**

-   A. `stream: true` is accepted and streams each result as it completes.
-   B. Results are returned in arbitrary order, and `custom_id` is the only reliable key for joining a result back to its input.
-   C. Batch requests bypass the input-tokens-per-minute rate limit entirely.
-   D. The 50% batch discount stacks with prompt caching.
-   E. A batch expires 24 hours after it is created.
-   F. `max_tokens: 0` may be used to price a request without generating output.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E9.19** Every request to a long-context runbook service carries 140,000 uncached input tokens and produces 2,000 output tokens. Compare Haiku 5.5 (base \$0.10 / \$0.50, with its long-context tier) against Sonnet 5.5 (\$2 / \$10) for a single request.

-   A. Haiku \$0.015, Sonnet \$0.30 — Sonnet costs about 20 times as much.
-   B. Haiku \$0.075, Sonnet \$0.06 — Sonnet is now the cheaper option.
-   C. Haiku \$0.375, Sonnet \$0.30 — the surcharge makes Sonnet cheaper.
-   D. Haiku \$0.075, Sonnet \$0.30 — Sonnet costs about 4 times as much even after Haiku’s 5× long-context surcharge.

**E9.20** A new team is building a grounded wiki assistant and has no eval set yet. What is the documented starting point?

-   A. Haiku 5.5, the cheapest model, escalating only on observed failures.
-   B. Fable 5.1, the most capable model, stepping down once quality has been measured.
-   C. Opus 5.5, the documented recommended default, then measure against an eval set and step down to Sonnet 5.5 or Haiku 5.5 wherever quality holds.
-   D. Sonnet 5.5, because its price sits in the middle of the range and hedges both directions.

**E9.21** A 180,000-token corpus is cached on Sonnet 5.5 with the 1-hour TTL. At 10:00 an operator changes the service-wide default from `output_config.effort: high` to `medium`. What is the one-off cost to the corpus cache, and what else is true?

-   A. \$0.45, and nothing else about the deployment changes.
-   B. \$0.72 — the cache restarts and the prefix is re-written at the 1-hour write multiplier; and since Sonnet 5.5’s documented default effort is `high`, this is a deliberate step down rather than a return to the default.
-   C. \$0.36 — the write is billed at 1.25×, and `medium` is Sonnet 5.5’s default so the cache is unaffected.
-   D. \$0.00 — effort is an output-side control and does not touch the prompt cache.

**E9.22** A team runs every wiki lookup on Fable 5.1 (\$10 / \$50) on the grounds that “accuracy matters most”. What is the strongest objection?

-   A. The design commits to the most expensive model before any eval exists; the documented default is Opus 5.5, and the correct move is to build an eval set of retrieval-grounded questions and step down until quality measurably degrades.
-   B. Fable 5.1 does not support prompt caching, so a large corpus cannot be cached behind a breakpoint.
-   C. Fable 5.1 has a smaller context window than Sonnet 5.5, so the corpus will not fit.
-   D. Fable 5.1 has an earlier knowledge cutoff, so it knows less about the company’s stack.

**E9.23** Which **TWO** changes reduce cost on a grounded knowledge assistant without changing the model? **(Select TWO)**

-   A. Lower `temperature` so the model generates shorter answers.
-   B. Set `max_tokens: 0` on requests that only need a retrieval lookup.
-   C. Move the stable corpus behind a cache breakpoint and keep the per-user retrieval after it.
-   D. Prefill the assistant turn with the expected answer prefix so generation is shorter.
-   E. Route everything that does not need an interactive answer through the Message Batches API, whose 50% discount stacks with caching.

**E9.24** The same 200,000-token corpus is held in a prompt cache and read once. Which model pays the least for that single read, and how much?

-   A. Sonnet 5.5 at \$0.020 — its 0.05× read multiplier beats Haiku’s 0.1×.
-   B. Fable 5.1 at \$0.050 — its 0.025× read multiplier is the lowest of any model.
-   C. Haiku 5.5 at \$0.002 — the 0.1× multiplier applied to the lowest base price.
-   D. Haiku 5.5 at \$0.010 — 0.1× of the base price, then the 5× long-context surcharge, because cache reads count toward the 100,000-token threshold.

**E9.25** A new hire asks the assistant about a travel policy that changed in September 2026. What is the correct design response?

-   A. Route policy questions to Opus 5.5, whose knowledge cutoff is later than the other models’.
-   B. All current models share a June 2026 reliable knowledge cutoff, so anything later must come from retrieval; the system prompt should additionally instruct the model to answer policy questions only from retrieved material.
-   C. Raise `output_config.effort` to `max` so the model recalls the September revision.
-   D. Move to the 1M context window so more of the policy history fits in a single request.

**E9.26** The snapshot a service depends on is announced for deprecation. What is the minimum planning window, and what does the team owe the migration?

-   A. 30 days; pin to a dateless alias so the upgrade happens automatically at the cutoff.
-   B. 90 days; after the date, requests fall back to the nearest live snapshot.
-   C. At least 60 days’ notice is given; because dateless 4.6-and-later identifiers are fixed snapshots rather than aliases, the migration is an explicit code change, and the eval suite must be re-run against the target model before cutover.
-   D. There is no minimum notice; snapshots are withdrawn as capacity is reclaimed.

**E9.27** A router sends questions under 15 words to Haiku 5.5 and longer questions to Opus 5.5. Costs are higher than modelled and quality is uneven. What is wrong?

-   A. Question length does not predict task difficulty, and the rule ignores the input side entirely: a short question asked over a 150,000-token retrieval pushes Haiku 5.5 past its 100,000-token threshold into the 5× surcharge. Route on measured difficulty and on total input size.
-   B. Haiku 5.5 cannot accept more than 100,000 input tokens, so the long retrievals are being rejected.
-   C. Routing decisions must themselves be made by a model; a word-count heuristic cannot be evaluated.
-   D. Opus 5.5 defaults to `medium` effort while Haiku 5.5 defaults to `high`, so the router inverts the intended quality ordering.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E9.28** An onboarding agent built on the Agent SDK sets `max_turns: 6`. What does this bound?

-   A. The total number of assistant and user messages exchanged in the run.
-   B. The number of model invocations, including the final text-only answer.
-   C. The number of distinct tools the agent is permitted to call.
-   D. The number of tool-use turns only; a turn that produces a final text answer with no tool call does not count against it.

**E9.29** An agent run sets `max_budget_usd: 10.00`. After its ninth step the run has spent \$9.60. The tenth step issues a request whose response costs \$1.45. What happens?

-   A. The tenth request is rejected before it is sent and the run ends having spent \$9.60.
-   B. The tenth response is truncated so that the run total lands exactly on \$10.00.
-   C. The tenth step completes, the run total reaches \$11.05, and the run then stops — the budget is checked after a response arrives, so it can overshoot by up to the cost of one response.
-   D. The budget is advisory; the run continues until `max_turns` is reached.

**E9.30** An onboarding orchestrator spawns a domain researcher, which spawns a wiki searcher, which spawns a citation checker, which spawns a formatter. The formatter never runs. Why?

-   A. Subagent concurrency defaults to 20, which this chain exceeds.
-   B. Subagent nesting depth defaults to 3, so the fourth level of spawning is not created; the chain has to be flattened or the depth limit raised deliberately.
-   C. Subagents cannot call tools, so the wiki searcher never produces anything for the chain to pass on.
-   D. Each spawned subagent restarts the parent’s prompt cache, and the run exhausts its budget before reaching the formatter.

**E9.31** A long-running runbook agent enables `clear_tool_uses_20250919` with its default settings. When does it fire and what survives?

-   A. It triggers once the context passes roughly 100,000 tokens and keeps the 3 most recent tool-use/tool-result pairs, clearing older ones.
-   B. It triggers at 50% of the context window and keeps the 10 most recent pairs.
-   C. It triggers on every turn and keeps only the single most recent pair.
-   D. It triggers at 100,000 tokens and clears thinking blocks before tool results by default.

**E9.32** Which **TWO** statements about context management on a long-running knowledge agent are correct? **(Select TWO)**

-   A. Context editing rewrites the cached prefix in place, so the prompt cache survives the edit intact.
-   B. When `clear_thinking_20251015` and `clear_tool_uses_20250919` are both enabled, thinking blocks are cleared first.
-   C. `clear_tool_uses_20250919` clears tool *definitions* as well as tool results.
-   D. The memory tool (`memory_20250818`) lets the agent write durable notes outside the context window, so conclusions survive the clearing of the tool results they were drawn from.
-   E. Context editing cannot be combined with prompt caching.

**E9.33** A workflow summarises 140 wiki sections, one subagent per section, with subagent concurrency left at its default. Each subagent takes about 25 seconds. Roughly how long does the fan-out take, and what should be checked first?

-   A. About 25 seconds — all 140 subagents run concurrently by default.
-   B. About 58 minutes — subagents run serially unless concurrency is raised.
-   C. About 7 minutes — concurrency defaults to 20 but each wave is serialised inside the parent.
-   D. About 3 minutes — the default concurrency of 20 gives 7 waves of about 25 seconds; the first thing to check is whether 20 concurrent callers fit inside the organisation’s rate limits.

**E9.34** An agent answers a multi-part onboarding question by issuing a fresh retrieval call for each sub-question, frequently pulling back the same three runbooks. Over 11 turns the context reaches 400,000 tokens and answers begin to contradict earlier ones. Which **TWO** changes address the actual problem? **(Select TWO)**

-   A. Deduplicate inside the retrieval tool, returning only sections not already present in the conversation.
-   B. Raise `max_turns` so the agent has room to reconcile the contradictions itself.
-   C. Set `tool_choice: "any"` so the agent is forced to re-retrieve before every sub-answer.
-   D. Enable `clear_tool_uses_20250919` so older tool results are cleared past the trigger, and give the agent the memory tool so its conclusions survive that clearing.
-   E. Move to Haiku 5.5 so that carrying a 400,000-token context is cheaper.

**E9.35** The onboarding assistant should remember across sessions which runbooks a given new hire has already been walked through. What is the right mechanism?

-   A. Keep the list in the system prompt and rewrite the prompt at the start of each session.
-   B. Rely on the 1M context window to hold the full history of the onboarding.
-   C. Use the memory tool (`memory_20250818`) so the agent reads and writes durable notes in a store outside the context window, keeping the stable corpus cached ahead of it.
-   D. Store the list in the Files API and pass the `file_id` on every session.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E9.36** Where should the user’s question sit relative to the retrieved wiki documents?

-   A. Documents first and the question last; the documentation reports quality improvements of up to 30% from query-last placement in its own tests.
-   B. The question first, so the model knows what it is looking for as it reads.
-   C. The question both before and after the documents, to anchor attention at both ends.
-   D. The question in the system prompt, with only documents in the user turn.

**E9.37** To force every answer to open with a citation marker, a team appends an assistant turn containing the text `[source:`. The API returns 400. What is the correct reading?

-   A. Assistant prefill must be a complete sentence, and a bare bracket is rejected as malformed.
-   B. Assistant prefill returns 400 on Claude 4.6 and later; the required format has to be specified in the instructions — or enforced with structured output, which would in turn rule out citations.
-   C. Prefill is incompatible with prompt caching, and the corpus here is cached.
-   D. Prefill requires `output_config.effort: low`, which this service does not set.

**E9.38** A request is assembled as: a 2,000-token system prompt; tool definitions used with `tool_choice: "auto"`, adding 1,400 tokens of schemas on top of the tool-use system overhead; 24 retrieved chunks of 1,800 tokens each; and a 300-token question. What is the prompt size, and what should sit behind the cache breakpoint?

-   A. 45,786 tokens; cache everything through the retrieved chunks.
-   B. 47,306 tokens; cache the system prompt only.
-   C. 43,200 tokens; the tool-use system overhead is not billed as input.
-   D. 47,186 tokens; cache the system prompt and tool definitions — 3,686 tokens, comfortably above the 512-token minimum — and leave the per-request chunks and question outside the breakpoint.

**E9.39** Which **TWO** measures most directly reduce ungrounded answers in a wiki assistant? **(Select TWO)**

-   A. Instruct the model to be concise.
-   B. Instruct the model to answer only from the supplied documents and to state explicitly when the documents do not contain the answer.
-   C. Raise `max_tokens` so answers are never truncated part-way through a citation.
-   D. Add “do not hallucinate” to the system prompt.
-   E. Enable citations on the document blocks so each claim is tied to a span the application can verify.

**E9.40** A team adds a line reading `Today is {date}` to the system prompt and expects the model to start flagging stale runbooks. It does not. What is the correct diagnosis?

-   A. The date alone gives the model nothing to compare against — each document needs its own last-reviewed date carried into the context — and a date string that changes daily also invalidates the cached prefix at every rollover.
-   B. The date belongs in the final user turn, where it stays outside the cached prefix; that change alone solves the problem.
-   C. The model’s June 2026 knowledge cutoff means it cannot reason about dates after that point.
-   D. The current date should be exposed as a tool the model calls when it needs it.

**E9.41** A prompt assembles 60 retrieved chunks and repeats the question both before and after them, to “anchor” it. Answers drift noticeably toward the first few chunks. What is the diagnosis?

-   A. Repeating the question doubles its token cost, which is the main harm here.
-   B. Sixty chunks exceeds the 20-block cache lookback, so the chunks are never matched.
-   C. The documented ordering is documents first and question last; the leading copy of the question gives the model a frame it applies while reading, and it is that copy that pulls attention toward the earliest chunks. Keep one copy, at the end.
-   D. The chunks are not sorted by relevance descending, so the strongest evidence is buried.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E9.42** To guarantee the assistant always searches before answering, an engineer sets `tool_choice: {"type": "tool", "name": "search_wiki"}`. The API returns 400. What is the correct approach?

-   A. `tool_choice` may be set only when exactly one tool is defined on the request.
-   B. Forced tool choice — both `any` and `tool` — returns 400 on current models; guarantee retrieval in the application by performing the search before the model call and passing the results in, rather than asking the model to choose.
-   C. The named tool must be the first entry in the `tools` array.
-   D. `tool_choice` cannot be combined with prompt caching, which this service uses.

**E9.43** A legacy service on an older model used `tool_choice: "any"`, carrying the 406-token tool-use system overhead. The rewrite targets Sonnet 5.5 with `tool_choice: "auto"` and its 286-token overhead. At 50,000 requests per day, what is the difference?

-   A. 120 tokens per request, 6,000,000 tokens per day, about \$1.20 saved daily.
-   B. 286 tokens per request, 14,300,000 tokens per day, about \$28.60 saved daily.
-   C. 120 tokens per request, 6,000,000 tokens per day, about \$60.00 saved daily.
-   D. 120 tokens per request, 6,000,000 tokens per day, about \$12.00 saved daily.

**E9.44** A wiki MCP server is being migrated to the stateless 2026-07-28 revision. What changes?

-   A. `server/discover` replaces `initialize`, per-request context moves into `_meta`, and the sampling and logging capabilities are deprecated.
-   B. `initialize` is retained but must be re-sent on every request.
-   C. Sampling is retained and becomes the only supported way to pass per-request context.
-   D. A persistent session identifier header becomes mandatory on every call.

**E9.45** A wiki MCP server uses sampling to call back into the client’s model and re-rank search results before returning them. What is wrong with this design?

-   A. Sampling calls are billed to the server operator rather than the client, which hides the cost.
-   B. Sampling cannot return structured output, so the ranking cannot be parsed reliably.
-   C. Sampling is deprecated in the stateless 2026-07-28 revision; ranking belongs in the server’s own logic, or in a separate model call made by the application, not in a callback into the client.
-   D. Sampling requires `tool_choice: "any"`, which now returns 400 on current models.

**E9.46** Which **TWO** statements about prompt caching and tool definitions are correct for a wiki assistant? **(Select TWO)**

-   A. Tool definitions sit at the top of the invalidation hierarchy: changing them invalidates the system-prompt and message caches below them.
-   B. Reordering the entries in the `tools` array has no effect on the cache.
-   C. Adding a tool to support a new wiki space re-writes the entire cached prefix, which is a reason to batch tool changes into scheduled releases rather than shipping them continuously.
-   D. Tool definitions cannot carry a cache breakpoint.
-   E. Tool results are excluded from the cached prefix by design.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E9.47** A retrieval service runs its vector search unscoped across the entire corpus, takes the top 20 chunks, and passes them to the model with a system-prompt instruction to ignore any document whose access list does not include the current user. What is wrong?

-   A. Twenty chunks is more than the model can use well, and the dilution is what degrades answers.
-   B. Documents the user is not entitled to see are being placed into the model’s context at all; enforcement has to happen in the retrieval query, filtering by the caller’s entitlements before candidates are selected, so unauthorised material is never retrieved.
-   C. The access list should itself be cached so that it does not invalidate the prefix on every request.
-   D. The instruction should be repeated in the final user turn, where the model attends to it more reliably.

**E9.48** Why is the instruction “only use documents the user is allowed to see” not an access control?

-   A. Because the system prompt is cached and the instruction may go stale relative to the access lists.
-   B. Because instructions consume tokens that would otherwise be available for retrieved documents.
-   C. Because the model cannot read access-control metadata attached to a document.
-   D. Because it is an instruction rather than an enforcement boundary: the content is already in the context, so any failure to follow the instruction — or any later summarisation of that context — discloses it. Authorisation has to be a property of the query, not of the prompt.

**E9.49** Which **TWO** belong in an access-scoped retrieval design? **(Select TWO)**

-   A. Pass the user’s entitlement list into the system prompt so the model can apply it while reading.
-   B. Resolve the caller’s entitlements server-side from an authenticated session and pass them into the retrieval query as a filter, never accepting a scope asserted by the client.
-   C. Log every retrieved chunk so that unauthorised disclosures can be identified afterwards.
-   D. Keep tenant or clearance partitions in separate Files API workspaces, since files are workspace-scoped and any key with workspace access can read any file in that workspace.
-   E. Hash document identifiers so that an identifier the user is not entitled to cannot be guessed.

**E9.50** A knowledge platform keeps every department’s uploaded exports in a single Files API workspace. What is the correct isolation design?

-   A. The workspace is the isolation boundary: create one workspace per tenant and scope API keys to it, and never accept a `file_id` supplied by an end user — keep the user-to-file mapping server-side.
-   B. Set a short `expires_in_seconds` on every upload so that files cannot be read for long.
-   C. Mark each uploaded file non-downloadable so that cross-department reads are blocked.
-   D. Rely on the 1 TB per-organisation storage limit to force departments into separate accounts.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E9.51** The knowledge-platform team wants every engineer’s Claude Code session in the retrieval-service repository to know the service’s conventions — chunking rules, the entitlement filter contract, and the eval command. Where do those conventions belong?

-   A. Pasted into each session as the first message of the conversation.
-   B. In a skill that an engineer invokes by name when they need it.
-   C. In a `CLAUDE.md` at the repository root, which is loaded as project memory for every session in that project and is version-controlled alongside the code.
-   D. In the user-level settings file, so they apply in every project the engineer opens.

**E9.52** Project settings deny `Bash(curl:*)`. An engineer adds an allow rule for `Bash(curl https://wiki.internal/*)` so that the wiki can be queried during development. What happens?

-   A. The more specific allow rule wins and the wiki calls are permitted.
-   B. Deny takes precedence over allow, and an allow rule cannot carve an exception out of a deny; the deny pattern itself has to be narrowed.
-   C. The rules conflict, so Claude Code prompts the user on each invocation.
-   D. User-level settings override project-level settings, so the allow applies.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E9.53** An eval suite for the onboarding assistant consists of the 200 most frequently asked onboarding questions, scored nightly by an LLM judge against the current wiki. Every question passes. Production complaints continue. What is the central flaw?

-   A. 200 questions is too small a sample to detect regressions reliably.
-   B. LLM judges are unreliable on grounded answers and should be replaced with human scoring.
-   C. Nightly is too infrequent; the suite should run on every deploy.
-   D. The set is drawn only from questions that already work, and it is scored against the same corpus the assistant retrieves from, so it cannot detect the failures that matter here — stale documents, questions with no answer anywhere in the corpus, and answers that cross an access boundary. Add unanswerable cases, known-stale documents, and per-entitlement retrieval cases with fixed expected outcomes.
