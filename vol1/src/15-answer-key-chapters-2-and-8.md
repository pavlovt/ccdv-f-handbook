# Answer Key: Chapters 2 and 8

## Chapter 2

**Q2.1 — B.** The Messages API keeps no conversation state, so every call must carry the prior turns. The model never saw the earlier answer, so “that” has no referent. Option D is tempting, but re-sending the system prompt alone supplies no history, and option A fails because two short turns fit trivially.

**Q2.2 — C.** Newer model families use a tokenizer that can produce roughly 30% more tokens for the same text, which raises cost and eats context with no prompt change. Option D is tempting because output length affects cost, but it would not explain prompts that previously fit now failing on input size. Counts should be re-measured per target model.

**Q2.3 — A.** Thinking tokens count inside `max_tokens`, so a small cap can be spent on reasoning, leaving little or nothing for the answer. Raise the cap or lower effort. Option D is wrong because streaming changes delivery, not token accounting, and option B fails because temperature does not control how many tokens are generated.

**Q2.4 — D.** Generation is not guaranteed identical across runs, so equality assertions on free-form text are brittle. Property checks plus multiple trials measure what matters. Option B is tempting but a longer system prompt reduces variance only partly and never guarantees identical strings; retrying until green (A) hides real regressions.

**Q2.5 — A.** Input plus the requested output exceeds the window, so on current models the request is accepted but generation is cut when the window fills, reported as `model_context_window_exceeded`. Option B is tempting, but rate limiting produces 429 errors, not partial completions with this stop reason.

**Q2.6 — C.** The system prompt carries standing operator policy and is the right place for durable rules, whereas a rule in an early user turn competes with later user pressure. Option A sounds robust but repetition plus temperature zero does not make a user-level rule authoritative. Truly sensitive information should also be protected in code, since system prompts are not a security boundary.

**Q2.7 — A.** The delay is time to first token on a long input; streaming shows output as it is produced, improving perceived latency while total generation time stays acceptable. Option B changes only the output cap, and option D moves content without reducing processing time.

**Q2.8 — D.** For simple high-volume classification, the smaller, faster, cheaper tier is the standard first test, validated on a labeled sample and optionally paired with routing for hard cases. Option A is tempting but adds latency and cost with no evidence of need, and REST versus SDK (C) does not materially change model cost or speed.

**Q2.9 — C.** The API is plain HTTPS, so any runtime can call it with the key, the `anthropic-version` header, and a JSON content type, handling retries and timeouts itself. Option D is tempting but the version header is required on raw calls; SDKs normally set it for you.

**Q2.10 — B.** claude.ai wraps the same models in its own system prompt, tools, and memory features, none of which exist in a raw API call unless you build them. Option A is tempting but the surfaces expose the same model families, and option D invents a temperature restriction.

**Q2.11 — A.** The token counting endpoint accepts system, messages, and tools and returns an input token count without generating output; it is free and an estimate. Option C works in a crude way but actually generates a response and incurs cost, while character-ratio heuristics (B, D) are unreliable for images, code, and tool schemas.

**Q2.12 — D.** When returning tool results during a thinking turn, the thinking block must be passed back complete and unmodified, with its signature; altering it causes an API error. Option A is tempting but thinking and tool use are designed to work together, including interleaved thinking on supported models.

**Q2.13 — C.** Tokens per word varies by language and script, so higher counts for Thai and Hindi are expected, not a defect. Measure budgets per language with the counting endpoint. Option B overlooks translation costs and quality tradeoffs, and caching (D) reduces cost of repeated prefixes but does not erase token-count differences.

**Q2.14 — B.** The first token arrives at 4 seconds, so roughly 36 seconds are spent generating 3,500 output tokens; generation time scales with output length. Shorten output or use a faster tier. Option A is tempting because the prompt is long, but caching mainly shortens the 4-second input phase, and streaming (D) does not reduce total generation time.

**Q2.15 — A.** The full history is replayed each turn, so it eventually exceeds the window and the input is rejected with “prompt is too long”. You must manage state by trimming, summarizing, clearing stale tool results, or using compaction or context editing. Option B is wrong because `max_tokens` governs output, and option D mistakes a deterministic size error for a transient one.

## Chapter 8

**Q8.1 — A.** Variation in length, structure, and framing signals that the prompt never defined them, so the model fills gaps differently each run. Specify the audience, format, and length. Option B is tempting, but even at low temperature an underspecified prompt yields an arbitrary, if more stable, choice that may still be wrong.

**Q8.2 — A.** For long multi-document inputs, documents belong at the top with the query at the end, and asking for relevant quotes first helps the model locate content in the middle. The documentation reports up to 30% quality gains from query-last placement in its tests. Option D is tempting but moving the data into the system prompt does not fix ordering and mixes untrusted data with standing instructions.

**Q8.3 — A.** Fencing untrusted text in tags and stating that it is data gives the model clear boundaries and is the standard first mitigation, alongside code-level limits on what can be exposed. Option C relies on user behavior, and option B has no effect on instruction hijacking. Tagging reduces rather than eliminates the risk.

**Q8.4 — D.** Few-shot examples that are all one class and one style teach the model that class as the default. Use diverse, balanced, correct examples with edge cases. Option B is tempting, but thinking cannot undo a skewed specification supplied by the examples.

**Q8.5 — B.** Starting with the Claude 4.6 generation, prefilling the final assistant turn is unsupported and returns a 400 error. Use direct instructions, structured outputs, or a tool schema, plus validation. Option D is tempting because 400s are sometimes about limits, but rate limiting returns 429, and the failure began exactly with the model change.

**Q8.6 — C.** Current guidance prefers adaptive thinking tuned with effort and general instructions over prescribed step lists, and `max_tokens` must cover thinking plus the answer. Option D is wrong because manual `budget_tokens` is deprecated and returns a 400 error on recent models.

**Q8.7 — B.** The problem is context selection: dumping an entire library dilutes attention and inflates cost, and recall degrades as context grows. Retrieve relevant sections, label them, and put them before the question. Option A is tempting but larger windows and models do not remove the dilution effect.

**Q8.8 — C.** Fabricated details come from missing grounding instructions. Constrain answers to the sources, require quotes, and provide a legitimate “not found” path. Option D is tempting but a more confident persona encourages invention rather than restraint.

**Q8.9 — A.** Caching matches on an identical prefix. A timestamp and username at the very start change on every request, so nothing after them can be a cache hit. Put the static policy first and variable values after it. Option D is tempting but the minimum cacheable length for current models is 512 to 4,096 tokens depending on model, and 3,000 tokens of static text is not the issue.

**Q8.10 — D.** The prompt is clear and the facts are verified present, and a stronger tier succeeds on the same inputs, which points to model capability on this task. Move up a tier or route hard cases. Option A is tempting, but if the prompt were the fault, a stronger model would not be the thing that fixes it so cleanly.

**Q8.11 — C.** The manual test works because the fact is in the window, and production logs show it is missing there, so retrieval or assembly is the fault. No prompt or model change recovers information that was never provided. Option B is the tempting reflex, but it is an expensive fix to the wrong layer.

**Q8.12 — B.** Versioned prompts, per-request logging of prompt and model versions, regression evals as a merge gate, and gradual rollout together make the regression visible, attributable, and reversible. Option D is tempting but temperature does not provide traceability or prevent a wording change from altering behavior.

**Q8.13 — C.** Positive instructions (“write flowing paragraphs”) give a clear target, and a prompt written in prose nudges the output toward prose, while heavy markup in the prompt nudges toward markup. Option A is tempting, but shouting a negative prohibition does not give the model something to aim at.

**Q8.14 — B.** Narrow examples make the surface content the signal, so the model copies it. Add variety and state that examples show style and structure only. Option A is tempting, but a single example is even more likely to be copied, and temperature (C) does not address the cause.

**Q8.15 — D.** The prompt contains conflicting and redundant rules, and a larger model or more reasoning cannot know which of two contradictory instructions you prefer. Audit, deduplicate, rank priorities, and verify each change with evals. Option B is the tempting shortcut but it papers over a specification defect.
