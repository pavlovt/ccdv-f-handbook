# Claude Code

Claude Code is Anthropic’s agentic coding tool. This chapter is short because the exam weights it lightly, but the questions that do appear are practical: where does an instruction belong, what enforces a rule, and which mechanism fits a given need.

## What Claude Code Is, and What It Is Not

Claude Code reads your codebase, edits files, runs commands, and integrates with development tools, working through an agent loop of the kind described in Chapter 9. It uses built-in tools (file read, edit, search, shell) and any MCP servers you connect, and it asks permission before doing risky things.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                    Messages API                            claude.ai chat                Claude Code
  ----------------- --------------------------------------- ----------------------------- -------------------------------------------------------------------------------------------------------
  Who you are       A developer building your own product   An end user chatting          A developer delegating engineering work

  Tools             Only the ones you define and execute    Product-provided features     Built-in file, search and shell tools plus MCP, running on your machine or in a managed cloud session

  Loop              You write it                            Handled for you               Handled for you, with a permission system

  State             You manage the message history          Conversation in the product   Session transcripts plus project files such as CLAUDE.md

  Customization     Everything is code                      Settings, projects            CLAUDE.md, settings files, hooks, skills, subagents, MCP
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The key distinction: with the API you build the agent; Claude Code is an agent already built, which you configure. Anthropic also ships the Agent SDK for building your own agents on the same engine, and `claude -p` runs Claude Code non-interactively from scripts and CI.

It is available as a terminal CLI, IDE extensions (VS Code and JetBrains), a desktop app and a web interface. All surfaces share the same engine, so a repository’s CLAUDE.md, settings and MCP servers work across them.

## Installation and Requirements

The recommended install is the native installer: a shell script on macOS, Linux and WSL, a PowerShell or CMD equivalent on Windows. Homebrew (`brew install --cask claude-code`), WinGet (`winget install Anthropic.ClaudeCode`) and apt, dnf or apk repositories also work, and an npm package (`@anthropic-ai/claude-code`) exists. Native installs update themselves in the background; Homebrew, WinGet and Linux package-manager installs do not, so you upgrade them with the package manager (or `claude update` where applicable).

At a high level the documented requirements are a recent OS (macOS 13+, Windows 10 1809+, Ubuntu 20.04+, Debian 10+, Alpine 3.19+), 4 GB or more of RAM, an internet connection, and a Bash, Zsh, PowerShell or CMD shell. Node.js is not needed for the native binary; the npm route requires Node.js 22 or later. Authentication requires a Pro, Max, Team, Enterprise or Console account (the free claude.ai plan does not include Claude Code), or a supported third-party provider such as Amazon Bedrock, Google Cloud, or Microsoft Foundry. Run `claude` in a project directory to start, `claude --version` to verify, and `claude doctor` for diagnostics.

## CLAUDE.md: Project Memory

Each session starts with a fresh context window. `CLAUDE.md` files are how you carry durable instructions across sessions. They are plain markdown, loaded into context at the start of every session. Claude also keeps its own **auto memory**, notes it writes about your corrections and preferences, which is a separate mechanism from the files you author.

  -------------------------------------------------------------------------------------------------------------------------------------
  Scope                   Location                                                                      Shared with
  ----------------------- ----------------------------------------------------------------------------- -------------------------------
  Managed policy          OS-specific system path (for example `/etc/claude-code/CLAUDE.md` on Linux)   Everyone in the organization

  User                    `~/.claude/CLAUDE.md`                                                         Only you, all projects

  Project                 `./CLAUDE.md` or `./.claude/CLAUDE.md`                                        The team, via version control

  Local                   `./CLAUDE.local.md` (add to `.gitignore`)                                     Only you, this project
  -------------------------------------------------------------------------------------------------------------------------------------

Claude Code loads every CLAUDE.md found in the directory hierarchy above your working directory and concatenates them into context; one file does not replace another. Files closer to the working directory appear later. Files in subdirectories load on demand when Claude works there. A file can import others with `@path/to/file`, expanded at launch (imports organize a long file but do not reduce its context cost). The `/init` command generates a starting CLAUDE.md by analyzing the repository, and `/memory` is where you inspect and edit memory.

**What belongs in it:** facts that Claude should hold in every session and could not easily discover alone. Build, test and lint commands; non-obvious conventions and architecture decisions; repository layout; “always do X, never do Y” rules; environment quirks. **What does not:** long multi-step procedures (use a skill), instructions that matter for one part of the tree (use a path-scoped file in `.claude/rules/`), and anything you need *guaranteed*.

Two principles to remember. First, keep it short and specific; the guidance is to target under roughly 200 lines per file, because longer files consume context and reduce adherence, and contradictory instructions get resolved arbitrarily. Second, CLAUDE.md is context, not enforcement. The model usually follows it, but nothing blocks a violation. If a rule must hold regardless of what the model decides, use a permission deny rule or a hook.

## Settings and Configuration Files

Settings are JSON and apply at several scopes. Higher entries override lower ones:

  -----------------------------------------------------------------------------------------------------------------------
  Precedence              Source                  Location
  ----------------------- ----------------------- -----------------------------------------------------------------------
  1 (highest)             Managed settings        Organization-deployed `managed-settings.json`, MDM, or server-managed

  2                       Command line            `claude --settings <file-or-json>` for one session

  3                       Project local           `.claude/settings.local.json` (personal, not committed)

  4                       Shared project          `.claude/settings.json` (committed, team-wide)

  5 (lowest)              User                    `~/.claude/settings.json`
  -----------------------------------------------------------------------------------------------------------------------

Commit `.claude/settings.json` so everyone gets the same permissions and hooks; individuals override in the local file. Array settings such as permission rules merge across scopes rather than replace. A separate file, `~/.claude.json`, is written by Claude Code itself and holds sign-in state, per-project state, and MCP servers added at local or user scope; you do not normally edit it. Project-scoped MCP servers live in `.mcp.json` at the repository root. Subagents, skills, rules and commands live in directories under `.claude/` (and `~/.claude/` for personal ones).

Common keys include `permissions` (with `allow`, `ask`, `deny`, `defaultMode`, `additionalDirectories`), `env`, `model`, and `hooks`. The `/config` command opens an interactive settings menu, and `claude doctor` validates files.

## Permissions and Modes

Claude Code asks before actions that could change things. Reads inside the working directory generally need no approval; shell commands (apart from a built-in set of read-only ones), file edits, and web access do. Choosing “Yes, and don’t ask again” saves an `allow` rule, by default into `.claude/settings.local.json`.

**Rule syntax.** Rules name a tool and optionally a specifier: `Bash(npm run *)`, `Read(./secrets/**)`, `Edit(src/**)`, `WebFetch(domain:example.com)`. For MCP tools the form is `mcp__<server>` or `mcp__<server>__<tool>`. Evaluation order is **deny, then ask, then allow**, and the first match wins, so an allow rule can never carve an exception out of a deny rule. A bare tool name in a deny rule removes the tool from the model’s context entirely; a scoped one blocks only matching calls. Rules are enforced by Claude Code, not by the model, so a prompt or CLAUDE.md line cannot override them. Be aware that Bash patterns match command text and are not a hard security boundary around a program; shell operators are understood, so `safe-cmd *` does not authorize `safe-cmd && other`.

**Modes.** Set with `defaultMode`, `--permission-mode`, or by cycling in the session with Shift+Tab:

  ----------------------------------------------------------------------------------------------------------------------------------
  Mode                                Behavior
  ----------------------------------- ----------------------------------------------------------------------------------------------
  `default` (shown as Manual)         Prompts on first use of each tool

  `acceptEdits`                       Auto-accepts file edits and simple filesystem commands in the working directory

  `plan`                              Read-only exploration; Claude proposes a plan and does not edit source files

  `auto`                              Runs without routine prompts; a background classifier checks actions against your request

  `dontAsk`                           Anything that would prompt is denied; pre-approved tools still run

  `bypassPermissions`                 Skips prompts (set by `--dangerously-skip-permissions`); only for isolated containers or VMs
  ----------------------------------------------------------------------------------------------------------------------------------

Some modes cannot be enabled from a committed project file; for example `auto` and `bypassPermissions` as a `defaultMode` take effect only from user or managed settings, which prevents a repository from switching off its own safeguards. Administrators can disable bypass or auto entirely in managed settings.

## Hooks

Hooks are user-defined handlers that Claude Code runs at lifecycle events, giving you **deterministic** behavior instead of hoping the model remembers. Most are shell commands. They are configured in a `hooks` block of a settings file, keyed by event, with a `matcher` selecting which tools or sources trigger it.

Frequently used events: `PreToolUse` (before a tool runs; can block), `PostToolUse` (after success), `UserPromptSubmit`, `SessionStart`, `Notification`, `Stop` (Claude finished responding), and `SubagentStop`. The handler receives event data as JSON on **stdin** and communicates through its exit code: **exit 0** means no objection, **exit 2** blocks the action with stderr fed back as the reason, and other codes are non-blocking errors. Hooks can also print structured JSON for finer control. When several hooks match, they run in parallel and for permission decisions the most restrictive answer wins.

Auto-format every edit:

``` {.sourceCode .json}
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write" }
        ]
      }
    ]
  }
}
```

Block edits to protected files: a `PreToolUse` hook on `Edit|Write` that reads `.tool_input.file_path` from stdin and, if it matches `.env` or `package-lock.json`, writes a message to stderr and exits 2.

Use hooks for formatting, linting, audit logging, notifications, and policy checks. Use CLAUDE.md for guidance, permissions for access control, hooks when you need code to run.

## Slash Commands and Skills

Built-in slash commands manage the session: `/help`, `/init`, `/memory`, `/permissions`, `/mcp`, `/config`, `/context`, `/compact` (summarize history to free context), `/clear`, `/model`, and `/doctor`, among others. Run `/help` for the current list.

You add your own as **skills**. Custom commands have been merged into skills: `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy`. A skill is a directory with a `SKILL.md` containing YAML frontmatter and instructions, optionally with supporting files. Personal skills live in `~/.claude/skills/`, project skills in `.claude/skills/`. Useful frontmatter includes `description` (what it does and when to use it, which lets Claude load it automatically), `disable-model-invocation: true` (only you can trigger it, important for deploy-style actions), `user-invocable: false`, and `allowed-tools`. Arguments typed after the command are available as `$ARGUMENTS`, or by position as `$0`, `$1`. Skills are the right home for repeatable procedures that would bloat CLAUDE.md.

## Subagents

A subagent is a specialized assistant that runs in its **own context window** with its own system prompt, tool access and permissions. Claude delegates to one when a task matches its `description`; the subagent does the noisy work (searching, reading many files, running tests) and returns only a summary, protecting the main conversation’s context.

Subagents are markdown files with YAML frontmatter, stored in `.claude/agents/` (project) or `~/.claude/agents/` (personal); project definitions outrank personal ones on a name clash. Only `name` and `description` are required. Other fields include `tools` (an allowlist, inherits everything if omitted), `disallowedTools`, `model` (`sonnet`, `opus`, `haiku`, `inherit` or a full ID), `permissionMode`, `maxTurns`, `skills`, `mcpServers`, and `hooks`.

``` {.sourceCode .markdown}
---
name: test-triage
description: Runs the test suite and diagnoses failures. Use after code changes or when CI is red.
tools: Read, Grep, Glob, Bash
model: sonnet
---
Run the relevant tests, group failures by root cause, and report the file,
the likely cause and a suggested fix for each. Do not edit files.
```

Built-in subagents include a fast read-only Explore agent for codebase search, a Plan agent used during plan mode, and a general-purpose agent. Restricting `tools` is the main safety lever: a reviewer that cannot edit cannot damage anything.

## Connecting MCP Servers

Claude Code is an MCP host (Chapter 9). Add servers from the shell with `claude mcp add`:

``` {.sourceCode .bash}
# Remote server over Streamable HTTP (recommended for remote)
claude mcp add --transport http tickets https://tickets.example.com/mcp \
  --header "Authorization: Bearer $TOKEN"

# Local stdio server: options first, then -- , then the server command
claude mcp add --transport stdio --env API_KEY=xxxx inventory -- npx -y inventory-mcp
```

The `--` separates Claude’s flags from the server’s own command line. SSE is deprecated in favor of HTTP.

  --------------------------------------------------------------------------------------------------------
  Scope             Flag                Stored in                                  Shared
  ----------------- ------------------- ------------------------------------------ -----------------------
  Local (default)   `--scope local`     `~/.claude.json`, under the project path   No

  Project           `--scope project`   `.mcp.json` in the repo                    Yes, via git

  User              `--scope user`      `~/.claude.json`                           No, all your projects
  --------------------------------------------------------------------------------------------------------

A `.mcp.json` file supports `${VAR}` and `${VAR:-default}` expansion in commands, URLs and headers, which keeps secrets out of version control. Project-scoped servers require each user’s approval the first time. Manage servers with `claude mcp list`, `get`, `remove`, and inside a session with `/mcp`, which also handles OAuth login for remote servers. MCP tools appear to permission rules and hook matchers as `mcp__<server>__<tool>`; to allow or deny a whole server, use `mcp__<server>` or `mcp__<server>__*`. Large MCP outputs are capped (a default of 25,000 tokens), and tool search is on by default so that huge tool catalogs do not fill the context.

## A Practical Workflow on a Real Codebase

1.  **Prepare the repository.** Run `/init`, then trim the result to what Claude could not infer: how to build, test and lint, and the conventions that bite newcomers. Commit it. Add `.claude/settings.json` with allow rules for safe, frequent commands (`Bash(npm run test *)`) and deny rules for files and commands that must never be touched.
2.  **Explore before editing.** Start in `plan` mode (Shift+Tab) for anything non-trivial. Ask Claude to read the relevant code and propose an approach; use the Explore subagent for broad searches so exploration does not consume your main context.
3.  **Give it a way to verify.** Point it at the test command or a failing test. An agent that can run tests and read the failures converges far better than one working blind.
4.  **Implement in small steps.** Switch to `acceptEdits` once the plan is sound. Review diffs as it works. Commit often; Claude can write the commit message and open the pull request.
5.  **Manage context.** Use `/compact` when a long session grows heavy, `/clear` between unrelated tasks, and `claude -c` or `claude -r <name>` to continue or resume sessions.
6.  **Automate the repeatable.** Promote recurring prompts into skills, deterministic checks into hooks, and CI tasks into `claude -p` runs with a narrow `--allowedTools` list, since nobody is there to answer a prompt. Save `bypassPermissions` for sandboxed environments.

## Chapter Summary

-   Claude Code is a configurable agent, not an API: you steer it with CLAUDE.md, settings, permissions, hooks, skills, subagents and MCP.
-   CLAUDE.md is context, kept short; anything that must be enforced belongs in deny rules or hooks.
-   Settings precedence runs managed, command line, local, project, user. Permission rules evaluate deny, ask, allow.
-   Hooks run code at lifecycle events; exit 2 blocks. Subagents isolate context. Skills package procedures.
-   `claude mcp add` registers servers at local, project (`.mcp.json`) or user scope.

## Practice Questions

**Q10.1** Your team’s policy says Claude must never modify anything under `migrations/`. A line in the project CLAUDE.md already says so, but a developer reports Claude edited a migration file during a long refactor. How do you make the rule reliable?

A. Move the line to the top of CLAUDE.md and put it in capital letters. B. Add the rule to `CLAUDE.local.md` on every developer machine. C. Add a deny rule such as `Edit(migrations/**)` in committed project settings, optionally backed by a `PreToolUse` hook. D. Create a subagent that reviews edits after they happen.

**Q10.2** You keep a personal sandbox URL and test credentials alias that Claude should know about when working in one repository, but they must not be committed. Where do they go?

A. `./CLAUDE.local.md`, listed in `.gitignore`. B. `./CLAUDE.md`, since the team can ignore it. C. `.claude/settings.json`, in the `env` block. D. `~/.claude/CLAUDE.md`, which applies only to that repository.

**Q10.3** Your CLAUDE.md has grown to about 900 lines covering build steps, deployment runbooks, API conventions for three services, and style rules. Claude follows some instructions inconsistently and some contradict each other. What is the best remediation?

A. Add `IMPORTANT:` prefixes to the rules that are being ignored. B. Cut it to the facts needed in every session, move service-specific conventions into path-scoped files under `.claude/rules/`, move runbooks into skills, and resolve contradictions. C. Split the content into several `@imports` so the file looks shorter. D. Switch to `bypassPermissions` so Claude stops hesitating.

**Q10.4** You want every teammate who clones the repository to get a new internal MCP server configured automatically (each person will still supply their own token through an environment variable). What should you do?

A. Run `claude mcp add` with the default scope and share your `~/.claude.json`. B. Add the server with user scope and ask teammates to do the same. C. Put the token directly in a committed settings file for convenience. D. Add it with `--scope project` so it is written to `.mcp.json`, referencing the token as `${TOKEN_VAR}` in `headers` or `env`.

**Q10.5** A project settings file contains `allow: ["Bash(git *)"]` and `deny: ["Bash(git push *)"]`. During a session Claude attempts `git push origin main`. What happens?

A. It runs, because the allow rule is broader and listed first. B. The user is prompted, because the two rules conflict. C. It is denied, because deny rules are evaluated first and a match ends evaluation. D. It runs only if the session is in `acceptEdits` mode.

**Q10.6** Your team wants Prettier to run on every file Claude edits, with no exceptions and without relying on the model to remember. Which approach is correct?

A. Add “Always run Prettier after editing” to CLAUDE.md. B. Configure a `PostToolUse` hook with matcher `Edit|Write` that runs Prettier on the edited file path. C. Create a skill named `format` and ask the team to invoke it. D. Create a subagent called `formatter` with the Bash tool.

**Q10.7** During a task Claude must understand how authentication is implemented across a 3,000-file monorepo. Reading dozens of files is filling the main conversation’s context and degrading later steps. Which feature best addresses this?

A. Run `/clear` and re-explain the task. B. Add the full source tree to CLAUDE.md with `@` imports. C. Raise the permission mode to `auto`. D. Delegate the investigation to a read-only subagent (such as Explore) so only a summary returns to the main context.

**Q10.8** A CI job must have Claude Code review a pull request diff and post findings. No human is present to approve prompts, and the runner is shared with other jobs. Which setup is most appropriate?

A. Run `claude -p` non-interactively with a narrowly scoped `--allowedTools` list (for example read and specific `git` commands) and no dangerous bypass. B. Run the interactive CLI under a terminal multiplexer and send keystrokes to approve prompts. C. Use `--dangerously-skip-permissions` on the shared runner for reliability. D. Run in `plan` mode so Claude can also post the comment.
