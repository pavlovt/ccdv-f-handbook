# Exam 4 — Developer Tooling and Code Agents

**53 questions · 120 minutes · closed book.**

Every scenario in this exam is drawn from engineering tooling built on Claude: repository analysis services, automated refactoring agents, CI integrations and code review assistants. Forty-four questions have four options and exactly one correct answer. Nine are multiple-response and are marked **(Select TWO)** or **(Select THREE)**; a multiple-response question scores only when every required option is chosen and no other. Several questions require arithmetic from figures given in the stem — bring a calculator or work on paper, and round money to the cent. No partial credit. Answers and worked explanations are in the answer key at the back of the volume; do not consult it until you have finished.

Assume the Claude API on the current model generation unless a question names a specific model or version.

------------------------------------------------------------------------

## Section 1 — Applications and Integration

**E4.1** A code review service posts a review on every pull request. Each review sends a 180,000-token repository digest that is identical for all PRs in a repository and is cached with a 1-hour breakpoint, plus 12,000 tokens of diff, and produces 3,000 output tokens. The service runs synchronously on Claude Opus 5.5 and handles 2,400 PRs a month at a measured 92% cache hit rate on the digest.

What is the closest monthly cost?

-   A. \$345.60
-   B. \$511.49
-   C. \$615.17
-   D. \$1,987.20

**E4.2** A review assistant returns findings as JSON through `output_config.format`, and the team also enables citations so each finding can point at the source text it came from. Every request now returns 400.

What is wrong, and what should they do?

-   A. Structured output and citations cannot be combined and the pairing returns 400; drop citations and carry file path and line range as fields in the schema instead.
-   B. Citations require the `structured-outputs-2025-11-13` beta header when used with a JSON schema.
-   C. Citations are available only on Claude Fable 5.1, so the service must change model.
-   D. Citations must be requested through `output_config` rather than on the document block.

**E4.3** An automated refactoring agent is asked to emit a fully rewritten source file of roughly 190,000 tokens in one response, and the caller sets `max_tokens: 200000`.

What happens, and what is the correct design?

-   A. The request succeeds, but the 1M context window leaves no room for the repository digest, so earlier turns are silently dropped.
-   B. `max_tokens` cannot exceed the 128,000-token output cap on current models, so the request is rejected; the agent must emit the rewrite in hunks or per-file chunks.
-   C. `max_tokens` above the cap is silently clamped, so the file comes back truncated with no error.
-   D. The extended-output beta raises the synchronous cap to 300,000 tokens, so the caller should add that header.

**E4.4** A repository analysis service wants to load as much of a monorepo as possible into a single request on a current model. It reserves 128,000 tokens for output and measures its system prompt and tool definitions at 14,000 tokens.

How many tokens of source code can it include?

-   A. 858,000
-   B. 872,000
-   C. 986,000
-   D. 1,000,000

**E4.5** Which TWO statements about structured outputs in a review pipeline are correct? **(Select TWO)**

-   A. Prefilling the assistant turn with `{` is the supported way to force a JSON body.
-   B. `output_config.format` requires no beta header on current models.
-   C. Structured outputs guarantee a schema-conformant body even when the model refuses the request.
-   D. The older `output_format` parameter is deprecated and now requires the `structured-outputs-2025-11-13` beta header.
-   E. Strict tool use and structured outputs cannot appear in the same request.

**E4.6** To reduce variance between runs of an automated refactoring agent, an engineer sets `temperature: 0.2` on every Claude Opus 5.5 request. Every request now returns 400.

Why?

-   A. The permitted range on Opus 5.5 is 0 to 1 inclusive, and 0.2 is being sent as a string.
-   B. Temperature is ignored when extended thinking is active, so the error must come from elsewhere in the request.
-   C. Temperature must be nested inside `output_config` on current models.
-   D. `temperature` is deprecated from the 4.7 generation onward and any non-default value returns 400; reasoning depth is controlled with `output_config.effort` instead.

**E4.7** A CI integration sets `thinking: {"type": "enabled", "budget_tokens": 8000}` on Claude Opus 5.5 so that difficult reviews get more reasoning. The requests return 400.

What is the correct configuration?

-   A. Raise `budget_tokens` to at least 1,024 — 8,000 is valid, so the error lies elsewhere in the request.
-   B. Switch to `thinking: {"type": "adaptive"}` and make `max_tokens` a multiple of 1,024.
-   C. Remove `budget_tokens`: `thinking` with a token budget returns 400 from the 4.7 generation onward, and reasoning depth is set with `output_config.effort`, not inside `thinking`.
-   D. Move the `thinking` block into a batch request, where token budgets are still accepted.

**E4.8** A visual-regression step attaches rendered screenshots to a review request. Each screenshot is 1,540 × 868 pixels.

How many input tokens does one screenshot contribute?

-   A. 1,705
-   B. 1,540
-   C. 3,410
-   D. 1,372

**E4.9** A UI review agent attaches 34 screenshots at 2,560 × 1,440 pixels to a single request.

What constraint does this hit?

-   A. A request may contain at most 20 images in total, so the agent must split the work into two requests.
-   B. Once a request carries more than 20 images, no image dimension may exceed 2,000 pixels; at 2,560 × 1,440 the screenshots must be downscaled or the request split.
-   C. Images longer than 1,568 pixels on any edge are rejected regardless of how many there are.
-   D. Screenshots must be converted to a lossless format before more than 20 can be attached.

**E4.10** A code review service caches a long repository prefix. Which THREE of the following cause at least part of the previously cached prefix to be reprocessed? **(Select THREE)**

-   A. Adding a tool definition to the `tools` array.
-   B. Reading from a cache entry that an earlier request wrote.
-   C. Changing `tool_choice` from `auto` to `none`.
-   D. Appending a new user message after the final breakpoint.
-   E. Changing top-level `output_config.effort` from `high` to `medium`.
-   F. Keeping the system prompt byte-identical between requests.

**E4.11** A multi-tenant code assistant wants tenants to share as much cached prefix as possible. Its system prompt is assembled as: the tenant’s repository digest, then 9,000 tokens of shared review instructions, then the cache breakpoint. Cache hit rates are good within a tenant and zero across tenants.

What is wrong?

-   A. Cache entries cannot be shared between API keys, so cross-tenant reuse is impossible by design.
-   B. The repository digest should move into the `tools` array, which is cached per tenant.
-   C. Each tenant should be given its own breakpoint, up to the limit of four.
-   D. Putting a per-tenant block ahead of the shared instructions makes every tenant’s prefix unique from the first token; the shared instructions must come first, with the tenant digest after them.

**E4.12** A repository agent on Claude Sonnet 5.5 sends a 90,000-token repository prefix. The relevant rates are \$2.00 per MTok of uncached input, \$2.50 per MTok for a 5-minute cache write, and \$0.10 per MTok for a cache read.

From which request onward does caching the prefix cost less than not caching it?

-   A. From the second request onward.
-   B. From the twelfth request onward.
-   C. From the twenty-fifth request onward.
-   D. Never, unless the 1-hour TTL is used instead.

**E4.13** A cost dashboard for a code assistant sums `input_tokens` from every response. The figure it reports is a small fraction of the input volume on the invoice.

Why?

-   A. `input_tokens` already includes cache reads, so the discrepancy must be in output tokens.
-   B. Cache writes are not billed, so only the reads are missing from the dashboard.
-   C. `input_tokens` counts only the tokens after the last cache breakpoint; total input is `cache_read_input_tokens` + `cache_creation_input_tokens` + `input_tokens`.
-   D. Cached tokens are billed to a separate meter that the Messages API does not report.

**E4.14** A monorepo agent connects nine MCP servers and loads all 240 of their tool definitions on every request. Engineers report that the agent often calls a near-miss tool, and the prefix is dominated by definitions.

What is the correct response?

-   A. The request will exceed the platform limit of 10,000 tools and must be split.
-   B. Tool selection accuracy degrades past roughly 30–50 available tools and the definitions crowd the prefix; defer most tools with the tool search tool and keep the three to five most used loaded.
-   C. MCP tool definitions cannot be cached, so all 240 are reprocessed on every request; move them into the system prompt.
-   D. Each tool needs its own subagent, so the work should be split across 240 subagent definitions.

**E4.15** A CI webhook occasionally redelivers the same event, and the review service posts two reviews on the same commit.

How should the service make its Claude calls safe to retry?

-   A. Send the webhook delivery ID as an `anthropic-idempotency-key` header.
-   B. Set `custom_id` on the Messages API request so the server deduplicates it.
-   C. Enable the tool runner beta, which deduplicates retried tool loops.
-   D. The Messages API has no idempotency key, so the service must deduplicate on its own side — keyed on the webhook delivery ID — before it calls the API at all.

**E4.16** A nightly job explains every outstanding lint finding in a monorepo: 48,000 findings, 1,400 input tokens and 220 output tokens each, on Claude Haiku 5.5 through the Batches API, with prompts well under the long-context threshold and no caching.

What does one night cost?

-   A. \$6.00
-   B. \$12.00
-   C. \$3.36
-   D. \$30.00

**E4.17** Which TWO of the following cause a request on Claude Opus 5.5 to fail? **(Select TWO)**

-   A. `output_config: {"effort": "xhigh"}`
-   B. `output_config: {"format": {"type": "json_schema", "schema": {...}}}`
-   C. `temperature: 0`
-   D. `cache_control` with `"ttl": "1h"`
-   E. `thinking: {"type": "enabled", "budget_tokens": 8000}`
-   F. `tool_choice: "auto"`

**E4.18** A review service retries every 429 immediately in a tight loop and ignores response headers. Throughput collapses during peak hours.

What should it do?

-   A. Treat 429 as fatal and fail the build, since rate-limit errors are never retryable.
-   B. Raise `max_tokens`, since output tokens are the usual cause of a 429.
-   C. Honour the `retry-after` header when it is present and back off otherwise; capacity refills continuously under a token bucket, so immediate retries only consume what has just been replenished.
-   D. Move to the Batches API, whose requests are exempt from rate limits.

------------------------------------------------------------------------

## Section 2 — Model Selection and Optimization

**E4.19** A platform team standardises every piece of developer tooling on Claude Fable 5.1 — code review, commit message drafting, lint explanation and release note generation — on the grounds that the best model should review the code.

What is the strongest objection?

-   A. Fable 5.1 cannot be used with the Agent SDK, so the code agents cannot run on it.
-   B. Opus 5.5 is the documented recommended default at \$4/\$20 per MTok, while Fable 5.1 bills \$10/\$50; most of this fleet — commit messages, lint explanations — belongs further down the range, and the model should be chosen per workload.
-   C. Fable 5.1 does not support tool use, so none of these agents can call tools.
-   D. Fable 5.1’s context window is too small to hold a repository digest.

**E4.20** A code review service handles 9,000 reviews a month. Each review sends 24,000 input tokens and produces 4,000 output tokens, synchronously, with no caching.

What does a month cost on Claude Opus 5.5?

-   A. \$1,584
-   B. \$1,224
-   C. \$792
-   D. \$1,152

**E4.21** A team sets `output_config.effort` to `"max"` on every request their CI tooling makes, including a step that rewrites a lint message into a single plain sentence. Latency per build rises sharply and costs roughly triple.

What is the right correction?

-   A. `max` is unavailable on Claude Haiku 5.5, so those requests are returning 400.
-   B. `max` forces extended thinking on, which is incompatible with structured outputs.
-   C. Effort is a hard token budget, so `max` will exhaust `max_tokens` on every request.
-   D. Effort trades latency and token cost for reasoning depth within a response; a one-sentence rewrite does not need it. Pick a level per workload — `low` for lookups and rewrites, higher for refactors — and hold it steady, because changing effort between requests restarts the prompt cache.

**E4.22** Which TWO statements about `output_config.effort` are correct? **(Select TWO)**

-   A. The available levels are `low`, `medium`, `high`, `xhigh` and `max`.
-   B. Effort is configured inside the `thinking` object.
-   C. Opus 5.5 and Haiku 5.5 default to `medium`; the other current models default to `high`.
-   D. Setting effort explicitly to the model’s own default invalidates the prompt cache.
-   E. Effort is a hard cap on the number of output tokens.

**E4.23** A repository analysis request on Claude Haiku 5.5 reports `cache_read_input_tokens: 71,200`, `cache_creation_input_tokens: 24,900` and `input_tokens: 6,400`.

What is the total input, and how is the request priced?

-   A. 102,500 tokens, billed at the standard rate because only `input_tokens` counts toward the threshold.
-   B. 102,500 tokens, with the whole request billed at the long-context rate.
-   C. 6,400 tokens, billed at the standard rate.
-   D. 96,100 tokens, billed at the standard rate.

**E4.24** A team pins `claude-sonnet-5-5` in their CI configuration and asks what warning they will get before that identifier stops working.

What is the correct answer?

-   A. None is needed, because dateless identifiers roll forward automatically to the newest minor version.
-   B. Thirty days.
-   C. At least 60 days’ notice, because a dateless identifier from 4.6 onward is a fixed snapshot and will eventually be retired like any other.
-   D. Notice is given only to Priority Tier customers.

**E4.25** A capacity plan for a CI integration on Claude Haiku 5.5 assumes that cache reads count toward the input-tokens-per-minute limit, and provisions roughly fifteen times the throughput the team actually needs.

Is the assumption correct?

-   A. Yes — every Haiku model counts cache reads toward ITPM.
-   B. Yes for Haiku 5.5, but only above the long-context threshold.
-   C. No — no model counts cache reads toward ITPM.
-   D. No — cache reads do not count toward ITPM on Haiku 5.5; Haiku 3.5 is the documented exception. Cache writes and uncached input do count.

**E4.26** A CI integration on Claude Haiku 5.5 runs at the Build tier, with 5,000,000 input tokens per minute and 5,000 requests per minute. Each review reads 120,000 cached tokens, writes 6,000 new cached tokens and sends 2,000 uncached tokens.

How many reviews per minute can the integration sustain?

-   A. 625
-   B. 5,000
-   C. 39
-   D. 2,500

**E4.27** A team is deciding between synchronous and batch processing for two code-tooling workloads. Which TWO statements are correct? **(Select TWO)**

-   A. Batch requests are validated synchronously at submission, so shape errors surface immediately.
-   B. Batch results may take up to 24 hours, so batch cannot back a blocking pull request check.
-   C. Batch supports `stream: true` so that a CI log can show progressive output.
-   D. The 50% batch discount stacks with prompt caching, which suits a nightly repository-wide pass.
-   E. A batch holds at most 1,000 requests.

------------------------------------------------------------------------

## Section 3 — Agents and Workflows

**E4.28** A refactoring agent built on the Agent SDK is run on developers’ laptops with `permissionMode: "bypassPermissions"` so that nobody has to approve each edit.

What is wrong with this?

-   A. `bypassPermissions` is available only in the Python SDK.
-   B. `bypassPermissions` is intended for CI, containers and other isolated environments where the agent’s actions cannot affect anything that matters; on a developer’s working tree, `acceptEdits` — or `dontAsk` with an explicit allow list — gives the same autonomy without removing the guardrails.
-   C. `bypassPermissions` has no effect unless `allowedTools` is left empty.
-   D. `bypassPermissions` also disables hooks, which is the real risk.

**E4.29** A headless code agent must never prompt, and anything not explicitly pre-approved should be denied rather than silently allowed.

Which permission mode fits?

-   A. `plan`
-   B. `acceptEdits`
-   C. `auto`
-   D. `dontAsk`

**E4.30** A CI agent is given `max_turns=5`. The repair it is asked to perform genuinely needs seven rounds of tool calls before it can report.

What does the caller receive?

-   A. A `ResultMessage` with subtype `success`, carrying the partial work in `result`.
-   B. A `ResultMessage` with subtype `error_during_execution` and no `result`.
-   C. A `ResultMessage` with subtype `error_max_turns` and no `result`; the last two tool-use turns never ran.
-   D. A `ResultMessage` with subtype `error_max_budget_usd`, because turns and budget share one counter.

**E4.31** A `PreToolUse` hook blocks a `Bash` call that would run `git push`.

What does the agent see?

-   A. The tool does not execute, and Claude receives the hook’s rejection message as the tool result, so it typically tries a different approach or reports that it could not proceed.
-   B. The query ends with `error_during_execution`.
-   C. The tool executes and the hook’s message is appended to the result.
-   D. The rejection is invisible to Claude, which retries the identical call until `max_turns` is reached.

**E4.32** A CI runner wraps an Agent SDK query and must report accurately when a run does not finish. Which TWO statements are correct? **(Select TWO)**

-   A. The `result` field is populated only on the `success` subtype.
-   B. `error_max_turns` carries the partial text in `result`.
-   C. Every subtype carries `total_cost_usd`, `usage`, `num_turns` and `session_id`.
-   D. A single-shot `query()` ends quietly on an error subtype, so the caller only needs to read the subtype.
-   E. `error_max_budget_usd` guarantees that spend did not exceed the cap.

**E4.33** A CI orchestration agent spawns one review subagent per changed file. On a large refactor that is 300 files. No concurrency, depth or budget limits are set.

What is the correct criticism?

-   A. The SDK refuses more than 10 subagents per turn, so the design cannot run as written.
-   B. The depth default of 3 and concurrency default of 20 still permit a large and expensive tree; the run needs `max_budget_usd`, which covers subagent spend, together with explicit `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` and `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` values.
-   C. Subagent spend is excluded from `total_cost_usd`, so the run cannot be costed at all.
-   D. Subagents cannot run in parallel, so the design gains nothing over a sequential loop.

**E4.34** A review subagent is defined with `tools: ["Read", "Grep", "Glob"]`. During a run it would be useful for it to call `Edit`.

What happens?

-   A. The subagent prompts the user for approval the first time it wants `Edit`.
-   B. The subagent receives a permission-denied tool result and tries again.
-   C. The subagent inherits `Edit` from the parent anyway, since `tools` only sets priority.
-   D. `Edit` is not in the subagent’s session at all: Claude works without it, with no prompt and no error.

**E4.35** A code review orchestrator runs style, security and coverage subagents in parallel and wants to track and aggregate their results as they start and finish.

Which hooks are intended for this?

-   A. `PreToolUse` and `PostToolUse`
-   B. `UserPromptSubmit` and `Stop`
-   C. `SubagentStart` and `SubagentStop`
-   D. `PreCompact` and `Stop`

------------------------------------------------------------------------

## Section 4 — Prompt and Context Engineering

**E4.36** A repository analysis agent reads hundreds of files per run, and file contents dominate its context. The team enables `clear_tool_uses_20250919` with its defaults. Context pressure improves, but input cost rises rather than falling.

What explains it, and what should they change?

-   A. Each clear invalidates the cached prefix from the clear point onward, so frequent small clears pay repeated cache-write costs; set `clear_at_least` so every clear frees enough tokens to justify the invalidation, and use `exclude_tools` for results that must persist.
-   B. Context editing cannot be combined with prompt caching at all, so caching must be turned off.
-   C. The trigger must be expressed in `tool_uses` rather than `input_tokens`, which is the only supported form.
-   D. `keep` must be raised above 3, because below that the agent loses the ability to call tools.

**E4.37** A repository agent’s conversation consists of one system block, one user block, and then nine assistant turns, each made up of a run of three `tool_use` blocks followed by a run of three `tool_result` blocks. A cache breakpoint sits on the final `tool_result` run. Remember that a consecutive run of `tool_use` blocks counts as one lookback position, and so does a consecutive run of `tool_result` blocks.

How many lookback positions back must the breakpoint reach to include the system block, counting the breakpoint itself?

-   A. 10
-   B. 19
-   C. 20
-   D. 56

**E4.38** A code tooling service runs across several model tiers and enables `clear_thinking_20251015` without setting `keep`. Behaviour differs between tiers.

Why?

-   A. `keep` defaults to 1 on every model, so the difference must come from elsewhere.
-   B. The default for `keep` is “all” on Opus 4.5 and later, Sonnet 4.6 and later, Haiku 5.5 and later, and the Fable and Mythos models, but only the last turn on earlier models; a service spanning tiers should set `keep` explicitly.
-   C. `keep` accepts only integers, so the string “all” is invalid and silently ignored.
-   D. Thinking blocks cannot be cleared on current models, so the strategy is a no-op there.

**E4.39** Which TWO measures help keep a monorepo prefix cached across a long agent run? **(Select TWO)**

-   A. Use `"ttl": "1h"` on the prefix breakpoint, and place longer-TTL entries before shorter-TTL ones.
-   B. Put the current git SHA at the top of the system prompt so every request is traceable.
-   C. Set `cache_control` on a deferred tool so it is pinned into the prefix.
-   D. Keep top-level `output_config.effort` constant for the whole session.
-   E. Use five breakpoints so that the whole prefix is covered.

**E4.40** A code agent appends the full text of each file it reads to its system prompt, “so Claude never forgets what it has seen”. After twenty files, cost per turn has grown far faster than the context has.

What is wrong?

-   A. The system prompt is capped at 100,000 tokens, which the agent will exceed.
-   B. File content in the system prompt is not billed as input, so the cost model is wrong rather than the design.
-   C. System prompts cannot carry `cache_control`, so nothing is ever cached.
-   D. The system prompt sits above messages in the invalidation hierarchy, so appending to it invalidates the whole prefix on every file read; file content belongs in tool results, where context editing can clear it and the prefix above stays cached.

**E4.41** A long-running refactoring agent should write down what it has established before older tool results are cleared from its context.

Which tool declaration enables that?

-   A. `memory_20250818`
-   B. `memory_20251015`
-   C. `context_memory_20250919`
-   D. `clear_tool_uses_20250919`

------------------------------------------------------------------------

## Section 5 — Tools and MCPs

**E4.42** A team’s MCP code-search server keeps per-connection state established during `initialize`. After the 2026-07-28 revision, the handshake never arrives and clients see no tools.

What changed?

-   A. The server must downgrade its protocol version header to the previous revision.
-   B. Session state must now be carried in a cookie set during `initialize`.
-   C. The revision is stateless: `server/discover` replaces the `initialize` handshake and request-scoped state travels in per-request `_meta`; sampling and logging are deprecated.
-   D. Stateful servers must register a webhook so the client can reconnect them.

**E4.43** A Python MCP server for a code index is being upgraded to the current revision. Which class does the server now subclass or instantiate?

-   A. `FastMCP2`
-   B. `MCPServer`
-   C. `StatelessServer`
-   D. `MCPApp`

**E4.44** A code agent connects nine MCP servers exposing 238 tools, whose definitions total 61,000 tokens. With the tool search tool enabled, a typical turn loads the search tool (180 tokens) plus four discovered tools averaging 260 tokens each.

What is in the prefix, and what reduction does that represent?

-   A. 1,220 tokens, about a 98% reduction.
-   B. 1,220 tokens, about an 80% reduction.
-   C. 1,040 tokens, about a 98% reduction.
-   D. 61,000 tokens and no reduction, because all definitions are still sent on every request.

**E4.45** Which TWO statements about forced tool use in a code agent are correct? **(Select TWO)**

-   A. `tool_choice: "none"` returns 400 on current models.
-   B. `tool_choice: {"type": "any"}` returns 400 on Claude Opus 5.5 and Claude Sonnet 5.5.
-   C. The tool-use system prompt overhead is identical for `auto` and `any`.
-   D. Changing `tool_choice` between requests leaves cached message blocks intact.
-   E. Forced tool use cannot be combined with manual extended thinking.

**E4.46** A team is choosing between the two tool search variants for a code agent with a large MCP surface.

Which description is accurate?

-   A. Both variants take natural-language queries; the regex variant simply compiles them into patterns.
-   B. The regex variant allows patterns up to 500 characters and the BM25 variant queries up to 200.
-   C. Only the BM25 variant searches argument names and descriptions; the regex variant matches tool names alone.
-   D. The regex variant takes case-insensitive `re.search()` patterns up to 200 characters and the BM25 variant takes natural-language queries up to 500 characters; both search tool names, descriptions, argument names and argument descriptions.

------------------------------------------------------------------------

## Section 6 — Security and Safety

**E4.47** A CI review agent reads the pull request title and description — which on this repository can come from any fork — into its prompt, and runs with `Bash` allowed so it can execute the test suite.

What is the correct criticism?

-   A. Pull request descriptions are sanitised by the forge, so no action is needed.
-   B. Content from a fork is untrusted third-party input: it must be delimited and labelled as data, and the agent should run with a minimal explicit allow list rather than general `Bash` access.
-   C. The agent should run with `bypassPermissions` so that the human reviewer is never interrupted.
-   D. The risk is removed by raising `output_config.effort` to `max` so the model reasons past any injected instruction.

**E4.48** A parent agent reads the final report of a review subagent. What does Claude Code’s subagent output scanning do to that report?

-   A. It deletes any matched pattern from the subagent’s message.
-   B. It rewrites permission-configuration mentions to a safe placeholder.
-   C. It neutralises control-tag imitations in place by inserting a backslash, escapes turn markers such as a leading `Human:` with a backslash before the colon, leaves permission-configuration mentions as written, and prepends a `[harness: ...]` marker line for the first two kinds of match.
-   D. It blocks delivery of the subagent’s final message entirely whenever any pattern matches.

**E4.49** Which TWO statements about hardening a code agent for CI are correct? **(Select TWO)**

-   A. `dontAsk` auto-approves anything that is not explicitly denied.
-   B. Hooks run inside the agent’s context window, so they should be kept short.
-   C. `bypassPermissions` cannot be used when running as root on Unix.
-   D. Deny rules are evaluated ahead of allow rules, and an allow rule cannot carve an exception out of a deny.
-   E. A tool left out of a subagent’s `tools` list triggers a permission prompt the first time it is wanted.

**E4.50** A repository’s CLAUDE.md contains a deployment token “so the agent doesn’t have to ask for it”.

What is the problem?

-   A. CLAUDE.md is loaded only in interactive sessions, so a CI run will never see the token and the deploys will fail.
-   B. The token is safe because CLAUDE.md content is prompt-cached rather than transmitted in full on every request.
-   C. The token should be moved to `.claude/settings.local.json`, which is never transmitted to the API.
-   D. CLAUDE.md is loaded as project memory and re-injected with every request, so the token reaches every session, every subagent and every transcript; it must be removed and read from the environment or a secret store at the point of use.

------------------------------------------------------------------------

## Section 7 — Claude Code

**E4.51** A platform team maintains a `/review-pr` custom slash command that loads a checklist and a set of conventions. They want to extend it with supporting files and a longer body, and ask where this kind of workflow now belongs.

What is the correct answer?

-   A. Custom slash commands are now merged into skills, so the workflow should be authored as a skill; it remains invocable by name.
-   B. Custom slash commands remain a separate feature and can only live in `.claude/commands/`.
-   C. Slash commands were removed with no replacement, so the checklist must move into CLAUDE.md.
-   D. Slash commands can only be defined in managed policy settings.

**E4.52** A developer adds an allow rule to `.claude/settings.local.json` so that a particular `Bash` command runs without prompting. The rule has no effect. The organisation deploys managed settings that deny that command.

Why?

-   A. Local settings are the highest precedence, so the rule should work and the file must be malformed.
-   B. Project settings override local settings, so the rule belongs in `.claude/settings.json`.
-   C. Managed settings deployed by the organisation take precedence over command-line arguments, local project settings, shared project settings and user settings, so a managed deny cannot be overridden locally.
-   D. Permission rules are not read from local settings at all.

------------------------------------------------------------------------

## Section 8 — Eval, Testing, and Debugging

**E4.53** A team evaluates their review agent’s cost by reading `usage` and `total_cost_usd` from each run’s `ResultMessage`. The figures consistently come in below what the account is billed, and the gap grows on runs that delegate heavily.

What is the explanation?

-   A. `total_cost_usd` excludes cache reads, so the figure is always low.
-   B. `usage` covers only the main agent loop; whole-tree token and cost accounting comes from `modelUsage` (`model_usage` in Python), and in Python those fields are optional and may be `None`.
-   C. `usage` is populated only on the `success` subtype, so failed runs contribute nothing.
-   D. Subagent spend is reported on each subagent’s own `ResultMessage` and must be summed by the caller, because nothing aggregates it.
