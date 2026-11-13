# Answer Key: Exam 2

Each entry gives the correct option, the domain the question belongs to, and the reasoning. Calculation questions show the full arithmetic. Where a distractor is a plausible-looking true statement, the entry says why it does not answer the question asked.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E2.1 — B.** *(Applications and Integration)* With the only breakpoint at the end of the system prompt, everything after it — the whole growing transcript — is reprocessed as fresh input on every turn, and that is what scales with turn count. Advancing a second breakpoint through the conversation means each turn reads almost the entire prior transcript from the cache and writes only the newest segment. A changes the output limit, not the input volume. C forces a tool call, which is both unrelated and rejected with a 400 on current models. D misunderstands citations, which attribute source documents and do not shrink the transcript.

**E2.2 — D.** *(Applications and Integration)* Only the 12,000-token system prompt is cached, so on turn *k* the fresh input is the whole transcript built up so far plus the current user message. Each completed turn adds 350 + 450 = 800 tokens, so before turn *k* the transcript holds 800 × (*k* − 1) tokens, and the current user message adds 350. Summing over *k* = 1 to 20: 800 × (0 + 1 + … + 19) = 800 × 190 = 152,000, plus 20 × 350 = 7,000. Total 159,000. A counts only the user messages. B is unrelated to any step of the calculation. C (152,000) is the replayed-history term alone and forgets the 20 current user messages, which is the most common slip here.

**E2.3 — A.** *(Applications and Integration)* Structured output is first-class through `output_config.format` with `type: "json_schema"`, which constrains the response rather than merely requesting a shape. B returns a 400 on Claude 4.6 and later, where prefill is no longer supported. C names the deprecated parameter. D is the old prompt-only approach and offers no guarantee; `temperature` is itself deprecated on 4.7+ and a non-default value returns a 400.

**E2.4 — C.** *(Applications and Integration)* Batch is an asynchronous mode with a 24-hour expiry window and no streaming, so it cannot produce a reply while a customer waits. The discount is real but belongs on work with no user waiting on it, such as overnight transcript summarisation or quality scoring. A, B and D are all true of the Message Batches API and all compatible with the proposal; none of them explains why it cannot serve a live turn.

**E2.5 — A and B.** *(Applications and Integration)* Summarising old turns into a compact state block keeps the facts while discarding the tokens that carried them, and caching the stable prefix with a 1-hour TTL converts a repeated full-price read into a 0.05x–0.1x read across a long session. C is wrong: `max_tokens: 0` is a batch-rejected pre-warming device, not a per-turn cost reduction in interactive use. D is wrong and actively harmful — moving the account profile behind the transcript puts stable content after variable content and destroys reuse. E raises cost.

**E2.6 — B.** *(Applications and Integration)* A sentinel string in free text is produced at the model’s discretion and can be omitted, reworded or emitted inside a quotation. An escalation is a state change, so it should arrive as a tool call or as a field in a schema-constrained response, where the client can branch on it deterministically. A, C and D are true statements about forced tool choice, citations and cache pricing, none of which bears on the reliability of the signal.

**E2.7 — A.** *(Applications and Integration)* Every request is well under 100,000 tokens, so Haiku 5.5’s base rates apply. Input: 4,000,000 × 1,400 = 5,600,000,000 tokens, which is 5,600 MTok at \$0.10 = \$560. Output: 4,000,000 × 180 = 720,000,000 tokens, which is 720 MTok at \$0.50 = \$360. Total \$920. B (\$560) is the input half only. C (\$4,600) applies the 5x long-context tier to everything, although no request approaches 100,000 tokens. D (\$2,360) applies the tiered output rate of \$2.50/MTok while leaving input at base: \$560 + 720 × \$2.50 = \$2,360.

**E2.8 — D.** *(Applications and Integration)* Visual tokens are ⌈width ÷ 28⌉ × ⌈height ÷ 28⌉. 1,456 ÷ 28 = 52 exactly and 896 ÷ 28 = 32 exactly, so 52 × 32 = 1,664. A (1,296) is the figure for a 1,000 × 1,000 image, 36 × 36. B (1,456) is the width restated. C (2,912) is 1,456 × 2 and corresponds to no step of the formula.

**E2.9 — C.** *(Applications and Integration)* Once a single request carries more than 20 images, every one of them must have both dimensions at or below 2,000 pixels — and the count includes images from earlier turns and images nested in tool results, which is what makes this fail mid-conversation rather than on the first attachment. At 2,560 × 1,440 the screenshots breach the width limit. A, B and D are all true limits on images that are not breached here: nothing suggests a single file exceeds 10 MB, nothing suggests the payload exceeds 32 MB, and no GIFs are mentioned.

**E2.10 — B.** *(Applications and Integration)* Invalidation runs tools → system → messages, so a change to the tools array invalidates everything, including the conversation prefix that had been accumulating cache value for fifteen turns. The practical rule is that the tool set should be fixed for the life of a cached conversation; flags that change tools belong at session start. A and C correctly describe the narrower invalidations caused by images and `tool_choice`, but neither is the change made here. D is true and irrelevant.

**E2.11 — A, B and C.** *(Applications and Integration)* Batch results come back in arbitrary order, `custom_id` must be unique within the batch and is the only reliable join key, and results stay downloadable for 29 days after batch creation. D is wrong: the limit is 100,000 requests, not 1,000,000. E is wrong: expired requests are not billed at all. F is wrong: `stream: true` is rejected in a batch request.

**E2.12 — A.** *(Applications and Integration)* There is no idempotency key on the Messages API, so the gateway has to carry its own request identifier, record the outcome against it, and refuse to create a second ticket or deliver a second reply for an identifier it has already settled. B, C and D are true statements about batch joining, rate-limit accounting and forced tool calls, none of which prevents the duplicate.

**E2.13 — D.** *(Applications and Integration)* Per conversation the first turn writes and the other five read. Write: 9,000 tokens at Opus 5.5’s 5-minute write rate of \$5.00/MTok = \$0.045. Reads: 5 × 9,000 = 45,000 tokens at the 0.05x read rate of \$0.20/MTok = \$0.009. Per conversation \$0.054, and across 50,000 conversations \$2,700. A (\$450) counts the reads only: 50,000 × \$0.009. B (\$2,250) counts the writes only: 50,000 × \$0.045. C (\$10,800) is the uncached cost, 50,000 × 6 × 9,000 = 2,700 MTok at \$4.00/MTok, which is what the caching saves.

**E2.14 — C.** *(Applications and Integration)* Assistant-message prefill returns a 400 on Claude 4.6 and later, so the old technique of opening the JSON for the model is gone; the constraint now goes in `output_config.format`. A is true but describes a different incompatibility and no citations are in play. B is true — `output_format` is indeed deprecated — but the code in the stem is not using it, so it is not the cause. D is a real limit that is nowhere near being breached by a triage response.

**E2.15 — B.** *(Applications and Integration)* Cache reads generally do not count toward ITPM, but cache *writes* do. At peak, the share of brand-new conversations rises, and each one writes a fresh prefix, so the ITPM budget is consumed by exactly the requests the hit- rate dashboard is not counting. A, C and D are true statements about read pricing, context size and breakpoint count, and none of them explains a rate-limit breach.

**E2.16 — A and B.** *(Applications and Integration)* Current models including Opus 5.5, Sonnet 5.5 and Haiku 5.5 use a 512-token minimum, and a prefix below it is processed without caching and without any error — a silent behaviour that makes this a common source of mystery misses. C is wrong: Opus 4.6, Opus 4.5 and Haiku 4.5 use 4,096. D is wrong: the minimum applies to the cumulative prefix up to the breakpoint. E is wrong: there is no 400.

**E2.17 — A.** *(Applications and Integration)* Plain-text documents are chunked into sentences automatically and cited with `char_location`, whose indices are 0-indexed with an exclusive end, and `cited_text` does not count toward output tokens — the cost advantage over asking the model to quote sources itself. B describes PDF citations. C describes custom content documents, where the caller supplies the blocks rather than the API generating them. D describes image citations, which do not exist.

**E2.18 — D.** *(Applications and Integration)* From Claude 4.6 onward a dateless model ID is a fixed snapshot rather than a rolling alias, so a service pinned to `claude-sonnet-5-5` received the same weights yesterday and today. The investigation should go to prompt changes, an effort change, a retrieval or knowledge-base change, or a routing change. A, B and C are all true statements about model selection, deprecation notice and knowledge cutoff, and none of them answers whether the model changed.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E2.19 — C.** *(Model Selection and Optimization)* Haiku 5.5 leg: input 850,000 × 2,000 = 1,700,000,000 tokens = 1,700 MTok at \$0.10 = \$170.00; output 850,000 × 250 = 212,500,000 tokens = 212.5 MTok at \$0.50 = \$106.25; subtotal \$276.25. Opus 5.5 leg: input 150,000 × 6,000 = 900,000,000 tokens = 900 MTok at \$4.00 = \$3,600.00; output 150,000 × 900 = 135,000,000 tokens = 135 MTok at \$20.00 = \$2,700.00; subtotal \$6,300.00. Total \$6,576.25. A (\$3,876.25) adds the Haiku subtotal to the Opus input only, omitting Opus output. B (\$6,300.00) is the Opus leg alone and ignores the 850,000 conversations that never escalate. D (\$7,920.00) matches no step of the calculation.

**E2.20 — B.** *(Model Selection and Optimization)* Opus 5.5 and Haiku 5.5 default to `medium`; the other models that support effort, including Sonnet 5.5 and Fable 5.1, default to `high`. A reverses the pairing. C is the belief being corrected. D is false: effort lives in `output_config.effort`, not inside `thinking`, and it does have per-model defaults.

**E2.21 — A and B.** *(Model Selection and Optimization)* The effort scale is `low`, `medium`, `high`, `xhigh`, `max`, and changing effort between requests restarts the prompt cache — which is why an effort-varying router is so expensive. C is wrong: effort sits in `output_config`, not in `thinking`. D is wrong: `thinking` with `budget_tokens` returns a 400 on 4.7 and later. E is wrong: effort can be set per subagent as well as per session.

**E2.22 — A.** *(Model Selection and Optimization)* Total input is 88,000 + 19,000 = 107,000 tokens, above the 100,000 threshold, so Haiku 5.5’s 5x rates apply to the whole request — cache reads included, since they count toward the threshold and are billed at the tiered rate. Cache read: 88,000 × \$0.05/MTok ÷ 1,000,000 = \$0.0044. Fresh input: 19,000 × \$0.50/MTok ÷ 1,000,000 = \$0.0095. Output: 600 × \$2.50/MTok ÷ 1,000,000 = \$0.0015. Total \$0.0154. B (\$0.0031) prices everything at base rates, ignoring the tier. C (\$0.0119) applies the tier to the fresh input and output but prices the cache read at the base \$0.01/MTok, forgetting that the tier lifts the read rate too. D (\$0.0770) multiplies the base-rate total by 25 rather than 5.

**E2.23 — D.** *(Model Selection and Optimization)* Fable 5.1’s \$10/MTok input is a hundred times Haiku 5.5’s \$0.10/MTok, and a short, well-specified classification is the archetypal Haiku task. The disciplined approach is to measure Haiku 5.5 against labelled data first and escalate only the slice where the evals show a real gap. A, B and C are all true statements about Fable 5.1 — the lowest read multiplier, the shared window and output cap, and the `high` default effort — and none of them justifies the routing decision.

**E2.24 — C.** *(Model Selection and Optimization)* Changing effort between requests restarts the prompt cache, so under strict alternation every turn pays a write. Alternating: 10,000 × 30,000 = 300,000,000 tokens = 300 MTok at Sonnet 5.5’s 5-minute write rate of \$2.50/MTok = \$750.00. Constant: 100 writes of 30,000 tokens = 3,000,000 tokens = 3 MTok at \$2.50 = \$7.50, plus 9,900 reads of 30,000 tokens = 297,000,000 tokens = 297 MTok at the 0.05x read rate of \$0.10/MTok = \$29.70, giving \$37.20. The excess is \$750.00 − \$37.20 = \$712.80. A (\$37.20) is the constant-effort cost itself. B (\$750.00) is the alternating cost rather than the excess. D (\$29.70) is the read component of the constant-effort case.

**E2.25 — A and B.** *(Model Selection and Optimization)* Holding effort constant keeps the cache alive across a conversation instead of restarting it on every switch, and moving the nightly scoring job to batch takes 50% off work nobody is waiting on. Neither touches what the assistant says to a customer. C is wrong: a prefix read once a day expires under either TTL, so paying the 2x write multiplier buys nothing. D is wrong: a breakpoint inside per-turn content can never be reused. E is wrong and would return a 400 on current models.

**E2.26 — B.** *(Model Selection and Optimization)* `temperature`, `top_p` and `top_k` are deprecated from Claude 4.7 onward, and a non-default value is rejected with a 400 rather than ignored. Tone and variation are prompt concerns now. A is true but describes a different parameter and does not explain the error. C and D are accurate facts about Sonnet 5.5 with no bearing on it.

**E2.27 — A.** *(Model Selection and Optimization)* Every current model has a reliable knowledge cutoff of June 2026, so a feature shipped in September 2026 is outside what the model can know; the assistant is reconstructing plausible detail. Post-cutoff facts have to be supplied through retrieval or a tool call against the live product catalogue. B, C and D are true statements about tiering, effort defaults and rate-limit accounting, and none of them explains a factual error about a recent release.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E2.28 — D.** *(Agents and Workflows)* Only the `success` subtype carries a `result` field; `error_max_turns`, `error_max_budget_usd`, `error_during_execution` and `error_max_structured_output_retries` do not, so the subtype must be branched on first. A, B and C are all true — cost fields are present on every subtype, `stop_reason` does take those values, and a single-shot query does raise after an error result — but none of them explains why the field is sometimes empty.

**E2.29 — C.** *(Agents and Workflows)* `max_turns` counts tool-use turns only, and the two parallel calls issued in one response are a single turn. The agent therefore spends turn 1 on `lookup_account`, turn 2 on the parallel pair, turn 3 on `create_ticket` — reaching the limit of 3 — and the loop stops before the fourth, text-only turn it would need to answer the customer. The result is `error_max_turns`, with no `result` field. A is the trap: it is true that the final text-only turn is not counted, but that is exactly why the agent never reaches it here. B misreads parallel calls as separate turns. D invents a success path.

**E2.30 — A and B.** *(Agents and Workflows)* A non-fork subagent starts with its own system prompt plus the Agent tool’s prompt string, and it inherits the main session’s extended thinking configuration. C and D are exactly what a subagent does *not* receive — that isolation is the point of delegating. E is wrong: only skills named in the subagent’s `skills` list are preloaded; the rest remain invocable but are not in context.

**E2.31 — B.** *(Agents and Workflows)* The spend check happens after a model response arrives, because the cost is derived from the usage returned with it. The response that crosses the cap therefore completes and counts, and any background subagents still running spend a little more before they stop, so the real total can exceed the configured figure. The cap must be set below the ceiling the business can tolerate. A, C and D are all true statements about how the budget is scoped, what it counts and how `/clear` resets it, but none of them is the risk of setting the cap with no headroom.

**E2.32 — A.** *(Agents and Workflows)* `clear_tool_uses_20250919` is the tool-result clearing strategy, and its documented defaults are a trigger of 100,000 input tokens and a keep value of 3 tool uses, which is exactly what the question asks for. B clears thinking blocks, not tool results. C is the memory tool, which persists state rather than pruning context. D changes reasoning depth and does nothing to the transcript.

**E2.33 — A and B.** *(Agents and Workflows)* When the two strategies appear together, `clear_thinking_20251015` must be listed first in the `edits` array, and tool-use clearing defaults to keeping the 3 most recent tool uses. C is wrong: combining them is supported and is the reason the ordering rule exists. D is wrong: the default trigger is 100,000 input tokens, not 50,000. E is wrong: tool definitions are untouched by either strategy.

**E2.34 — D.** *(Agents and Workflows)* Twenty concurrent subagents is the default, and the error quoted is the one that limit produces. Raising it only moves the bottleneck — a backlog burst is throughput work, better handled by a queue with bounded workers or by the Message Batches API than by one agent per ticket. A, B and C are all true of subagents — background by default, spend counted against the budget, depth capped at 3 — and none of them produces a concurrency error.

**E2.35 — C.** *(Agents and Workflows)* Restating preferences in the reply pays output-token prices, which are five times input prices, on every single turn; and because the restatement lives in the transcript, compaction eventually summarises it away anyway. Durable facts belong outside the context — in the memory tool or the account record — and should be injected into the cached prefix, where they are paid for once and read cheaply. A and B are true statements about compaction and subagents, and A even hints at the mechanism, but neither states the defect or the fix. D is unrelated.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E2.36 — B.** *(Prompt and Context Engineering)* Caching rewards the most stable content first and the most variable last, with breakpoints at the boundaries where reuse changes. Tool definitions and the system prompt are identical across every customer, so a breakpoint after the system prompt gives one shared entry; the account profile is stable for one customer across many sessions, so a second breakpoint there gives a per-customer entry; the transcript, which changes every turn, comes last. A, C and D all place variable content ahead of stable content, which destroys reuse from that point onwards: everything after the first variable block is a cache miss.

**E2.37 — A.** *(Prompt and Context Engineering)* A request may declare at most four `cache_control` breakpoints, and from each one the system examines at most 20 block positions, counting the breakpoint itself, when searching for a usable prefix. That bound matters for a rolling breakpoint, because a conversation that adds several blocks per turn can move the target beyond the window. B inflates the breakpoint count and halves the window, C makes the window unlimited, and D halves the breakpoint count.

**E2.38 — A, B and C.** *(Prompt and Context Engineering)* Invalidation runs tools → system → messages; a `tool_choice` change invalidates the messages level only; and reading a 5-minute entry refreshes its TTL, so an entry used at least once every five minutes persists. D is wrong: adding an image invalidates messages only, not tools. E is wrong: reads are cheap, at 0.025x to 0.1x depending on the model, but never free. F is wrong: 1.25x is the 5-minute write multiplier; the 1-hour multiplier is 2x.

**E2.39 — D.** *(Prompt and Context Engineering)* By turn 60 the opening system prompt sits tens of thousands of tokens behind the generation point, competing with everything since. Restating the escalation contract as a short, stable block near the end of the prompt puts the rule where the decision is made, while the long policy stays in the cached prefix so the restatement costs almost nothing. A spends far more on a placement problem. B lengthens the answer without improving adherence. C attributes sources and does nothing for policy adherence.

**E2.40 — C.** *(Prompt and Context Engineering)* The minimum cacheable prefix on Sonnet 5.5 is 512 tokens, and a prefix below it is simply processed without caching, with no error returned — which is why the block silently never hits. Small stable blocks should be merged into a larger cached prefix rather than given breakpoints of their own. A, B and D are all true statements about read pricing, breakpoint count and the 1-hour write multiplier, and none of them explains a silent miss on a 300-token block.

**E2.41 — B.** *(Prompt and Context Engineering)* Cache diagnostics work as a pair: the request carries `diagnostics.previous_message_id` naming the request whose prefix it expected to match, and the response carries `diagnostics.cache_miss_reason` identifying where the two diverged. That turns an invisible regression into a specific block. A names a field that does not exist. C changes reasoning depth, and changing effort in fact restarts the cache, which would make the problem worse. D is unrelated to cache behaviour.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E2.42 — A.** *(Tools and MCPs)* Forced `tool_choice` of type `any` or `tool` returns a 400 on current models including Sonnet 5.5. The documented alternatives are `auto` with strict tool use, or — when what is really wanted is a guaranteed response shape rather than a tool call — structured outputs through `output_config.format`. B and C are true of forced tool choice on the models that still accept it, describing its token overhead and the absence of a thinking block. D correctly describes the cache effect of a `tool_choice` change. None of the three causes a 400 here.

**E2.43 — D.** *(Tools and MCPs)* With `tool_choice: auto` the tool-use system prompt costs 286 tokens per request on current models. 12,000,000 × 286 = 3,432,000,000 tokens, which is 3,432 MTok, at Haiku 5.5’s base input price of \$0.10/MTok = \$343.20. A (\$34.32) is off by a factor of ten. B (\$487.20) uses 406 tokens, the figure for forced tool choice: 12,000,000 × 406 = 4,872 MTok × \$0.10. C (\$1,716.00) applies the 5x long-context rate of \$0.50/MTok, although the stem states that every request is well under 100,000 tokens.

**E2.44 — A and B.** *(Tools and MCPs)* The 2026-07-28 revision is stateless: `server/discover` replaces the `initialize` handshake, and sampling and logging are deprecated. C contradicts the revision’s whole purpose — statelessness exists so that requests can land on any process. D is invented. E inverts the change: `_meta` is sent per request precisely because there is no longer a per-connection handshake to carry it.

**E2.45 — C.** *(Tools and MCPs)* Two things are wrong and both are worth saying: tool search exists to defer MCP tool schemas and load them on demand rather than putting all 180 in every request, and a support assistant should in any case be scoped to the handful of CRM operations it actually needs, so that the permission surface matches the job. A, B and D are true statements about caching tool results, cache invalidation and the MCP revision, none of which addresses the context consumed by the schemas.

**E2.46 — B.** *(Tools and MCPs)* Per request the tool block costs 180 × 140 = 25,200 tokens plus 286 tokens of tool-use system prompt, for 25,486 tokens. Across the month: 2,000,000 × 25,486 = 50,972,000,000 tokens, which is 50,972 MTok, at Sonnet 5.5’s \$2.00/MTok input price = \$101,944. A (\$50,972) reports the token count in millions as if it were dollars, which is the same thing as applying a \$1.00/MTok rate. C (\$1,144) omits the per-request multiplication entirely. D (\$203,888) applies the \$4.00/MTok Opus 5.5 rate rather than Sonnet 5.5’s.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E2.47 — A.** *(Security and Safety)* Everything the customer types is attacker-controlled input, and no amount of prompting makes a model a reliable authorisation boundary. A refund must pass a deterministic check outside the model — entitlement, amount ceiling, order state, and a human approval above a threshold — and the system prompt should additionally state that instructions appearing in conversation content are data, never commands. B, C and D are true statements about forced tool choice, structured outputs and hooks; D in particular describes a useful enforcement point, but a hook is only as good as the deterministic rule it enforces, which is what A states.

**E2.48 — D.** *(Security and Safety)* The warehouse has become a second, less controlled copy of the customer record, holding the same PII with none of the retention limits, redaction or access scoping applied to the original. Either the transcripts must inherit those controls or the pipeline must write redacted text and metadata only. A, B and C are true statements about batch retention, citation billing and cache keying, and none of them bears on log exposure.

**E2.49 — C.** *(Security and Safety)* Few-shot examples drawn from real conversations put one customer’s data into every other customer’s prompt, which is a disclosure at the moment the prompt is assembled — regardless of whether the model ever repeats it. Examples must be synthetic or fully redacted, and cache efficiency is never a reason to cross a customer boundary. A, B and D are all true statements about caching mechanics and billing, and none of them is the objection that matters.

**E2.50 — B.** *(Security and Safety)* The customer-visible promise and the side effect that fulfils it are produced by the same non-deterministic step, so whenever the model writes the sentence but skips the tool call, a customer waits for a human who was never summoned. The handoff must be created by the application from a structured escalation signal, with the message to the customer sent only once the ticket exists. A, C and D are true statements about subagents and the Messages API; C even names a relevant mechanism, but restricting tools does not make a tool call happen.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E2.51 — A.** *(Claude Code)* Settings precedence runs managed settings, then command-line `--settings`, then `.claude/settings.local.json`, then `.claude/settings.json`, then `~/.claude/settings.json`. Managed settings sit at the top exactly so that an organisation’s policy cannot be overridden locally, which is why B loses despite being the more specific file. C places the user file above the project files, inverting the order. D is wrong: the precedence is a resolution order per key, not a merge in load order.

**E2.52 — D.** *(Claude Code)* Listing `tools` on the subagent definition means the omitted tools are not in its session at all — there is no prompt to approve and no error to handle, because Write, Edit and Bash simply do not exist for that agent. A applies a mode to the whole session rather than to one subagent, and affects more than this agent. B tries to undo damage after it is done, which is not a control. C caps work, not capability.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E2.53 — C.** *(Eval, Testing, and Debugging)* An eval whose labels came from the system under test measures self-consistency, not accuracy, so a high score is guaranteed and meaningless; and a year-old resolved queue has drifted from the traffic the service now sees. The fix is independent labels, by humans or by a genuinely separate process, over a fresh sample that matches the current mix. A changes the eval’s cost, not its validity. B is sound practice but makes a wrong measurement reproducible rather than correct. D speeds up a measurement that is not measuring the right thing.

------------------------------------------------------------------------

## Scoring by domain

Mark each question right or wrong, then total the column. A domain where you score below 70% is where to spend your next study session.

  Section   Domain                             Questions     Your score   Out of
  --------- ---------------------------------- ------------- ------------ --------
  1         Applications and Integration       E2.1–E2.18                 18
  2         Model Selection and Optimization   E2.19–E2.27                9
  3         Agents and Workflows               E2.28–E2.35                8
  4         Prompt and Context Engineering     E2.36–E2.41                6
  5         Tools and MCPs                     E2.42–E2.46                5
  6         Security and Safety                E2.47–E2.50                4
  7         Claude Code                        E2.51–E2.52                2
  8         Eval, Testing, and Debugging       E2.53                      1
            **Total**                                                     **53**

Thirty-seven out of 53 is about 70%; forty-two is about 79%.
