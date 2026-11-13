# Streaming, Caching, and Batching

Three mechanisms determine whether a Claude integration is pleasant or painful to run at scale. Streaming governs perceived latency and whether long generations survive the network. Prompt caching governs cost and time-to-first-token on prompts with a large stable prefix. Batching governs throughput and unit economics for work that nobody is waiting on.

They are orthogonal to the model’s capabilities and almost entirely a property of your integration layer. An engineer who understands all three can usually halve the cost of a working prototype without touching a prompt.

## Why Stream at All

Set `"stream": true` and the response arrives as server-sent events instead of one JSON document. You get three distinct benefits, and only the first is about user experience.

**Perceived latency.** Time-to-first-token is a fraction of time-to-last-token. For a 2,000-token answer, the user sees text in under a second rather than after thirty seconds.

**Connection survival.** This is the operational reason, and it is not optional at scale. A non-streaming request holds an idle HTTP connection for the full generation. Load balancers, proxies, and NAT devices drop idle connections. For requests that may run beyond roughly ten minutes, the documentation directs you to streaming or the Batches API, and the SDKs validate that a non-streaming Messages request is not *expected* to exceed a ten-minute timeout. The SDK also sets a TCP keep-alive socket option. A large `max_tokens` on a non-streaming call is the canonical way to produce failures that return nothing at all — no HTTP status, no body, just a dead socket.

**Incremental processing.** You can act on partial output: render markdown progressively, start a downstream call on the first complete JSON key, or abort generation early when you have what you need.

The cost is complexity. You now own event accumulation, mid-stream error handling, and the possibility of a partial result that no status code tells you about.

## The SSE Event Sequence

A stream is a sequence of named SSE events. Each has an `event:` line and a `data:` line whose JSON carries a matching `type`.

The canonical order:

1.  `message_start` — a `Message` object with `content` empty. Carries initial `usage`.
2.  For each content block, in order:
    -   `content_block_start` — includes an `index` matching the block’s eventual position in `content`.
    -   one or more `content_block_delta` — incremental payload.
    -   `content_block_stop`.
3.  One or more `message_delta` — top-level changes: `stop_reason`, `stop_sequence`, cumulative `usage`.
4.  `message_stop` — the final event.

`ping` events may appear anywhere and carry no information; discard them. `error` events may also appear anywhere, including after a 200 has already been sent.

An abbreviated real stream:

    event: message_start
    data: {"type":"message_start","message":{"id":"msg_01...","type":"message","role":"assistant","content":[],"model":"claude-sonnet-5-5","stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":25,"output_tokens":1}}}

    event: content_block_start
    data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

    event: ping
    data: {"type":"ping"}

    event: content_block_delta
    data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

    event: content_block_stop
    data: {"type":"content_block_stop","index":0}

    event: message_delta
    data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":15}}

    event: message_stop
    data: {"type":"message_stop"}

Note the `index`. This example has a single block, so every delta carries index 0. A response with several blocks (text, then a tool call, then more text) gives each block its own index, and the index on a delta tells you which block it extends. Route every delta to its accumulator by index; never assume a delta belongs to the block you most recently saw start.

## Delta Types

`content_block_delta` always carries an `index` and a `delta` whose `type` tells you how to apply it.

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
  Delta type           Payload field     Applies to                      How to accumulate
  -------------------- ----------------- ------------------------------- -----------------------------------------------------------------------------------------
  `text_delta`         `text`            `text` blocks                   String concatenation.

  `input_json_delta`   `partial_json`    `tool_use`, `server_tool_use`   Concatenate the **string fragments**, parse once at `content_block_stop`.

  `thinking_delta`     `thinking`        `thinking` blocks               String concatenation.

  `signature_delta`    `signature`       `thinking` blocks               Store verbatim; it validates block integrity. Arrives just before `content_block_stop`.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------

`input_json_delta` is the one that catches people. The deltas are fragments of a JSON *string* — `{"location": "San Fra` is a legitimate delta. You cannot parse each one. You concatenate, then parse once the block closes; the final `tool_use.input` is always an object. Current models tend to emit one complete key-and-value at a time, which means you may see noticeable pauses between these events while the model works. That is normal, not a stall.

A thinking block opens with a `content_block_start` whose block is `{"type": "thinking", "thinking": "", "signature": ""}`. With `display: "summarized"`, `thinking_delta` events then stream the summary; a single `signature_delta` follows, and `content_block_stop` closes the block.

Thinking blocks with `display: "omitted"`, the default on current models, are a special case: you receive a single `thinking_delta` with an empty string, then a `signature_delta`, then the block closes. Do not interpret the empty thinking text as a failure. With `display: "updates"` (beta), only progress-update blocks carry text in their `thinking_delta` events, and a pause of several seconds before one opens is normal. To reassemble complete blocks with their signatures, prefer the SDK's accumulator (`stream.get_final_message()` in Python) over concatenating deltas yourself.

A `fallback` content block can arrive as a `content_block_start`/`content_block_stop` pair with no deltas between them. Handle zero-delta blocks gracefully.

## Usage Accounting in a Stream

Usage is split across two points in the stream, and the semantics differ.

-   `message_start` carries initial `usage` — input tokens, cache fields, and an `output_tokens` value of 1 (a placeholder, not a real count).
-   `message_delta` carries **cumulative** usage. The last `message_delta` before `message_stop` holds the final figures.

So if you are metering cost, read input tokens and cache fields from `message_start`, and take output tokens from the final `message_delta`. Summing `output_tokens` across `message_delta` events double-counts, because the values are cumulative rather than incremental.

## Accumulating a Stream by Hand

Writing an accumulator is instructive even if you then use the SDK helper, because it makes the index routing concrete.

``` {.sourceCode .python}
import json

def accumulate(event_iter):
    message = None
    blocks = {}   # index -> dict

    for event in event_iter:
        t = event.type

        if t == "message_start":
            message = event.message.model_dump()
            message["content"] = []

        elif t == "content_block_start":
            blocks[event.index] = {
                "block": event.content_block.model_dump(),
                "text": "",
                "json": "",
            }

        elif t == "content_block_delta":
            acc = blocks[event.index]
            d = event.delta
            if d.type == "text_delta":
                acc["text"] += d.text
            elif d.type == "thinking_delta":
                acc["text"] += d.thinking
            elif d.type == "input_json_delta":
                acc["json"] += d.partial_json
            elif d.type == "signature_delta":
                acc["block"]["signature"] = d.signature

        elif t == "content_block_stop":
            acc = blocks[event.index]
            b = acc["block"]
            if b["type"] in ("text",):
                b["text"] = acc["text"]
            elif b["type"] == "thinking":
                b["thinking"] = acc["text"]
            elif b["type"] in ("tool_use", "server_tool_use"):
                b["input"] = json.loads(acc["json"]) if acc["json"] else {}

        elif t == "message_delta":
            message.update(event.delta.model_dump())
            message["usage"].update(event.usage.model_dump(exclude_none=True))

        elif t == "message_stop":
            message["content"] = [blocks[i]["block"] for i in sorted(blocks)]
            return message

        # unknown event types: ignore, per the versioning policy
    raise StreamTruncated("stream ended without message_stop")
```

Two things in that code are not incidental. The final `else` is absent on purpose — unknown event types must be ignored, because new ones can be added as a non-breaking change. And the function raises if the iterator ends without `message_stop`, because a stream that simply stops is the failure mode you must detect yourself.

In practice, use the SDK:

``` {.sourceCode .python}
with client.messages.stream(
    model="claude-sonnet-5-5",
    max_tokens=16000,
    messages=messages,
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    final = stream.get_final_message()
```

`text_stream` yields only text chunks. `get_final_message()` returns a complete `Message` identical in shape to what `messages.create()` would have returned — which is the right tool when you need streaming purely for connection survival on a large `max_tokens` and do not care about incremental display. You can also iterate raw events with `for event in stream:` and branch on `event.type` yourself.

## Errors in the Middle of a Stream

This is the part that distinguishes a robust integration. **Once the server has sent a 200 and begun streaming, HTTP-level error handling is over.** Failures after that point arrive as `error` events inside the stream.

    event: error
    data: {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"}}

That `overloaded_error` would have been HTTP 529 on a non-streaming request. Because it arrives mid-stream, the SDK’s automatic retry logic does not apply — retries are keyed off HTTP status codes and connection failures, neither of which occurred.

So your stream consumer needs three things your non-streaming consumer does not:

1.  **An `error` event branch** that surfaces the error type rather than silently ending the loop.
2.  **Truncation detection** — a flag set only on `message_stop`, checked after the loop exits. A stream that ends without `message_stop` is incomplete, and nothing else will tell you.
3.  **A resumption or retry policy** for partial output.

For resumption, the current guidance depends on model generation. On older models you could capture the partial text and continue it as a prefilled assistant turn. On newer models, where prefill is restricted, the recommended approach is to send a new request containing a **user** message that includes the partial response and asks the model to continue from where it stopped.

``` {.sourceCode .python}
resume = [
    *original_messages,
    {"role": "user", "content":
        f"Your previous response was interrupted and ended with:\n\n{partial}\n\n"
        "Continue from exactly where you left off."},
]
```

Tool use and thinking blocks cannot be partially recovered. If a stream dies mid-`tool_use`, you have an incomplete JSON fragment and no usable call; you must retry the turn. Only text blocks support resumption.

## Prompt Caching: What It Is

Before the model can write a single word of its answer, it has to read and process every token of the prompt. For a 100,000-token prompt that is a large amount of work, and it is repeated in full on every request, even when most of the prompt (the system prompt, the tool definitions, a reference document) is exactly the same as last time.

Prompt caching lets the API keep the result of that processing for the beginning of a prompt and reuse it. You mark a point in the prompt; everything up to and including that point becomes a cache entry; later requests that start with exactly the same content, byte for byte, read the stored result instead of processing those tokens again. Only the part after the matching beginning (the new question, the latest turn) is processed fresh. The cache stores the model’s internal working state, not your text, and it never changes the answer: a cached request produces the same output it would have without caching.

The economics are what make it mandatory for serious workloads:

  Operation                   Cost relative to base input rate
  --------------------------- -------------------------------------------------
  Normal uncached input       1×
  Cache write, 5-minute TTL   1.25×
  Cache write, 1-hour TTL     2×
  Cache read (hit)            0.1×, and as low as 0.025×–0.05× on some models

A cache read costs roughly a tenth of a fresh read. Write once at 1.25×, read ten times at 0.1×, and you have spent 2.25× instead of 11×. Cache hits also reduce latency — the prefix is not reprocessed — and, critically, **cache reads do not count toward your input-tokens-per-minute rate limit** on current models. That last property is how a workload with a 200,000-token shared context stays inside a 2,000,000 ITPM budget at meaningful concurrency: if the shared context counted, ten requests a minute would use the whole budget.

## Marking a Cache Breakpoint

The explicit mechanism is a `cache_control` field on a content block:

``` {.sourceCode .python}
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=2048,
    system=[
        {"type": "text", "text": LEGAL_CORPUS,
         "cache_control": {"type": "ephemeral"}},
    ],
    messages=[{"role": "user", "content": question}],
)
```

Only `"ephemeral"` is supported as a cache type. Adding `"ttl": "1h"` selects the one-hour variant:

``` {.sourceCode .python}
"cache_control": {"type": "ephemeral", "ttl": "1h"}
```

`cache_control` can only sit on a content block, so whatever you mark must be in block-list form. `system` accepts a plain string, but a string has nowhere to carry the marker. The same applies to a message whose `content` is a string, as `question` is in the example above. To place a breakpoint inside `messages`, write that message's content as a list of blocks:

``` {.sourceCode .python}
messages=[{"role": "user", "content": [
    {"type": "text", "text": LONG_DOCUMENT,
     "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": question},
]}]
```

Here the document is cached and the question after it is not, so a new question against the same document still produces a hit. Tool definitions take the marker directly on the tool entry in `tools`.

There is also an automatic mode: a top-level `cache_control` on the request, which places a breakpoint on the last cacheable block and moves it forward as the conversation grows. This is the easiest correct answer for an ordinary chat application. It consumes one of your breakpoint slots.

``` {.sourceCode .python}
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=2048,
    cache_control={"type": "ephemeral"},   # automatic breakpoint
    system=SYSTEM_PROMPT,
    messages=history,
)
```

Limits and interactions:

-   **At most 4 explicit breakpoints** per request. The four slots are shared across `tools`, `system`, and `messages`: a marker in any of them counts toward the same total. Automatic caching occupies one slot; if you already have 4 explicit ones, the request returns 400.
-   The limit is **per API call, not per conversation**. Every call is built from scratch, so markers placed on earlier turns do not accumulate; you can place up to four again on each request.
-   If the last block already carries explicit `cache_control` with the **same** TTL, automatic caching is a no-op. With a **different** TTL it is a 400.
-   If the final block is not eligible, automatic caching walks backward to the nearest eligible block; if there is none, caching is skipped silently.
-   Breakpoints themselves cost nothing. You pay only for tokens written, read, or left uncached.

## Caching a Growing Conversation

A breakpoint caches everything before it plus the marked block itself, in `tools` → `system` → `messages` order. Put the marker on the last block of the latest message and the cached prefix is the whole request: tools, system prompt, every earlier message, and every earlier block in the same message.

Because the API is stateless, each turn resends the full history, and the marker moves to the newest block:

  -------------------------------------------------------------------------------------------------
  Turn   Request ends with                          Cache behaviour
  ------ ------------------------------------------ -----------------------------------------------
  1      system, user “Hi” **(marker)**             No entry exists yet: the whole prefix is a
                                                    write.

  2      system, user “Hi”, assistant “Hello!”,     The prefix up to “Hi” matches turn 1’s entry
         user “Explain X” **(marker)**              and is read at the cache rate. Only the new
                                                    blocks are processed and written as a new,
                                                    longer entry.

  3      ...as turn 2, plus the next exchange       Turn 2’s entry is read; the new exchange is
         **(marker)**                               written.
  -------------------------------------------------------------------------------------------------

You do not need to keep the old marker on “Hi”. Matching is by content, not by marker position: on turn 2 the lookback (described below) walks back from the new marker and finds the entry turn 1 wrote. Two conditions keep this working:

-   **The earlier history must stay byte-identical.** Editing or reformatting an earlier message makes everything from that point onward a miss.
-   **The new marker must stay within the lookback window** of the last written entry. A turn that adds many blocks at once, such as a long run of tool calls in an agent loop, can outrun it; add a second breakpoint partway through the new blocks.

### Explicit or Automatic?

For this common case the two modes produce the same result: one breakpoint on the last block, caching the entire request. The differences are in who places it.

-   **Automatic mode** is one top-level field. The API finds the last eligible block on every request, so you never touch your `messages` array to move a marker. It is the right default for an ordinary chat application.
-   **Explicit markers** put the placement in your hands, and you are responsible for choosing a cacheable block. Use them when you need breakpoints in the middle of a request: after the tool definitions, after the system prompt, or after a large document, so that a change to a later layer does not throw away the earlier ones.

The two can be combined, within the four-slot limit and the TTL rule above.

## What Is Cacheable, and the Prefix Rule

The cached prefix is assembled in a fixed order: **`tools` → `system` → `messages`**, up to and including the marked block.

Cacheable:

-   The entire `tools` array definition.
-   `system` content blocks.
-   `messages` content blocks: text in both user and assistant turns, images and documents in user turns, `tool_use` blocks, and `tool_result` blocks.

Not cacheable:

-   Thinking blocks cannot carry a `cache_control` marker themselves. They are still cached when they sit inside an earlier assistant turn that falls within a cached prefix, and they count as input tokens when read from it.
-   Sub-content such as individual citations — mark the containing document block instead.
-   Empty text blocks.

The matching rule is unforgiving: the prefix must be **100% byte-identical**, across text and images alike. A changed whitespace character, a reordered JSON key in a tool definition, a re-encoded image — any of these is a miss.

## Minimum Cacheable Length

A prompt below the model’s minimum is simply processed without caching. **No error is returned.** This is the quietest way to pay for a feature you are not getting.

  --------------------------------------------------------------------------------------------------------
  Minimum cacheable tokens            Example model families
  ----------------------------------- --------------------------------------------------------------------
  512                                 Current-generation Opus, Sonnet, Haiku, Fable, Mythos (5.x series)

  1,024                               Several 4.x and 5.0-era Opus and Sonnet models

  2,048                               Certain Opus 4.7 and legacy Haiku models

  4,096                               Opus 4.5/4.6, Haiku 4.5
  --------------------------------------------------------------------------------------------------------

Exact thresholds are model-specific and change as models are released, so confirm the value for the model you deploy. The operationally important point is the diagnostic: if `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` are both zero, your prompt was not cached, and the most common reason is that it fell below the minimum.

## Reading the Usage Object

``` {.sourceCode .json}
{
  "usage": {
    "input_tokens": 50,
    "cache_read_input_tokens": 100000,
    "cache_creation_input_tokens": 248,
    "output_tokens": 503,
    "cache_creation": {
      "ephemeral_5m_input_tokens": 148,
      "ephemeral_1h_input_tokens": 100
    }
  }
}
```

The field that misleads everybody: **`input_tokens` counts only tokens after the last breakpoint.** It is not total input. In the example above, total input is 100,298 tokens, not 50.

    total_input = cache_read_input_tokens
                + cache_creation_input_tokens
                + input_tokens

Dashboards built on `input_tokens` alone will report a 200,000-token cached workload as a 50-token workload, and your cost model will be wrong by three orders of magnitude in the wrong direction (it will look too cheap, then the invoice arrives).

`cache_creation` breaks writes down by TTL, and its components sum to `cache_creation_input_tokens`.

## TTL Semantics and Mixing

The 5-minute TTL is the default. The lifetime is measured **from the start of the request** that writes or reads the entry — generation time counts against it. Each use refreshes a 5-minute entry at no additional cost, so a steadily used cache stays warm indefinitely.

The 1-hour TTL costs 2× to write instead of 1.25×, and is the right choice when reuse intervals fall between five minutes and an hour: periodic jobs, batch submissions, low-traffic endpoints.

When mixing TTLs in one request, **1-hour breakpoints must appear before 5-minute breakpoints** in the prompt. Billing then follows a cascade, working from the start of the prompt: a cache read for everything up to the furthest point where an existing entry matched, a 1-hour write from there to the last 1-hour breakpoint, and a 5-minute write for the remainder up to the last breakpoint.

For example, take a request with a 1-hour breakpoint at the end of a 50,000-token reference document and a 5-minute breakpoint at the end of the 10,000 tokens of conversation that follow it. On a cold cache nothing is read: the first 50,000 tokens are a 1-hour write and the next 10,000 a 5-minute write. Ten minutes later the 5-minute entry has expired but the 1-hour entry has not. Now the 50,000 document tokens are a cache read, there is no 1-hour write because the match already reaches the last 1-hour breakpoint, and the 10,000 conversation tokens are a 5-minute write again.

There is no manual cache-clear operation. Entries expire through inactivity.

## What Invalidates a Cache

Changes propagate downward through the `tools → system → messages` hierarchy. A change at one level invalidates that level and everything after it.

  ----------------------------------------------------------------------------------------------------------
  Change                                                Invalidates
  ----------------------------------------------------- ----------------------------------------------------
  Any tool definition — name, description, parameters   Tools, system, and messages — everything

  Toggling web search or citations                      System and messages

  Switching `speed` between fast and standard           System and messages

  Editing the top-level `system` text                   System and messages

  `tool_choice`                                         Messages only

  Adding or removing images anywhere in the prompt      Messages only

  Thinking configuration or effort level                Messages only

  Appending a new user turn                             Nothing already cached; only the new content is
                                                        processed
  ----------------------------------------------------------------------------------------------------------

Note the middle group. `tool_choice`, images, and thinking settings are not part of the system prompt, so they leave the tools and system entries intact and cost you only the message-level entries. Toggling web search or citations, by contrast, changes the system prompt the API builds for you, so it reaches one level higher.

The asymmetry is the design guidance in disguise. Appending is cheap; editing anything early is catastrophic. So:

-   Never put a timestamp, a request id, a user name, or a session token before a cache breakpoint. It guarantees a write-every-request, hit-never pattern — the worst of both worlds, paying 1.25× forever.
-   Put the breakpoint on the last block that is identical across the requests you want to share.
-   Keep tool definitions byte-stable. Serialize them from a constant, not from a dict whose key order can shift.
-   Setting an effort level explicitly to the model’s default is equivalent to omitting it and does not invalidate.
-   Where supported, add mid-conversation instructions as an appended `{"role": "system"}` message rather than editing the top-level `system` field, precisely so the cached prefix survives.

## The Lookback Window

Cache *writes* happen only at a marked breakpoint, and each writes one entry, keyed by a hash of the whole prefix up to and including that block. Because the hash covers everything before the block, an entry can match only a request whose prefix is identical up to that point.

Cache *reads* check the breakpoint’s own hash first. On a miss, the system walks backward, checking up to **20 positions** per breakpoint (the breakpoint itself counts as the first). A run of consecutive `tool_use` blocks, or of consecutive `tool_result` blocks, counts as a single position.

This matters for growing conversations. If the breakpoint has drifted more than twenty positions past the last entry that was actually written, the lookback cannot reach it and you get a full miss on a conversation that should have been warm. The fix is to maintain a second, earlier breakpoint closer to the written entry, so there is something within range to find.

For example, suppose the last request that wrote an entry had its marker at position 40, and the next request carries its marker at position 70 because the history has grown in between. The read checks position 70, then 69, and so on back to position 51. That is twenty positions, and the search stops there. The entry at position 40 is never reached, so the whole prefix is processed and written again at the write rate. A second breakpoint kept at position 40 would have been checked directly and would have hit.

## Concurrency and Pre-Warming

A cache entry becomes available only once the first response **begins**. Fire ten parallel requests with the same prefix from cold and you get ten writes and zero hits. For a fan-out pattern, send one request first, wait for it to start responding, then release the rest.

You can also pre-warm deliberately with `max_tokens: 0`:

``` {.sourceCode .python}
client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=0,
    system=[{"type": "text", "text": BIG_PREFIX,
             "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
    messages=[{"role": "user", "content": "warmup"}],
)
```

The response has empty `content`, `stop_reason: "max_tokens"`, and a populated `usage`. No output tokens are billed. Constraints: the warm-up must use the same thinking and effort configuration as your real requests, it cannot combine `max_tokens: 0` with streaming, extended thinking, structured output format, or a forced `tool_choice`, and it is **not permitted inside Message Batches requests**.

## Scoping and Privacy

Caches are isolated at the organization level, always — no cross-organization sharing. On the Claude API and some partner platforms, isolation is additionally per-Workspace. Caching has no effect on output: responses are identical with or without it. Raw prompt text is not stored; the cached representation lives in memory and is deleted after its TTL.

## The Message Batches API

Batching inverts the latency/cost tradeoff. You submit many requests at once, poll, and collect results later. In exchange you pay **50% of standard pricing** on all batch usage.

### Why the Batches API Exists

A large share of real Claude traffic has no one waiting on any individual answer: classifying a million support tickets, summarizing a document archive, running an evaluation suite, generating labels or synthetic data, re-processing a corpus after a prompt change. Pushing that work through the synchronous Messages API has three costs:

-   **Price.** You pay interactive rates for non-interactive work.
-   **Rate-limit contention.** A backfill running at full speed consumes the same ITPM/OTPM budget as your production traffic, and can starve it.
-   **Plumbing.** You have to build and operate your own concurrency control, throttling, backoff, and retry layer to push tens of thousands of requests through without tripping 429s.

The Batches API trades latency for all three. The discount is 50% on input and output tokens and **stacks with prompt caching**. Batches draw on their own rate limits rather than your live per-minute limits, so bulk work does not compete with production. Anthropic does the scheduling, so your client code shrinks to create, poll, and collect.

The lifecycle in one line: **create** the batch with a list of `{custom_id, params}` items → **poll** until `processing_status` is `ended` → **retrieve** the results file and join on `custom_id`. Each `params` object is an ordinary non-streaming Messages API request body.

``` {.sourceCode .python}
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

batch = client.messages.batches.create(requests=[
    Request(
        custom_id=f"doc-{doc.id}",
        params=MessageCreateParamsNonStreaming(
            model="claude-sonnet-5-5",
            max_tokens=1024,
            system=CLASSIFIER_PROMPT,
            messages=[{"role": "user", "content": doc.text}],
        ),
    )
    for doc in documents
])
```

`custom_id` is required, must match `^[a-zA-Z0-9_-]{1,64}$`, and must be unique within the batch. It is the only way to correlate results, because **result order is not guaranteed**.

### The Batch Object

``` {.sourceCode .json}
{
  "id": "msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d",
  "type": "message_batch",
  "processing_status": "in_progress",
  "request_counts": {
    "processing": 2, "succeeded": 0, "errored": 0,
    "canceled": 0, "expired": 0
  },
  "created_at": "2026-09-24T18:37:24.100435Z",
  "ended_at": null,
  "expires_at": "2026-09-25T18:37:24.100435Z",
  "cancel_initiated_at": null,
  "results_url": null
}
```

`processing_status` has three values:

  -------------------------------------------------------------------------------------------------------------------
  Status                              Meaning
  ----------------------------------- -------------------------------------------------------------------------------
  `in_progress`                       Set at creation; work is underway.

  `canceling`                         Cancellation requested, not yet complete.

  `ended`                             All requests finished and results are ready. A canceled batch also ends here.
  -------------------------------------------------------------------------------------------------------------------

Note there is no separate `completed` or `failed` terminal state — poll for `ended`, then inspect `request_counts` and the per-result types.

### Timing and Expiration

-   Most batches finish in **under an hour**.
-   Results become available when all requests complete, or after **24 hours**, whichever comes first.
-   Requests not processed within 24 hours **expire** and are not billed.
-   Results remain downloadable for **29 days** from `created_at`. After that the batch metadata is still viewable but results are gone.

Under heavy demand processing can slow, which raises the share of expirations. Build for it: an `expired` result is a normal outcome to resubmit, not an exception.

Two consequences of these timings are easy to miss. First, “most batches finish within an hour” is an observation, not a service level: the only guarantee is the 24-hour window, so a job with a harder deadline than that does not belong in a batch. Second, the 29-day retention is the end of the results, not just the batch: persist what you need as soon as the batch ends, because there is no way to regenerate expired results except by paying for the requests again.

Cancellation is coarse. You can cancel a batch, but you cannot modify one: there is no way to add, remove, or edit individual requests after creation. Cancellation is also not instantaneous — the batch passes through `canceling`, requests already being processed may still complete, and those come back as `succeeded` and are **billed**. Only requests that had not yet reached the model come back as `canceled`.

### Result Types

  ---------------------------------------------------------------------------------------------------------------------------------
  Result type             Billed                  Meaning
  ----------------------- ----------------------- ---------------------------------------------------------------------------------
  `succeeded`             Yes                     `result.message` holds a normal `Message`.

  `errored`               No                      Invalid request or server error; `result.error` holds the standard error shape.

  `canceled`              No                      Canceled before reaching the model.

  `expired`               No                      The 24-hour window closed before the request reached the model.
  ---------------------------------------------------------------------------------------------------------------------------------

A crucial operational detail: **request params are validated asynchronously**, and validation errors appear only after the whole batch has ended. Submit 100,000 malformed requests and you learn about it an hour later. Always smoke-test one request against the synchronous Messages API before submitting the batch.

### Retrieving Results

Results come back as `.jsonl` from `results_url`, one JSON object per line. Stream them rather than buffering — a 100,000-request batch is not something you want in memory.

``` {.sourceCode .python}
for result in client.messages.batches.results(batch.id):
    outcome = result.result
    match outcome.type:
        case "succeeded":
            store(result.custom_id, outcome.message)
        case "errored":
            if outcome.error.error.type == "invalid_request_error":
                quarantine(result.custom_id)   # fix the request; retrying is pointless
            else:
                resubmit(result.custom_id)     # server-side; safe to retry
        case "expired" | "canceled":
            resubmit(result.custom_id)
```

The branch on `invalid_request_error` versus everything else is the one piece of logic that matters. A validation error will fail identically forever; a server error will probably succeed on retry. Treating them the same means either an infinite retry loop or silently dropped work.

### Limits and Compatibility

  Constraint               Value
  ------------------------ -------------------------------------------
  Max requests per batch   100,000
  Max batch payload        256 MB (413 `request_too_large` above it)
  Visibility               Workspace-scoped
  Retention                29 days from creation

Supported inside batches: all active models, vision, tool use including server tools, system prompts, multi-turn conversations, extended thinking, prompt caching, and mixed request types in one batch. Not supported, returning a validation error: `stream: true` (results are one file), fast-mode speed tuning, and `max_tokens: 0`.

Batch rate limits are separate: a shared RPM budget across endpoints, plus a cap on how many batch requests may sit in the processing queue, both tiered. A request counts against the queue limit until the model has processed it.

Caching inside batches is best-effort, since you cannot control execution order. The useful pattern is to send one request with a **1-hour** breakpoint on the shared prefix synchronously, wait for it to complete, then submit the batch — which is also why `max_tokens: 0` pre-warming is disallowed inside a batch: the entry would likely expire before the dependent requests ran.

### When to Batch, and When Not To

Batching is the right tool when no human or downstream system is waiting on the individual answer and the job is large enough for the savings to matter:

-   **Bulk offline processing:** classification, extraction, translation, tagging, moderation backfills.
-   **Evaluations and benchmarking:** thousands of prompts against one model, or the same prompts against several. One batch can mix models and parameters, since each request carries its own `params`.
-   **Scheduled pipelines:** nightly enrichment, report generation, re-processing a dataset after a prompt change.
-   **Workloads with a large shared prefix** — the same system prompt and reference document for every item — where the batch discount and cache reads compound, subject to the best-effort caching caveat above.

It is the wrong tool in four situations:

-   **Interactive or latency-sensitive work.** Chat, autocomplete, and user-facing agents cannot tolerate an unpredictable completion time.
-   **Dependent multi-step work.** Each batch request is one independent Messages call. A request may carry a multi-turn conversation history, but nothing in a batch can feed one request's output into another. An agentic tool-use loop, or a pipeline where step *N*+1 needs step *N*'s answer, would need a new batch per step, and the latency compounds with every step.
-   **Small jobs.** For a few dozen requests, the polling and result-handling code costs more engineering than the discount saves.
-   **Deadlines shorter than 24 hours** that must be met, as discussed under timing.

### Limitations at a Glance

  -------------------------------------------------------------------------------------------------------------------------
  Limitation                       Consequence for your code
  -------------------------------- ----------------------------------------------------------------------------------------
  100,000 requests / 256 MB        Split larger jobs across several batches.

  24-hour window                   Detect `expired` results and resubmit them; they are not billed.

  No result ordering               Join on `custom_id` only; make it unique and meaningful.

  Per-request outcomes             A batch can end with any mix of result types; handle each one.

  Asynchronous validation          Smoke-test one request synchronously before submitting.

  No streaming, fast mode,         These return validation errors inside a batch.
  or `max_tokens: 0`

  No modification after creation   Cancel and resubmit; in-flight requests may still complete and be billed.

  29-day retention                 Persist results promptly; expired results cannot be recovered.

  Best-effort caching              Warm the shared prefix synchronously with a 1-hour TTL first.
  -------------------------------------------------------------------------------------------------------------------------

## Choosing Among the Three

  -------------------------------------------------------------------------------------------------------
  Dimension          Streaming                      Non-streaming          Batching
  ------------------ ------------------------------ ---------------------- ------------------------------
  Latency            Lowest perceived               Full generation wait   Minutes to 24 hours

  Cost               Standard                       Standard               50% of standard

  Long generations   Safe                           Risky past \~10 min    Safe

  Partial failure    Mid-stream `error` events      HTTP status            Per-request result type

  Retry              Manual for mid-stream faults   SDK automatic          Per-`custom_id` resubmission

  Throughput shape   One conversation at a time     One at a time          Up to 100k per submission

  Caching            Full control                   Full control           Best-effort; warm separately
  -------------------------------------------------------------------------------------------------------

The decision is usually straightforward. A human is waiting: stream. No human is waiting and the work is divisible: batch, and take the 50%. A human is waiting *and* the generation is enormous: stream, and reconsider whether a human should be waiting.

The one combination that does not exist is streaming inside a batch. They are opposite answers to the same question, and `stream: true` in a batch request is a validation error.

## Practice Questions

**Q4.1** You set `max_tokens: 64000` on a non-streaming request. Most calls succeed, but roughly one in twenty fails after several minutes with a connection reset and no HTTP status. What is the correct fix?

A. Lower `max_tokens` until the failures stop. B. Increase the client-side timeout to 30 minutes. C. Use streaming (optionally with `get_final_message()`) or the Batches API for long generations. D. Add a retry wrapper that resends on connection reset.

**Q4.2** While consuming a stream, you parse each `input_json_delta` payload with `json.loads` as it arrives and get constant parse errors. Why?

A. Each delta is a fragment of a JSON string; you must concatenate all of them and parse at `content_block_stop`. B. `input_json_delta` payloads are base64-encoded. C. Tool inputs stream as `text_delta`, not `input_json_delta`. D. You must set `eager_input_streaming: false` to get parseable deltas.

**Q4.3** Your streaming metering code sums `usage.output_tokens` across every `message_delta` event. Reported output tokens are far higher than your invoice. Why?

A. `message_delta` reports tokens including cache writes. B. `usage` in `message_delta` is cumulative, not incremental, so summing double-counts. C. Only `message_start` carries valid output token counts. D. Streaming bills output tokens at a discounted rate.

**Q4.4** Mid-stream your consumer receives `{"type":"error","error":{"type":"overloaded_error",...}}`. Your SDK’s `max_retries=3` does not retry. Why not?

A. `overloaded_error` is never retryable. B. The error arrived after `message_stop`, which closes the retry window. C. Retries are disabled automatically whenever `stream=True`. D. The HTTP response was already 200, so status-based retry logic never engages; mid-stream errors are yours to handle.

**Q4.5** A streaming consumer sometimes writes truncated answers to your database. No exception is raised and no `error` event is seen. What is the missing safeguard?

A. Check that `stop_reason` is `end_turn` in `message_start`. B. Verify `content_block_stop` arrived for index 0. C. Track whether `message_stop` was received, and treat a stream that ends without it as incomplete. D. Compare accumulated text length against `max_tokens`.

**Q4.6** You add `cache_control` to a 300-token system prompt. `usage` reports zero for both cache fields on every call, and no error appears. What is happening?

A. The prompt is below the model’s minimum cacheable length, so caching is skipped silently. B. The breakpoint was placed on a non-cacheable block type. C. You need a beta header to enable prompt caching. D. Cache fields only populate on the second and later requests.

**Q4.7** Your system prompt is structured as: `[current timestamp]`, then a 40,000-token policy document marked with `cache_control`. You pay cache-write costs on every request and never get a hit. Why?

A. 40,000 tokens exceeds the maximum cacheable prefix size. B. Only the `messages` array supports caching, not `system`. C. The default 5-minute TTL is too short for the request interval. D. The timestamp precedes the breakpoint, so the prefix differs every request and can never match.

**Q4.8** A dashboard built on `usage.input_tokens` reports your document-QA service averaging 60 input tokens per request. You know each request includes a 180,000-token cached document. Which statement is correct?

A. The dashboard is right; cached tokens are not input tokens. B. `input_tokens` counts only tokens after the last breakpoint; total input is `cache_read + cache_creation + input_tokens`. C. `input_tokens` excludes the system prompt, which holds the document. D. Cached documents are billed as output tokens.

**Q4.9** Your conversational agent caches a stable tool array plus system prompt. After you add a description to one tool definition, costs spike. What was invalidated?

A. Only the tools portion of the cache. B. Nothing — descriptions are metadata and do not affect the cache. C. Tools, system, and messages — a change at the tools level invalidates everything after it. D. Only requests that actually invoke the changed tool.

**Q4.10** You fan out 20 parallel requests sharing a 150,000-token prefix from a cold cache. You expected 1 write and 19 hits; you got 20 writes. Why?

A. A cache entry only becomes available once the first response has begun, so simultaneous cold requests all write. B. Parallel requests are load-balanced to different cache shards. C. Explicit breakpoints are not shared across concurrent requests. D. The 5-minute TTL expired between requests.

**Q4.11** You run a nightly job against a 100,000-token reference corpus, with roughly 20 minutes between calls. Which caching configuration is most appropriate?

A. Default 5-minute ephemeral caching. B. A 1-hour TTL breakpoint on the corpus. C. No caching; the interval is too long for any benefit. D. Four breakpoints spread evenly through the corpus with the default TTL.

**Q4.12** You submit a 50,000-request batch. An hour later `processing_status` is `ended` and `request_counts.errored` is 50,000. Every error is `invalid_request_error`. What process change would have caught this?

A. Setting a lower per-batch request count. B. Adding `stream: true` to surface validation errors incrementally. C. Polling more frequently so errors surface sooner. D. Validating one representative request against the synchronous Messages API before submitting, since batch params are validated asynchronously.

**Q4.13** Your batch result processor matches results to inputs by array position. Occasionally records are attributed to the wrong document. What is wrong?

A. Batch result order is not guaranteed; you must match on `custom_id`. B. Results are paginated and you are missing a page. C. `errored` results are omitted from the file, shifting indices. D. The `.jsonl` file is sorted by token count.

**Q4.14** A batch of 80,000 requests returns with 61,000 `succeeded` and 19,000 `expired`. What does this mean and what are you billed?

A. The expired requests failed validation and are billed at 50%. B. Expired means results were deleted after 29 days; they are billed in full. C. The 24-hour window closed before those requests reached the model; expired requests are not billed and can be resubmitted. D. The batch exceeded 256 MB, so the remainder was dropped and billed.

**Q4.15** You want 50% cost savings and incremental token display for the same workload. What should you do?

A. Set both `stream: true` and submit via the Batches API. B. Choose one — `stream: true` is a validation error in a batch request, so pick based on whether a human is waiting. C. Use the Batches API and consume `results_url` as a stream of SSE events. D. Use streaming and apply the batch discount by setting `service_tier: "batch"`.
