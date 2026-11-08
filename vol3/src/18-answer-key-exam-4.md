# Answer Key: Exam 4

## Section 1 — Applications and Integration

**E4.1 — C.** *(Applications and Integration)* Opus 5.5 bills \$4.00 per MTok of base input and \$20.00 per MTok of output; a 1-hour cache write is 2x (\$8.00) and a cache read is 0.05x (\$0.20). Digest reads: 2,400 × 0.92 = 2,208 × 180,000 = 397.44 MTok × \$0.20 = \$79.49. Digest writes: 192 × 180,000 = 34.56 MTok × \$8.00 = \$276.48. Diffs: 2,400 × 12,000 = 28.8 MTok × \$4.00 = \$115.20. Output: 2,400 × 3,000 = 7.2 MTok × \$20.00 = \$144.00. Total **\$615.17**. A (\$345.60) never pays for a cache write. B (\$511.49) uses the 5-minute write rate of \$5.00 instead of the 1-hour rate. D (\$1,987.20) ignores caching altogether.

**E4.2 — A.** *(Applications and Integration)* Structured output is incompatible with citations and the combination returns 400. The practical workaround is to make provenance part of the schema — a file path and a line range per finding — rather than relying on the citations feature. B names the beta header that belongs to the deprecated `output_format` parameter and has nothing to do with citations. C is false; citations are not model-exclusive. D invents a location for the citations flag.

**E4.3 — B.** *(Applications and Integration)* Current models accept at most 128,000 output tokens, so `max_tokens: 200000` is rejected outright. A rewrite of that size has to be emitted in pieces — per file, or per hunk — which is generally better engineering anyway because each piece can be validated. A confuses the input window with the output cap. C is wrong: the value is rejected, not clamped. D is the trap: the extended-output header that raises `max_tokens` to 300,000 applies to batch requests, not to synchronous ones.

**E4.4 — A.** *(Applications and Integration)* The context window on current models is 1,000,000 tokens and it has to hold the output reservation as well as the input. 1,000,000 − 128,000 − 14,000 = **858,000 tokens** of source. B forgets the system prompt and tools. C reserves only the system prompt and tools. D ignores both reservations.

**E4.5 — B, D.** *(Applications and Integration)* `output_config.format` is first-class on current models and needs no beta header, while the older `output_format` parameter is deprecated and now requires the `structured-outputs-2025-11-13` header or it returns 400. A is false — prefill returns 400 from 4.6 onward. C is false: a refusal returns HTTP 200 with `stop_reason: "refusal"` and the body may not match the schema, because the refusal takes precedence. E is false; strict tool use and structured outputs can appear in the same request.

**E4.6 — D.** *(Applications and Integration)* `temperature`, `top_p` and `top_k` are deprecated from the 4.7 generation onward, and sending any non-default value returns 400. The replacement lever for how hard the model works is `output_config.effort`. A invents a range and a type error. B is false — temperature is not merely ignored, it is rejected. C invents a nesting that does not exist.

**E4.7 — C.** *(Applications and Integration)* On 4.7 and later, `thinking` with `budget_tokens` returns 400; reasoning depth is set through `output_config.effort` with values `low`, `medium`, `high`, `xhigh` or `max`, and effort sits at the top level, not inside `thinking`. A treats the error as a range problem. B invents a `max_tokens` multiple rule. D is false; batch applies the same validation, just asynchronously.

**E4.8 — A.** *(Applications and Integration)* Image tokens are ceil(width/28) × ceil(height/28). ceil(1540/28) = 55 exactly, and ceil(868/28) = 31 exactly, so 55 × 31 = **1,705 tokens**. B simply restates the width. C doubles the correct answer, as if each 28-pixel tile cost two tokens. D uses a 32-pixel tile instead of 28: ceil(1540/32) = 49 and ceil(868/32) = 28, giving 1,372.

**E4.9 — B.** *(Applications and Integration)* There is no hard limit of 20 images; the rule is that once a request carries more than 20, no image dimension may exceed 2,000 pixels. At 2,560 × 1,440 the screenshots breach that, so the agent must downscale them or split the request so that each carries 20 or fewer. A states the limit as absolute. C quotes a resizing threshold from an earlier generation. D invents a format requirement.

**E4.10 — A, C, E.** *(Applications and Integration)* The invalidation hierarchy is tools → system → messages. Adding a tool definition (A) invalidates every level. Changing `tool_choice` (C) leaves tools and system cached but invalidates the message blocks. Changing top-level `output_config.effort` (E) likewise forces reprocessing, because effort is rendered into the prompt. B is the opposite of invalidation — a read refreshes the entry. D is normal operation: new content after the final breakpoint does not touch the cached prefix. F is the condition under which the prefix stays cached.

**E4.11 — D.** *(Applications and Integration)* A cache entry is keyed on an exact prefix, so anything tenant-specific placed first makes every tenant’s prefix unique from the first token and no sharing is possible. Reordering so that the 9,000 shared tokens come first, with a breakpoint after them and the tenant digest below, lets all tenants read one entry. A is false: sharing is governed by prefix identity within an organisation, not by key. B is wrong — the tools level sits above system and is not a storage area for digests. C would consume breakpoints without creating any shared prefix.

**E4.12 — A.** *(Applications and Integration)* The prefix is 0.09 MTok. Uncached it costs 0.09 × \$2.00 = \$0.18 per request. Cached it costs one write of 0.09 × \$2.50 = \$0.225, then 0.09 × \$0.10 = \$0.009 per read. After one request: \$0.225 cached against \$0.18 uncached, so caching is behind. After two: \$0.234 against \$0.36, so caching is already ahead. Breakeven falls at about 1.26 requests, which means **from the second request onward**. B and C treat the write premium as far larger than the 1.25x it is. D is false; the 1-hour TTL changes the write multiplier but not the direction of the result.

**E4.13 — C.** *(Applications and Integration)* `input_tokens` reports only the tokens after the last cache breakpoint — the part that was not eligible for caching. Total input is `cache_read_input_tokens + cache_creation_input_tokens + input_tokens`, and on a service with a 180,000-token cached digest the uncached remainder is a tiny fraction of the whole. A has it backwards. B is false: cache writes are billed, at 1.25x or 2x. D invents a separate meter; all three figures are on the same `usage` object.

**E4.14 — B.** *(Applications and Integration)* Tool selection accuracy degrades once more than roughly 30 to 50 tools are available, and a multi-server surface of this size can consume tens of thousands of tokens of definitions on every request. Tool search is the documented answer: defer most tools with `defer_loading: true`, keep the three to five most used loaded, and let the model discover the rest. A misreads the 10,000-tool ceiling, which 240 is nowhere near. C is false — definitions are cacheable. D is not a thing.

**E4.15 — D.** *(Applications and Integration)* There is no idempotency key on the Messages API, so at-most-once behaviour has to be built in the calling service: record the webhook delivery ID, and skip the model call entirely if that ID has already been handled. A invents a header. B misapplies `custom_id`, which belongs to the Batches API and is unique only within a batch. C invents a deduplication property for the tool runner.

**E4.16 — A.** *(Applications and Integration)* Haiku 5.5 under the long-context threshold bills \$0.10 / \$0.50 per MTok, halved by batch to \$0.05 / \$0.25. Input: 48,000 × 1,400 = 67,200,000 tokens = 67.2 MTok × \$0.05 = \$3.36. Output: 48,000 × 220 = 10,560,000 = 10.56 MTok × \$0.25 = \$2.64. Total **\$6.00**. B omits the batch discount (\$6.72 + \$5.28). C counts input only. D (\$30.00) applies the long-context batch rates of \$0.25 / \$1.25, which do not apply at 1,400-token prompts.

**E4.17 — C, E.** *(Applications and Integration)* `temperature` is deprecated from 4.7 onward and any non-default value — including 0 — returns 400 on Opus 5.5. `thinking` with `budget_tokens` likewise returns 400 on that generation. A is valid: `xhigh` is supported on Opus 5.5. B is valid; structured output is first-class. D is valid and in fact the recommended TTL for long shared prefixes. F is valid — `auto` works on every model; it is `any` and `tool` that are rejected here.

**E4.18 — C.** *(Applications and Integration)* A 429 is retryable, and when the response carries `retry-after` that value is how long to wait. Because the limit is enforced with a token bucket that refills continuously, a tight retry loop simply consumes each newly replenished token and keeps the service pinned at the limit. A throws away recoverable work. B is wrong — `max_tokens` does not count toward OTPM at all, only generated tokens do. D is false; batch has its own rate limits on both HTTP requests and queued requests.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E4.19 — B.** *(Model Selection and Optimization)* Opus 5.5 is the documented recommended default at \$4/\$20 per MTok, and Fable 5.1 at \$10/\$50 is two and a half times its input price and two and a half times its output price. Commit message drafting and lint explanation are short, well-specified tasks that run perfectly well on Haiku 5.5 at a fraction of either. The error is picking one model for a fleet rather than matching model to workload. A, C and D are all simply false: Fable 5.1 works with the Agent SDK, supports tool use, and shares the 1M-token context window.

**E4.20 — A.** *(Model Selection and Optimization)* Opus 5.5 bills \$4.00 per MTok of input and \$20.00 per MTok of output. Input: 9,000 × 24,000 = 216,000,000 tokens = 216 MTok × \$4.00 = \$864. Output: 9,000 × 4,000 = 36,000,000 = 36 MTok × \$20.00 = \$720. Total **\$1,584**. C (\$792) is the Sonnet 5.5 figure, half of the Opus one because Sonnet’s rates are exactly half at both ends. B (\$1,224) prices the input on Opus 5.5 but the output at Sonnet 5.5’s \$10; D (\$1,152) does the reverse, pricing the input at Sonnet 5.5’s \$2 and the output on Opus 5.5.

**E4.21 — D.** *(Model Selection and Optimization)* Effort is a behavioural signal, not a token budget: it buys reasoning depth at the cost of latency and tokens within each response. Rewriting a lint message into a sentence needs none of it, and because changing top-level effort between requests restarts the prompt cache, the fix is a level chosen per workload and then held steady rather than tuned per request. A is false — `max` is available on Haiku 5.5. B is false; effort and extended thinking are independent, and structured outputs work with both. C is the misconception the question targets.

**E4.22 — A, C.** *(Model Selection and Optimization)* The five levels are `low`, `medium`, `high`, `xhigh` and `max`, and the defaults are `medium` on Opus 5.5 and Haiku 5.5 and `high` elsewhere. B is wrong: effort lives in `output_config`, not inside `thinking` — putting it inside `thinking` is the most common mistake when migrating from `budget_tokens`. D is wrong: setting effort explicitly to the model’s default is equivalent to omitting it and does not invalidate the cache. E is wrong; `max_tokens` caps output, effort does not.

**E4.23 — B.** *(Model Selection and Optimization)* Total input is `cache_read_input_tokens + cache_creation_input_tokens + input_tokens` = 71,200 + 24,900 + 6,400 = **102,500 tokens**. Haiku 5.5 is the only current model with tiered input pricing, its threshold is 100,000, the threshold counts cache reads and writes, and once crossed the whole request bills at the higher tier. A gets the total right but excludes cached tokens from the threshold test. C reports only `input_tokens`. D omits the cache writes.

**E4.24 — C.** *(Model Selection and Optimization)* From version 4.6 onward model IDs are dateless, and a dateless ID is a fixed snapshot rather than an alias, so it will one day be deprecated like any other snapshot. Anthropic’s commitment is at least 60 days’ notice. A states the misconception the dateless scheme most often creates. B understates the window. D is false; deprecation notice is not a tier benefit, and Priority Tier is in any case closed to new purchase.

**E4.25 — D.** *(Model Selection and Optimization)* Cache reads do not count toward ITPM on current models; the documented exception is Claude Haiku 3.5, not Haiku 5.5. Cache writes and uncached input do count. Assuming otherwise inflates the apparent token rate by roughly the cache hit ratio, which is exactly the fifteen-fold over-provisioning described. A over-generalises from the Haiku 3.5 exception. B invents an interaction with the long-context tier. C overcorrects by denying the Haiku 3.5 exception.

**E4.26 — A.** *(Model Selection and Optimization)* Only cache writes and uncached input count toward ITPM, so each review charges 6,000 + 2,000 = 8,000 tokens against the limit. 5,000,000 ÷ 8,000 = **625 reviews per minute**. The RPM limit of 5,000 is far looser, so ITPM binds. B quotes the RPM limit. C (39) counts the cache reads too, dividing by 128,000. D (2,500) counts only the uncached input and forgets that cache writes are charged against ITPM as well.

**E4.27 — B, D.** *(Model Selection and Optimization)* Batch results are available when every request completes or after 24 hours, whichever comes first, which rules batch out of any check a developer is waiting on; and the 50% batch discount stacks with prompt caching, which is precisely what makes a nightly repository-wide pass cheap. A is false — batch `params` are validated asynchronously. C is false: `stream` is rejected in batch. E is false; a batch holds up to 100,000 requests or 256 MB.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E4.28 — B.** *(Agents and Workflows)* `bypassPermissions` runs all allowed tools without asking and is documented for CI, containers and other isolated environments where the agent cannot affect systems anyone cares about. On a developer’s working tree, `acceptEdits` auto-approves file edits and common filesystem commands while still gating other `Bash` commands, and `dontAsk` with an explicit allow list gives a fixed, headless tool surface. A is false — both SDKs have it, though the TypeScript SDK additionally requires `allowDangerouslySkipPermissions`. C invents a precondition. D is false; hooks continue to run.

**E4.29 — D.** *(Agents and Workflows)* `dontAsk` never prompts: tools pre-approved by permission rules run, calls that need no approval in `default` mode run, and everything that would otherwise prompt is denied. That is exactly “never prompt, deny by default”. `plan` blocks edits but still prompts through the approval callback. `acceptEdits` auto-approves edits, which is the opposite of deny-by-default. `auto` uses a model classifier to decide, which is not a fixed pre-approved surface.

**E4.30 — C.** *(Agents and Workflows)* `max_turns` counts tool-use turns only, so five of the seven needed turns run and the loop then stops with a `ResultMessage` of subtype `error_max_turns`. The `result` field is present only on `success`, so the caller gets no text. A is wrong on both counts. B names the subtype for an interrupted or cancelled run. D invents a shared counter; turns and budget are enforced independently.

**E4.31 — A.** *(Agents and Workflows)* A `PreToolUse` hook that rejects a call short-circuits it: the tool never executes and Claude receives the rejection as the tool result, so it usually tries a different route or reports that it could not proceed. Hooks run in the application process and consume no context window. B is false — a blocked tool does not end the query. C contradicts the point of `PreToolUse`. D is false; the rejection is delivered to Claude.

**E4.32 — A, C.** *(Agents and Workflows)* `result` holds the final text only on the `success` subtype, so a caller must always check the subtype before reading it; and every subtype carries `total_cost_usd`, `usage`, `num_turns` and `session_id`, which is what makes cost tracking and resumption possible after a failure. B contradicts A. D is false: a single-shot `query()` yields the error result and then raises. E is false — spend can overshoot the cap by the response that crossed it, plus running subagents.

**E4.33 — B.** *(Agents and Workflows)* The defaults bound the tree but do not make it cheap: depth defaults to 3 layers below the main agent and concurrency to 20 at once, so 300 file-level subagents will still run, twenty at a time, each making its own API calls. The controls are `max_budget_usd`, which counts subagent spend and refuses further spawns at the cap, plus explicit `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` and `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` values. A invents a per-turn limit. C is false — subagent spend is included in `total_cost_usd`. D is false; parallelism is one of the main reasons to delegate.

**E4.34 — D.** *(Agents and Workflows)* A tool left out of a subagent’s `tools` list is not present in that subagent’s session at all. There is no prompt and no error: Claude simply works with what it has. That is what makes `tools` a clean way to build a review agent that provably cannot write. A and B both assume the tool exists but is gated, which is how allow and deny rules behave, not how `tools` behaves. C inverts the field’s meaning.

**E4.35 — C.** *(Agents and Workflows)* `SubagentStart` and `SubagentStop` fire when a subagent spawns and completes, and are documented for exactly this — tracking and aggregating parallel task results. `PreToolUse` and `PostToolUse` fire per tool call and would see the Agent call but not the subagent lifecycle cleanly. `UserPromptSubmit` and `Stop` bracket the whole session. `PreCompact` concerns compaction.

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E4.36 — A.** *(Prompt and Context Engineering)* Clearing tool results rewrites the conversation, which invalidates the cached prefix from the point of the clear onward; every clear therefore pays cache-write costs again. With a default configuration on an agent that reads constantly, clears are frequent and each one frees relatively little, so the writes outweigh the savings. `clear_at_least` exists precisely to make each clear worth the invalidation, and `exclude_tools` protects results that must survive. B is false — the two features are designed to work together. C is false; both trigger forms are supported. D invents a constraint.

**E4.37 — C.** *(Prompt and Context Engineering)* The lookback window is 20 block positions per breakpoint, counting the breakpoint itself, and a consecutive run of `tool_use` blocks counts as one position, as does a consecutive run of `tool_result` blocks. Nine turns therefore contribute 9 × 2 = 18 positions, the user block one more (19) and the system block one more (**20**). The prefix is reachable, but only just: one more turn would push the system block out of range and require a second breakpoint. A (10) counts one position per turn plus the system block, ignoring that each turn contributes two runs. B forgets the system block. D counts every individual block — 9 × 6 = 54, plus the user and system blocks — ignoring the run rule entirely.

**E4.38 — B.** *(Prompt and Context Engineering)* The `keep` default for `clear_thinking_20251015` is model-specific: “keep all” on Opus 4.5 and later, Sonnet 4.6 and later, Haiku 5.5 and later, and the Fable and Mythos models, but “keep the last turn only” on earlier models. A service that spans tiers should therefore set `keep` explicitly rather than inherit two different behaviours. A denies the model-specific default. C is false: `"all"` is a valid value. D is false; the strategy applies on current models, and separately those models never invalidate thinking blocks through server-side context management.

**E4.39 — A, D.** *(Prompt and Context Engineering)* The 1-hour TTL keeps the prefix alive through the gaps in a long run, and when TTLs are mixed the longer-lived entries must come before the shorter-lived ones. Keeping top-level `output_config.effort` constant matters because changing it restarts the cache. B is the classic own goal: a volatile git SHA at the top of the system prompt makes every request’s prefix unique. C returns 400 — a deferred tool may not carry `cache_control`. E exceeds the limit of four explicit breakpoints.

**E4.40 — D.** *(Prompt and Context Engineering)* The invalidation hierarchy runs tools → system → messages, so every append to the system prompt invalidates the system level and everything below it. An agent that grows its system prompt once per file read is paying a full cache write on every turn. File content belongs in tool results, which sit in the message level below the cached prefix and which context editing can clear when they age out. A invents a cap. B is false — system prompt tokens are ordinary input. C is false; the system prompt is the most common place to put a breakpoint.

**E4.41 — A.** *(Prompt and Context Engineering)* The memory tool is declared as `memory_20250818`. When context approaches the clearing threshold, Claude is warned and can write what matters to memory files before the related tool results are cleared, which is exactly the behaviour described. B and C are invented version strings. D is the tool-result clearing strategy, which removes context rather than preserving it.

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E4.42 — C.** *(Tools and MCPs)* The 2026-07-28 MCP revision is stateless. `server/discover` replaces the `initialize` handshake, so a server that waits for `initialize` is never called; request-scoped data moves into per-request `_meta`; and sampling and logging are deprecated. Per-connection state has to be re-expressed as something the client sends on each request. A, B and D all try to preserve a session that the revision deliberately removes.

**E4.43 — B.** *(Tools and MCPs)* The Python server class was renamed from `FastMCP` to `MCPServer` in the same revision that made the protocol stateless. A, C and D are plausible-sounding names that do not exist in the SDK.

**E4.44 — A.** *(Tools and MCPs)* With tool search, deferred definitions are excluded from the system-prompt prefix and only discovered tools are appended inline. The prefix therefore carries 180 + (4 × 260) = 180 + 1,040 = **1,220 tokens**, against 61,000 unloaded. The reduction is (61,000 − 1,220) ÷ 61,000 = 98.0%, consistent with the documented “more than 85%” figure for a typical multi-server setup. B has the right token count but misstates the ratio. C (1,040) omits the 180 tokens of the tool search tool itself, which must never be deferred and is therefore always in the prefix. D confuses sending definitions in the `tools` array — which does still happen — with loading them into the prefix, which does not.

**E4.45 — B, E.** *(Tools and MCPs)* Forced tool use (`any` and `tool`) returns 400 on Opus 5.5, Sonnet 5.5, Fable 5.1 and Mythos 5.1, and it cannot be combined with manual extended thinking on any model. A is false: `none` is supported everywhere. C is false — the tool-use system prompt costs 286 tokens for `auto`/`none` and 406 for `any`/`tool`. D is false; changing `tool_choice` invalidates the cached message blocks, though tools and system stay cached.

**E4.46 — D.** *(Tools and MCPs)* `tool_search_tool_regex_20251119` takes case-insensitive Python `re.search()` patterns up to 200 characters; `tool_search_tool_bm25_20251119` takes natural-language queries up to 500 characters. Both search tool names, descriptions, argument names and argument descriptions, and both return five matches by default with `limit` adjustable. A collapses the distinction. B swaps the two length limits. C invents a difference in search coverage.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E4.47 — B.** *(Security and Safety)* A pull request title and description from a fork is attacker-controlled text. It must be delimited and introduced as data rather than placed where it reads as instruction, and the agent’s tool surface should be the minimum the job needs — `dontAsk` with `Read`, `Grep` and `Glob`, say, with any test execution confined to an isolated runner. A is wishful; forges do not sanitise prose for prompt injection. C removes the remaining guardrails. D is not a security control; raising effort does not make a model immune to instructions in its input.

**E4.48 — C.** *(Security and Safety)* The scan modifies and never removes. A tag that only the harness emits is neutralised in place by inserting a backslash after the opening angle bracket; a line beginning `Human:` or `Assistant:` gets a backslash before the colon so it cannot imitate a turn boundary; and references to the permission configuration are deliberately left as written so the parent can see them. A marker line naming the matched patterns is prepended for control-tag and permission-configuration matches, but not for turn markers. A, B and D each describe a deletion, rewrite or block that the scan explicitly does not perform.

**E4.49 — C, D.** *(Security and Safety)* `bypassPermissions` cannot be used when running as root on Unix, and deny rules are evaluated ahead of allow rules with an allow unable to carve an exception out of a deny. A inverts `dontAsk`, which denies anything that would otherwise prompt. B is false — hooks run in the application process and consume no context. E is false; a tool omitted from a subagent’s `tools` list is absent from the session, with no prompt and no error.

**E4.50 — D.** *(Security and Safety)* CLAUDE.md is project memory: its full content is sent with every request, it is prompt-cached, and subagents that do not set `omitClaudeMd` load it too. A credential there is therefore present in every session, every subagent context and every stored transcript, and is likely committed to the repository as well. It must be removed and the value read from the environment or a secret store at the point of use. A is false — CLAUDE.md loads in SDK and CI sessions through setting sources. B misunderstands caching, which stores the content rather than omitting it. C is false; local settings are read by Claude Code and can still end up in a request.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E4.51 — A.** *(Claude Code)* Custom slash commands have been merged into skills, so a workflow of this shape should be authored as a skill, which supports a longer body and supporting files while remaining invocable by name. B describes the previous arrangement. C is wrong: nothing was removed without replacement. D is false; skills and commands load from the project and user directories, not only from managed policy.

**E4.52 — C.** *(Claude Code)* Settings precedence runs managed settings, then command-line arguments, then local project settings, then shared project settings, then user settings. A managed deny therefore cannot be overridden by anything the developer writes locally — and on top of that, deny beats allow regardless of file. A inverts the order. B inverts the relationship between project and local settings. D is false; permission rules are read from local settings, they are simply outranked here.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E4.53 — B.** *(Eval, Testing, and Debugging)* The `usage` field on a `ResultMessage` covers only the main agent loop, which is why the gap widens precisely on runs that delegate. Whole-tree token and cost accounting comes from `modelUsage` in TypeScript and `model_usage` in Python, and in Python `total_cost_usd`, `usage` and `model_usage` are all typed as optional, so a harness must guard for `None` before reading them. A is false — cache reads are billed and counted. C is false: all subtypes carry `usage`. D is false; the aggregate exists, the team is just reading the wrong field.

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

A score of 32–37 out of 53 (60–70%) on this exam is the expected range for a candidate who is ready for the real CCDV-F. Compare your per-domain rows with those from Exam 3 before moving on: a row that is weak in both exams is a gap in knowledge, while a row that is weak in only one is usually a gap in a particular scenario vocabulary rather than in the underlying material.
