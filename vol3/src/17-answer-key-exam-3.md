# Answer Key: Exam 3

## Section 1 — Applications and Integration

**E3.1 — B.** *(Applications and Integration)* Sonnet 5.5 bills \$2.00 per MTok of base input; a 1-hour cache write is 2x (\$4.00) and a read is 0.05x (\$0.10), and the Batches API halves all of it. Cached prefix: 480,000 × 0.95 = 456,000 reads × 3,200 = 1,459.2 MTok at \$0.10 = \$145.92, halved to \$72.96; 24,000 writes × 3,200 = 76.8 MTok at \$4.00 = \$307.20, halved to \$153.60. Unique text: 480,000 × 600 = 288 MTok at \$2.00 = \$576.00, halved to \$288.00. Total \$72.96 + \$153.60 + \$288.00 = **\$514.56**. A (\$364.80) prices every prefix token as a read and never pays for a write; C (\$1,029.12) is the correct cache arithmetic with the 50% batch discount forgotten; D (\$1,824.00) keeps the batch discount but ignores caching entirely.

**E3.2 — B.** *(Applications and Integration)* `temperature`, `top_p` and `top_k` are deprecated from the 4.7 generation onward and any non-default value returns 400 on Sonnet 5.5. The compounding problem is that batch `params` are validated asynchronously, so the submission is accepted and the failure only becomes visible once the batch has ended — a whole processing window lost. A is wrong twice over: model IDs are dateless from 4.6 onward and pinning one would not help here. C invents an advisory-temperature behaviour and a seed parameter that does not exist. D fails for exactly the same reason as the original code, since `top_k` is deprecated alongside `temperature`.

**E3.3 — B.** *(Applications and Integration)* Batch results may be returned in any order; `custom_id` is the only key that joins a result to its request, and it must be unique within the batch. A positional join is therefore silently wrong for whatever fraction of the file happens to be reordered. A is a real recommendation — large result files should be streamed — but streaming does not change ordering. C is false: expired requests do appear in the results file with `result.type` of `expired`. D is false; the batch ID is stable.

**E3.4 — C.** *(Applications and Integration)* Two limits bind a batch: 100,000 requests and 256 MB. At 2.1 KB per request, 100,000 requests is 210,000 KB = 210 MB, comfortably inside 256 MB, so the request count is the binding constraint. 7,400,000 ÷ 100,000 = **74 batches**. A (61) applies only the size limit: 7,400,000 × 2.1 KB = 15,540,000 KB = 15,540 MB, and 15,540 ÷ 256 ≈ 60.7 → 61 — fewer than 74, which is precisely why size is not the binding constraint here. B (37) halves the correct figure. D (148) doubles it.

**E3.5 — B, E.** *(Applications and Integration)* Expired requests are never billed, and because they were never sent to the model they can simply be resubmitted in a fresh batch. A is wrong: `errored` results are not billed at all, not even for input. C is wrong because expired requests do get a line in the results file. D misstates the retention clock, which runs 29 days from `created_at`, not `ended_at`. F is wrong: the 24-hour window is fixed and retrieving the batch does not extend it.

**E3.6 — A.** *(Applications and Integration)* Results remain downloadable for 29 days after `created_at`. 4 March plus 29 days: March has 31 days, so 4 + 29 = 33 → 33 − 31 = **2 April 2026**. B (2026-04-03) is the same arithmetic run from `ended_at`, which is the single most common error here. C counts 25 days. D adds a day to the `ended_at` miscalculation.

**E3.7 — D.** *(Applications and Integration)* `stream: true` is one of the three parameters a batch request rejects outright, alongside `speed` and `max_tokens: 0`. The supported route to progress reporting is to poll the batch for `request_counts` and, once it has ended, stream the `.jsonl` at `results_url` rather than buffering it. A invents a size-dependent rule. B is wrong: the extended-output header raises `max_tokens`, it does not re-enable streaming. C substitutes another rejected parameter.

**E3.8 — C.** *(Applications and Integration)* Haiku 5.5 is the only current model with tiered input pricing, and the 100,000-token threshold counts cache reads and cache writes as well as uncached input. Here 86,000 + 9,000 + 7,400 = 102,400, which is over the threshold, so the entire request — not merely the excess — is billed at the higher tier, and the tier is decided per request. A and B both exclude cached tokens from the threshold, which is the trap. D applies a marginal-rate model that the platform does not use.

**E3.9 — A.** *(Applications and Integration)* Assistant prefill returns 400 from the 4.6 generation onward. Structured output is first-class: declare the shape with `output_config.format` using a `json_schema`. B does not work because a system prompt is not an assistant turn. C names the beta header that applies to the deprecated `output_format` parameter, not to prefill. D would also fail, because forced `tool_choice` returns 400 on Opus 5.5.

**E3.10 — A, D.** *(Applications and Integration)* `custom_id` must match `^[a-zA-Z0-9_-]{1,64}$`. A contains forward slashes, which are outside the character class. D is 72 characters, past the 64-character limit. B, C, E and F all consist only of letters, digits, hyphens and underscores and are within length, so all four are valid — note that a purely numeric ID such as `000912` is perfectly legal.

**E3.11 — C.** *(Applications and Integration)* Batch cache hit rates run 30–98%, and the documented recommendation for a batch with a long shared prefix is the 1-hour TTL, precisely because a nine-hour run leaves gaps far longer than the 5-minute default lifetime. A is wrong: breakpoints do not refresh one another, and the invalidation hierarchy is unaffected. B would multiply submission overhead without addressing the gap between bursts, and the server schedules batches as it pleases. D is false; placement in the message list does not change an entry’s lifetime.

**E3.12 — B.** *(Applications and Integration)* Cache reads do not count toward ITPM on current models — Haiku 3.5 is the lone exception — but cache writes and uncached input both do. Chargeable per request is 2,000 + 1,500 = 3,500 tokens, so 5,000,000 ÷ 3,500 = 1,428.6, i.e. about **1,428 requests per minute**. A (114) counts the cache reads too; C (3,333) counts only `input_tokens` and forgets that writes are charged; D (5,000) is the RPM figure, not an ITPM calculation.

**E3.13 — D.** *(Applications and Integration)* There is no idempotency key on the Messages API or the Batches API, so the client must own deduplication: deterministic `custom_id` values plus a local submission ledger, reconciled against a list of the workspace’s batches before any retry. A invents a header. B is wrong — `custom_id` uniqueness is enforced within a batch, never across batches. C invents a `parent_batch_id` field.

**E3.14 — A.** *(Applications and Integration)* Image tokens are ceil(width/28) × ceil(height/28). ceil(1344/28) = 48 and ceil(896/28) = 32, so 48 × 32 = **1,536 tokens**. B and C are plausible-looking round numbers with no derivation. D doubles the correct answer, as if each 28-pixel tile cost two tokens.

**E3.15 — B, D, F.** *(Applications and Integration)* The Batches API rejects `stream`, `speed` and `max_tokens: 0`. A is valid: `max_tokens` must be at least 1, and 1 satisfies that. C is valid — structured output works in batch. E is not only valid but recommended, since the 1-hour TTL is the documented choice for batches with shared context.

**E3.16 — D.** *(Applications and Integration)* `processing_status: "ended"` means processing has finished, nothing more. A batch can end with any mix of `succeeded`, `errored`, `canceled` and `expired` results, and each line in the `.jsonl` carries its own `result.type`. The pipeline must branch on `request_counts` and per-result type. A is false: results are written before the status flips. B is false; `ended_at` is set when processing ends, regardless of outcome. C invents a second file.

**E3.17 — C.** *(Applications and Integration)* Server tools do work in batch, and batch loops actually run more iterations per turn before pausing. When a result does come back with `stop_reason: "pause_turn"`, the continuation is to submit a follow-up request — batch or synchronous — containing the paused assistant content. A loses the work already done and will likely pause again. B confuses `pause_turn` with `max_tokens`. D is false: all server tools are supported in batch.

**E3.18 — B.** *(Applications and Integration)* Batches may slightly exceed a workspace spend limit because many requests are in flight concurrently when the limit is evaluated. This is documented behaviour, not a billing fault, and the right response is headroom in the limit. A is false — the limit is per workspace. C and D invent accounting rules; the batch discount and cache writes are both part of ordinary spend.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E3.19 — A.** *(Model Selection and Optimization)* Batch halves list prices. Haiku 5.5 under the threshold: \$0.05 in / \$0.25 out. Input 12,000,000 × 900 = 10,800 MTok × \$0.05 = \$540; output 12,000,000 × 120 = 1,440 MTok × \$0.25 = \$360; total \$900. Sonnet 5.5 at batch rates \$1.00 / \$5.00: 10,800 × \$1.00 = \$10,800 plus 1,440 × \$5.00 = \$7,200, total \$18,000. The difference is \$18,000 − \$900 = **\$17,100**. B (\$18,900) adds the two totals instead of subtracting. C (\$8,550) halves the difference a second time. D (\$34,200) doubles it.

**E3.20 — D.** *(Model Selection and Optimization)* The default effort is `medium` on Opus 5.5 and Haiku 5.5 and `high` on the other current models, Sonnet 5.5 included. Two stages that both omit `output_config.effort` are therefore running at different levels, which is exactly the kind of silent asymmetry that makes cost and latency comparisons meaningless. A gets Sonnet wrong; B is false, since every supported model has a default; C invents a dependency on extended thinking.

**E3.21 — A.** *(Model Selection and Optimization)* Effort is rendered into the prompt, so changing `output_config.effort` at the top level between requests restarts the prompt cache. Interleaving two levels in one stream means each level keeps invalidating the other’s entry, which is why the hit rate settles near the share of consecutive same-effort pairs. B is false; low effort does not disable caching. C is wrong — the schema text tokenises identically. D is wrong: top-level effort is honoured, and the per-message form is a separate beta.

**E3.22 — C.** *(Model Selection and Optimization)* Opus 5.5 base input is \$4.00 per MTok and its cache-read multiplier is 0.05x, so reads cost \$0.20 per MTok. 400,000 × 60,000 = 24,000,000,000 tokens = 24,000 MTok × \$0.20 = **\$4,800**. A (\$1,200) applies a 0.0125x rate that exists on no model. B (\$2,400) applies Sonnet 5.5’s \$0.10 read rate. D (\$12,000) applies the generic 0.1x multiplier, forgetting that Opus 5.5 and Sonnet 5.5 read at 0.05x.

**E3.23 — C, E.** *(Model Selection and Optimization)* Haiku 5.5 is the only current model with tiered input pricing, and the 5x multiplier is decided and applied per request. A misstates the threshold, which is 100,000 tokens. B is the central trap: the threshold counts cache reads and writes as well as uncached input. D is false — Haiku 4.5 has flat input pricing.

**E3.24 — B, D.** *(Model Selection and Optimization)* From 4.6 onward model IDs are dateless, and a dateless ID is a fixed snapshot rather than a floating alias; separately, Anthropic commits to at least 60 days’ notice before deprecating a model. A states the opposite of B and is the most common misconception. C is wrong: current models have a 1M-token context window. E is wrong on two counts — Priority Tier is closed to new purchase and has nothing to do with snapshot pinning.

**E3.25 — B.** *(Model Selection and Optimization)* Priority Tier is closed to new purchase and covers none of the current models, so it should never be presented as an option. For offline work the right levers are the Batches API, a 1-hour cache TTL and an ITPM budget that accounts for cache writes counting and cache reads not. A, C and D each present Priority Tier as available in some form, which is the error the question is testing.

**E3.26 — D.** *(Model Selection and Optimization)* Opus 5.5 is the documented recommended default, and Fable 5.1 at \$10/\$50 per MTok is the most expensive model on the platform — roughly 100x Haiku 5.5’s input rate. An eleven-category classification over short text is the clearest case for selecting down the range. A, B and C are all simply false: Fable 5.1 supports batch and prompt caching and shares the 1M-token context window.

**E3.27 — A.** *(Model Selection and Optimization)* Sonnet 5.5 base input is \$2.00 per MTok, so a 5-minute write is 1.25x = \$2.50 and a 1-hour write is 2x = \$4.00. Default lifetime: 96 × 20,000 = 1,920,000 tokens = 1.92 MTok × \$2.50 = \$4.80. 1-hour lifetime: 8 × 20,000 = 160,000 tokens = 0.16 MTok × \$4.00 = \$0.64. The 1-hour option is cheaper by \$4.80 − \$0.64 = **\$4.16**. B inverts the comparison. C assumes the 1.6x write premium cancels a 12x reduction in rewrites, which it plainly does not. D quotes the 1-hour cost rather than the saving.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E3.28 — C.** *(Agents and Workflows)* `max_turns` counts tool-use turns only, so with `max_turns=5` the loop runs five tool-use turns and then stops. The SDK emits a `ResultMessage` with subtype `error_max_turns`, and the `result` field is present only on the `success` subtype. A is wrong on both the subtype and the presence of `result`. B names the subtype used for an interrupted or cancelled run. D wrongly counts the final text-only turn, which is exactly what `max_turns` excludes.

**E3.29 — B.** *(Agents and Workflows)* The budget is compared against spend after a model response arrives, because the cost of that response is only known from the usage the API returns with it. The response that crosses the cap therefore completes and is billed, and any subagents still running add whatever they spend before they are stopped. The documented advice is to leave headroom. A is false: subagent spend does count toward the cap. C is false — the cap is enforced, including by refusing further subagent spawns. D is false; the budget total accumulates across messages in a session until `/clear`.

**E3.30 — D.** *(Agents and Workflows)* `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` defaults to 20, counting every subagent spawned through the Agent tool. Spawns beyond that are refused with `Concurrent subagent limit reached` returned as the Agent tool result, which Claude sees and can retry once capacity frees up. A confuses concurrency with depth. B confuses the concurrency default with the depth default of 3. C is wrong: hitting the concurrency limit does not end the query.

**E3.31 — A.** *(Agents and Workflows)* `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` defaults to 3 layers below the main agent; setting it to 1 allows the main agent to spawn subagents but stops those subagents spawning any of their own. B would describe a configuration where the main agent cannot delegate at all, which is not what the team wants. C caps how many run at once, not how deep nesting goes. D limits each subagent’s tool-use turns and does nothing about delegation.

**E3.32 — B, D.** *(Agents and Workflows)* A non-fork subagent starts with its own system prompt and the prompt string from the Agent tool call, plus project CLAUDE.md when it is loaded through setting sources, plus its tool definitions. A and C name precisely what it does *not* receive: neither the parent’s conversation history and tool results nor the parent’s system prompt. E is wrong because only skills named in `AgentDefinition.skills` are preloaded; the rest stay invocable but unloaded.

**E3.33 — C.** *(Agents and Workflows)* The only content that crosses from parent to a non-fork subagent is the Agent tool’s prompt string. Anything the parent discovered — file paths, error text, decisions — has to be written into that prompt literally. A is wrong in this scenario, since the problem is the missing paths rather than a missing tool. B and D invent mechanisms; CLAUDE.md is static project memory and `memory` selects a memory source, not a channel for parent-resolved values.

**E3.34 — D.** *(Agents and Workflows)* `error_max_structured_output_retries` is the subtype emitted when no schema-valid structured output was produced within the configured retry limit — every attempt failed validation, or a model fallback retracted a completed output with no successful retry. A covers an interrupted run, B the turn cap. C is not a real combination: `result` is populated precisely on `success`.

**E3.35 — B.** *(Agents and Workflows)* `PreCompact` fires before context compaction and receives a `trigger` field of `manual` or `auto`, which is exactly where a full transcript should be archived. `Stop` fires when the agent finishes, too late to capture what compaction discarded. `SubagentStop` fires per subagent. `PostToolUse` fires after each tool returns and would capture the same material piecemeal at far greater cost.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E3.36 — A.** *(Prompt and Context Engineering)* The cache invalidation hierarchy is tools → system → messages, and a change at one level invalidates that level and everything after it. Changing the `tools` array therefore invalidates the entire prefix, which is why mid-run tool additions are so expensive. B is false — tool definitions are cached, they simply sit at the top of the hierarchy. C is wrong; tools do not consume breakpoints. D is wrong, since adding a tool makes the prefix longer, not shorter.

**E3.37 — C.** *(Prompt and Context Engineering)* Each breakpoint looks back at most 20 positions, counting itself, so 70 positions need ceil(70 ÷ 20) = 4 breakpoints. Four is also the maximum number of explicit breakpoints per request, so the prefix is at its structural ceiling and further growth means restructuring rather than adding a fifth. A and B undercount. D treats the lookback as 10 positions.

**E3.38 — D.** *(Prompt and Context Engineering)* The minimum cacheable prompt length on current models is 512 tokens; a 380-token block falls short, so the prompt is simply processed without caching and no error is returned — which is why both usage fields read zero. (On Opus 4.6, Opus 4.5 and Haiku 4.5 the minimum is 4,096.) A is false: the TTL defaults to 5 minutes. B is false — message content is cacheable. C is false; the write is reported on the first request.

**E3.39 — A, D.** *(Prompt and Context Engineering)* When both strategies appear in `edits`, `clear_thinking_20251015` must be listed first. And `clear_tool_uses_20250919` defaults to a trigger of 100,000 input tokens and keeps the 3 most recent tool uses, clearing oldest first. B is wrong: `clear_tool_inputs` defaults to `false`. C inverts `exclude_tools`, which names tools that are *never* cleared. E is wrong — clearing invalidates the cached prefix from the clear point on, which is why `clear_at_least` exists.

**E3.40 — B.** *(Prompt and Context Engineering)* Cache diagnostics are explicitly designed for this: pass `diagnostics.previous_message_id` naming the earlier request and the API compares the two prefixes and reports `diagnostics.cache_miss_reason`. A can show that something changed but never where. C is a misuse of pre-warming, which is rejected in several configurations anyway. D burns all four breakpoints and still only brackets the change.

**E3.41 — C.** *(Prompt and Context Engineering)* A cache entry is keyed on the exact prefix, so a volatile run date at the very top of the system prompt guarantees a fresh prefix every night no matter how stable the taxonomy below it is. Moving the volatile text after the cached block — ideally into the first user message — lets the taxonomy be the shared prefix. A does not help: with a changed prefix there is nothing to hit, whatever the TTL. B makes it worse by caching the volatile line itself. D is false; tools are a separate hierarchy level, not a place to park a taxonomy.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E3.42 — A.** *(Tools and MCPs)* Forced `tool_choice` — both `any` and `tool` — returns 400 on Opus 5.5, Sonnet 5.5, Fable 5.1 and Mythos 5.1. The documented replacements are `auto` with strict tool use for schema-valid inputs, or structured outputs via `output_config.format` when the goal is really a shaped response rather than a side effect. B swaps one rejected form for the other. C is backwards: forced tool use cannot be combined with manual extended thinking at all. D invents a field.

**E3.43 — A.** *(Tools and MCPs)* The overhead difference is 406 − 286 = 120 tokens per request. Over 2,400,000 requests that is 288,000,000 tokens = 288 MTok. Opus 4.8 bills \$5.00 per MTok of input, and batch halves it to \$2.50, so 288 × \$2.50 = **\$720.00**. B (\$1,440.00) forgets the batch discount. C (\$360.00) applies the discount twice. D (\$2,436.00) prices the full 406-token `any` overhead rather than the 120-token difference.

**E3.44 — D.** *(Tools and MCPs)* A tool carrying `defer_loading: true` may not also carry `cache_control`; the combination returns 400. The breakpoint belongs on a non-deferred tool. This is not a limitation in practice, because deferred tools are excluded from the system-prompt prefix anyway and their `tool_reference` blocks are appended inline, so the cached prefix is already preserved. A invents a special rule for the search tool, which in fact must never be deferred. B is false — every tool definition, deferred or not, is sent on every request. C is false; tool definitions can carry breakpoints.

**E3.45 — B, C.** *(Tools and MCPs)* A request may defer at most 10,000 tools, and at least one tool must have `defer_loading: false` or the request returns 400 — the documented practice is to keep the three to five most-used tools loaded. A is wrong: all definitions, deferred included, are sent on every request so the API can search them. D is wrong — tool search is not metered separately; loaded definitions are ordinary input tokens. E inverts the guidance, which recommends tool search from about 10 tools upward.

**E3.46 — B.** *(Tools and MCPs)* The 2026-07-28 MCP revision is stateless: `server/discover` replaces the `initialize` handshake, request-scoped data moves into per-request `_meta`, and sampling and logging are deprecated. A server still implementing `initialize` will simply never be called. (The Python server class was also renamed from `FastMCP` to `MCPServer` in the same move.) A, C and D all describe transport or direction changes that did not happen.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E3.47 — C.** *(Security and Safety)* Batches are scoped to a workspace. They can be accessed by requests made in that workspace, and by users who hold Console permission to view that workspace’s batches. A over-broadens the scope to the organisation. B under-states it — any key in the workspace can retrieve the batch, not only the creating key. D is false; `results_url` is not an unauthenticated public link.

**E3.48 — D.** *(Security and Safety)* Content written by field staff and third parties is untrusted input. Placing it in the system prompt puts it in the one position the model is most inclined to read as instruction, which is why labels start contradicting the taxonomy. It belongs in user content, clearly delimited and introduced as data to be classified — ideally with a constrained output schema behind it. A is false; the system prompt has no separate limit. B is false, though the placement does wreck caching for a different reason. C is a real engineering concern but would produce malformed requests, not wrong labels.

**E3.49 — A, E.** *(Security and Safety)* Request and response data is stored for up to 29 days from batch creation, and a batch can be deleted after processing — an in-progress batch must be cancelled first. B contradicts workspace scoping. C is wrong: a cancelled batch may contain partial results, and anything already processed was billed. D is wrong; expired requests fall under the same 29-day retention as everything else.

**E3.50 — A.** *(Security and Safety)* The direct, structural control is a constrained output: `output_config.format` with the label field declared as a nine-value enum makes values outside the set impossible to emit, and keeping row text in user content stops it reading as instruction. B spends money on reasoning without constraining the output space. C doubles the cost and inherits the same injection. D is brittle keyword filtering that any rephrasing defeats.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E3.51 — B.** *(Claude Code)* Deny rules are evaluated ahead of allow rules and win outright; an allow rule cannot carve an exception out of a deny. To permit read-only `psql`, the deny itself must be narrowed — for example denying the destructive invocations specifically rather than the whole command. A is a red herring; no pattern in the allow list can beat the deny. C is false: allow rules work in project settings. D is false; `Bash` rules match against the command string including arguments.

**E3.52 — C.** *(Claude Code)* CLAUDE.md is project memory and is re-injected into every request, so rules placed there survive compaction, whereas an instruction given once in the first user message lives only in conversation history and can be replaced by a summary. A gives up on a mechanism that exists. B is wrong: skill content loads when the skill is invoked, not on every request. D invents a switch; compaction is automatic when the window fills.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E3.53 — D.** *(Eval, Testing, and Debugging)* Batch `params` are validated asynchronously, so a malformed request shape produces an error only after the whole batch has finished — which is exactly the day-long feedback loop described. The documented practice is to validate each distinct request shape against the synchronous Messages API first, where errors come back immediately. A is wrong on two counts: `max_tokens: 0` is rejected in batch, and pre-warming is rejected in batch requests generally. B invents a reserved `custom_id`. C invents an empty-batch schema check.

------------------------------------------------------------------------

## Scoring

  Domain                             Questions   Your score
  ---------------------------------- ----------- -----------------
  Applications and Integration       18          \_\_\_ / 18
  Model Selection and Optimization   9           \_\_\_ / 9
  Agents and Workflows               8           \_\_\_ / 8
  Prompt and Context Engineering     6           \_\_\_ / 6
  Tools and MCPs                     5           \_\_\_ / 5
  Security and Safety                4           \_\_\_ / 4
  Claude Code                        2           \_\_\_ / 2
  Eval, Testing, and Debugging       1           \_\_\_ / 1
  **Total**                          **53**      **\_\_\_ / 53**

A score of 32–37 out of 53 (60–70%) on this exam is the expected range for a candidate who is ready for the real CCDV-F. Treat anything below 28 as a signal to revisit the domain with the weakest row before attempting Exam 4.
