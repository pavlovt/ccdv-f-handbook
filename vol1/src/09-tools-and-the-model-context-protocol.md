# Tools and the Model Context Protocol

A language model on its own can only emit text. Tool use is the mechanism that turns that text into actions: querying a database, calling an internal API, running a shell command. This chapter covers how the tool-use loop works at the wire level, how to design tools a model can use correctly, how to handle the failure modes you will see in production, and how the Model Context Protocol (MCP) standardizes tool integration across applications.

## How Tool Use Actually Works

The model never executes anything. It produces a structured request, and your code (or Anthropic’s infrastructure, for server tools) does the work. For a client tool, one round trip looks like this:

1.  You send a request that includes a `tools` array describing what is available.
2.  The model decides, based on the conversation and the tool descriptions, whether to call a tool. If it does, the response contains one or more `tool_use` content blocks and `stop_reason` is `"tool_use"`.
3.  Your code runs the operation.
4.  You send a new request. It contains the full history so far, including the assistant turn exactly as returned, followed by a user message holding `tool_result` blocks.
5.  The model reads the results and either answers or requests more tools. You repeat until `stop_reason` is something other than `"tool_use"`.

Be clear about what reaches your function. The `messages` you send go to the model, not to the tool. The model reads the conversation and writes the tool’s arguments itself, in the `input` field of the `tool_use` block, and that object is the only thing your code passes to the tool. If a customer writes “Order ORD-20481932 arrived smashed. Refund the \$19.99.”, the user message is an English sentence, but the call the model produces is:

``` {.sourceCode .json}
{
  "type": "tool_use",
  "id": "toolu_01AbC",
  "name": "refund_order",
  "input": { "order_id": "ORD-20481932", "amount_cents": 1999, "reason": "damaged" }
}
```

The model has done a translation: it found the order ID in the sentence, turned “\$19.99” into the integer `1999` because the schema asks for cents, and mapped “smashed” onto `damaged`, one of the values the schema allows. Your code then calls `refund_order(**block.input)`. Every way a tool call can go wrong (a missing field, a wrong type, a value outside the enum, a plausible but wrong ID) is a fault in that translation step, which is why the later sections on schemas, strict mode and validation all focus on `input`.

Two properties of this loop matter for everything that follows. First, the API is stateless: every request must carry the whole conversation, so the `tool_use` blocks from step 2 must be present in the history when you submit the results in step 4. Second, the decision to call a tool is made by the model from text alone. The description you wrote is the only evidence it has about what your function does.

Tool definitions count as input tokens on every request, and each model adds a small fixed system-prompt overhead whenever tools are enabled. Large tool catalogs therefore cost money and latency, and they also dilute the model’s attention; we return to this when discussing granularity and tool search.

## The Tool Definition Schema

Each entry in the `tools` array is a JSON object. For a user-defined (client) tool the fields are:

  ------------------------------------------------------------------------------------------------------------------------------------------------------------
  Field                   Required                Purpose
  ----------------------- ----------------------- ------------------------------------------------------------------------------------------------------------
  `name`                  Yes                     Identifier the model uses to call the tool. Must match `^[a-zA-Z0-9_-]{1,128}$`.

  `description`           Strongly recommended    Plain-text explanation of what the tool does, when to use it, and its limits.

  `input_schema`          Yes                     A JSON Schema object (`"type": "object"`) describing the parameters.

  `input_examples`        No                      Array of example input objects. Each must validate against `input_schema` or the request fails with a 400.

  `strict`                No                      When `true`, sampling is constrained so that tool inputs conform to the schema.

  `cache_control`         No                      Prompt-caching breakpoint on the tool entry.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------

A complete definition for a support-desk system:

``` {.sourceCode .json}
{
  "name": "lookup_order",
  "description": "Retrieve a single customer order by its order ID. Use this when the customer mentions a specific order number (format ORD- followed by 8 digits) or when you already have an order ID from another tool result. Returns status, line items, shipping address and tracking number. Does NOT search by customer name or email; use find_customer_orders for that. Returns an error object if the ID does not exist.",
  "input_schema": {
    "type": "object",
    "properties": {
      "order_id": {
        "type": "string",
        "pattern": "^ORD-[0-9]{8}$",
        "description": "The order identifier, e.g. ORD-20481932. Never guess or construct one; it must come from the user or a previous tool result."
      },
      "include": {
        "type": "array",
        "items": { "type": "string", "enum": ["line_items", "shipping", "payments"] },
        "description": "Optional sections to include. Defaults to line_items and shipping."
      }
    },
    "required": ["order_id"]
  }
}
```

The `input_schema` is ordinary JSON Schema, so everything you know applies: `type`, `enum`, `pattern`, `minimum`/`maximum`, nested objects, arrays with `items`, and per-property `description`. Property descriptions are part of what the model reads, so use them. Without `strict: true`, the schema guides generation but is not a hard guarantee; we cover that distinction in the section on malformed arguments.

### Why the description is the highest-leverage field

Anthropic’s guidance is blunt: detailed descriptions are the most important factor in tool performance. The model chooses between tools and fills in arguments by reading prose. A tool named `search` with the description “Searches” forces the model to guess what is searched, when it is appropriate, and what the query should look like. A good description covers:

-   **What** the tool does and what it returns, including what it does not return.
-   **When** to use it, and just as important, when not to, naming the sibling tool that handles the neighboring case.
-   **Parameter semantics**: formats, units, valid ranges, where values come from.
-   **Behavior and limits**: side effects, rate limits, pagination, what an error looks like.

A rule of thumb from the documentation is at least three to four sentences per tool, more for complex ones. When a schema alone cannot convey a tricky format, `input_examples` add concrete cases at modest token cost. Descriptions beat every other lever you have: before adding retry logic, a router model, or a bigger prompt, read your descriptions as if you were seeing the tool for the first time.

One warning from the same guidance: avoid adding a parameter that asks the model to explain its reasoning step by step. Ask for a short rationale if you need one; requests to expose chain-of-thought can trigger a refusal.

## Designing Tool Interfaces the Model Can Use Correctly

Treat the tool surface as an API whose only consumer is an inattentive but literate colleague.

**Naming.** Use verb-noun names that describe the action (`create_ticket`, `list_invoices`). When you operate many tools across services, namespace with a prefix such as `github_list_prs` or `slack_send_message`; this is especially valuable once tool search is in play. Names that differ only in a suffix (`get_user`, `get_user_v2`, `get_user_info`) invite wrong picks.

**Granularity.** Too many narrow tools and the model must choose among near-duplicates; one mega-tool with fifty optional parameters and the model must reason about which combinations are legal. The documented guidance is to consolidate related operations, for example one `pull_request` tool with an `action` enum instead of separate create, review and merge tools, while keeping each tool’s purpose clear. A good test is whether a new engineer reading the tool list could say which tool applies to a given request in under ten seconds. Also design around the task, not around your internal endpoints: one `schedule_meeting` tool that checks availability and books is better than exposing five low-level calendar endpoints the model must orchestrate.

**Required versus optional.** Mark a parameter `required` only if the tool cannot work without it. Required parameters that the model cannot know will be hallucinated; optional ones with sensible defaults will be omitted. Document the default in the description. If a value must come from an earlier tool call (an ID, a cursor), say so explicitly, and say what to do if it is missing.

**Enums over free text.** Anything that has a closed set of values should be an `enum`. Free-text `"status": "open"` will come back as `"Open"`, `"OPEN"`, `"opened"` and `"in progress"`. An enum eliminates the whole class of error and doubles as documentation. Use `pattern`, `minimum`, `maximum` and `format` for the same reason on strings and numbers.

**Return high-signal output.** What the tool returns is part of the interface. Return semantic, stable identifiers (slugs, UUIDs) rather than opaque internal handles, trim fields the model does not need, and paginate large result sets. A 40,000-token JSON blob wastes context and buries the answer.

**Avoid ambiguous overlap.** If two tools could plausibly serve a request, the descriptions must state the boundary. “Use `find_customer_orders` for searches by customer; use `lookup_order` when you have an order ID” resolves most mis-selections without any code.

## The Content Blocks and Conversation Construction

Responses and requests carry typed content blocks. The two that matter here:

`tool_use` appears in an assistant message:

``` {.sourceCode .json}
{
  "type": "tool_use",
  "id": "toolu_01A09q90qw90lq917835lq9",
  "name": "lookup_order",
  "input": { "order_id": "ORD-20481932" }
}
```

`tool_result` appears in the following user message:

  -------------------------------------------------------------------------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -------------------------------------------------------------------------------------------------
  `type`                              `"tool_result"`

  `tool_use_id`                       The `id` of the `tool_use` block this answers. Required.

  `content`                           A string, or a list of content blocks (`text`, `image`, `document`, `search_result`). Optional.

  `is_error`                          Set `true` when the tool failed. Optional.
  -------------------------------------------------------------------------------------------------------------------------------------

The assistant message may also contain a `text` block before the `tool_use` block. Treat it as ordinary prose and do not parse it for control flow.

The history for a single tool round trip is therefore:

    user:      "Where is order ORD-20481932?"
    assistant: [text?, tool_use(id=toolu_A, name=lookup_order, input={...})]
    user:      [tool_result(tool_use_id=toolu_A, content="...")]
    assistant: "It shipped yesterday and arrives Thursday."   <- stop_reason: end_turn

The construction rules are strict, and breaking them produces a 400 error:

1.  The `tool_result` message must come **immediately after** the assistant message containing the matching `tool_use`. Nothing may sit in between.
2.  Inside that user message, `tool_result` blocks must come **first**. Any text goes after all of them. Putting text first yields the error “tool\_use ids were found without tool\_result blocks immediately after.”
3.  Every `tool_use` id in the assistant turn needs a matching `tool_result`. No exceptions, even for calls you chose to skip.
4.  Append the assistant turn to your history unchanged, using the content the API returned, so ids and block order are preserved.

### A complete cycle in Python

This is a full loop with an order-lookup tool, including error handling and a safety cap on iterations.

``` {.sourceCode .python}
import json
import anthropic

client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY
MODEL = "claude-sonnet-5-5"             # substitute the model you deploy

tools = [{
    "name": "lookup_order",
    "description": (
        "Retrieve one customer order by order ID (format ORD- plus 8 digits). "
        "Use when the user gives an order number. Returns status, items and "
        "tracking number. Cannot search by customer; the ID must come from "
        "the user or a previous tool result. Returns an error if not found."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "pattern": "^ORD-[0-9]{8}$",
                "description": "Order identifier, e.g. ORD-20481932.",
            }
        },
        "required": ["order_id"],
    },
}]

ORDERS = {"ORD-20481932": {"status": "shipped", "eta": "Thursday", "tracking": "1Z999"}}

class ToolInputError(Exception):
    pass

def lookup_order(order_id: str) -> dict:
    if order_id not in ORDERS:
        raise ToolInputError(f"No order {order_id}. Ask the user to confirm the number.")
    return ORDERS[order_id]

HANDLERS = {"lookup_order": lookup_order}

def execute(block) -> dict:
    """Run one tool_use block and return a tool_result block."""
    result = {"type": "tool_result", "tool_use_id": block.id}
    handler = HANDLERS.get(block.name)
    try:
        if handler is None:
            raise ToolInputError(f"Unknown tool '{block.name}'. Available: {list(HANDLERS)}")
        result["content"] = json.dumps(handler(**block.input))
    except (ToolInputError, TypeError) as exc:      # bad or missing arguments
        result["content"] = f"Invalid call: {exc}"
        result["is_error"] = True
    except Exception as exc:                        # genuine failure in our code
        result["content"] = f"Tool failed ({type(exc).__name__}). You may retry once."
        result["is_error"] = True
    return result

messages = [{"role": "user", "content": "Where is order ORD-20481932?"}]

for _ in range(8):                                  # hard cap on loop iterations
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "max_tokens":
        raise RuntimeError("Truncated; a tool_use block may be incomplete. Raise max_tokens.")
    if response.stop_reason != "tool_use":
        break                                       # end_turn, refusal, etc.

    results = [execute(b) for b in response.content if b.type == "tool_use"]
    messages.append({"role": "user", "content": results})   # all results, one message

print("".join(b.text for b in response.content if b.type == "text"))
```

Notice what the loop does not do: it never inspects the assistant’s prose to decide whether to continue, and it never mutates `response.content`. The only control signal is `stop_reason`. Other values you may meet are `end_turn` (finished), `max_tokens` (cut off, and if the last block is a half-written `tool_use`, retry with a larger limit), `refusal`, and `pause_turn`, which applies only to server-tool loops.

## Controlling Tool Choice

The `tool_choice` parameter governs whether and how the model calls tools:

  -----------------------------------------------------------------------------------------------------
  Value                               Behavior
  ----------------------------------- -----------------------------------------------------------------
  `{"type": "auto"}`                  The model decides. This is the default when tools are supplied.

  `{"type": "any"}`                   The model must call one of the supplied tools, but picks which.

  `{"type": "tool", "name": "..."}`   The model must call exactly that tool.

  `{"type": "none"}`                  No tool calls. This is the default when no tools are supplied.
  -----------------------------------------------------------------------------------------------------

Use `tool` to force structured extraction: define a `record_invoice` tool whose schema is the output you want, force it, and read the `input`. Use `any` when a plain-text reply would be a bug in your pipeline. Use `none` when you want to keep tool definitions in the request, for cache stability or because earlier turns contain tool blocks, but do not want further calls.

Details worth knowing for the exam and for production:

-   With `any` or `tool`, the API starts the assistant turn for the model so that it opens directly with the tool call (the turn is prefilled). The model therefore emits no explanatory text before the `tool_use`. If you want prose alongside the call, use `auto` and instruct it in the prompt.
-   Forcing a tool is incompatible with manual extended thinking (`thinking: {type: "enabled"}`); that combination returns an error. Adaptive thinking is allowed, but a forced call skips the thinking step.
-   On the newest models, forcing is not available at all: Opus 5.5, Sonnet 5.5, Fable 5.1, and Mythos 5.1 reject `any` and `tool` with a 400. Check the support matrix for the model you deploy. The portable alternative is `auto` with `strict: true` tools, or structured outputs when you only need a fixed JSON shape.
-   Changing `tool_choice` between requests invalidates cached message blocks under prompt caching; tool definitions and the system prompt stay cached.

## Parallel Tool Calls

The model may return several `tool_use` blocks in one assistant turn when the calls are independent. The API gives no ordering; you can run them concurrently with `asyncio.gather` or sequentially. Run independent reads in parallel; run anything with side effects or ordering requirements sequentially.

The response format is the critical detail: return **one `tool_result` per `tool_use`, all in a single user message**, each matched by `tool_use_id`, all before any text. Sending results in separate user messages is wrong twice over: it breaks the adjacency rule, and the documentation notes it teaches the model to stop issuing parallel calls. If you deliberately skip a call (say, an earlier write failed), you must still return a result for it, flagged `is_error: true`, with an explanatory message like “Not executed: the preceding write failed.”

To limit the model to one call per turn, set `disable_parallel_tool_use: true` inside `tool_choice`, for example `{"type": "auto", "disable_parallel_tool_use": true}`. With `auto` it means at most one call; with `any` or `tool` exactly one (and that variant is not supported on the newest model generations). It is a field of `tool_choice`, not a top-level parameter.

If the model fires dependent calls in parallel and the second one fails because its prerequisite had not finished, do not disable parallelism wholesale. Return the failure with `is_error: true`; the model will reissue the call on the next turn. Add a line to the system prompt such as “only batch tool calls that are independent of each other.” To encourage more parallelism, a system prompt instructing the model to invoke all independent tools simultaneously works, and the metric to watch is average tool calls per tool-calling message, which should exceed 1.0.

## Errors: Return Them or Raise Them

There are two distinct audiences for a failure. The model can recover from some failures; your operations team must see others.

**Return to the model** (with `is_error: true`) when the failure is something the model could fix or explain: invalid arguments, a record that does not exist, a validation rule violated, a rate limit with a retry hint, a transient upstream error. Make the message instructive. “failed” gives the model nothing; “No order ORD-123: IDs have 8 digits. Ask the user to confirm the number” lets it self-correct or relay accurately. The documentation notes that when parameters are invalid or missing, the model typically retries two to three times with corrections before apologizing, so a precise error converts directly into a successful retry.

**Raise in your own code** when the failure is yours and the model cannot help: a bug in your handler, a misconfigured credential, an unrecoverable infrastructure outage, a security policy violation. Log it, alert on it, and either abort the conversation or return a sanitized `is_error` message that does not leak stack traces, hostnames or secrets. The model should never see a raw traceback.

Two anti-patterns recur. One is letting an unhandled exception escape the loop, leaving the conversation with a dangling `tool_use` and no result; the next request will 400 on the missing `tool_result`. The other is swallowing the error and returning an empty or success-shaped result, which the model will happily treat as truth and build an answer on. Always put the failure in the result.

Also cap the loop. A model that is consistently getting errors can retry indefinitely; an iteration limit, a budget limit, and a repeated-identical-call check turn a runaway into a clean failure.

## Hallucinated and Malformed Arguments

Even a well-described tool will occasionally receive bad input. Know the layers of defense.

**Prevention in the definition.** Tight schemas (enums, patterns, ranges, `required`), explicit provenance for IDs (“must come from a previous tool result”), and `input_examples` for tricky formats prevent most problems.

**Strict tool use.** Without `strict`, the `input_schema` is guidance the model almost always follows, but nothing enforces it. Take the refund tool from the start of the chapter. Once in a while its `input` can arrive in one of these shapes:

``` {.sourceCode .json}
{"order_id": "ORD-20481932", "amount_cents": "1999", "reason": "damaged"}
{"order_id": "ORD-20481932", "reason": "broken"}
{"order_id": "ORD-20481932", "amount_cents": 1999, "reason": "late", "notify": true}
```

The first sends the number as a string. The second leaves out a required field and uses a reason that is not in the enum. The third adds a field the tool never defined. Each one reaches your function unless you check for it.

Setting `"strict": true` on the tool makes the schema a hard rule. The API restricts what the model can generate while it writes the arguments, so the only output it can produce is JSON that matches the schema. Nothing is checked or rejected afterwards; an invalid call cannot be produced in the first place. The tool `name` is also always one you supplied. Two changes turn it on:

``` {.sourceCode .python}
tools = [{
    "name": "refund_order",
    "description": "Refund a customer order. The order ID must come from the user or lookup_order.",
    "strict": True,                          # 1. on the tool, next to name and description
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id":     {"type": "string"},
            "amount_cents": {"type": "integer"},
            "reason":       {"type": "string", "enum": ["damaged", "late", "wrong_item"]},
        },
        "required": ["order_id", "amount_cents", "reason"],
        "additionalProperties": False,       # 2. required on every object in a strict schema
    },
}]
```

Now the only shape the call can take is `{"order_id": "...", "amount_cents": 1999, "reason": "damaged"}`: an integer amount, one of the three reasons, nothing missing and nothing extra. This removes the validate-and-retry code you would otherwise write for structural errors. Note where `strict` goes: at the top level of the tool definition, not inside `input_schema` and not on `tool_choice`. The schema is also limited to the subset described in Chapter 5, so `minimum`, `maximum`, `minLength` and `maxLength` are not allowed; a rule such as “no more than 50000 cents” has to be checked in your handler.

Strict mode does not make the values correct. A schema-valid date can still be the wrong date, a valid enum member can still be the wrong member, and a well-formed order ID can still belong to a different customer. It also does not guarantee that the model calls a tool at all. On models that reject forced `tool_choice`, the usual pattern is `auto` plus a strict tool, with the prompt telling the model which tool to use. Two exceptions remain: a response that stops with `stop_reason` `refusal` or `max_tokens` can leave the arguments incomplete, so check `stop_reason` before running anything.

**Validation in your handler.** Treat tool input as untrusted user input, because it is derived from untrusted text. Validate types and ranges, check authorization for the acting user (never trust a `user_id` the model supplies), and verify that referenced entities exist. A hallucinated ID will usually fail the existence check; return an error that tells the model where valid IDs come from.

**Recovery.** Return the validation error with `is_error: true` and let the model retry. If a specific argument keeps going wrong, the fix is almost always in the description or schema, not in more retries.

**Dangerous actions.** For irreversible operations, add a human confirmation step outside the model: have the tool return a preview or a pending-approval status, and require explicit approval before the real action. The model’s confidence is not an authorization mechanism.

The natural place for the check is inside the handler, immediately before the side effect. Whatever the model decided, and whether your own loop or an SDK helper calls the function, nothing happens until a person agrees. Here is the refund handler with an approval step:

``` {.sourceCode .python}
AUTO_APPROVE_LIMIT_CENTS = 500          # refunds up to $5.00 need no human

def ask_operator(order_id: str, amount_cents: int, reason: str) -> bool:
    """Show the pending refund and wait for a yes or no from a person."""
    print(f"Refund {order_id}: ${amount_cents / 100:.2f} ({reason})")
    return input("Approve? [y/N] ").strip().lower() == "y"

def refund_order(order_id: str, amount_cents: int, reason: str) -> str:
    if order_id not in ORDERS:
        raise ToolInputError(f"No order {order_id}. Use lookup_order to find the ID.")

    # The approval gate: runs before any money moves.
    if amount_cents > AUTO_APPROVE_LIMIT_CENTS:
        if not ask_operator(order_id, amount_cents, reason):
            return (f"Refund for {order_id} was NOT issued: an operator declined it. "
                    "Tell the customer the request has been passed to the support team.")

    issue_refund(order_id, amount_cents)     # the real payment call
    return f"Refund of {amount_cents} cents issued for {order_id}. Ref: RF-7781"
```

Four choices in this code matter more than its details:

-   **The default is no.** With `[y/N]`, anything other than an explicit `y`, including just pressing Enter, declines. For an action that moves money, a mistake should leave things as they were.
-   **A decline is a normal result, not an error.** The tool worked correctly and a person said no, so the handler returns a plain string without `is_error`. The model reads it and tells the customer what happened. Marking it as an error would suggest something broke, and the model might retry the call.
-   **The operator sees the arguments that will be executed.** The prompt shows the model’s `input` (order, amount, reason), not the customer’s original sentence. If the model misread “\$19.99”, the operator catches it here.
-   **A threshold keeps people for the cases that matter.** Small refunds go through without a person. Set the limit to match the risk.

`input()` works only when someone is at the terminal. In a web application the gate has the same shape, but it does not wait: `ask_operator` records the pending refund (an approvals table, a chat message with Approve and Decline buttons) and the handler returns at once with a status such as “Refund for ORD-20481932 is awaiting approval (ticket APR-311).” The model tells the customer the request is pending, and the refund is issued later by whatever handles the Approve button, outside the model loop.

## Server-Side and Built-In Tools

Not every tool runs in your process. The distinction is who executes it.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
                          Client tools                                                                             Server tools
  ----------------------- ---------------------------------------------------------------------------------------- ----------------------------------------------------
  Runs on                 Your application                                                                         Anthropic’s infrastructure

  Signal                  `stop_reason: "tool_use"`, you return `tool_result`                                      Results appear in the response; you do nothing

  Examples                Your own tools; Anthropic-schema tools such as bash, text editor, memory, computer use   Web search, web fetch, code execution, tool search
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Anthropic-schema client tools** (bash, text editor, memory, computer use) have schemas Anthropic publishes and the models are trained on, but you implement and sandbox the execution. Because the model is trained on the exact schema, these tend to work better than a hand-rolled equivalent, and the security responsibility is entirely yours.

**Server tools** run inside the API call. Web search returns cited results, web fetch retrieves pages and PDFs, code execution runs Python and bash in a sandboxed container, and tool search lets the model discover tools on demand from a very large catalog instead of loading every definition up front (a mitigation for the token and attention cost mentioned earlier). Some server tools carry usage fees beyond tokens.

Two operational notes. If a server-tool loop reaches its iteration limit, the response ends with `stop_reason: "pause_turn"`; send the assistant content back unchanged to let the model continue. And if a response mixes a server tool with a client tool in the same parallel group, you may see a `server_tool_use` block with no result yet: return `tool_result` blocks for every client `tool_use`, keep the same `tools` array, and put only `tool_result` blocks in that user message.

## The Model Context Protocol

### The problem

Without a standard, every AI application integrates every data source and capability by hand. N applications and M systems means N times M bespoke connectors, each with its own auth, schema translation and bugs. MCP is an open protocol that collapses this to N plus M: a system exposes an MCP server once, and any MCP-capable application can use it.

### Architecture

MCP has three participants:

-   **Host**: the AI application (Claude Code, Claude Desktop, an IDE, your own app) that coordinates everything and talks to the model.
-   **Client**: a component inside the host that maintains one dedicated connection to one server. A host with four servers runs four clients.
-   **Server**: a program that provides context and capabilities. “Local” and “remote” describe where it runs, not what it is.

The protocol has two layers. The **data layer** is JSON-RPC 2.0 messages defining the primitives, capability negotiation and notifications. The **transport layer** carries those messages and handles connection setup and authorization. Because the data layer is transport-independent, the same server logic works over either transport.

One version note. Earlier revisions of the specification opened every connection with an `initialize` handshake that negotiated protocol version and capabilities and then held per-connection state. The current documentation describes a stateless design in which each request carries the protocol version and client capabilities in its `_meta` field, and a `server/discover` request is available (but optional) for learning a server’s supported versions and capabilities. The practical idea is stable across revisions: both sides declare what they support, and neither attempts operations the other did not advertise. Do not memorize handshake details without checking which revision a question assumes.

### Transports

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Transport               How it works                                                                                                                                                                                                                Typical use
  ----------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------------------------------------------------
  **stdio**               The host launches the server as a child process and exchanges messages over stdin/stdout.                                                                                                                                   Local tools on the same machine: filesystem, local database, developer utilities. One client per server process; no network.

  **Streamable HTTP**     The client sends messages with HTTP POST; the server may stream responses using Server-Sent Events. Supports standard HTTP auth (bearer tokens, API keys, custom headers); OAuth is the recommended way to obtain tokens.   Remote, shared servers serving many clients, such as a SaaS vendor’s hosted server.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Older material also describes a standalone SSE transport; it is deprecated in favor of Streamable HTTP, though some clients still accept it.

A stdio rule that causes real incidents: **never write to stdout from a stdio server except protocol messages.** A stray `print()` corrupts the JSON-RPC stream. Log to stderr or to a file.

### Primitives

Servers expose three primitives. Each has list and retrieval methods (`tools/list`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`) plus `tools/call` for execution.

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Primitive         What it is                                              Who controls use                                   Example
  ----------------- ------------------------------------------------------- -------------------------------------------------- -------------------------------------
  **Tools**         Executable functions with a JSON Schema `inputSchema`   The model decides to call them                     `query_database`, `create_issue`

  **Resources**     Read-only context data identified by URI                The application (or user) decides what to attach   Database schema, a file, a document

  **Prompts**       Reusable templates or workflows                         The user selects them, often as slash commands     “Review this PR” template
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------

Note the field name: MCP tools use `inputSchema` (camelCase), while the Messages API uses `input_schema`. A host translates between them when it hands MCP tools to the model.

Clients can offer primitives back to servers. Elicitation lets a server ask the user for more input or confirmation mid-operation. Sampling (a server requesting a model completion through the client) and server logging are marked deprecated in the latest revision, with direct provider APIs and stderr or OpenTelemetry logging recommended instead. Servers can also announce that their tool list changed; clients that opted in re-list tools and refresh what the model sees.

Under the hood an MCP tool call is a JSON-RPC request:

``` {.sourceCode .json}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
 "params": {"name": "weather_current", "arguments": {"location": "Sofia", "units": "metric"}}}
```

and the result carries a `content` array of typed items (text, images, embedded resources). The host takes that content and packages it as a `tool_result` for the model. The model never speaks MCP; the host does.

### A minimal server

With the Python SDK, a tool is a decorated, type-annotated function; the docstring becomes the description and the annotations become the schema. The SDK’s server class has been renamed across releases (older material shows `FastMCP`; current docs show `MCPServer`), so check your installed version.

``` {.sourceCode .python}
from mcp.server import MCPServer

mcp = MCPServer("inventory")

@mcp.tool()
async def stock_level(sku: str) -> str:
    """Return units on hand for one SKU (format ABC-1234).

    Use when asked about availability of a specific product. Does not
    reserve stock and does not search by product name.

    Args:
        sku: Stock-keeping unit, e.g. ABC-1234.
    """
    ...

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Everything said earlier about descriptions applies unchanged: the docstring is the description, and it is still the highest-leverage text you write.

### When to build an MCP server rather than hand-wire tools

Hand-wiring (defining tools in your own `tools` array and writing handlers in the same codebase) is the right default for a single application with a handful of tools that live next to your business logic. It has the least moving parts, the simplest deployment and full control.

Build an MCP server when:

-   **Multiple applications or agents need the same capability.** One server replaces N integrations.
-   **The capability is owned by a different team** or vendor and should be versioned and deployed independently.
-   **You want to use the existing ecosystem**: community or vendor servers for GitHub, databases, issue trackers and so on, instead of rewriting them.
-   **You need a security boundary.** Credentials and network access live in the server process rather than in every agent.
-   **Hosts such as Claude Code or Claude Desktop must reach it** without you modifying the host.

Do not build one just for the sake of it. An MCP server for a single in-process function adds a process, a protocol and an auth story for no benefit. Also remember that exposing many tools has a context cost, which is why large servers pair well with tool search and per-tool allowlists.

### Connecting MCP servers to Claude

There are three integration paths, and mixing up the first two is a common error.

**1. Your own application, via the Messages API MCP connector.** The API can connect to **remote** MCP servers for you, in beta (a `betas` header such as `mcp-client-2025-11-20`). You pass the server in `mcp_servers` and enable its tools with an `mcp_toolset` entry in `tools`:

``` {.sourceCode .python}
response = client.beta.messages.create(
    model=MODEL,
    max_tokens=1000,
    betas=["mcp-client-2025-11-20"],
    messages=[{"role": "user", "content": "List open tickets assigned to me."}],
    mcp_servers=[{
        "type": "url",
        "url": "https://tickets.example.com/mcp",
        "name": "tickets",
        "authorization_token": ACCESS_TOKEN,   # you obtain and refresh the OAuth token
    }],
    tools=[{
        "type": "mcp_toolset",
        "mcp_server_name": "tickets",
        "default_config": {"enabled": False},                 # allowlist pattern
        "configs": {"list_tickets": {"enabled": True}},
    }],
)
```

Key facts: the URL must be `https://`; each server in `mcp_servers` must be referenced by exactly one `mcp_toolset`; the connector supports tool calls only, not resources or prompts; it connects over Streamable HTTP or SSE, and **local stdio servers cannot be connected directly**; you handle the OAuth flow and token refresh yourself. Allowlists (disable by default, enable specific tools) or denylists restrict what the model can call. Responses contain `mcp_tool_use` and `mcp_tool_result` blocks, and the API executes the call server-side, so you do not write a tool loop for these. The connector is not covered by zero-data-retention arrangements.

**2. Your own MCP client.** When you need stdio servers, resources, prompts, or full control over approval and logging, your application embeds an MCP client (the official SDKs provide one). It lists the server’s tools, converts each to the Messages API shape (`inputSchema` becomes `input_schema`), passes them as ordinary client tools, and when the model emits a `tool_use` routes it to `tools/call` on the right server, then returns the content as a `tool_result`. In this model you own the loop, so you decide which calls need user approval.

**3. Hosts.** Claude Code and Claude Desktop are MCP hosts. You register servers in their configuration and they handle the client side. Chapter 10 covers Claude Code’s commands for this.

Security applies on every path. A tool description or result from a third-party server is untrusted input that can contain instructions aimed at the model (prompt injection). Prefer allowlists to expose only the tools you need, require confirmation for state-changing operations, scope credentials narrowly, and treat servers you did not write like third-party dependencies.

## Chapter Summary

-   The model requests; your code executes. The loop is declare, decide, execute, return, continue, driven by `stop_reason`.
-   The description is the highest-leverage field. Explain what, when, when not, and parameter provenance.
-   Prefer enums, tight schemas, consolidated tools with clear boundaries, and high-signal outputs.
-   `tool_result` blocks go first, immediately after the matching assistant turn, one per `tool_use`, all in one user message.
-   Use `tool_choice` to force or forbid; know its limits with thinking and newer models.
-   Return recoverable errors with `is_error: true` and an instructive message; raise and log your own bugs.
-   `messages` go to the model; the tool receives only the `input` the model writes from them.
-   `strict: true` guarantees shape, not truth. Validate and authorize in the handler.
-   Gate irreversible actions inside the handler, before the side effect. Default to no, and return a decline as a normal result, not an error.
-   MCP standardizes integration: host, client, server; stdio and Streamable HTTP; tools, resources, prompts. Build a server when many consumers share a capability; otherwise hand-wire.
-   The API’s MCP connector reaches remote servers only and supports tools only.

## Practice Questions

**Q9.1** Your support agent has a tool named `search` with the description “Searches.” In logs, the model frequently calls it with one-word queries like “refund” and sometimes uses it when it should be calling `lookup_order`. What is the most effective first change?

A. Add a system prompt paragraph listing every tool by name and repeating when to use each. B. Rewrite the tool name and description to state what is searched, what a good query looks like, what it returns, and when to use `lookup_order` instead. C. Set `tool_choice` to force `lookup_order` whenever the user message contains digits. D. Add a `reasoning` string parameter so the model explains each choice before calling.

**Q9.2** After a `stop_reason` of `tool_use`, your code appends the assistant message and then sends this user message. The API returns a 400 saying `tool_use` ids were found without `tool_result` blocks immediately after.

``` {.sourceCode .python}
{"role": "user", "content": [
    {"type": "text", "text": "Here is the data you asked for:"},
    {"type": "tool_result", "tool_use_id": "toolu_01", "content": "42 rows"},
]}
```

What is the fix?

A. Move the text into the system prompt, because user messages cannot mix text and tool results. B. Wrap the text block inside the `content` of an assistant message instead. C. Place the `tool_result` block before the text block in the same user message. D. Send the text and the `tool_result` as two consecutive user messages.

**Q9.3** The model returns an assistant turn with three `tool_use` blocks. Your loop is written for single calls and executes only the first block, then sends one `tool_result`. The next request fails with a 400. What should the loop do?

A. Execute every `tool_use` block and return one `tool_result` for each id, all in a single user message. B. Send three separate user messages, one `tool_result` each, in the order the blocks appeared. C. Set `disable_parallel_tool_use` at the top level of the request so only one block is ever returned. D. Return a `tool_result` only for the call that succeeded and omit the others, since the model will re-ask.

**Q9.4** Your `run_query` tool raises an unhandled `IntegrityError` when the model supplies a duplicate key. The exception propagates out of your agent loop and the user sees a stack trace. What is the best design?

A. Let the exception propagate; retries at the HTTP layer will eventually succeed. B. Catch it and return an empty string so the conversation continues smoothly. C. Catch it, log it, and end the conversation with a generic apology. D. Catch it and return a `tool_result` with `is_error: true` and a message such as “Duplicate key ‘sku-17’; use update\_record to change an existing row,” while logging the full exception server-side.

**Q9.5** Your `set_ticket_status` tool has a string parameter `status`. Production logs show values like “Open”, “OPEN”, “in-progress”, “In Progress”, and “done!” and your handler rejects about 15% of calls. What is the most robust fix?

A. Declare `status` as a string `enum` with the exact allowed values and describe what each means. B. Lowercase and fuzzy-match the value in the handler and accept anything close. C. Add a system prompt line demanding lowercase values. D. Set `tool_choice` to `any` so the model concentrates on the tool arguments.

**Q9.6** A data-extraction service forces a tool call with `tool_choice: {"type": "tool", "name": "record_invoice"}`. After a developer enables manual extended thinking (`thinking: {"type": "enabled", ...}`) on the same requests, every call fails with an error. What should the team do?

A. Keep both settings and increase `max_tokens`. B. Move the tool definition into the system prompt. C. Use `tool_choice: auto` (optionally with `strict: true` on the tool) and instruct the model in the prompt to call `record_invoice`, or drop manual thinking. D. Replace the tool with a `tool_choice` of `none` and parse the JSON from the text reply.

**Q9.7** Your app enables Anthropic’s web search server tool. Occasionally a response arrives with `stop_reason: "pause_turn"` and no final answer. What is the correct handling?

A. Treat it as a failure and retry the original request from scratch. B. Append the assistant content unchanged and call the API again so the model can continue its server-side loop. C. Execute the search yourself and return a `tool_result`. D. Increase `max_tokens`, because `pause_turn` means the output was truncated.

**Q9.8** Three products at your company (an IDE plugin, a Slack bot and a CI reviewer agent) each need to query the same internal issue tracker. Each team currently has its own hand-written tool definitions and handlers, and they have drifted apart. What is the best architectural move?

A. Copy the best implementation into all three repositories and add a code-owners file. B. Replace the tools with a single, larger tool that accepts a free-text instruction. C. Build one MCP server in front of the tracker and have each product connect to it as an MCP host or client. D. Move the tracker credentials into each product’s system prompt so the model can call the API directly.

**Q9.9** You wrote a Python MCP server that runs over stdio. Your host logs repeated JSON parse errors on startup, and the server never becomes ready. The server contains `print("starting up")` near the top. What is the problem and fix?

A. Anything printed to stdout corrupts the JSON-RPC stream; log to stderr or a file instead. B. The server must use Streamable HTTP for logging to work; switch transports. C. The host requires a `server/discover` call before any output; add a delay on startup. D. The `print` call is slow and times out the host; remove it only if startup exceeds a second.

**Q9.10** A developer passes a local stdio MCP server (`npx some-local-server`) in the `mcp_servers` list of a Messages API request using the MCP connector. The request fails. Which statement explains why and offers a valid path forward?

A. The connector only supports resources, so change the server to expose resources. B. The `betas` header is missing a version suffix; add one and retry. C. The server must be listed in `tools` directly with `type: "stdio"`. D. The connector can reach only remote servers over HTTPS; host the server remotely over Streamable HTTP, or run your own MCP client in your application that spawns the stdio process and relays tool calls.

**Q9.11** An agent has 60 tools, including `create_pr`, `review_pr`, `merge_pr`, `close_pr`, `get_pr`, `list_prs`, and similar groups for issues and branches. It often picks the wrong one of two near-identical tools and token usage per request is high. Which change addresses both problems?

A. Increase `temperature` so the model explores alternatives. B. Consolidate related operations into fewer tools (for example one `pull_request` tool with an `action` enum), namespace the rest, and consider tool search so only relevant definitions are loaded. C. Set `tool_choice` to `any` to make the model decisive. D. Shorten every description to one sentence to save tokens.

**Q9.12** The model sometimes calls `refund_order` with an `order_id` that looks valid but was never returned by any earlier tool and does not exist. What combination of changes is best?

A. Make `order_id` optional so the model can omit it when unsure. B. Enable `strict: true`, which guarantees that the ID refers to a real order. C. State in the description that the ID must come from the user or from `lookup_order`, validate existence in the handler, and return an `is_error` result that tells the model how to obtain a valid ID. D. Catch the exception and silently substitute the most recent order ID in the session.

**Q9.13** The model calls `create_folder` and `upload_file` (into that folder) in one parallel batch. The upload fails because the folder did not exist yet. How should you respond to reduce this without giving up parallelism for independent calls?

A. Return the failed upload as a `tool_result` with `is_error: true`, so the model reissues it, and add a system prompt line to only batch calls that are independent of each other. B. Set `disable_parallel_tool_use: true` permanently for every request in the application. C. Return the two results in separate user messages so the folder call is guaranteed to finish first. D. Remove `upload_file` from the tool list and tell the model to upload manually.

**Q9.14** You set `strict: true` on a `book_flight` tool with `departure_date` as `format: date`. Tool calls are now always structurally valid, but users report flights booked for the wrong year when they say “next Friday”. What explains this and what is the right fix?

A. `strict` is broken for date formats; remove it and validate in code. B. The model needs `tool_choice: any` to compute dates correctly. C. Raise `max_tokens`; the date is being truncated. D. Strict mode guarantees shape and types, not semantic correctness; give the model the current date in the system prompt and clarify the parameter description.

**Q9.15** You are building an MCP server for an analytics database. You want the host application to be able to attach the table schemas as background context for the model whenever a user opens a data-analysis session, without the model having to decide to fetch them. Which primitive fits best?

A. A tool named `get_schema`, since only tools can return data. B. A resource exposing the schema, which the application chooses to attach. C. A prompt that embeds the schema text in its name. D. A sampling request from the server to the client.

**Q9.16** A new developer writes a `refund_order` handler that runs a regular expression over the customer’s latest message to find the order ID and the amount, reasoning that the tool is given the conversation. The tool’s `input_schema` has no properties. What is wrong with this design?

A. Nothing; the API forwards the latest user message to the tool as its input, so the handler has to parse it. B. The tool receives the whole `messages` array, so the handler should search every turn, not only the latest one. C. The tool receives the text block the model writes before the `tool_use` block, so the handler should parse that text instead. D. The tool receives only the `input` object the model writes from the conversation; declare `order_id` and `amount_cents` as schema parameters and let the model fill them.

**Q9.17** A team adds strict mode to a tool, but calls still occasionally arrive with an extra `notify` field and with `amount_cents` as the string `"1999"`. The definition is:

``` {.sourceCode .python}
{"name": "refund_order",
 "description": "Refund a customer order.",
 "input_schema": {"type": "object", "strict": True,
                  "properties": {"order_id": {"type": "string"},
                                 "amount_cents": {"type": "integer"}},
                  "required": ["order_id", "amount_cents"]}}
```

What is the fix?

A. Strict mode takes effect only when the tool is forced, so set `tool_choice` to `{"type": "tool", "name": "refund_order"}`. B. Move `strict` to the top level of the tool definition, next to `name` and `description`, and add `"additionalProperties": False` to the schema. C. Set `strict` on `tool_choice` instead, as `{"type": "auto", "strict": True}`. D. Strict mode supports only string parameters, so declare `amount_cents` as a string and convert it in the handler.

**Q9.18** Refunds must never exceed 50,000 cents. A developer adds `"maximum": 50000` to `amount_cents` in a `strict: true` tool and sends the definition from a raw HTTP client; the request fails with a 400. What is the best fix?

A. Remove `strict` from the tool, because enforcing the cap matters more than a guaranteed schema. B. Replace `maximum` with an `enum` listing every allowed amount from 0 to 50,000. C. Remove `maximum`, state the cap in the parameter description, and enforce it in the handler, returning an `is_error` result that explains the limit when it is exceeded. D. Change `amount_cents` to a string with the pattern `^[0-9]{1,5}$`, which keeps the value under the cap.

**Q9.19** A `refund_order` handler asks an operator to approve large refunds. When the operator declines, the handler returns a `tool_result` with `is_error: true` and the content “Refund failed.” Logs show the model then calls `refund_order` two or three more times and tells the customer there is a technical problem. What is the best change?

A. Set `disable_parallel_tool_use: true` so the model cannot call the tool again in the same turn. B. Remove `refund_order` from the `tools` list for the rest of the conversation after any decline. C. Keep `is_error: true` and add a system prompt rule that the model must never retry a refund. D. Return the decline as a normal result without `is_error`, saying that an operator declined the refund and what to tell the customer.

**Q9.20** Refunds above \$5 must never be issued without a person’s approval, whatever the model decides. Which design meets this requirement?

A. In the `refund_order` handler, before the payment call, check the amount and require explicit approval above the threshold, treating anything other than a clear yes as a decline. B. Add a system prompt instruction: “Before calling `refund_order` for more than \$5, always ask the customer to confirm.” C. Set `strict: true` on the tool so the model cannot produce an amount above 500 cents without approval. D. Add a required boolean parameter `human_approved` to the schema and issue the refund only when the model sets it to `true`.
