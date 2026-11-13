# Answer Key: Exam 1

Each entry gives the correct option, the domain the question belongs to, and the reasoning. Calculation questions show the full arithmetic. Where a distractor is a plausible-looking true statement, the entry says why it does not answer the question asked.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E1.1 — A.** *(Applications and Integration)* The one cache write is billed at the 5-minute write rate for Sonnet 5.5, which is 1.25x the \$2.00/MTok base, or \$2.50/MTok: 40,000 × \$2.50 ÷ 1,000,000 = \$0.10. The 1,199 reads are billed at Sonnet 5.5’s 0.05x read multiplier, or \$0.10/MTok: 1,199 × 40,000 = 47,960,000 tokens, × \$0.10 ÷ 1,000,000 = \$4.796. Total \$4.896, which rounds to \$4.90. B (\$4.96) applies the 1-hour write multiplier of 2x (\$4.00/MTok, giving \$0.16 for the write) although the stem specifies a 5-minute TTL. C (\$9.69) uses the general 0.1x read multiplier instead of the 0.05x that Opus 5.5 and Sonnet 5.5 get. D (\$96.00) is the uncached cost: 1,200 × 40,000 × \$2.00 ÷ 1,000,000.

**E1.2 — C.** *(Applications and Integration)* A cached prefix is everything up to and including the breakpoint, so placing the only breakpoint after the per-tenant style guide makes the tenant’s content part of the cache key. Each tenant therefore gets a private entry and none of the 38,000-token playbook is shared. The fix is a breakpoint immediately after the shared playbook, with the per-tenant breakpoint kept as a second one. A, B and D are all accurate statements about caching, but none of them explains why hit rates collapse *across tenants*: the read multiplier affects price not hit rate, TTL refresh affects longevity not sharing, and the tools array is not changing here.

**E1.3 — B.** *(Applications and Integration)* Visual tokens are ⌈width ÷ 28⌉ × ⌈height ÷ 28⌉. For 1,120 × 1,540: 1,120 ÷ 28 = 40 exactly, and 1,540 ÷ 28 = 55 exactly, so 40 × 55 = 2,200 tokens per page. Across 8 pages that is 2,200 × 8 = 17,600. A (8,800) covers only four pages. C (19,200) comes from using 60 rather than 55 for the vertical patch count. D (492,800) divides the whole pixel area by 28 once per page — (1,120 × 1,540) ÷ 28 = 61,600, then × 8 — which misapplies the formula by a factor of 28.

**E1.4 — D.** *(Applications and Integration)* Batch results are explicitly not guaranteed to come back in request order, so positional joining is unsafe at any batch size; `custom_id`, which must be unique within the batch, is the only reliable join key. A, B and C are all true of the Message Batches API but none of them produces mismatched rows: the job completed, so expiry is irrelevant; caching discounts affect price; and 60,000 requests is comfortably inside the 100,000 limit.

**E1.5 — A.** *(Applications and Integration)* Citations and `output_config.format` are mutually exclusive, and combining them returns a 400. The team must either run a schema-constrained extraction pass and a separate cited pass, or drop one requirement. B, C and D are correct statements about PDFs and citations, but none of them causes a 400 — they describe tokenisation, index conventions and billing respectively.

**E1.6 — A and C.** *(Applications and Integration)* Batch requests reject `stream: true`, the `speed` parameter, and `max_tokens: 0`. B is wrong because structured output is a normal request parameter and is accepted in a batch. D is wrong because `cache_control` works in batch and its discount stacks with the batch discount. E is wrong because 128,000 is the maximum output of current models, not an illegal value. F is wrong because `tool_choice: auto` is the default and is perfectly valid.

**E1.7 — C.** *(Applications and Integration)* When a single request carries more than 20 images, every image must have both dimensions at or below 2,000 pixels; 2,480 × 3,508 violates that on both axes. Downscaling the pages satisfies the rule while keeping all 34 in one request. A is wrong because `max_tokens` governs output and does not change the request payload. B is wrong because caching does not change image validation. D is wrong because effort affects reasoning depth, not image limits. Note that splitting the request into chunks of 20 or fewer images would also clear the error, but the stem requires all 34 pages to stay in one request.

**E1.8 — B.** *(Applications and Integration)* Haiku 5.5’s long-context tier applies when a request’s total input — cache reads and writes included — exceeds 100,000 tokens. Here 94,000 + 11,000 = 105,000, so every category is billed at 5x. Cache read: 94,000 × \$0.05/MTok ÷ 1,000,000 = \$0.0047. Fresh input: 11,000 × \$0.50/MTok ÷ 1,000,000 = \$0.0055. Output: 400 × \$2.50/MTok ÷ 1,000,000 = \$0.0010. Total \$0.0112. A (\$0.0022) ignores the tier and uses base rates throughout. C (\$0.0074) applies the tier to the fresh tokens only and forgets that cache reads both count toward the threshold and are billed at the tiered read rate. D (\$0.0560) multiplies the base-rate total by 25 rather than 5.

**E1.9 — D.** *(Applications and Integration)* There is no idempotency key on the Messages API, so a retry that duplicates work can only be prevented in the application: the gateway must assign its own request identifier, record the outcome, and refuse to re-create downstream records for an identifier it has already settled. A, B and C are true but speak to batch billing, batch joining and rate-limit accounting, none of which prevents a duplicate extraction.

**E1.10 — A.** *(Applications and Integration)* Plain text documents are chunked into sentences automatically and cited with `char_location`, whose `start_char_index` and `end_char_index` are 0-indexed with an exclusive end. B describes PDFs, which produce `page_location` with 1-indexed pages. C describes custom content documents, where the caller supplies the blocks. D names a location type that applies to search results, not to a plain-text document block.

**E1.11 — B.** *(Applications and Integration)* Cache invalidation runs in the hierarchy tools → system → messages, and a change at one level invalidates that level and everything below it. Changing the tools array therefore invalidates all three. A would be correct for a change to `tool_choice` or for adding an image. C would be correct for enabling web search or citations. D is simply false: tool definitions sit at the head of the cached prefix.

**E1.12 — A and B.** *(Applications and Integration)* Current models including Opus 5.5 have a 512-token cache minimum, and Opus 5.5 and Sonnet 5.5 read cached tokens at 0.05x base input rather than the general 0.1x. C is wrong: the maximum is 4 breakpoints, not 8. D is wrong: cache *writes* count toward ITPM, but reads generally do not. E is wrong: 1.25x is the 5-minute write multiplier; the 1-hour multiplier is 2x.

**E1.13 — C.** *(Applications and Integration)* Assistant-message prefill returns a 400 on Claude 4.6 and later, so the old trick of opening the JSON for the model no longer works. Structured output is now first-class through `output_config.format`. A is wrong because adaptive thinking and structured output coexist. B is wrong because `output_format` is the deprecated parameter, not the remedy. D is wrong because `temperature` is itself deprecated on 4.7+ and a non-default value would return its own 400.

**E1.14 — D.** *(Applications and Integration)* Batch halves every price. Cache reads: 19,999 × 30,000 = 599,970,000 tokens at Opus 5.5’s batched read rate of \$0.10/MTok = \$60.00. The single cache write: 30,000 tokens at the batched 5-minute write rate of \$2.50/MTok = \$0.08. Fresh input: 20,000 × 4,000 = 80,000,000 tokens at the batched input rate of \$2.00/MTok = \$160.00. Output: 20,000 × 1,200 = 24,000,000 tokens at the batched output rate of \$10.00/MTok = \$240.00. Total ≈ \$460. A (\$520) uses the general 0.1x read multiplier instead of Opus 5.5’s 0.05x. B (\$920) omits the batch discount entirely. C (\$1,600) ignores caching and bills all 34,000 input tokens per request at the full batched input rate.

**E1.15 — A.** *(Applications and Integration)* Each extraction is independent, so replaying prior results only inflates the input without supplying anything the model needs; whatever consistency the team wants should be written as explicit rules in the cached system prompt, where it is paid for once and read cheaply thereafter. B, C and D are true but describe cache mechanics, context size and output pricing, none of which explains why accuracy fails to improve.

**E1.16 — B.** *(Applications and Integration)* Standard endpoints cap the whole request payload at 32 MB, and a 38 MB base64 document exceeds that before any page or token limit is reached. A is true but applies to images, not document blocks. C is true but 600 pages is a page limit, not a byte limit, and the stem does not say the document is over 600 pages. D is true but the stem does not say the PDF is encrypted.

**E1.17 — A, B and D.** *(Applications and Integration)* Citations must be enabled on all documents in a request or none; `title` and `context` reach the model but cannot be cited; and a document block can carry `cache_control`, even though the citation blocks themselves cannot be cached. C is wrong — `cited_text` sent back in a later turn does *not* count toward input tokens, which is part of the feature’s cost advantage. E is wrong because a scanned PDF with no extractable text is not citable. F is wrong because image citations do not exist.

**E1.18 — C.** *(Applications and Integration)* From Claude 4.6 onward model IDs are dateless, and a dateless ID of that generation is a fixed snapshot rather than a rolling alias, so there is no dated ID to pin and nothing will change underneath the team. A is a true statement about the earlier naming convention but does not address the current one. B is true and reassuring but concerns retirement, not silent change. D is true and irrelevant to versioning.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E1.19 — D.** *(Model Selection and Optimization)* Sonnet 5.5: 2,400,000 input ÷ 1,000,000 × \$2 = \$4.80, plus 300,000 output ÷ 1,000,000 × \$10 = \$3.00, giving \$7.80. Opus 5.5: 2,400,000 ÷ 1,000,000 × \$4 = \$9.60, plus 300,000 ÷ 1,000,000 × \$20 = \$6.00, giving \$15.60. The difference is \$15.60 − \$7.80 = \$7.80. A (\$4.80) is Sonnet’s input cost alone. B (\$6.00) is Opus’s output cost alone. C (\$15.60) is Opus’s total rather than the difference, which is tempting because Opus happens to cost exactly twice Sonnet here.

**E1.20 — A.** *(Model Selection and Optimization)* Reasoning depth on 4.7 and later models is controlled by `output_config.effort`, whose values are `low`, `medium`, `high`, `xhigh` and `max`. Opus 5.5 defaults to `medium`, so `high` is a genuine increase. B is wrong because `thinking` with `budget_tokens` returns a 400 on 4.7+. C is wrong because `temperature` is deprecated and a non-default value returns a 400. D moves effort in the wrong direction; a larger `max_tokens` permits a longer answer but not a deeper one.

**E1.21 — B.** *(Model Selection and Optimization)* The Haiku 5.5 threshold counts every input token in the request, cache reads included, and applies per request. Base rates hold up to and including 100,000 tokens, so the headroom is 100,000 − 72,000 = 28,000 tokens. A (26,000) is the average chunk size quoted in similar scenarios, not the limit. C (72,000) is the taxonomy itself. D (100,000) ignores the cached taxonomy, which is exactly the error the question tests.

**E1.22 — A and B.** *(Model Selection and Optimization)* Fable 5.1 is \$10/\$50 per MTok against Opus 5.5’s \$4/\$20, and its 0.025x cache read multiplier is the lowest among current models. C is wrong: both have 1M-token context windows. D reverses the defaults — Opus 5.5 defaults to `medium` and Fable 5.1 to `high`. E is wrong: forced `any` and `tool` return a 400 on both.

**E1.23 — C.** *(Model Selection and Optimization)* Fable 5.1’s \$10/MTok input is one hundred times Haiku 5.5’s \$0.10/MTok base rate, so serving a 3% minority from the top model means overpaying on 97% of traffic; a cheap classifier with confidence-based escalation captures the hard cases at a fraction of the cost. A, B and D are all true statements about Fable 5.1 — the shared context window, the best-in-class read multiplier, and the `high` default effort — but none of them addresses the cost of the routing decision.

**E1.24 — D.** *(Model Selection and Optimization)* Changing `output_config.effort` between requests restarts the prompt cache, so under strict alternation no request ever reads a live entry and every one pays a write. 600 × 50,000 = 30,000,000 tokens at Sonnet 5.5’s 5-minute write rate of \$2.50/MTok = \$75.00. A (\$3.12) is what the hour would cost with effort held constant: one write at \$0.125 plus 599 reads of 29,950,000 tokens at \$0.10/MTok = \$2.995. C (\$37.50) halves the write volume, as if only the flagged half of the traffic rewrote the cache. B (\$6.00) does not follow from any rate in the price table; it is there only as a plausible-looking figure.

**E1.25 — A.** *(Model Selection and Optimization)* `temperature`, `top_p` and `top_k` are deprecated from Claude 4.7 onward, and sending any non-default value returns a 400 rather than being ignored. B is sensible advice and a true statement, but it is a remedy rather than the explanation the question asks for. C and D are accurate facts about Sonnet 5.5 that have nothing to do with the error.

**E1.26 — A and B.** *(Model Selection and Optimization)* Hoisting the shared playbook above all variable content makes it a stable cached prefix, and a 1-hour TTL keeps it alive across quiet periods at a 2x write for a 0.05x read. Moving the re-processing queue to batch takes 50% off, and stacks with caching. C raises cost by generating more reasoning tokens. D does not change cost at all, since unused `max_tokens` is not billed. E adds a breakpoint inside content that is unique per document, so it can never be reused.

**E1.27 — B.** *(Model Selection and Optimization)* Under the 5-minute TTL the entry expires in each 30-minute gap, so every burst pays one write and eight reads. Write: 60,000 × \$5.00/MTok ÷ 1,000,000 = \$0.30. Reads: 8 × 60,000 = 480,000 tokens × \$0.20/MTok ÷ 1,000,000 = \$0.096. Per burst \$0.396, and across 48 bursts \$19.01. Under the 1-hour TTL the reads keep refreshing one entry, so the day costs a single write plus 431 reads. Write: 60,000 × \$8.00/MTok ÷ 1,000,000 = \$0.48. Reads: 431 × 60,000 = 25,860,000 tokens × \$0.20/MTok ÷ 1,000,000 = \$5.17. Total \$5.65. The 1-hour TTL is cheaper by \$19.01 − \$5.65 = \$13.36. A has the right magnitude but the wrong direction. C understates the gap by about two orders of magnitude. D ignores the write/read asymmetry entirely.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E1.28 — C.** *(Agents and Workflows)* `max_turns` counts tool-use turns only. The final text-only response, which ends the loop, is not charged against the limit. A is the common misreading that gives the agent one fewer working turn than it has. B is wrong because several tool calls issued in one response are one turn, not several. D confuses turns with subagent invocations, which are capped separately by the concurrency and depth settings.

**E1.29 — D.** *(Agents and Workflows)* The budget is checked after a response arrives, because the cost is computed from the usage the API returns with it, so the response that crosses the cap still completes and still counts. Spend therefore runs \$1.84 + \$0.47 = \$2.31, plus the \$0.12 each that the two background subagents spend before they are stopped: \$2.31 + \$0.24 = \$2.55. The loop then ends with subtype `error_max_budget_usd`. A assumes the cap is a hard ceiling. B reports the right intermediate figure with the wrong subtype — the turn limit was never reached. C ignores turn 8 altogether.

**E1.30 — A.** *(Agents and Workflows)* A non-fork subagent’s conversation starts fresh. The only content that crosses from parent to subagent is the Agent tool’s prompt string, so anything the subagent needs — file paths, error text, prior decisions — has to be written into that prompt. B, C and D are all true of subagents, but inheriting a thinking configuration, loading CLAUDE.md and returning only a final message are not why the path could not be resolved.

**E1.31 — A and B.** *(Agents and Workflows)* The five `ResultMessage.subtype` values are `success`, `error_max_turns`, `error_max_budget_usd`, `error_during_execution` and `error_max_structured_output_retries`. C, D, E and F are invented; a rate limit that ends a run surfaces as `error_during_execution`, and context pressure is handled by compaction rather than by a distinct subtype.

**E1.32 — B.** *(Agents and Workflows)* The defaults are three layers of subagents below the main agent and twenty subagents running at once, settable through `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` and `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. A, C and D each get one of the two numbers wrong; note that a depth of 1 is a legal setting that stops subagents spawning their own, but it is not the default.

**E1.33 — C.** *(Agents and Workflows)* `clear_tool_uses_20250919` defaults to a trigger of 100,000 input tokens and keeps the 3 most recent tool uses. A and B each alter one of the two values, and D doubles the trigger. Both values are configurable, but the question asks for the documented defaults.

**E1.34 — A and B.** *(Agents and Workflows)* When the two strategies are combined, `clear_thinking_20251015` must come first in the `edits` array, and the memory tool’s type string is `memory_20250818`. C is wrong: context editing and prompt caching solve different problems and are used together. D is wrong: the default is 3 tool uses, not 10. E is wrong: clearing tool results does not touch the system prompt.

**E1.35 — D.** *(Agents and Workflows)* The default cap of 20 concurrent subagents is what the error message reports, and raising it would only move the bottleneck: 900 independent document reviews are a throughput problem, better served by the Message Batches API or by a workflow that orchestrates the fan-out outside the conversation. A, B and C are all true of subagents and all irrelevant to the stall: background execution, budget accounting and the final-message contract do not produce a concurrency error.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E1.36 — A.** *(Prompt and Context Engineering)* Cache reuse requires the most stable content first and the most variable content last, with breakpoints at each boundary where reuse changes. Tools and the shared playbook are identical for every tenant, so a breakpoint after the playbook gives all 300 tenants one shared entry; a second breakpoint after the tenant guide gives each tenant a private entry covering both. B, C and D all place variable content ahead of stable content, which destroys reuse from that point onwards: everything after the first variable block is a cache miss.

**E1.37 — B.** *(Prompt and Context Engineering)* A request may declare at most 4 `cache_control` breakpoints, and from each breakpoint the system examines at most 20 block positions, counting the breakpoint itself, when looking for a usable prefix. A halves the lookback, C doubles the breakpoint count, and D halves it.

**E1.38 — C.** *(Prompt and Context Engineering)* Instructions placed 600,000 tokens before the generation point compete with everything in between. Restating the task and the output contract immediately after the documents puts the contract where generation begins, and — because the restatement sits *after* the documents — the long document prefix stays byte-identical and keeps its cache entry. A does not affect adherence. B spends far more money on a problem of placement rather than capability. D shortens the answer without making it follow the brief.

**E1.39 — D.** *(Prompt and Context Engineering)* Opus 4.6 requires a 4,096-token minimum cacheable prefix while current models require 512, and a prefix under the minimum is processed without caching and without any error — which is exactly the silent failure described. A is a true statement about Opus 4.6’s read multiplier but concerns price, not whether an entry exists. B and C are true constraints that apply equally to both models and so cannot explain a difference between them.

**E1.40 — A and B.** *(Prompt and Context Engineering)* Cache diagnostics work as a pair: you send `diagnostics.previous_message_id` naming the request you expected to match, and the response carries `diagnostics.cache_miss_reason` telling you where the prefix diverged. C names a field that does not exist. D changes reasoning depth, and in fact changing effort restarts the cache, making matters worse. E adds citations, which are unrelated to cache behaviour.

**E1.41 — A.** *(Prompt and Context Engineering)* A cached prefix is matched byte for byte, so removing tool results from the middle of the history changes everything from the edit point on; the next request reads whatever prefix still matches and writes the rest afresh. That one-off write is usually worth paying to shed a large amount of recurring input, but it is a real cost and should be expected. B, C and D are true statements about read pricing, the memory tool and tool-level invalidation, none of which is the consequence of editing the message history.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E1.42 — B.** *(Tools and MCPs)* On current models the tool-use system prompt costs 286 tokens for `auto` and `none`, and 406 tokens for `any` and `tool`. So the change is 286 → 406. A quotes 354, which is Sonnet 5’s figure for `auto`. C reverses the direction. D is wrong because the two settings genuinely differ.

**E1.43 — C.** *(Tools and MCPs)* With `tool_choice: auto` the overhead is 286 tokens per request. 900,000 × 286 = 257,400,000 tokens, which is 257.4 MTok. At Sonnet 5.5’s \$2.00/MTok input price that is 257.4 × \$2.00 = \$514.80. A (\$257.40) reports the token count in millions as if it were dollars. B (\$51.48) applies a \$0.20/MTok rate. D (\$730.80) uses 406 tokens, the figure for forced tool choice: 900,000 × 406 = 365.4 MTok × \$2.00 = \$730.80.

**E1.44 — D.** *(Tools and MCPs)* Forced `tool_choice` of type `any` or `tool` returns a 400 on current models including Opus 5.5; the documented alternatives are `auto` combined with strict tool use, or structured outputs when what you actually need is a guaranteed response shape. A, B and C are all true statements about forced tool choice on the models that still accept it — the token overhead, the absence of a thinking block, and the incompatibility with manual extended thinking — but none of them is why *this* request failed.

**E1.45 — A and B.** *(Tools and MCPs)* The 2026-07-28 revision is stateless: `server/discover` replaces the `initialize` handshake, and per-request `_meta` carries what the handshake used to establish once per connection. C contradicts the revision’s purpose. D is wrong — sampling is deprecated, not mandatory. E is invented.

**E1.46 — A.** *(Tools and MCPs)* Because the revision is stateless, a server cannot assume that two requests from the same client reach the same process, so pagination cursors and anything else established at connection time must travel in the request. Behind a load balancer the failure is intermittent precisely because some requests happen to land on the process that holds the state. B is true and related but describes a different deprecation. C and D are true statements about caching and context cost that have nothing to do with the load-balancer failure.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E1.47 — B.** *(Security and Safety)* Counterparty documents are attacker-controlled input. The defence is structural: fence the document, tell the model in the system prompt that text inside documents is data and never instruction, and — most importantly — do not let the model’s free output be the compliance verdict. A deterministic check over structured extracted fields is what should decide. A improves auditability and is worth doing, but a visible citation does not stop the agent complying with the injected instruction. C raises cost without creating a boundary. D makes the problem worse by promoting untrusted content into the prefix.

**E1.48 — C.** *(Security and Safety)* The proposal would put ten tenants’ confidential house rules into the prompt of every request from every other tenant. That is a data-isolation breach at the point the prompt is assembled, independent of what the model outputs or whether anyone notices. Cache efficiency is never a reason to cross a tenant boundary. A, B and D are all true statements about caching mechanics and billing, and none of them is the objection that matters here.

**E1.49 — D.** *(Security and Safety)* The request body contains the tenant’s documents, so the observability index has become a second, less controlled copy of the document store. It needs the same redaction, retention limits and per-tenant access scoping as the primary store, or the logging must be reduced to metadata. A, B and C are true statements about citations, batch retention and cache keying that do not bear on log exposure.

**E1.50 — A.** *(Security and Safety)* A confidence number the model produces about its own output is not an independent signal and cannot be used as an authorisation control. An irreversible financial write needs either a deterministic validation gate — totals reconciled, vendor matched, duplicate check passed — or a human approval, placed outside anything the model decides. B, C and D are true statements about forced tool choice, subagent tool restriction and where hooks run; C and D even describe useful controls, but neither is the control that a ledger write requires.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E1.51 — B.** *(Claude Code)* Settings precedence runs managed settings, then command-line `--settings`, then `.claude/settings.local.json`, then `.claude/settings.json`, then `~/.claude/settings.json`. Managed settings are highest precisely so that an organisation’s policy cannot be overridden locally, so D loses to B here. A and C sit lower still.

**E1.52 — C.** *(Claude Code)* Compaction replaces older messages with a summary, so an instruction given once in the opening prompt can be lost. CLAUDE.md content is re-injected on every request, which makes it the right home for persistent rules. A delays the problem rather than solving it, and lowering the auto-compact window in fact makes compaction happen sooner, not less often. B does not affect what is in context. D fires on tool calls, which is both unreliable and unrelated to the compaction boundary.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E1.53 — D.** *(Eval, Testing, and Debugging)* Exact string equality is the wrong assertion for generative output: phrasing varies run to run even on a fixed model snapshot, so the suite reports failures that are not regressions and will be ignored within a week. Grading the parsed field values against a schema, field by field, measures what the product actually depends on. A changes the cost of the suite, not its validity. B is good practice and may already be in place — the IDs are dateless snapshots — but pinning does not make free text byte-stable. C affects price and latency, not output text.

------------------------------------------------------------------------

## Scoring by domain

Mark each question right or wrong, then total the column. A domain where you score below 70% is where to spend your next study session.

  Section   Domain                             Questions     Your score   Out of
  --------- ---------------------------------- ------------- ------------ --------
  1         Applications and Integration       E1.1–E1.18                 18
  2         Model Selection and Optimization   E1.19–E1.27                9
  3         Agents and Workflows               E1.28–E1.35                8
  4         Prompt and Context Engineering     E1.36–E1.41                6
  5         Tools and MCPs                     E1.42–E1.46                5
  6         Security and Safety                E1.47–E1.50                4
  7         Claude Code                        E1.51–E1.52                2
  8         Eval, Testing, and Debugging       E1.53                      1
            **Total**                                                     **53**

Thirty-seven out of 53 is about 70%; forty-two is about 79%.
