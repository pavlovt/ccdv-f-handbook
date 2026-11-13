# How Claude Works, at the Level That Affects Your Code

You do not need to understand transformer internals to build on Claude. You do need an accurate mental model of the handful of mechanics that leak into your code: how text becomes tokens, what the context window is a budget of, why outputs vary, why the API remembers nothing, and where the time goes. Most production bugs involving “weird model behavior” trace back to one of these, not to the model being unpredictable in some mystical way. This chapter builds that model, and later chapters assume it.

## Tokens and tokenization

Claude does not read characters or words. Text is split by a tokenizer into tokens, which are chunks drawn from a fixed vocabulary learned from data. Common words are often a single token; rare words, identifiers, and unusual strings split into several pieces. Whitespace, punctuation, and capitalization all influence the split.

Consequences you will actually hit:

-   **Counts are not proportional to characters or words.** English prose averages somewhere around three to four characters per token, but that is a rule of thumb, not a contract. Treat it as a rough budget estimate only.
-   **Content type matters.** Source code, JSON with long keys, base64 blobs, UUIDs, and minified text tokenize poorly (few characters per token, so many tokens for their length). Non-English languages and non-Latin scripts frequently cost more tokens per word than English.
-   **Tokenizers change between model generations.** Anthropic’s documentation states that newer model families use a newer tokenizer, and the same text can yield roughly 30% more tokens than on earlier models, depending on content. A model upgrade can therefore raise cost and consume context faster with no change to your prompt. Never reuse token counts measured against one model to plan for another.
-   **Models are weak at character-level tasks.** Counting letters, reversing strings, or exact-length constraints (“exactly 140 characters”) are unreliable because the model operates on tokens, not letters. Verify such constraints in code.

To measure instead of guess, use the token counting endpoint (`messages.count_tokens` in the SDKs). It accepts the same shape as a message request (model, system, messages, tools) and returns the input token count. It is free, subject to its own requests-per-minute limit independent of message creation, and the result is an estimate that may differ slightly from the billed count. It does not support server tools (such as web search or code execution), the MCP connector, or images and documents supplied by URL or file reference rather than base64. For those requests, read the `usage` object on the real response.

  -----------------------------------------------------------------------------------------------------------------------
  Question                              Wrong approach                Right approach
  ------------------------------------- ----------------------------- ---------------------------------------------------
  Will this prompt fit?                 `len(text) / 4`               `count_tokens` against the target model

  What will this request cost?          Word count times a constant   Token counts from `usage` on real responses

  Did the upgrade change my costs?      Assume equal                  Re-count a representative sample on the new model

  Is the output exactly N characters?   Ask the model nicely          Validate and retry in code
  -----------------------------------------------------------------------------------------------------------------------

## The context window is one shared budget

The context window is the maximum number of tokens the model can handle in a single request, and it is shared. Everything counts against it:

-   the system prompt,
-   every message in the conversation, including prior assistant turns, tool calls, and tool results,
-   tool definitions,
-   images and PDF pages (converted to tokens),
-   the output Claude generates, including any thinking.

Current models in the documentation have windows up to 1M tokens, with large maximum outputs (128K on the current flagship tiers); some older models have 200K. Check the models overview for the model you deploy, because these numbers differ per model and change over time.

A bigger window is not a license to fill it. The documentation explicitly notes that accuracy and recall degrade as the amount of context grows (often called context rot), so more tokens is not automatically better. Chapter 8 covers deciding what belongs in the window at all.

### Input, output, and thinking

Think of the window as `input + output <= window`, where “output” includes thinking tokens. Three rules follow:

1.  `max_tokens` is a cap on output, and thinking tokens count inside it. If you enable thinking and set `max_tokens` sized for a short answer, the thinking can consume the allowance and leave nothing, or too little, for the visible answer. The response then ends with `stop_reason: "max_tokens"`.
2.  Thinking tokens are billed as output tokens even if you only see a summary or nothing at all. Hiding thinking from the response changes visibility, not cost.
3.  Whether previous turns’ thinking stays in the window depends on the model. Per the documentation, newer models keep prior thinking blocks: the old blocks take up space in the window and are billed as input on every later turn. Older models strip them automatically. A separate rule covers tool use: when you return tool results in the middle of a turn that used thinking, you must pass the thinking block back unmodified, including its signature, or the API returns an error.

### What happens when you exceed it

Two different situations, two different behaviors:

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Situation                                                         Behavior (Claude 4.5 and newer)
  ----------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------
  The input alone is larger than the window                         The request is rejected with a 400 `invalid_request_error` (“prompt is too long”).

  Input fits, but input plus `max_tokens` would exceed the window   The request is accepted. Generation stops at the limit and the response carries `stop_reason: "model_context_window_exceeded"`.

  Output reaches `max_tokens` before finishing                      `stop_reason: "max_tokens"`; the answer is cut mid-thought.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Older models returned a validation error for the middle case rather than truncating. Both truncation outcomes mean you received a partial answer. Production code must check `stop_reason` on every response and treat anything other than `end_turn` (and `tool_use`/`stop_sequence` where expected) as a condition to handle: continue, retry with a larger budget, or fail loudly. Silently passing a truncated JSON document downstream is a classic production incident.

For long-running conversations, the platform offers server-side compaction (beta on supported models) and context editing (clearing old tool results or thinking blocks). The simpler, universal tools are still yours: trim, summarize, or retrieve instead of replaying everything.

## Non-determinism and temperature

Claude generates text one token at a time. At each step the model produces a probability distribution over the vocabulary, and a token is selected from it. **Temperature** rescales that distribution before selection: lower values concentrate probability on the top candidates, higher values flatten the distribution so less likely tokens are chosen more often. Temperature near zero is “mostly greedy”, not a guarantee of identical output.

Why identical requests can still differ, even at low temperature:

-   Selection among near-ties can still vary, and tiny numerical differences in how computation is batched and distributed across hardware can flip a near-tie. Small early differences compound, because every later token is conditioned on earlier ones.
-   Infrastructure details (model updates behind an alias, different serving hardware) change over time.
-   Thinking adds a long stochastic reasoning path before the answer.

One important version note, and a likely exam trap. On Claude 4.7 and later, `temperature`, `top_p`, and `top_k` are deprecated: passing a non-default value returns a 400, and version 1.0 of the Python SDK removes the parameters altogether, so passing one raises a `TypeError` before a request is ever sent. Reasoning depth is steered instead through `output_config.effort`, with levels `low`, `medium`, `high`, `xhigh`, and `max` — note that effort lives at `output_config.effort`, not inside a `thinking` object. Defaults differ by model: `medium` on Opus 5.5 and Haiku 5.5, `high` on the others.

Be careful how you carry this into the exam. CCDV-F Exam Guide v1.0 dates to July 2026, so exam questions may still treat `temperature` as a live parameter and may still expect `thinking` with an explicit `budget_tokens`. Learn both: know what the parameters *mean*, because that is what a conceptual question tests, and know that they are deprecated on current models, because that is what production code requires. The underlying principle survives every version change: temperature governs the randomness of token selection, not correctness or reasoning quality, and reaching for it to fix an underspecified prompt is the wrong instinct.

### Implications for testing

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Do                                                                                                        Don’t
  --------------------------------------------------------------------------------------------------------- -----------------------------------------------------------
  Assert on properties: valid JSON, schema conformance, required fields present, forbidden strings absent   Assert exact string equality on free-form output

  Run each eval case multiple times and track a pass rate                                                   Treat one passing run as proof

  Use a rubric or model-based grader for subjective quality, calibrated against human labels                Grade quality by diffing against a golden answer

  Pin a specific model version for regression tests and re-run evals before moving to a new one             Point tests at a floating alias and be surprised by drift

  Mock the API in unit tests of your own code                                                               Make unit tests depend on live model output
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

Layer your tests: deterministic unit tests for everything around the model (parsing, retries, routing), plus a statistical eval suite for the model-dependent behavior.

## The request/response cycle and statelessness

The Messages API is stateless. Each call is independent; the server keeps no conversation. If you want the model to know what was said earlier, you send it again, every time. A conversation is an array you maintain:

``` {.sourceCode .python}
history = []

def ask(client, user_text):
    history.append({"role": "user", "content": user_text})
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=history,          # the whole conversation, every call
    )
    if resp.stop_reason != "end_turn":
        history.pop()              # drop the unanswered turn so history stays valid
        raise RuntimeError(f"unexpected stop: {resp.stop_reason}")
    history.append({"role": "assistant", "content": resp.content})
    return resp
```

Implications:

-   **Cost and latency grow with conversation length.** Turn 30 re-sends turns 1 through 29 as input. Prompt caching (cache reads priced at a small fraction of base input, with a default five-minute lifetime refreshed on use) and trimming strategies exist because of this.
-   **Caching is prefix-based.** The prefix order is tools, then system, then messages. A change anywhere invalidates the cache from that point on: a changed tool definition invalidates everything, a changed system prompt invalidates the system prompt and the messages, and a changed message invalidates only the messages from there onward. Put stable content first and volatile content (timestamps, per-user data) last, or the cache never hits. Each model has a minimum cacheable prefix length (between 512 and 4,096 tokens depending on the model); a shorter prompt is simply processed uncached, with no error.
-   **You own the state.** Storage, truncation, summarization, and per-user isolation of history are your responsibilities. Mixing two users’ histories in one array is a data leak you created, not a model behavior.
-   **“The model forgot” is almost always a missing message.** Before blaming the model, log the exact payload you sent.
-   Messages alternate between `user` and `assistant` roles, and tool results travel back as user-role content blocks. The `usage` field in each response reports input, output, and cache token counts, which is your ground truth for metering.

## System prompt versus user message

Position in the array is the smallest part of the difference. The system prompt is a separate parameter that the model is trained to treat as the operator’s standing instructions: who it is, what it should and should not do, how to format output, and what the deployment context is. User messages are the turn-by-turn requests.

Practical effects:

-   **Durability.** System-level instructions are weighted as governing the whole conversation. A rule stated once in turn 1 of the user messages competes with later user turns and tends to erode; the same rule in the system prompt is a standing condition.
-   **Trust boundary.** Operators write the system prompt; end users write user messages. Place policy, persona, and constraints in the system prompt and untrusted input in user content. This does not make prompt injection impossible, but it gives the model the right framing for whose instructions carry authority.
-   **Cache stability.** The system prompt is near the front of the cached prefix, so a static system prompt caches well while per-request variable data placed there ruins hit rates.
-   **Not a security control.** Anything in the system prompt can potentially be elicited by a determined user. Never put secrets there, and enforce authorization in your code.

  ---------------------------------------------------------------------------------------------
  Put in system prompt                Put in user message
  ----------------------------------- ---------------------------------------------------------
  Role, tone, output conventions      The specific task or question for this turn

  Policies and hard constraints       Documents and data to process this turn

  Tool-usage guidance                 Per-request variables and examples of the current input

  Stable domain background            Anything the end user supplied
  ---------------------------------------------------------------------------------------------

## Model tiers, conceptually

Claude models come in tiers that trade capability against speed and price. The current family in the documentation spans a most capable tier for demanding reasoning and long-horizon agentic work, a general-purpose tier recommended as the default for most workloads, a balanced tier emphasizing speed and intelligence, and a small tier for high-volume, latency-sensitive tasks. Larger tiers cost more per token and respond more slowly; smaller tiers are cheaper and faster but have less headroom on hard reasoning, subtle instructions, and long multi-step work. Model names, IDs, and prices change often, so do not memorize them; know the shape of the tradeoff.

How to choose:

1.  Start with the default tier and build an eval set.
2.  Try the smaller tier on the same evals. If it meets your quality bar, the saving is large at volume.
3.  Move up only for cases the evals show failing, or route: send easy requests (classification, extraction, routing) to the small tier and hard ones to the larger.
4.  Treat model choice as one of three diagnostic suspects, along with prompt and context, covered in Chapter 8.

Also remember that thinking is a second dial on the same model. On current models, thinking is adaptive: the model decides how much to reason, steered by an `effort` setting (levels from low up to max). Lower effort cuts latency and cost on simple work; higher effort buys quality on hard problems. Changing the effort level between requests invalidates the prompt cache for the messages portion, so hold it constant within a conversation.

## SDK versus REST

Everything is an HTTPS call to the Messages endpoint. REST means you build that call yourself with the required headers (`x-api-key`, `anthropic-version`, `content-type: application/json`). The official SDKs (Python, TypeScript, Java, Go, C\#, Ruby, PHP) wrap it.

  -------------------------------------------------------------------------------------------------------------------------------------------
  Concern                                   SDK                                                           Raw REST
  ----------------------------------------- ------------------------------------------------------------- -----------------------------------
  Auth and version headers                  Set for you                                                   You set them

  Retries and backoff on transient errors   Built in                                                      You write it

  Streaming                                 Helpers that accumulate events and a final-message accessor   You parse server-sent events

  Types and request validation              Typed request and response objects                            Hand-rolled

  Long requests with large `max_tokens`     SDK enforces streaming to avoid HTTP timeouts                 You must manage timeouts yourself

  Footprint and control                     Dependency; tracks API changes via upgrades                   Zero dependencies, full control
  -------------------------------------------------------------------------------------------------------------------------------------------

Use the SDK by default. Choose REST when no SDK exists for your language or runtime, when a dependency is not acceptable (small edge runtimes, locked-down environments), or when you need to prototype with curl. Either way the same rules apply: stateless calls, the same parameters, the same errors. Handle 429 (rate limited) and overloaded/5xx errors with exponential backoff and jitter; the SDKs do some of this for you, raw clients do not. Never ship an API key to a browser or mobile client; call Claude from a server you control.

## Three surfaces, same models

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Surface           What it is                                                                                          Who configures behavior                                                               Typical use
  ----------------- --------------------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------- --------------------------------------
  Claude API        Programmatic access to models; you build the application                                            You: system prompt, tools, parameters, state, caching                                 Products, pipelines, agents you ship

  claude.ai         Anthropic’s consumer and team chat application                                                      Anthropic’s product layer plus user settings, projects, memory features               Interactive work by people

  Claude Code       Anthropic’s agentic coding tool built on the models, which reads and edits code and runs commands   Its own system prompt and tool harness, plus project files and settings you provide   Software engineering workflows
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The models are shared, but behavior is not, because each surface wraps the model in its own system prompt, tools, memory, and defaults. Therefore a prompt that works in claude.ai may behave differently through the API, where there is no hidden product system prompt and no memory unless you build it. Do not prototype final prompts in a chat UI and assume parity; validate against the API with your own harness. Conversely, features that belong to a product surface (chat history, project knowledge, uploaded-file handling) do not exist in the API unless you recreate them.

## Latency anatomy

A request’s latency has two parts you can reason about separately:

-   **Time to first token (TTFT):** the delay before any output arrives. It covers network, queueing, and processing the entire input prompt (and any thinking before the visible answer begins). Long inputs and heavy thinking raise TTFT. Caching a long shared prefix reduces the processing cost for repeat requests.
-   **Generation time:** after the first token, output arrives at a roughly steady rate, so total time grows approximately linearly with the number of output tokens. A 2,000-token answer takes much longer than a 100-token one regardless of how short the prompt was.

Total latency is therefore approximately `TTFT + (output tokens / generation rate)`.

  -----------------------------------------------------------------------------------------------------------------------------------------------------
  Symptom                                           Likely lever
  ------------------------------------------------- ---------------------------------------------------------------------------------------------------
  Blank screen for many seconds on long documents   Streaming for perceived latency; shorter or cached prompts; lower effort

  Fast start, but takes a minute to finish          Cut output length (ask for concise output, structured fields instead of prose), use a faster tier

  Slow on every simple query                        Lower thinking effort or a smaller tier

  Timeouts on very long outputs                     Stream; do not rely on one long blocking HTTP response
  -----------------------------------------------------------------------------------------------------------------------------------------------------

Streaming does not shorten total generation time. It sends tokens as they are produced (as server-sent events: message start, content block start/delta/stop, message delta, message stop), so users see progress immediately and your code can act on partial output. It improves perceived latency and is required in practice for large outputs. Accumulate tool-use JSON deltas and parse only when the block closes. A stream can also fail midway with an error event such as overloaded; design for resuming from the last complete text block, since partial tool-use or thinking blocks cannot be recovered.

## Chapter checklist

-   Measure tokens with the counting endpoint against the exact target model; expect differences across model generations.
-   Budget input plus output plus thinking inside one window; always check `stop_reason`.
-   Test model-dependent behavior statistically, not by equality.
-   Send full state on every call; manage history, caching, and isolation yourself.
-   Put standing rules in the system prompt and untrusted data in user content.
-   Match the tier and effort to the task; verify with evals.
-   Default to the SDK; use REST when you must.
-   Do not assume parity between claude.ai, Claude Code, and the API.
-   Stream for responsiveness; reduce output length to reduce total latency.

## Practice Questions

**Q2.1** A support chatbot built on the Messages API answers the first question correctly, but on the second turn the user asks “can you shorten that?” and Claude replies that it does not know what “that” refers to. The code sends only the newest user message on each call. What is the most likely cause?

A. The model’s context window is too small to hold two turns. B. The API is stateless, and the earlier turns were never included in the second request. C. Temperature is too high, causing Claude to ignore earlier context. D. The system prompt must be re-sent after every turn for the model to retain memory.

**Q2.2** A team estimates its monthly bill by multiplying word counts by a fixed tokens-per-word ratio measured last year. After migrating to a newer model family with no prompt changes, spend rises about 30% and some long prompts that used to fit now fail. What is the most likely explanation?

A. The new model charges a higher per-token price only for long prompts. B. Prompt caching was disabled automatically by the migration. C. The newer model family uses a different tokenizer that produces more tokens for the same text. D. The new model always generates longer answers regardless of instructions.

**Q2.3** A developer enables thinking, sets `max_tokens` to 1,024 for a hard analytical question, and receives a response that ends abruptly with `stop_reason: "max_tokens"` and little or no visible answer. What is the best fix?

A. Increase `max_tokens` to cover thinking plus the answer, or lower the effort level for this task. B. Lower the temperature so the model generates fewer tokens. C. Move the question from the user message into the system prompt. D. Switch to streaming, which does not count thinking tokens against `max_tokens`.

**Q2.4** An engineering team writes CI tests that call Claude with a fixed prompt and assert that the output string equals a stored golden answer. The tests pass locally but fail intermittently in CI even though nothing in the prompt changed. What is the best remediation?

A. Retry each test until it passes. B. Add a longer system prompt to make the model more deterministic. C. Run the tests only on weekdays when the service is less loaded. D. Replace equality checks with property checks (schema validity, required fields, forbidden content) and run multiple trials to track a pass rate.

**Q2.5** An application sends a 180,000-token prompt to a model with a 200,000-token window and sets `max_tokens` to 40,000. On a current model the request is accepted, but responses frequently end early with `stop_reason: "model_context_window_exceeded"`. What is happening?

A. Input plus the requested output exceeds the window, so generation is cut off when the window fills. B. The API rate-limited the request and returned a partial response. C. The prompt cache expired in the middle of generation. D. The model decided the task was complete and stopped.

**Q2.6** A developer places “Never reveal internal pricing tiers” in the first user message of each conversation. In long sessions the model occasionally discusses the tiers after the user pushes back several times. Which change is most appropriate?

A. Repeat the rule in every user message and set temperature to zero. B. Move the rule to a tool definition. C. Put the rule in the system prompt as a standing policy, and enforce confidentiality in application code for anything truly sensitive. D. Ask the model to confirm the rule each turn.

**Q2.7** A chat UI summarizing 80-page reports shows users a blank pane for roughly twelve seconds, after which the full summary appears at once. Total generation is acceptable. What change most improves the user experience without changing the summary?

A. Enable streaming so tokens render as they arrive. B. Increase `max_tokens`. C. Raise the temperature to speed up sampling. D. Move the report text from the user message to the system prompt.

**Q2.8** A pipeline classifies two million short support tickets per day into one of eight categories. It currently uses the most capable model tier and meets accuracy targets, but cost and latency are high. What is the best next step?

A. Keep the tier but increase thinking effort for consistency. B. Lengthen the prompt with more instructions. C. Switch to raw REST calls to reduce overhead. D. Evaluate a smaller, faster tier on a labeled sample, and adopt it (possibly with routing for hard cases) if it meets the quality bar.

**Q2.9** A team deploys on a runtime for which no official SDK exists and cannot add native dependencies. Which statement about their options is correct?

A. They cannot use Claude from that runtime. B. They must wait for an SDK, because REST access is only for testing. C. They can call the Messages endpoint over HTTPS directly, supplying the API key, version header, and content type, and implementing retries and timeouts themselves. D. They can call the endpoint without a version header since the default applies.

**Q2.10** A developer perfects a prompt in claude.ai, where it produces excellent, well-formatted results, then ports it unchanged to an API integration and sees different tone, formatting, and no recall of prior preferences. What best explains the difference?

A. The API serves a different, weaker set of models. B. claude.ai wraps the model in its own system prompt, tools, and memory features that the raw API does not provide. C. The API ignores user messages unless a system prompt is present. D. claude.ai applies a lower temperature than the API permits.

**Q2.11** Before launching a feature that sends a long system prompt, tool definitions, and several base64 images, an engineer wants to confirm the request fits the context window and estimate cost without actually generating output. What should they use?

A. The token counting endpoint with the target model and the same system, messages, and tools, noting its result is an estimate. B. A character count divided by four. C. Send the request with `max_tokens` of 1 and ignore the response. D. Count words in the prompt and multiply by the English average.

**Q2.12** An agent loop using thinking calls tools. On the request that returns a tool result, the API responds with a 400 error mentioning the thinking block. The code rebuilt the assistant message but trimmed the thinking text to save tokens. What is wrong?

A. Thinking blocks cannot be used together with tool calls. B. The assistant message must be removed entirely before returning tool results. C. The tool result must be placed in the system prompt. D. Thinking blocks must be returned complete and unmodified, including their signature, when passing back tool results.

**Q2.13** A multilingual product shows that Thai and Hindi requests use far more input tokens than equivalent English requests and hit context limits sooner. The team asks whether this indicates a bug. What is the best answer?

A. Yes; the tokenizer is misconfigured for those requests. B. Yes; non-English text should be translated to English before every call, with no tradeoffs. C. No; tokens per word varies by language and script, so budgets should be measured per language with the counting endpoint. D. No; but the difference disappears once caching is enabled.

**Q2.14** A document-analysis call takes 40 seconds. The prompt is 60,000 tokens, the answer is 3,500 tokens, and the first token arrives after 4 seconds. The team wants to halve total time. Which lever is most effective?

A. Cache the 60,000-token prompt, since input processing dominates the total. B. Reduce output length (more concise, structured output) or use a faster tier, since generation time dominates. C. Increase the temperature to speed up generation. D. Enable streaming, which reduces total generation time by half.

**Q2.15** A chat product works well for the first dozen turns, but around turn 60 requests begin failing with a 400 “prompt is too long” error. The code replays the full history each time. What is the most appropriate architectural response?

A. Implement history management: summarize or trim older turns, drop stale tool results, or use platform compaction or context editing where available. B. Increase `max_tokens` so the longer conversation fits. C. Remove the system prompt to free space. D. Retry the same request after a delay, since the error is transient.
