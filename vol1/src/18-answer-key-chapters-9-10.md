# Answer Key: Chapters 9–10

## Chapter 9

**Q9.1 — B.** The description is the model’s only evidence about what a tool does, so a one-word description and generic name are the root cause; stating what is searched, what a good query looks like and the boundary with `lookup_order` fixes both symptoms. A is tempting but duplicates information that belongs on the tool and still leaves the tool itself ambiguous. C hard-codes routing in a brittle way, and D adds a reasoning parameter that does not help selection and can trigger refusals.

**Q9.2 — C.** In the user message that carries results, `tool_result` blocks must come first and any text after them; text first produces the “tool\_use ids were found without tool\_result blocks immediately after” error. A is false because mixing is allowed when ordered correctly. D fails because nothing may sit between the assistant `tool_use` message and the result message, so splitting into two user messages breaks adjacency.

**Q9.3 — A.** Every `tool_use` id needs a matching `tool_result`, and all results for one assistant turn go in a single user message. B breaks the adjacency rule (and teaches the model to stop calling tools in parallel). D is tempting because the model might re-ask, but omitting results is itself the 400 error; a skipped call still needs a result, flagged `is_error`. C is wrong because `disable_parallel_tool_use` lives inside `tool_choice`, not at the top level.

**Q9.4 — D.** A recoverable failure should be returned as a `tool_result` with `is_error: true` and an instructive message so the model can self-correct, while the full exception is logged for your team. A leaves a dangling `tool_use` and crashes the loop. B swallows the failure into a success-shaped result the model will treat as truth, and C gives up on a problem the model could have fixed.

**Q9.5 — A.** A closed set of values should be an `enum`, which both constrains the output and documents the meaning of each value. B hides the problem with ever-growing normalization code and can accept wrong values, and C relies on a prose request the model will sometimes ignore. D does not change argument quality, since `any` only forces some tool call.

**Q9.6 — C.** Forcing a specific tool (`any` or `tool`) is not supported together with manual extended thinking, so either use `auto` and instruct the model (adding `strict: true` for schema-valid inputs) or drop manual thinking. A does not address an API-level incompatibility. D abandons the structured tool route for fragile text parsing, and B misunderstands where tools are declared.

**Q9.7 — B.** `pause_turn` means a server-tool loop hit its iteration limit; you send the assistant content back unchanged and the model continues. A throws away work already done. C is wrong because server tools run on Anthropic’s infrastructure and you do not execute them, and D confuses `pause_turn` with `max_tokens`.

**Q9.8 — C.** Several consumers sharing one capability owned by another team is the textbook case for an MCP server: build it once and let each host connect. A keeps the drift problem and the duplication. B makes the interface vaguer and less reliable, and D exposes credentials in prompts, which is a serious security flaw.

**Q9.9 — A.** For a stdio server, stdout is the protocol channel, so a stray `print` corrupts the JSON-RPC stream; log to stderr or a file. B is wrong because stdio servers can log perfectly well to stderr, and C and D invent requirements; the problem is correctness, not timing.

**Q9.10 — D.** The Messages API MCP connector reaches only remote servers over HTTPS (Streamable HTTP or SSE), and local stdio servers cannot be connected directly. The valid paths are to host the server remotely or run your own MCP client that spawns the process and relays calls as ordinary tools. A is backwards, since the connector supports tool calls only, and B and C describe settings that do not exist.

**Q9.11 — B.** Consolidating near-duplicate operations, namespacing, and loading definitions on demand with tool search reduces both wrong-tool selection and token overhead. A adds randomness, which makes selection worse. C forces some call on every turn, and D removes the detail the model needs to choose correctly, which is the opposite of the guidance on descriptions.

**Q9.12 — C.** Hallucinated identifiers are best handled by stating provenance in the description, validating existence in the handler, and returning an error that tells the model how to obtain a valid ID. B is the tempting one, but `strict` guarantees shape and types, not that a value refers to a real record. A makes the problem worse for a needed field, and D silently performs a refund on the wrong order.

**Q9.13 — A.** Returning the failure with `is_error: true` lets the model reissue the dependent call on its next turn, and a system prompt line to batch only independent calls reduces recurrence while preserving parallelism where it helps. B sacrifices all parallelism to fix one pattern. C breaks the rule that all results sit in one message immediately after the assistant turn, and D removes functionality.

**Q9.14 — D.** `strict: true` constrains the form of the input, so `format: date` guarantees a date string but cannot know what “next Friday” means without a reference point; supply the current date and sharpen the parameter description. A is wrong because strict is working as designed. B has no bearing on date reasoning, and C invents a truncation problem.

**Q9.15 — B.** Resources are read-only context identified by URI that the application decides to attach, which matches attaching schemas without the model choosing to fetch them. A is tempting because tools can return data, but tools are model-controlled and would require the model to decide to call them. C misuses prompts, which are user-selected templates, and D is a server-to-client model-completion request (also deprecated in the latest revision) and is unrelated to supplying context.

## Chapter 10

**Q10.1 — C.** CLAUDE.md is context the model usually follows but is not enforced; a deny rule is enforced by Claude Code itself, and a `PreToolUse` hook can add a deterministic check. A and B only change how the same unenforced guidance is presented. D acts after the damage is done.

**Q10.2 — A.** `CLAUDE.local.md` at the project root holds personal, project-specific instructions and should be gitignored. B commits private details to the team, and C is a shared file that would also be committed. D is tempting but `~/.claude/CLAUDE.md` applies to all your projects, not one.

**Q10.3 — B.** Long files reduce adherence, so trim to what is needed every session, scope instructions to the files they concern with `.claude/rules/`, move procedures to skills, and remove contradictions. C fails because imports load at launch and do not reduce context cost. A does not fix contradictions or length, and D changes approval behavior, which is unrelated to instruction-following.

**Q10.4 — D.** Project scope writes the server into `.mcp.json` in the repository so teammates receive it through git, and `${VAR}` expansion keeps secrets out of version control. A and B leave configuration in per-user storage that is not shared, and C commits a secret.

**Q10.5 — C.** Rules are evaluated deny, then ask, then allow, and the first match decides, so a broad allow cannot override a matching deny. A has the order backwards. B is wrong because there is no conflict prompt, and D confuses permission modes with rule precedence.

**Q10.6 — B.** A `PostToolUse` hook with an `Edit|Write` matcher runs deterministically after every matching edit. A is context only and can be forgotten. C and D depend on someone or something choosing to invoke them, so they are not guaranteed.

**Q10.7 — D.** A subagent runs in its own context window and returns only a summary, which keeps the main context clean for a broad read-heavy investigation. A discards useful context instead of isolating the noise, B would load even more into context, and C changes prompting behavior, not context usage.

**Q10.8 — A.** Headless `claude -p` with a tightly scoped `--allowedTools` list lets the job proceed without prompts while limiting what it can do. B is fragile hackery, and C is the tempting shortcut but disabling all permission checks on a shared runner is exactly what the documentation says to avoid outside isolated environments. D is wrong because `plan` mode does not edit or act, so it cannot post findings.
