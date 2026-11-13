# The Messages API

Everything you build on Claude ultimately resolves to one HTTP call: `POST /v1/messages`. Tool loops, agent frameworks, retrieval pipelines, and multi-agent orchestration are all conventions layered on top of that single endpoint. If you understand its request shape, its response shape, and the handful of ways it can terminate, you can reason about any Claude integration from first principles — including ones built with SDKs whose internals you have never read.

This chapter treats the endpoint as a protocol rather than as a library. We start with the wire format, work through each parameter that materially changes behavior, and finish with the choices you make at the integration layer: SDK versus raw REST, how to count tokens before you spend them, and how to manage conversation state in a system that has none of its own.

## Request and Response Anatomy

The endpoint is `POST https://api.anthropic.com/v1/messages`. A minimal request carries three headers and three body fields.

``` {.sourceCode .bash}
curl https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --data '{
    "model": "claude-sonnet-5-5",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Summarize the CAP theorem."}]
  }'
```

Three headers matter on every call:

  ------------------------------------------------------------------------------------------------------------------------------------------------------
  Header                  Required                Notes
  ----------------------- ----------------------- ------------------------------------------------------------------------------------------------------
  `x-api-key`             Yes                     Your API key. Not a bearer token — this is a custom header, so copy-pasted OAuth code will not work.

  `anthropic-version`     Yes                     Date-based API version string, e.g. `2023-06-01`. Required on raw REST; SDKs set it for you.

  `content-type`          Yes                     `application/json` for the Messages API. The Files API uses multipart instead.

  `anthropic-beta`        No                      Opts into beta features. Comma-separated when you need more than one.
  ------------------------------------------------------------------------------------------------------------------------------------------------------

A successful call returns HTTP 200 and a `Message` object. The shape is stable and worth memorizing, because almost all defensive coding you write keys off two of its fields: `content` and `stop_reason`.

``` {.sourceCode .json}
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "model": "claude-sonnet-5-5",
  "content": [
    { "type": "text", "text": "The CAP theorem states that..." }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 14,
    "output_tokens": 203,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  }
}
```

Points worth internalizing:

-   `role` on a response is always `assistant`. There is no scenario where the API replies with a user-role message.
-   `content` is **always an array**, even when the model produced one text block. The single most common beginner bug is treating `response.content` as a string.
-   `stop_reason` tells you *why* generation ended, and is the field your control flow should branch on.
-   `stop_sequence` is non-null only when `stop_reason` is `stop_sequence`, and holds the sequence that matched.
-   `usage` is authoritative for billing. Do not compute your own cost estimates from string lengths.

The `id` is also worth logging. Paired with the `request-id` response header, it is what support needs to investigate a specific call.

## The Messages Array

`messages` is an ordered list of turns. Each turn is an object with a `role` and a `content`. The roles you supply are `user` and `assistant` (plus, on newer models, a mid-conversation `system` role discussed below).

The API enforces alternation. A conversation must begin with a `user` turn and must not contain two consecutive turns of the same role. This is the structural invariant that trips up applications which maintain their own chat log: if your UI lets a user send two messages in a row before the model replies, you cannot forward both as separate `user` turns. You must merge them — either into one text block, or into one turn with two text blocks.

``` {.sourceCode .python}
# Rejected with 400: consecutive user turns
messages = [
    {"role": "user", "content": "Here is my code."},
    {"role": "user", "content": "Why does it crash?"},
]

# Accepted: one turn, two blocks
messages = [
    {"role": "user", "content": [
        {"type": "text", "text": "Here is my code."},
        {"type": "text", "text": "Why does it crash?"},
    ]},
]
```

A conversation may *end* with an `assistant` turn. That is not a malformed request; it is the prefill technique, covered in Chapter 5, and it is restricted on newer models. A conversation may not *begin* with an `assistant` turn.

Tool use adds a wrinkle: tool results travel in `user` turns, as `tool_result` blocks, and each `tool_result` must immediately follow the assistant turn that produced the corresponding `tool_use`. In a user turn containing tool results, the `tool_result` blocks must come before any text blocks. Omitting a result for a `tool_use` id yields a 400 complaining that tool\_use ids were found without matching results.

## System Prompts Are Not Messages

In the Messages API, the system prompt is a **top-level request parameter**, not an entry in `messages`. There is no `{"role": "system"}` first element the way other chat APIs model it.

``` {.sourceCode .python}
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    system="You are a terse code reviewer. Reply in bullet points only.",
    messages=[{"role": "user", "content": diff_text}],
)
```

`system` accepts either a plain string or an array of content blocks. Use the array form when you want to mark part of the system prompt with `cache_control` (Chapter 4) or to keep structurally distinct sections separate.

``` {.sourceCode .python}
system=[
    {"type": "text", "text": STYLE_GUIDE, "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": f"Today is {today}."},
]
```

That ordering is deliberate. Static content first, volatile content after, so the cacheable prefix stays identical between requests.

Newer models additionally allow a `{"role": "system"}` entry *inside* `messages`, appended after a user turn, to introduce an instruction mid-conversation with the same authority as the top-level field. It cannot be the first entry. The practical benefit is caching: because it is appended at the end rather than edited into the top-level `system` field, it does not invalidate an already-cached prefix. Model support for this is not universal, so check availability for the specific model you target before relying on it.

## Content Blocks Versus Plain Strings

`content` on a message accepts two forms:

``` {.sourceCode .python}
# Shorthand
{"role": "user", "content": "Hello"}

# Canonical
{"role": "user", "content": [{"type": "text", "text": "Hello"}]}
```

These are equivalent for plain text. The shorthand exists for convenience; the block form is what the API actually works with, and it is the only form that supports anything other than text.

Input block types you will encounter:

  -------------------------------------------------------------------------------------------------------
  Block type                          Purpose
  ----------------------------------- -------------------------------------------------------------------
  `text`                              Plain text.

  `image`                             Image input, with a `base64`, `url`, or `file` source.

  `document`                          PDF or plain-text document input.

  `tool_result`                       The output of a client tool you executed.

  `search_result`                     Retrieved passages supplied with citation metadata.

  `thinking` / `redacted_thinking`    Extended-thinking blocks echoed back from a prior assistant turn.

  `container_upload`                  A file handed to the code execution container.
  -------------------------------------------------------------------------------------------------------

Output block types include `text`, `thinking`, `tool_use`, `server_tool_use`, and the various server-tool result blocks. Because new block types are added over time under the versioning policy, **write your response handling as a dispatch over `block.type` with a default branch**, not as `response.content[0].text`.

``` {.sourceCode .python}
def extract_text(message):
    return "".join(b.text for b in message.content if b.type == "text")
```

That one helper eliminates a whole class of production incidents: the first time you enable extended thinking or tools, index 0 stops being a text block, and code that assumed otherwise raises an attribute error on a perfectly valid response.

### Thinking blocks

When the model thinks, the `content` array opens with one or more `thinking` blocks, followed by the `text` or `tool_use` blocks that make up the actual answer:

``` {.sourceCode .json}
{
  "content": [
    {
      "type": "thinking",
      "thinking": "Two parts to the question; solve the simpler one first...",
      "signature": "WaUjzkypQ2mUEVM36O2Txu..."
    },
    {
      "type": "text",
      "text": "Based on my analysis..."
    }
  ]
}
```

A thinking block has exactly three fields:

-   `type` is always `"thinking"`.
-   `thinking` is readable text, but it is never the raw chain of thought. At most it is a *summary* of the reasoning, written by a separate summarization model; no setting returns the raw reasoning. You are billed for the full reasoning tokens, not the summary, so the billed `output_tokens` will not match what you could count in the block.
-   `signature` is an opaque, encrypted copy of the full reasoning. The API uses it to verify that the block came from Claude and to reconstruct the reasoning when you send the block back. Never parse, trim, or regenerate it.

**Whether the `thinking` field contains text depends on `display`,** a field on the thinking configuration:

  ----------------------------------------------------------------------------------------------------------
  `display`             What the `thinking` field holds                Default on
  --------------------- ---------------------------------------------- -------------------------------------
  `"summarized"`        The reasoning summary.                         Opus 4.6, Sonnet 4.6, and earlier.

  `"omitted"`           An empty string. `signature` is still          The current generation: Opus 5.5,
                        present and complete.                          Sonnet 5.5, Haiku 5.5, Fable 5.1,
                                                                       Mythos 5.1, the Claude 5 models,
                                                                       Opus 4.8, and Opus 4.7.

  `"updates"` (beta)    Empty for reasoning blocks; text only in the   Never; needs the beta header
                        short progress notes some models write         `thinking-display-updates-2026-08-18`.
                        between tool calls.
  ----------------------------------------------------------------------------------------------------------

So on a current model, an empty `thinking` string is the normal default, not a failure. To see the summary, ask for it explicitly:

``` {.sourceCode .python}
thinking={"type": "adaptive", "display": "summarized"}
```

`"omitted"` reduces latency, because the server skips streaming the thinking text, but not cost: the same reasoning is generated and billed either way, and the `signature` is identical. `display` is invalid with `thinking: {"type": "disabled"}`, since there is nothing to display.

**Redacted blocks are a separate type.** When part of the reasoning is safety-redacted, the API returns a block with no readable text at all, only encrypted data:

``` {.sourceCode .json}
{ "type": "redacted_thinking", "data": "..." }
```

Do not confuse this with `display: "omitted"`, which returns an ordinary `thinking` block whose text field is empty.

**Not every response has a thinking block.** With adaptive thinking the model can skip thinking on a simple request, and then no block is produced whatever `display` says. Where forced tool use is accepted, the response starts directly with the `tool_use` block. In a tool loop, further thinking blocks can appear between tool calls, each with its own signature. Dispatch on `block.type`; never assume a position.

**Round-tripping rules.** These are where integrations break:

1.  **Within a tool-use turn, thinking blocks are mandatory.** When you return tool results, send back every `thinking` and `redacted_thinking` block from that assistant turn complete, unmodified, and in the original order, alongside the `tool_use` it accompanied. Editing, reordering, or dropping part of the sequence returns a 400. There is one harmless exception: when a block came back with an empty `thinking` field because of `display: "omitted"`, any text you put into that field is ignored.
2.  **Filtering by type is a trap.** Code that keeps only `block.type == "thinking"` silently drops `redacted_thinking` blocks and breaks the protocol. The safe pattern is to append `response.content` verbatim, as the history example later in this chapter does.
3.  **Across turns, pass everything back.** Outside tool use, omitting earlier turns' thinking is allowed, but the recommended practice is to send it all and let the API filter it. Whether prior-turn blocks stay in context, and are billed as input, depends on the model (Chapter 6).
4.  **Keep the history append-only.** On Claude 5.1 and later models, the API checks each block's signature against the model that produced it and against everything sent before it: the `system` prompt, `tools`, and earlier messages. If any of that has changed since the block was produced, the check fails and the API ignores the reasoning in that block. Add new turns at the end and leave everything already sent alone: editing an early message costs you the reasoning attached to every turn after the edit, not just the turn you edited.

## max\_tokens and Why It Is Required

`max_tokens` is a required integer. There is no default.

This surprises engineers used to APIs where the limit is optional and defaults to the model’s maximum. The requirement is a deliberate forcing function: generation length is the dominant driver of both latency and output cost, so the API makes you declare a ceiling rather than letting an unbounded generation drain a budget.

Four consequences follow:

1.  **It is a cap, not a target.** Setting `max_tokens: 8192` does not make responses longer. The model stops when it is done, and `stop_reason` is `end_turn`.
2.  **It does not consume rate limit headroom.** Output-tokens-per-minute is measured against tokens actually generated, so a generous `max_tokens` carries no rate-limit penalty. This is the opposite of how reservation-style quotas work elsewhere.
3.  **It must be within the model’s output limit.** Exceeding it is a 400.
4.  **Thinking tokens count against it.** All thinking generated in the turn comes out of `max_tokens`, even when `display` hides the text, so size it for reasoning plus answer. In the legacy manual mode (`thinking: {"type": "enabled", "budget_tokens": N}`, deprecated on the 4.6 models and rejected with a 400 on 4.7 and later), the budget must be at least 1,024 and strictly less than `max_tokens`; otherwise there is no room left for a visible answer.

The practical failure mode of setting it too low is silent truncation. You get HTTP 200, a well-formed `Message`, and a partial answer — with `stop_reason: "max_tokens"` as the only signal. If your code does not check `stop_reason`, truncated JSON and half-finished sentences flow straight into your database.

The practical failure mode of setting it very high on a non-streaming request is a dropped connection. A long generation can exceed the ten-minute window that the SDKs validate against, and intermediate network equipment may kill an idle socket before any bytes arrive. For large `max_tokens`, stream (Chapter 4) or batch.

## stop\_reason: The Field Your Control Flow Hangs On

Every terminal response carries a `stop_reason`. Treat it as the primary branch point.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Value                             Meaning                                           What your code should do
  --------------------------------- ------------------------------------------------- ---------------------------------------------------------------------------------------------------
  `end_turn`                        The model finished naturally.                     Normal path. Use the content.

  `max_tokens`                      Hit your `max_tokens` ceiling.                    Treat output as incomplete. Raise the cap, or continue from the partial text.

  `stop_sequence`                   A sequence from `stop_sequences` was generated.   Inspect `stop_sequence` to learn which one. The sequence itself is not in the text.

  `tool_use`                        The model is requesting one or more tools.        Execute the tools, append results, call again.

  `pause_turn`                      A long-running server-side turn was paused.       Resend the conversation, including the paused assistant turn, to continue.

  `refusal`                         The model declined on safety grounds.             Surface a user-facing message. Inspect `stop_details` for category and explanation. Still billed.

  `model_context_window_exceeded`   The context window filled.                        Trim or summarize history; retry with less input.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Three of these deserve emphasis because they look like success to naive code.

`max_tokens` returns 200. Nothing throws. A structured-output pipeline that parses JSON without checking `stop_reason` will fail downstream with a cryptic parse error whose real cause is three layers up.

`refusal` also returns 200 and bills you for the tokens generated. When you are using constrained JSON output, a refusal can override schema compliance — so the one case where you are promised valid JSON is also the one case where you can still get prose. Check `stop_reason` before parsing.

`pause_turn` is not an error. It is a cooperative yield from a long server-side operation. The correct handling is to resend the conversation with the paused assistant turn appended, which resumes the work. Treating it as a failure and restarting from scratch wastes everything already computed.

And because the version policy permits new enum values to be added, your handler needs a default branch. A `match` statement with no fallback is a time bomb.

``` {.sourceCode .python}
match response.stop_reason:
    case "end_turn":
        return finalize(response)
    case "tool_use":
        return run_tools(response)
    case "max_tokens":
        raise OutputTruncated(response.id)
    case "refusal":
        return refusal_message(response)
    case "pause_turn":
        return resume(response)
    case other:
        log.warning("unhandled stop_reason=%s id=%s", other, response.id)
        return finalize(response)
```

## stop\_sequences

`stop_sequences` is an array of strings. If the model generates one, generation halts immediately, `stop_reason` becomes `stop_sequence`, and `stop_sequence` names the matched string.

Two properties matter. First, the matched sequence is **excluded** from the returned text — you get everything before it, not including it. Second, matching is on generated output only; a stop sequence appearing in your input has no effect.

Stop sequences were historically the main way to delimit structured output: prefill an opening brace, stop on a closing one. That technique is now largely superseded by constrained structured outputs and tool use (Chapter 5). The remaining legitimate uses are narrower:

-   Cutting off a known runaway pattern, e.g. stopping at `\nUser:` when a model starts role-playing both sides of a dialogue.
-   Segmenting a generation where you want to process one unit at a time.

Beware over-eager sequences. A stop sequence of `}` will terminate on the first closing brace anywhere, including inside a nested object. A stop sequence of `.` will end the first sentence.

## Multi-Turn Conversations and Statelessness

**The Messages API is stateless.** It stores nothing between calls. There is no conversation id, no session handle, no server-side thread. Every request must carry the entire history you want the model to see.

This is the single most consequential architectural fact in the chapter. It means:

-   *You* own conversation persistence. Database, cache, or client-side — your choice, your problem.
-   Input token cost grows with conversation length, because you resend the whole history each turn. If every exchange adds about 500 tokens, turn 10 sends roughly 5,000 input tokens and turn 20 roughly 10,000. The cost of one turn grows in step with the turn number, so the total for the whole conversation grows with its square: twenty turns cost about four times as much as ten, not twice.
-   Context window pressure accumulates. Eventually you must truncate, summarize, or window the history.
-   Nothing stops you from *editing* the history. Turns you send need not be turns that actually happened.

That last point is a feature, not a loophole. You can synthesize an assistant turn to demonstrate a format, drop a tool exchange that is no longer relevant, or replace ten turns of back-and-forth with a one-paragraph summary you generated out of band. The model has no way to know and no reason to care — it sees only the array you sent.

Building a turn is mechanical: append the assistant’s returned `content` verbatim, then append the next user turn.

``` {.sourceCode .python}
history = []

def ask(question: str) -> str:
    history.append({"role": "user", "content": question})
    response = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    history.append({"role": "assistant", "content": response.content})
    return extract_text(response)
```

Note `response.content` — the block list, not extracted text. Round-tripping blocks verbatim is what keeps tool\_use/tool\_result pairs and thinking-block signatures intact. Reconstructing the assistant turn from a flattened string silently discards structure the model needs on the next call.

The statelessness also pairs with prompt caching to make long conversations affordable. Resending history is cheap when the prefix is cached: you pay a fraction of the input rate for the repeated portion. Without caching, a fifty-turn conversation is genuinely expensive. Chapter 4 covers the mechanics.

## Token Counting

`POST /v1/messages/count_tokens` tells you the input token count for a request without generating anything.

``` {.sourceCode .python}
count = client.messages.count_tokens(
    model="claude-sonnet-5-5",
    system=SYSTEM_PROMPT,
    tools=TOOLS,
    messages=history,
)
print(count.input_tokens)
```

The response is a single field: `{"input_tokens": N}`.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------
  Property                            Detail
  ----------------------------------- -----------------------------------------------------------------------------------------------------------------------
  Cost                                Free.

  Rate limit                          Separate from Messages, measured in RPM; thousands per minute depending on tier.

  Accepts                             `model`, `system`, `messages`, `tools`, `thinking`. Images and PDFs with **base64** sources.

  Rejects                             `url` and `file` sources for images and documents; server tools; MCP connector. These return `invalid_request_error`.

  Accuracy                            An estimate. Actual counts can differ slightly, and may include system-added tokens you are not billed for.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------

Legitimate uses: deciding whether a prompt fits a context window, routing between a cheap and an expensive model based on size, estimating cost before a batch submission, and enforcing your own per-request budget.

One significant caveat: tokenization is **model-dependent**. Newer models use a different tokenizer that produces materially more tokens for the same text — on the order of thirty percent more. A count obtained against one model is not a valid estimate for another. Always count against the model you will actually call.

Also note that because `url` and `file` sources are rejected, you cannot use token counting to price a request that references Files API uploads. For those, read the `usage` object on the actual response instead.

## SDK Versus Raw REST

The official SDKs cover Python, TypeScript, C\#, Go, Java, PHP, and Ruby. They are thin wrappers over the same HTTP endpoint — nothing an SDK does is unavailable over REST — but they fold in several behaviors you would otherwise have to build.

What the Python SDK gives you:

``` {.sourceCode .python}
import anthropic
client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from the environment
```

  -----------------------------------------------------------------------------------------------------------------------------------
  Behavior                Default                                Override
  ----------------------- -------------------------------------- --------------------------------------------------------------------
  API key                 From `ANTHROPIC_API_KEY`               `Anthropic(api_key=...)`

  Base URL                Production endpoint                    `base_url=` or `ANTHROPIC_BASE_URL`

  `anthropic-version`     Set automatically                      —

  Retries                 `max_retries=2`, exponential backoff   `Anthropic(max_retries=5)` or `client.with_options(max_retries=0)`

  Timeout                 10 minutes                             `timeout=20.0`, or per-request via `with_options`

  Async                   `AsyncAnthropic`                       —
  -----------------------------------------------------------------------------------------------------------------------------------

Retried conditions are connection errors, 408, 409, 429, and any 5xx; `retry-after` is honored when present. Streaming helpers (`messages.stream()`, `text_stream`, `get_final_message()`) and schema helpers (`messages.parse()`) are SDK-only conveniences built over the raw protocol.

The error hierarchy is worth knowing by name, because catching on class is far more robust than string-matching messages:

    APIError
    ├── APIConnectionError
    │   └── APITimeoutError
    └── APIStatusError
        ├── BadRequestError          (400)
        ├── AuthenticationError      (401)
        ├── PermissionDeniedError    (403)
        ├── NotFoundError            (404)
        ├── ConflictError            (409)
        ├── UnprocessableEntityError (422)
        ├── RateLimitError           (429)
        └── InternalServerError      (>=500)

Choose raw REST when you have a hard dependency-count constraint, when you are in a language with no official SDK, when you are proxying requests and want to pass bodies through untouched, or when you need precise control over connection pooling and retry semantics. Accept that you then own the retry loop, the SSE parser, the version header, and the accumulation logic.

Choose the SDK otherwise. The retry defaults and streaming accumulation alone represent a meaningful amount of code you would otherwise write and test yourself.

## Versioning

`anthropic-version` is a required date-stamped header. The current value is `2023-06-01`.

Within a version, the API guarantees that existing input parameters and existing output parameters keep working. What it explicitly reserves the right to do, without a version bump:

-   Add new optional input parameters.
-   Add new fields to output objects.
-   Add new variants to enum-like values, including `stop_reason` values and streaming event types.
-   Change the conditions under which a particular error type is returned.

That list *is* your compatibility contract, and it dictates two coding rules. Tolerate unknown enum values. Ignore unrecognized fields rather than failing validation on them. A client that treats the documented enum as exhaustive will break on a Tuesday for reasons that look like a server bug but are a documented, non-breaking change.

## Getting the Request ID

Every response carries a `request-id` header (note the hyphen; it is not `x-request-id`). Error response bodies also include it as a top-level `request_id` field. In the Python and TypeScript SDKs, read it from `_request_id` on the response object.

``` {.sourceCode .python}
message = client.messages.create(...)
log.info("claude call id=%s request_id=%s", message.id, message._request_id)
```

Log it on every call. It is the only identifier that lets anyone correlate your observed behavior with server-side records, and the first thing a support investigation will ask for.

## Putting It Together

A production-grade call site looks less like the quickstart and more like this:

``` {.sourceCode .python}
import anthropic

client = anthropic.Anthropic(max_retries=3)

def complete(history, system, model="claude-sonnet-5-5", max_tokens=4096):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=history,
    )

    if response.stop_reason == "max_tokens":
        raise OutputTruncated(response.id, response.usage.output_tokens)
    if response.stop_reason == "refusal":
        raise ModelRefused(response.id)

    log.info(
        "ok id=%s req=%s in=%d out=%d stop=%s",
        response.id, response._request_id,
        response.usage.input_tokens, response.usage.output_tokens,
        response.stop_reason,
    )
    return response
```

The shape of that function encodes most of this chapter: an explicit `max_tokens`, a `system` kept out of `messages`, history passed whole because the server keeps none, `stop_reason` checked before the content is trusted, and `usage` plus `request_id` logged for the cost and support questions that will eventually arrive.

## Practice Questions

**Q3.1** Your chat UI lets a user send a follow-up before Claude responds. You append both as separate entries with `"role": "user"` and call the API. You get a 400. What is the correct fix?

A. Merge the two into one `user` turn, with each original message as a separate text block. B. Insert an empty `{"role": "assistant", "content": ""}` turn between them. C. Set `allow_consecutive_roles: true` in the request. D. Send the first message, discard the response, then send the second.

**Q3.2** A teammate writes `text = response.content[0].text` and it works for months. After extended thinking is enabled, it starts raising attribute errors on successful 200 responses. Why?

A. Extended thinking changes `content` from an array to an object. B. Enabling thinking makes `content` null until the stream completes. C. Index 0 is now a `thinking` block, which has no `text` attribute. D. The response role changes from `assistant` to `system`.

**Q3.3** Your JSON extraction service intermittently produces records with truncated field values. HTTP status is always 200 and no exception is raised. Which check is missing?

A. Verify `response.role == "assistant"`. B. Compare `usage.input_tokens` against the context window. C. Confirm `stop_sequence` is null. D. Branch on `stop_reason` and treat `max_tokens` as an incomplete result.

**Q3.4** You want to reduce output cost on a summarization endpoint. A colleague proposes lowering `max_tokens` from 4096 to 512 to “make Claude write less.” What will actually happen?

A. Summaries get proportionally shorter and cost drops accordingly. B. Summaries that would have exceeded 512 tokens are cut off mid-sentence with `stop_reason: "max_tokens"`. C. The API returns 400 because 512 is below the minimum. D. The model automatically compresses its output to fit the new limit.

**Q3.5** You set `max_tokens` to a very large value on a non-streaming request. Requests sometimes fail with no response body at all, after several minutes. What is the most likely cause?

A. The connection is being dropped before any bytes arrive; long generations need streaming or batching. B. The account’s OTPM rate limit is being consumed by the large `max_tokens` reservation. C. `max_tokens` above a threshold is silently rejected as a 204. D. The model is refusing requests whose `max_tokens` exceeds the input length.

**Q3.6** Your application stores conversation history as plain strings: it extracts the assistant’s text and appends `{"role": "assistant", "content": text}`. Tool-using conversations start failing on the second tool call. Why?

A. Tool results must be stored in a separate array from messages. B. Each tool call needs a new conversation because tool state is server-side. C. The API requires assistant turns to be strings, not blocks, when tools are in use. D. Flattening to text discards the `tool_use` blocks, so the `tool_result` blocks you send have no matching ids.

**Q3.7** You are designing the system prompt for a support assistant. Which placement is correct for the Messages API?

A. First element of `messages` with `"role": "system"`. B. Top-level `system` parameter, as a string or array of content blocks. C. A `system` content block inside the first user message. D. The `metadata.system` field.

**Q3.8** You want to cache a large static style guide that precedes a short dynamic timestamp in your system prompt. How should you structure `system`?

A. One concatenated string with the timestamp first, then the style guide. B. An array with the timestamp block first carrying `cache_control`, then the style guide. C. An array with the style guide block carrying `cache_control` first, then the timestamp block. D. Caching does not apply to the `system` parameter.

**Q3.9** A request returns `stop_reason: "pause_turn"`. What should your handler do?

A. Append the returned assistant turn to the history and send the conversation again to continue. B. Treat it as a transient error and retry the identical request from scratch. C. Raise an exception, since `pause_turn` indicates a malformed request. D. Poll a status endpoint using the message id until the turn resumes.

**Q3.10** You add `stop_sequences: ["}"]` so that generation halts at the end of a JSON object. Output is consistently cut off too early. Why?

A. Stop sequences match against input as well as output. B. `stop_sequences` only accepts multi-character strings. C. Stop sequences are matched case-insensitively. D. The first `}` closing any nested object triggers the stop.

**Q3.11** You need to know whether a 180,000-token document plus your system prompt will fit before you pay for a call. The document is referenced via a Files API `file_id`. What happens if you call the token counting endpoint with that request?

A. It returns an accurate `input_tokens` count including the file contents. B. It returns a count of only the system prompt and silently ignores the file. C. It returns `invalid_request_error`, because `file` sources are not supported by token counting. D. It bills you a small fee for resolving the file.

**Q3.12** You measured a prompt at 12,000 input tokens against an older model and sized your chunking strategy around it. On a newer model the same prompts start overflowing the context window. What is the most likely explanation?

A. The newer model has a smaller context window. B. Newer models use a different tokenizer that yields substantially more tokens for the same text. C. Token counting results expire after 24 hours. D. The newer model counts output tokens toward the input limit.

**Q3.13** Your raw-REST client validates responses against a strict schema and rejects unknown fields. After a routine platform update, previously working calls start failing in your client even though the API returns 200. What went wrong?

A. The `anthropic-version` header expired and must be refreshed monthly. B. Strict validation requires the `anthropic-beta` header. C. The API switched to a new version automatically. D. Adding new output fields is a documented non-breaking change within a version; clients must tolerate them.

**Q3.14** Support asks you to identify a specific failing call from last Tuesday. Your logs record the prompt, the response text, and a timestamp. What should you have been logging instead or in addition?

A. The `request-id` response header (also present as `request_id` in error bodies). B. The `anthropic-version` header value. C. The `x-api-key` prefix. D. The `anthropic-ratelimit-tokens-remaining` value.

**Q3.15** You are deciding between the Python SDK and a hand-rolled `httpx` client. Which of the following is a capability you would gain *only* by using the SDK?

A. The ability to send images as base64 content blocks. B. Access to prompt caching via `cache_control`. C. Automatic retries with exponential backoff that honor `retry-after`, plus streaming accumulation helpers. D. A server-side conversation store that removes the need to resend history.
