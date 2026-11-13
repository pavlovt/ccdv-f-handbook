# Structured Output, Multimodal Input, and Failure Handling

The previous chapters covered how to call the API and how to make those calls fast and cheap. This one covers the three places where integrations actually break in production: getting output your code can parse, getting non-text input in correctly, and responding sensibly when something goes wrong. The unifying theme is the distinction drawn in the final section — a failure at the integration layer versus one at the model layer. Almost every bad on-call hour with an LLM integration starts with someone misclassifying one as the other.

## Why “Just Ask for JSON” Fails

The naive approach is a prompt that says “respond only with JSON matching this shape.” It works most of the time, which is exactly what makes it dangerous. The failure modes are conversational preamble (“Here’s the JSON you requested:”), markdown fencing, trailing commentary after the closing brace, schema drift (a renamed field, a string where you expected a number, an enum value outside your enum), and truncation when `stop_reason` is `max_tokens` and the object lands half-written.

A regex that strips fences and finds the outermost braces handles maybe 97% of cases. The remaining 3% becomes a retry loop, and retry loops on a non-deterministic generator are a cost and latency problem that scales with traffic. The right move is a mechanism that constrains generation rather than requesting a format.

## Constrained Structured Output

The API supports schema-constrained JSON via `output_config.format`. Rather than asking the model to produce JSON, the decoder is constrained so that only schema-valid tokens can be emitted.

``` {.sourceCode .python}
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": email_body}],
    output_config={
        "format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "name":           {"type": "string"},
                    "email":          {"type": "string", "format": "email"},
                    "plan_interest":  {"type": "string"},
                    "demo_requested": {"type": "boolean"},
                },
                "required": ["name", "email", "plan_interest", "demo_requested"],
                "additionalProperties": False,
            },
        }
    },
)
payload = json.loads(next(b.text for b in response.content if b.type == "text"))
```

The JSON arrives in a normal `text` content block. There is no new block type.

With the SDK, `messages.parse()` wraps the whole round trip — it transforms a Pydantic model into a schema, sends it, validates the response, and hands back a typed object in `parsed_output`:

``` {.sourceCode .python}
from pydantic import BaseModel

class ContactInfo(BaseModel):
    name: str
    email: str
    plan_interest: str
    demo_requested: bool

response = client.messages.parse(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": email_body}],
    output_format=ContactInfo,
)
contact = response.parsed_output   # a ContactInfo instance
```

### The Supported Schema Subset

Constrained decoding compiles your schema into a grammar, which means the schema language is a subset of JSON Schema, not all of it.

  ---------------------------------------------------------------------------------------------------------------------------------
  Feature                             Supported
  ----------------------------------- ---------------------------------------------------------------------------------------------
  Types                               `object`, `array`, `string`, `integer`, `number`, `boolean`, `null`

  `enum`                              Yes, with string, number, boolean, or null members only

  `const`, `anyOf`, `allOf`           Yes (`allOf` combined with `$ref` is not)

  `$ref`, `$def`, `definitions`       Internal references only

  `default`                           Yes

  `required`                          Yes

  `additionalProperties`              **Must be `false`** on objects

  String `format`                     `date-time`, `time`, `date`, `duration`, `email`, `hostname`, `uri`, `ipv4`, `ipv6`, `uuid`

  `minItems`                          Only values 0 and 1

  `pattern`                           Basic regex: quantifiers, character classes, groups
  ---------------------------------------------------------------------------------------------------------------------------------

Not supported, and a **400** if you send them: recursive schemas, complex types inside enums, external `$ref` (anything resolving over HTTP), numeric constraints (`minimum`, `maximum`, `multipleOf`), string length constraints (`minLength`, `maxLength`), array constraints beyond `minItems` 0/1, `additionalProperties` set to anything but `false`, and advanced regex features — backreferences, lookahead/lookbehind, word boundaries, large `{n,m}` ranges.

The SDK softens this. Its transformation step strips unsupported constraints, appends them to the field’s description so the model still sees the intent, forces `additionalProperties: false`, filters `format` values to the supported set, and — if the helper validates — checks the response against your *original* schema including the stripped constraints. A field declared `minimum: 100` is therefore sent as a plain integer with `{minimum: 100}` in its description, enforced client-side after the fact. `transform_schema()` runs that transformation without sending anything.

### Complexity Limits

Constrained decoding has hard ceilings. They apply to every schema the API compiles into a grammar in a single request: the `output_config.format` schema, if there is one, and the `input_schema` of every tool marked `strict: true` (strict tools are covered in the next section). The first limit counts tool definitions; the other two count fields, summed across all of those schemas rather than per schema:

  -------------------------------------------------------------------------------------------
  Limit                               Value
  ----------------------------------- -------------------------------------------------------
  Strict tools per request            20 tool definitions (non-strict tools do not count)

  Optional parameters, total          24 (anything not in `required`)

  Union-type parameters, total        16 (`anyOf`, or type arrays like `["string","null"]`)
  -------------------------------------------------------------------------------------------

Required fields do not count toward the optional-parameter limit, but a required field whose type is a union (`anyOf`, or a type array such as `["string","null"]`) still counts toward the union-type limit; a Pydantic `Optional[str] = None` field is both optional and a union, so it counts against both. The budgets are shared, so 20 strict tools with two optional fields each is within the tool limit but spends 40 optional parameters against a budget of 24, and the request fails; a single strict tool with 24 optional fields is fine.

Beyond these there is an internal grammar-size cap that produces a 400 reading *“Schema is too complex for compilation.”*, plus a 180-second compilation timeout as a backstop.

The remedies, in order of preference: mark only the critical tools `strict`; make parameters required and have the model supply explicit defaults rather than omitting them; flatten deeply nested optional structures; split the work across requests or sub-agents. The second cuts against instinct — `Optional[str]` everywhere is good defensive typing and bad schema design here, because each optional field spends part of a budget of 24.

### Latency, Caching, and Interactions

-   The **first** use of a schema pays grammar compilation latency. Compiled grammars are cached 24 hours from last use, and invalidated by a change to the schema *structure* or the set of tools — changing only `name` or `description` does **not** invalidate.
-   Constrained output adds a system prompt describing the format, which adds input tokens.
-   Changing `output_config.format` **invalidates the prompt cache** for that thread. Do not vary the schema per request on a cached workload.
-   Incompatible with citations (400 if both are enabled) and with message prefilling. Compatible with batching, streaming, and token counting.
-   The `output_config.format` grammar applies only to the model’s direct output — not to tool arguments (constrain those with `strict: true` on the tool), tool results, or thinking. The constraint is applied only while the final answer is being written. Thinking and tool calls that come before it in the same response are generated without it, so the model can reason freely and still emit constrained final output.

### Failure Modes That Still Exist

Constrained decoding guarantees syntactic validity, not that you get a result.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Case                    Signal                                       Handling
  ----------------------- -------------------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------
  Refusal                 `stop_reason: "refusal"`, HTTP 200, billed   The refusal text can override schema compliance. Check `stop_reason` before parsing.

  Truncation              `stop_reason: "max_tokens"`                  Output may be incomplete and invalid. Retry with a higher `max_tokens`.

  Enum casing             None — completes normally                    The model may alter capitalization of enum or const values. Compare case-insensitively; never define enum values that differ only by case.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

One specific trap: asking for the model’s step-by-step reasoning inside a constrained schema can trigger a reasoning-extraction refusal. Request a short explanation field instead of a reasoning trace.

For HIPAA-regulated work, structured outputs are HIPAA eligible, but the schema itself is cached for up to 24 hours, so **PHI must never appear in property names, enum values, const values, or regex patterns** — only in message content.

## Tool Use as a Structured Output Mechanism

Before constrained output existed, the standard technique for reliable JSON was to define a tool whose `input_schema` was your target shape, force the model to call it, and read the arguments without ever executing anything. It remains relevant: it works on every model, it is how you get structured *tool arguments* rather than a structured final answer, and a large amount of existing code does it.

``` {.sourceCode .python}
tools = [{
    "name": "record_ticket",
    "description": "Record a classified support ticket.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            "component": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": ["severity", "component", "summary"],
        "additionalProperties": False,
    },
}]

response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "tool", "name": "record_ticket"},
    messages=[{"role": "user", "content": ticket_text}],
)

block = next(b for b in response.content if b.type == "tool_use")
ticket = block.input      # already a dict
```

Forcing the call means `stop_reason` is `tool_use` and the block’s `input` is already a parsed object — no string parsing at all. Adding `strict: true` applies the same schema guarantee to the arguments.

`tool_choice` options:

  ----------------------------------------------------------------------------------------
  Value                               Behavior
  ----------------------------------- ----------------------------------------------------
  `{"type": "auto"}`                  Default. The model decides whether to call a tool.

  `{"type": "any"}`                   Must call some tool, model’s choice which.

  `{"type": "tool", "name": "X"}`     Must call tool X.

  `{"type": "none"}`                  Tool calls disabled.
  ----------------------------------------------------------------------------------------

Any of these also accepts `disable_parallel_tool_use: true` to limit the model to one call per turn.

Which mechanism to use:

  ----------------------------------------------------------------------------------------------------------------------------------
  Need                                                           Use
  -------------------------------------------------------------- -------------------------------------------------------------------
  A structured **final answer** to the user                      `output_config.format`

  Schema-valid **tool arguments**                                `strict: true` on the tool

  Both in one request                                            Both; they compose

  Structured output on a model without `output_config` support   Forced tool call

  Structured output alongside citations                          Forced tool call (citations conflict with `output_config.format`)
  ----------------------------------------------------------------------------------------------------------------------------------

## Prefill, and Why It Is Mostly Historical

Prefill means ending `messages` with a partial `assistant` turn, which the model continues:

``` {.sourceCode .python}
messages=[
    {"role": "user", "content": "What is Latin for ant? (A) Apoidea (B) Rhopalocera (C) Formicidae"},
    {"role": "assistant", "content": "The answer is ("},
]
```

It was the classic trick for suppressing preamble and forcing a format — prefill `{` and the model has no room for “Here’s your JSON.”

**Prefilling is not supported on newer models and returns a 400.** The documented replacements are structured outputs or system prompt instructions. It is also explicitly incompatible with `output_config.format`, so even where prefill works you cannot combine the two. Know the technique for migration work; do not reach for it in new code.

## Schema Design Guidance

Independent of mechanism, schema shape affects output quality, because the schema is part of what the model reads.

-   **Name fields the way a human would.** `shipping_address_line_1` outperforms `addr1`; names are semantic signal, not just keys.
-   **Use `description` liberally.** It is the only place for nuance a type cannot express: units, timezone, format, what “unknown” looks like.
-   **Prefer `enum` to free strings** wherever the value space is closed.
-   **Prefer required fields with explicit sentinels** over optional ones. `{"status": "unknown"}` beats a missing key, and optionals are a scarce budget.
-   **Keep nesting shallow**, and avoid enum members distinguished only by case.

## Vision: Image Input

Images are `image` content blocks inside a user message, with one of three source types.

``` {.sourceCode .python}
# base64
{"type": "image", "source": {
    "type": "base64", "media_type": "image/png", "data": b64_string}}

# URL
{"type": "image", "source": {
    "type": "url", "url": "https://example.com/chart.png"}}

# Files API reference
{"type": "image", "source": {"type": "file", "file_id": "file_011CN..."}}
```

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Source                  When to use                                   Caveats
  ----------------------- --------------------------------------------- -----------------------------------------------------------------------------------------------------------
  `base64`                One-off images, images you generate locally   Inflates payload \~33%; resent on every turn of a conversation; the only option on some partner platforms

  `url`                   Publicly reachable images                     The fetch must succeed from Anthropic’s side; no auth

  `file`                  Images reused across turns or runs            Requires an upload first; workspace-scoped
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The base64 caveat deserves emphasis. Every turn resends the entire history, so a 4 MB base64 image is re-uploaded on each call. For agentic or multi-turn image work, the Files API is the correct design: upload once, reference by id.

### Formats and Limits

Supported media types: `image/jpeg`, `image/png`, `image/gif` (first frame only — animation is ignored), `image/webp`.

  ---------------------------------------------------------------------------------------------
  Limit                               Value
  ----------------------------------- ---------------------------------------------------------
  Max dimensions                      8000 × 8000 px

  Max size per image (base64)         10 MB on the Claude API; 5 MB on some partner platforms

  Max images per request              100 on 200k-context models; 600 on others

  Max images per claude.ai message    20

  Request size                        32 MB for the Messages API
  ---------------------------------------------------------------------------------------------

A conditional rule bites in batch-image workloads: if a request contains **more than 20 images**, every image must have **neither dimension above 2000 px** — a count that includes images from earlier turns and images inside `tool_result` content. Violating it returns an `invalid_request_error` referring to many-image requests. So “send 50 screenshots” requires downscaling to 2000 px first, even though the per-image limit is 8000 px.

### Resolution Tiers and Token Cost

Images are tokenized as patches, with each 28×28 pixel patch costing one visual token:

    tokens = ceil(width / 28) * ceil(height / 28)

A 1000×1000 image is therefore 36 × 36 = 1,296 tokens.

Images larger than the model’s maximum long edge are **downscaled** before processing, preserving aspect ratio. There are two tiers:

  Tier              Models          Max long edge   Max visual tokens
  ----------------- --------------- --------------- -------------------
  Standard          Most models     1568 px         \~1568
  High-resolution   Newest models   2576 px         \~4784

High-resolution handling is automatic on supporting models and needs no beta header. It can cost roughly 3× the tokens of standard-tier processing for the same source image — a material cost difference arising purely from a model change, with no code change.

Consequences of downscaling:

  Input         Standard tier               High-res tier
  ------------- --------------------------- ----------------------------
  1000 × 1000   unchanged, 1296 tokens      unchanged, 1296 tokens
  1920 × 1080   1456 × 819, \~1560 tokens   unchanged, \~2691 tokens
  3840 × 2160   1456 × 819, \~1560 tokens   2576 × 1449, \~4784 tokens

Uploading a 4K screenshot to a standard-tier model buys you nothing: it is downscaled to about 1456 px wide, so you paid the bandwidth and got 1456-px detail. Pre-resize to the tier’s limit for identical results at a fraction of the payload.

To have an oversized image **rejected** rather than silently downscaled — when coordinate accuracy matters, for instance — set `"oversized_image": "error"` in the image block’s `transformations` field. One exception runs the other way: images returned as `tool_result` to the computer-use and browser-use tools are rejected rather than downscaled when over the limits, so resize those yourself.

### Practical Guidance

-   Place images **before** text in the user turn. Other orderings work, but image-then-question is the documented preference.
-   Label multiple images with short text blocks (`Image 1:`, `Image 2:`) and refer to them by label.
-   In multi-turn work, add new images in later user turns; earlier ones stay in history without re-upload if you used the Files API.
-   Images under about 200 px may be misinterpreted, and heavy JPEG compression can make text unreadable — inspect what you actually send, not the original.
-   The model will not identify people by name, counts and coordinates are approximate, and it is unsuited to diagnostic medical imaging.

## Document and PDF Input

PDFs go in `document` content blocks.

``` {.sourceCode .python}
{"type": "document",
 "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
 "cache_control": {"type": "ephemeral"}}
```

Source types mirror images: `base64`, `url`, and `file` (a Files API id). The `file` source additionally supports `title`, `context`, and `citations: {"enabled": true}`.

  --------------------------------------------------------------------------------------------
  Limit                               Value
  ----------------------------------- --------------------------------------------------------
  Max request size                    32 MB (the whole payload, including everything else)

  Max pages per request               600, or 100 when the context window is under 1M tokens

  Format                              Standard, unencrypted, no password
  --------------------------------------------------------------------------------------------

The tokenization model is what people underestimate. **Each page is processed twice**: rendered as an image, *and* with its extracted text supplied alongside. Cost is text (roughly 1,500–3,000 tokens per page, depending on density) plus the standard visual-token calculation for each page image.

A 200-page report is therefore a 300,000–600,000 token input before page images. Dense PDFs routinely exhaust the context window well below the 600-page ceiling. Mitigations: split the document, downsample embedded images, or pre-extract text if you do not need visual layout. Token counting against a base64 copy prices a specific file.

PDFs are cacheable — put `cache_control` on the document block, the standard pattern for repeated queries against one document. They also work in batches.

Plain-text documents (`.txt`, `.csv`, `.md`) can be sent as `document` blocks, uploaded to the Files API with MIME type `text/plain`. Binary office formats (`.xlsx`, `.docx`) are **not** supported in document blocks; convert them to text, or to PDF when images matter.

## The Files API

The Files API exists, is out of beta, and needs no beta header. (The legacy `files-api-2025-04-14` header still works but yields older response shapes.)

  --------------------------------------------------------------------------------------------------------
  Operation                           Method and path
  ----------------------------------- --------------------------------------------------------------------
  Upload                              `POST /v1/files` (multipart; optional `expires_in_seconds`)

  List                                `GET /v1/files` (paginated; `limit` default 20, max 1000)

  Metadata                            `GET /v1/files/{file_id}`

  Download                            `GET /v1/files/{file_id}/content` (only when `downloadable: true`)

  Delete                              `DELETE /v1/files/{file_id}`
  --------------------------------------------------------------------------------------------------------

``` {.sourceCode .python}
up = client.files.upload(
    file=("report.pdf", open("report.pdf", "rb"), "application/pdf"),
)
# up.id -> "file_011CNha8iCJcU1wXNR6q4V8w"
```

The file object:

``` {.sourceCode .json}
{
  "id": "file_011CNha8iCJcU1wXNR6q4V8w",
  "type": "file",
  "filename": "report.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1024000,
  "created_at": "2026-01-01T00:00:00Z",
  "downloadable": false,
  "expires_at": null
}
```

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Property                            Detail
  ----------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------
  Max file size                       500 MB (413 above it)

  Total storage                       1 TB per organization

  Rate limit                          \~500 file operations per minute, shared across all file endpoints

  Persistence                         Until deleted or `expires_at`; `expires_in_seconds` ranges from 3,600 to 7,776,000 (1 hour to 90 days) and cannot be changed after upload

  Immutability                        Files cannot be modified or renamed; upload a new one and delete the old

  `downloadable`                      `false` for files you upload; `true` only for files produced by skills or code execution

  Billing                             All file operations are free; content is billed as input tokens when used in a Messages request
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

A `file_id` is accepted by `document` blocks (PDF, plain text), `image` blocks (JPEG, PNG, GIF, WebP), and `container_upload` blocks (datasets for the code execution tool).

**The security property matters more than the limits.** Uploaded files are shared across the entire **workspace** — not scoped to a user, conversation, or session. Any API key with workspace access can reference any file id in it. So never accept a `file_id` from an end user or untrusted source, keep the user-to-file mapping on your own server, and for hard multi-tenant isolation use one workspace per tenant.

Expiration is not a deletion guarantee. After `expires_at`, downloads 404 and Messages requests referencing the file fail before inference, but metadata stays readable for up to 30 days and content may be briefly retained for safety review.

## The Error Taxonomy

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------
  Status            `error.type`              Meaning                                                                                   Retry?
  ----------------- ------------------------- ----------------------------------------------------------------------------------------- ---------------------------
  400               `invalid_request_error`   Malformed or invalid request. Also returned when a spend limit *you* configured is hit.   No — fix the request

  401               `authentication_error`    API key malformed, revoked, or expired                                                    No

  402               `billing_error`           Billing or payment problem                                                                No

  403               `permission_error`        Key lacks permission for the resource                                                     No

  404               `not_found_error`         Resource not found; check path and ids                                                    No

  409               `conflict_error`          Conflicts with the resource’s current state                                               Yes, after resolving

  413               `request_too_large`       Payload over the endpoint maximum                                                         No — shrink it

  429               `rate_limit_error`        Rate limit, or a spend cap                                                                Conditionally — see below

  500               `api_error`               Unexpected internal error                                                                 Yes, with backoff

  504               `timeout_error`           Timed out during processing                                                               Yes; consider streaming

  529               `overloaded_error`        API temporarily overloaded across users                                                   Yes, with backoff
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------

Error bodies have a consistent shape:

``` {.sourceCode .json}
{
  "type": "error",
  "error": {"type": "not_found_error", "message": "..."},
  "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy"
}
```

Request size limits determine when you get a 413: 32 MB for Messages and token counting, 256 MB for Batches, 500 MB for Files. On the direct API a 413 is returned at the edge, before the request reaches application servers, so you get no detail about which part was too large.

### The Two Kinds of 429

This distinction is the one most likely to cost you an outage.

**A rate-limit 429** usually carries a `retry-after` header. Wait that long and retry; the condition clears.

**A spend-cap 429** carries **no `retry-after`**, and retrying will fail until access resumes — at 00:00 UTC on the first of the next month, or when the tier is raised. The body distinguishes it:

``` {.sourceCode .json}
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "You have reached your API usage limits...",
    "details": { "error_code": "enforced_spend_limit_reached" }
  }
}
```

Check `error.details.error_code == "enforced_spend_limit_reached"`. A retry loop that does not check it becomes an infinite loop running for days.

Confusingly, a spend limit *you* configured yourself returns **400 `invalid_request_error`** rather than 429. There is also an acceleration limit: a sharp rise in organization-wide usage can produce 429s even below your nominal ceiling, so ramp traffic gradually rather than going from zero to peak.

### Rate Limit Headers

Limits are enforced per model class on three axes — **RPM** (requests per minute), **ITPM** (input tokens per minute), **OTPM** (output tokens per minute) — using a token bucket that replenishes continuously rather than resetting on a boundary. That is why a burst can trigger a limit even when your per-minute average is comfortable: 60 RPM may be enforced closer to 1 per second.

Headers on every response:

  -------------------------------------------------------------------------------------------------------------------
  Header                                                                Meaning
  --------------------------------------------------------------------- ---------------------------------------------
  `retry-after`                                                         Seconds to wait. Not always present.

  `anthropic-ratelimit-requests-limit` / `-remaining` / `-reset`        Request budget; reset is RFC 3339

  `anthropic-ratelimit-tokens-limit` / `-remaining` / `-reset`          Most restrictive token limit in effect

  `anthropic-ratelimit-input-tokens-limit` / `-remaining` / `-reset`    Input token budget

  `anthropic-ratelimit-output-tokens-limit` / `-remaining` / `-reset`   Output token budget

  `anthropic-priority-input-tokens-*` / `-output-tokens-*`              Priority Tier only

  `anthropic-workspace-id`                                              Which workspace the request counted against
  -------------------------------------------------------------------------------------------------------------------

Remaining-token values are rounded to the nearest thousand, so do not build fine-grained admission control on them. Still, reading `-remaining` and shedding load proactively is far cheaper than absorbing 429s.

Two interactions are worth memorizing:

-   **Cache reads do not count toward ITPM** on current models. Only `input_tokens` (post-breakpoint) and `cache_creation_input_tokens` do. This is why caching raises effective throughput, not just lowers cost.
-   **`max_tokens` does not count toward OTPM.** Only tokens actually generated do. A generous `max_tokens` carries no rate-limit cost.

### Retry Strategy

The SDKs retry automatically: `max_retries=2` by default, exponential backoff, honoring `retry-after`, on connection errors, 408, 409, 429, and any 5xx. For most applications, raising that to 3–5 is the entire retry strategy you need.

When you implement it yourself, the required elements are exponential backoff **and jitter**. Backoff alone, applied to a fleet that all failed at the same instant, produces a synchronized retry wave that re-overloads the service at every doubling — the thundering herd. Jitter decorrelates them.

``` {.sourceCode .python}
import random, time, anthropic

RETRYABLE = (429, 500, 502, 503, 504, 529)

def call_with_backoff(fn, *, attempts=5, base=1.0, cap=60.0):
    for n in range(attempts):
        try:
            return fn()
        except anthropic.APIStatusError as e:
            if e.status_code not in RETRYABLE:
                raise                            # 400/401/403/404/413: never retry
            if e.status_code == 429:
                body = e.body if isinstance(e.body, dict) else {}
                code = body.get("error", {}).get("details", {}).get("error_code")
                if code == "enforced_spend_limit_reached":
                    raise                        # retrying cannot help
            if n == attempts - 1:
                raise
            hinted = e.response.headers.get("retry-after")
            if hinted:
                delay = float(hinted)
            else:
                delay = min(cap, base * 2 ** n)
                delay = random.uniform(delay / 2, delay)   # full-ish jitter
            time.sleep(delay)
        except anthropic.APIConnectionError:
            if n == attempts - 1:
                raise
            time.sleep(min(cap, base * 2 ** n) * random.random())
```

The structural rules there are what to carry away: never retry a 4xx that is not 408/409/429, prefer a server-supplied `retry-after` over your own computed delay, add jitter whenever you compute your own, cap the delay, and treat the spend-cap 429 as terminal.

### Idempotency

There is no idempotency-key header on the Messages API. Nothing you send makes a retry safe at the protocol level.

The consequence is concrete: if a request times out after the server began processing, a retry is a **second billed generation**, and in a system with side effects (sending an email, writing a row, acting on a classification) it can double-apply them. You must handle this at your layer — derive your own deduplication key from the request content and record it before calling, make downstream side effects idempotent against that identifier, and log the `request-id` on every attempt so you can later determine whether a generation actually occurred.

For bulk work, the Batches API sidesteps the problem: `custom_id` gives exactly-once correlation, and resubmitting an `expired` or `errored` id is unambiguous.

### Handling Overload Specifically

A 529 `overloaded_error` is a capacity signal across all users, not a problem with your request. The correct response is backoff with jitter plus, at scale, a circuit breaker: after N consecutive 529s, stop sending for a cooling period rather than piling on.

Remember from Chapter 4 that in a streaming request, overload arrives as an `error` event inside a 200 response. That handler is separate code from your HTTP error handler, and it must exist.

## Integration-Layer Versus Model-Layer Failures

The final skill is diagnostic. Two failure classes look similar in a log and require entirely different responses.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                          Integration-layer failure                                  Model-layer failure
  ----------------------- ---------------------------------------------------------- ---------------------------------------------------------------------------------------
  HTTP status             Non-200 (or a connection fault)                            **200**

  Where it surfaces       Your HTTP client                                           Your parsing or business logic

  Primary signal          `error.type`                                               `stop_reason`, content shape

  Example                 429, 413, 401, 400 on a malformed schema                   `max_tokens` truncation, `refusal`, a hallucinated field value, an enum case mismatch

  Fix                     Retry, backoff, resize, fix credentials, fix the request   Change the prompt, raise `max_tokens`, tighten the schema, add validation

  Retrying helps?         Often                                                      Rarely — the same input usually produces the same class of output
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The diagnostic rule is simple and worth stating as a rule: **HTTP 200 with `stop_reason` anything other than `end_turn` or `tool_use` is a model-layer event, and your error handler probably ignores it.**

A worked example. A JSON extraction pipeline starts failing with parse errors, and retries succeed on the second attempt roughly half the time. That pattern *looks* like a flaky integration. It is not: the cause is `stop_reason: "max_tokens"` on long inputs, and retries “succeed” only when the second generation happens to be more concise. Adding retries raised cost and fixed nothing. The real fix is raised limits and a `stop_reason` assertion before parsing.

A second example runs the other way. An image pipeline returns 400 on 5% of requests, and the temptation is to blame moderation at the model layer. The cause is the 32 MB request limit being breached by base64-expanded images in long histories — an integration-layer sizing problem, fixed by the Files API, not by prompt changes.

The instrumentation that makes the distinction cheap is small: log `request_id`, `stop_reason`, and `usage` on every success, and `error.type` plus `request_id` on every failure. Alert on the rate of non-`end_turn` stop reasons as a metric separate from your HTTP error rate. Those two time series are the whole diagnosis.

## Practice Questions

**Q5.1** Your extraction service prompts “Reply with only JSON.” Parse failures occur on about 2% of calls — usually markdown fences or a leading sentence. You have added a regex to strip both. What is the best next step?

A. Add more regex cases and a two-attempt retry loop. B. Move the format instruction from the user message into the system prompt. C. Lower temperature to 0 to make the format deterministic. D. Use `output_config.format` with a JSON Schema so generation is constrained to valid output.

**Q5.2** You send a schema containing `{"type": "integer", "minimum": 1, "maximum": 100}` directly to `output_config.format` without the SDK helper. What happens?

A. The constraint is enforced during decoding. B. A 400 error, because numeric constraints are not in the supported schema subset. C. The constraint is ignored silently and a plain integer is produced. D. The value is clamped into range before being returned.

**Q5.3** Your constrained-output request intermittently returns text that is not valid against your schema. `stop_reason` on those responses is `refusal`. What is the correct interpretation?

A. The refusal message can override schema compliance; check `stop_reason` before parsing, and you are still billed. B. A bug — constrained decoding guarantees schema validity unconditionally. C. The schema failed to compile and was dropped. D. The response was truncated and should be retried with a higher `max_tokens`.

**Q5.4** You define 30 tools, all with `strict: true`, in one request. You get a 400 about schema complexity. Which change is most directly aligned with the documented guidance?

A. Replace `anyOf` unions with free-form strings everywhere. B. Split the schemas across four cache breakpoints. C. Mark only the critical tools `strict` and leave the rest non-strict, since non-strict tools do not count toward the limit. D. Raise the compilation timeout above 180 seconds.

**Q5.5** You want structured JSON output on a request that also has citations enabled. The request returns 400. What should you do?

A. Add the `structured-outputs-2025-11-13` beta header. B. Citations are incompatible with `output_config.format`; use a forced tool call to get structured output instead. C. Move the schema into the system prompt as text. D. Disable `additionalProperties: false` to reduce conflict.

**Q5.6** Legacy code ends `messages` with `{"role": "assistant", "content": "{"}` to force JSON. After a model upgrade it returns 400. Why, and what replaces it?

A. The opening brace must be escaped; escape it and the code works. B. Prefill now requires `tool_choice: {"type":"none"}`. C. Assistant turns must be arrays of blocks on newer models; wrap it in a text block. D. Prefilling is unsupported on newer models; use structured outputs or system prompt instructions.

**Q5.7** Your agent sends a 3840×2160 screenshot on every turn to a standard-tier model. Latency and cost are high and detail is no better than expected. What is happening?

A. The image is downscaled to roughly 1456 px wide before processing; you are paying to upload detail that is discarded. B. The model rejects images above 1568 px, so it is processing a cached fallback. C. 4K images are billed at a 3× multiplier. D. Screenshots must be PNG to avoid re-encoding cost.

**Q5.8** A document-review conversation attaches one 6 MB base64 image in the first turn. By turn six, requests fail with 413. Why?

A. The per-image size limit is 5 MB on the Claude API. B. Images expire after five turns and must be re-uploaded. C. Each turn resends the full history, so the base64 image is retransmitted every time until the 32 MB request limit is exceeded; use the Files API. D. The 413 comes from the Files API storage quota.

**Q5.9** You need to send 45 product photos in one request for comparison. Each is 3000×2000 px, well under the 8000 px per-image limit. The request returns `invalid_request_error`. Why?

A. The maximum is 20 images per request on the API. B. A request with more than 20 images requires every image to have no dimension above 2000 px. C. Only `file` sources are allowed above 20 images. D. Product photos must be sent as `document` blocks.

**Q5.10** You want to price a 180-page PDF before sending it. Which statement about its tokenization is correct?

A. Only extracted text is tokenized, at roughly 1,500–3,000 tokens per page. B. PDF pages are free below the 600-page limit. C. PDFs are billed per page at a flat document-processing rate. D. Each page is tokenized twice — extracted text plus a rendered page image — so cost is the sum of both.

**Q5.11** Your multi-tenant application lets clients pass a `file_id` in an API call that your backend forwards to Claude. A security reviewer flags this. Why?

A. Files are shared across the entire workspace, so any valid id lets one tenant read another tenant’s file; keep the user-to-file mapping server-side. B. `file_id` values expire and will 404 unpredictably. C. `file_id` cannot be used in `document` blocks, only `image` blocks. D. Forwarding a `file_id` triggers a 403 unless a beta header is present.

**Q5.12** Your retry wrapper treats all 429s identically with exponential backoff. One morning it retries continuously for nine hours without a single success. What did it fail to check?

A. The `anthropic-ratelimit-tokens-remaining` header. B. That `retry-after` was under 60 seconds. C. `error.details.error_code == "enforced_spend_limit_reached"`, which indicates a spend cap that retrying cannot clear. D. Whether the model id was still valid.

**Q5.13** A fleet of 200 workers all receives 529 at the same moment. Your retry logic uses pure exponential backoff with no jitter. What happens?

A. Nothing problematic; backoff resolves it. B. All 200 retry simultaneously at each doubling, re-overloading the service — a thundering herd. Add jitter and a circuit breaker. C. The SDK deduplicates identical concurrent retries. D. 529s are not retryable, so all requests fail permanently.

**Q5.14** A request times out client-side after the server began processing. Your code retries, and a downstream email is sent twice. What is the correct mitigation?

A. There is no API-level idempotency key; derive your own dedup key, make side effects idempotent, and log `request-id` per attempt. B. Send an `Idempotency-Key` header on the Messages API. C. Set `max_retries=0` so timeouts never retry. D. Use `metadata.user_id` as an idempotency key.

**Q5.15** Your pipeline shows intermittent JSON parse errors. HTTP status is 200 on every call, and your HTTP error rate dashboard is flat. Where should you look first?

A. The `anthropic-version` header, which may be stale. B. The prompt cache, which may be serving a stale response. C. The TLS configuration of your HTTP client. D. `stop_reason` — a value of `max_tokens` or `refusal` on a 200 response is a model-layer failure your error handler ignores.
