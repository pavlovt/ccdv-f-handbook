# Glossary

**A/B testing** — Comparing two variants of a prompt, model, or configuration by splitting real or representative traffic between them and measuring a defined outcome. Use it when offline evals cannot tell you which change users will prefer.

**Agent** — A system in which a model decides, over several steps, which tools to call and what to do next, until a task is complete or a limit is hit. Contrast it with a workflow, where your code decides the sequence of steps.

**Agent loop** — The repeated cycle of sending messages to the model, executing any `tool_use` blocks it returns, appending the `tool_result` blocks, and calling the model again. The loop ends when `stop_reason` indicates a final answer or a limit is reached.

**Anthropic Academy** — Anthropic’s free learning platform, open to anyone with any email address. Its catalog lives at anthropic.com/learn and its courses at anthropic.skilljar.com.

**Batch processing** — Submitting many Messages requests together as an asynchronous job, which is processed later rather than in real time. It is typically priced lower than synchronous calls and suits offline work such as bulk classification or evaluation runs.

**Cache breakpoint** — A marker in a request that tells the API where a cacheable prefix ends. Content before the breakpoint can be reused on later requests if it is identical.

**CCDV-F** — The exam code for Claude Certified Developer – Foundations, the certification this book prepares you for.

**Chain of thought** — A prompting technique in which the model works through intermediate reasoning steps before giving its answer. It can improve accuracy on multi-step problems, at the cost of more output tokens.

**CLAUDE.md** — A Markdown file that Claude Code reads at the start of a session to pick up project instructions, conventions, and context. Keep it short and specific, because everything in it consumes context.

**Confirmation gate** — A point in an agent workflow where execution pauses and a human (or a separate trusted check) must approve an action before it runs. Use it before any action that writes, deletes, sends, or spends money.

**Content block** — A typed element within a message’s `content` array, such as `text`, `image`, `tool_use`, or `tool_result`. A message can contain several blocks of different types.

**Context compaction** — Shortening a long conversation by summarizing or pruning earlier turns so the remaining content fits within the context window. It trades some detail for the ability to continue the task.

**Context window** — The maximum number of tokens a model can consider in a single request, covering the input and the output it generates. Everything you need the model to see must fit inside it.

**CPN (Claude Partner Network)** — The program of organizations that partner with Anthropic. Exam registration and the official prep course are gated to people employed by a CPN organization.

**Credly** — The digital badge platform that issues the badge for a passed Claude certification. The badge is a verifiable record you can share.

**Direct prompt injection** — An attack in which the user’s own input contains instructions meant to override the system prompt or the application’s intended behavior. Defend with clear role boundaries, output validation, and limits on what actions the model can take.

**Domain linking** — The step that connects your company’s email domain to the partner program so that you can register. It takes 7–10 days via partner-support\@anthropic.com.

**Eval set** — A fixed collection of inputs, with expected outputs or grading criteria, used to measure how a prompt, model, or system performs. A good eval set covers normal cases, edge cases, and past failures.

**Exam Guide** — The official scope document for the exam, Exam Guide v1.0 dated July 2026. It sits behind the partner login and is the authoritative source for what the exam covers.

**Exponential backoff** — A retry strategy in which the wait between attempts grows geometrically, usually with random jitter added. It is the standard response to rate limits and transient server errors.

**Extended thinking** — A mode in which the model produces reasoning content before its final answer. The legacy manual form sets a fixed `budget_tokens`; current models use adaptive thinking steered by effort. It can improve performance on hard problems, and the thinking tokens count toward cost and latency.

**Few-shot prompting** — Including a small number of worked input-output examples in the prompt to show the model the expected format or behavior. Examples are often more reliable than a long description of the same rule.

**Grounding** — Constraining a model’s answer to information you supply, such as retrieved documents or tool results, and requiring it to cite that source. Grounded answers are easier to verify and less prone to fabrication.

**Guardrail** — A check placed around a model call, either before the input reaches the model or after the output leaves it, that blocks or flags content that violates a policy. Guardrails complement, but do not replace, least privilege and output validation.

**Hallucination** — A confident output that is not supported by the input, the tools, or reality. Reduce it with grounding, retrieval, citations, and evals that test for it.

**Human-in-the-loop** — A design in which a person reviews or approves model decisions at defined points. It is the practical control for high-impact or irreversible actions.

**Idempotency** — The property that performing an operation more than once has the same effect as performing it once. Retried tool calls that write data must be idempotent, or retries will duplicate side effects.

**Indirect prompt injection** — An attack in which malicious instructions arrive through content the model reads, such as a web page, email, or document retrieved by a tool. The attacker never talks to the model directly.

**JSON Schema** — A standard for describing the structure of JSON data. Tool definitions use it for `input_schema`, and structured output can be constrained to it.

**Least privilege** — Giving a tool, agent, or credential only the permissions it needs for its task. Limit the scopes of API keys and the actions each tool can perform, so that a manipulated model has little to misuse.

**LLM-as-judge** — Using a model to grade another model’s output against a rubric or reference answer. It scales evaluation beyond manual review, but the judge needs its own validation against human grades.

**max\_tokens** — A required request parameter that caps how many tokens the model may generate in its response. A response that stops at this cap has a `stop_reason` of `max_tokens`.

**MCP (Model Context Protocol)** — An open protocol that standardizes how applications expose tools, resources, and prompts to language models. It lets one integration work across any compatible client.

**MCP server** — A process that implements the MCP protocol and exposes tools, resources, or prompts to a client. Your own systems are usually connected to Claude through a server you write or install.

**Messages API** — The primary API for interacting with Claude. You send a list of messages and receive a response made of content blocks, along with a `stop_reason` and token usage.

**Model tier** — A family of models that trade capability against latency and cost. Choose the smallest tier that meets your eval thresholds, and re-test when you change tiers.

**Multimodal input** — Input that combines text with other media, such as images or documents. Each media type has its own size and format limits, which you check in the current documentation.

**OnVUE** — Pearson VUE’s online-proctored delivery option. You take the exam from home or your office under remote supervision, with your webcam, microphone, and screen monitored.

**Orchestrator-worker** — A pattern in which a central model or program breaks a task into subtasks, delegates them to worker agents or calls, and combines the results. Use it when subtasks are independent and the breakdown is not known in advance.

**Output validation** — Checking a model’s output against a schema, a set of rules, or a second check before the system acts on it or shows it to a user. It catches malformed, out-of-policy, or unsafe output.

**Partner gate** — The eligibility rule that limits exam registration and the official prep course to people employed by a CPN organization and registered with a recognized company email domain.

**Pearson VUE** — The testing company that delivers the exam, either online-proctored or at a test center. Your name on its profile must match your government ID exactly.

**PII (personally identifiable information)** — Data that identifies a person, such as names, email addresses, identification numbers, or account details. Minimize it in prompts and logs, and redact it before storing or sending content to a model when the task does not need it.

**Prefill** — Supplying the start of the assistant’s response so the model continues from that text. It is a way to steer format or tone. Check the current documentation for which models support it.

**Prompt caching** — Storing a request’s prefix on the server so that identical prefixes in later requests are processed at a reduced cost and latency. Caching depends on the prefix matching exactly, so place stable content first.

**Prompt chaining** — Splitting a task into a fixed sequence of model calls, where each call’s output feeds the next. It trades flexibility for predictability and is easy to evaluate step by step.

**Prompt injection** — Any attempt to make a model follow instructions that were not intended by the developer. It includes both direct and indirect forms, and no single defense eliminates it.

**RAG (retrieval-augmented generation)** — A pattern in which you retrieve relevant documents for a query and include them in the prompt, so the model answers from that content. Retrieval quality usually matters more than prompt wording.

**Rate limit** — A cap on how many requests or tokens your organization may send within a time window. Exceeding it returns an error, and your client should back off and retry.

**Recertification** — Renewing a certification before it expires. For this program, it is a free, non-proctored assessment.

**Regression testing** — Re-running an eval set after every change to a prompt, model, or tool, to catch behavior that previously worked and now fails. It is the main protection against silent quality loss.

**Retake waiting period** — The mandatory delay before you may retry a failed exam: 14 days after the first fail, 30 days after the second, and 90 days after the third. You may make at most 4 attempts in a rolling 12 months.

**Routing** — Sending each input to a specialized prompt, model, or workflow based on a classification step. Routing lets you use cheaper or faster paths for simple cases.

**Sampling** — The process of choosing each next token from the model’s probability distribution. Parameters such as temperature and top-p control how much randomness enters sampling.

**Scaled score** — The exam’s reported score, on a scale from 100 to 1000. A score of 720 or higher is a pass. It is not a percentage of questions answered correctly.

**Scenario-based multiple response** — A question type in which a described situation is followed by a prompt asking you to select more than one correct answer. Read the whole stem and every option before selecting.

**SSE (server-sent events)** — A one-way streaming protocol in which the server sends a sequence of events over a single HTTP response, each formatted as text. Streamed Messages API responses use it.

**Stdio transport** — An MCP transport in which the client launches the server as a subprocess and exchanges JSON-RPC messages over its standard input and output. It is the usual choice for local servers.

**Stop reason** — A field in the response that explains why generation ended, such as `end_turn`, `max_tokens`, `stop_sequence`, or `tool_use`. Your agent loop branches on it.

**Stop sequence** — A custom string you supply, at which the model stops generating. The response then reports a `stop_reason` of `stop_sequence`.

**Streaming** — Receiving the model’s response incrementally as it is generated, rather than waiting for the full message. It reduces perceived latency and is delivered as a series of events.

**Structured output** — A response constrained to a defined format, usually JSON that matches a schema. Pair it with output validation, because a format constraint does not guarantee that the values are correct.

**Subagent** — A separate model invocation, with its own context and often a narrower toolset, that performs a delegated task and returns a result to the parent. Its main value is keeping the parent’s context clean.

**Success criteria** — The measurable conditions that define a system as good enough, such as accuracy thresholds, latency budgets, or refusal rates. Define them before you build, so evals have something to measure.

**System prompt** — Instructions supplied separately from the conversation that set the model’s role, constraints, and context for the whole session. It is the right place for rules that should apply to every turn.

**Temperature** — A sampling parameter that controls randomness. Lower values make output more deterministic, and the Claude API accepts values from 0 to 1.

**Thinking block** — A response content block of type `thinking` with a `thinking` field (a summary of the reasoning, or an empty string under `display: "omitted"`) and an encrypted `signature`. It must be passed back unmodified during tool use. Safety-redacted reasoning arrives instead as a `redacted_thinking` block with an encrypted `data` field.

**Token** — The unit a model reads and generates, typically a fragment of a word. Tokens determine cost, latency, and whether content fits within the context window.

**Tool choice** — A request parameter that controls whether and how the model may call tools. Common settings let the model decide, require some tool, require a specific tool, or forbid tools.

**Tool definition** — The description of a tool sent with a request: its name, a description the model reads to decide when to use it, and an `input_schema` in JSON Schema form. Vague descriptions cause wrong tool choices.

**Tool result block** — A `tool_result` content block, sent back by your code in a user turn. It carries the output of a tool call and is matched to the call by its ID.

**Tool use** — The mechanism by which the model requests that your code run a function, instead of answering directly. Your code runs the function and returns the result to the model.

**Tool use block** — A `tool_use` content block in the model’s response. It names the tool, provides its input, and has an ID that the matching `tool_result` must reference.

**Trust boundary** — The line between content your system trusts, such as the system prompt and your own code, and content it does not, such as user input, retrieved documents, and tool output. Controls should sit at each boundary crossing.

**Workflow** — A system in which your code defines the sequence of model calls and tool uses in advance. Workflows are more predictable and easier to test than agents, and the exam expects you to know when each fits.

**XML tagging** — Wrapping parts of a prompt in tags such as `<document>` or `<instructions>` to separate data from instructions. Tags make it clearer to the model where one kind of content ends and another begins.
