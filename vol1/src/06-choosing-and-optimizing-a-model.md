# Choosing and Optimizing a Model

Model selection is the one architectural decision in a Claude application that you will revisit most often, and the one that engineers most often get wrong in the same two directions: reaching for the largest model because the task feels important, or freezing a cheap model into a pipeline whose quality ceiling then becomes the product’s ceiling. Neither failure is about the model. Both are about not having measured anything.

This chapter treats model selection as an engineering problem with measurable inputs: what distinguishes the tiers, how the API identifies and versions them, how tokens are actually priced, what extended thinking costs and buys, and how to build a routing layer that sends most traffic to the cheapest model that passes your evaluations. Everything in this chapter was verified against Anthropic’s documentation in October 2026. Model lineups move faster than books do, so treat the specific numbers as a snapshot and the reasoning as durable.

## The model tiers and what actually distinguishes them

The current lineup is four models. Anthropic’s documentation describes them by tier name rather than by raw benchmark position, and the useful mental model is a speed-versus-depth axis, not a simple quality ladder.

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Model               API model string      Positioning                                                                                          Default effort   Input / output per MTok
  ------------------- --------------------- ---------------------------------------------------------------------------------------------------- ---------------- ---------------------------
  Claude Fable 5.1    `claude-fable-5-1`    Slowest; demanding reasoning and long-horizon agentic work                                           `high`           \$10 / \$50

  Claude Opus 5.5     `claude-opus-5-5`     Moderate speed; long-running agentic coding and knowledge work. The documented recommended default   `medium`         \$4 / \$20

  Claude Sonnet 5.5   `claude-sonnet-5-5`   Fast; best balance of speed and intelligence                                                         `high`           \$2 / \$10

  Claude Haiku 5.5    `claude-haiku-5-5`    Fastest; high-volume, latency-sensitive classification, extraction, routing                          `medium`         from \$0.10 / from \$0.50
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Four properties are worth internalizing because they overturn assumptions carried over from earlier generations.

**All four share the same context window and output ceiling.** Every current model offers a 1M-token context window and a 128K-token maximum output. Context size is no longer a reason to pick a bigger model. If your prompt is enormous, Haiku 5.5 will accept it; the question becomes whether Haiku can reason well enough over it, and whether you want to pay Haiku’s long-prompt rate (more on that below).

**All four think adaptively, and thinking is always on.** On this generation you do not enable reasoning. The model decides per request whether to produce a thinking block and how deep to go, steered by an effort level you set. The older `thinking: {"type": "enabled", "budget_tokens": N}` form is rejected with a 400 error on Claude 4.7 and later. Engineers migrating from a 4.5-era codebase hit this immediately.

**The reliable knowledge cutoff is June 2026** for all four. Anything after that must come from retrieval, tools, or the prompt. Anthropic distinguishes the “reliable knowledge cutoff” from the raw training-data cutoff and publishes the latter separately; for application design, the reliable figure is the one to plan against.

**Fable is positioned as an escalation target, not a default.** The documentation’s guidance is explicit and worth quoting as a decision rule rather than a sentiment: reach for Fable when your evaluations on Opus 5.5 at a higher effort level still fall short. That is a measurement-gated upgrade, not a reflex. At \$10/\$50, Fable costs two and a half times Opus 5.5 per token, and it is also the slowest model in the lineup, so an unjustified Fable deployment buys you both a cost problem and a latency problem.

The practical consequence is that the tiers differ mainly along two axes that benchmarks capture poorly: how much latency you are willing to spend per response, and how long a horizon the model needs to hold a coherent plan over. A single-shot classification of a support ticket is a Haiku task regardless of how important the ticket is. A forty-tool-call refactor across an unfamiliar repository is an Opus or Fable task regardless of how trivial each individual edit looks.

## Model strings and version pinning

Anthropic changed the identifier scheme at the 4.6 generation, and the change matters for production code.

For models from 4.6 onward, the model ID is dateless: `claude-sonnet-4-6`, `claude-opus-5`, `claude-opus-5-5`, `claude-haiku-5-5`. For models before 4.6, the ID carries a snapshot date: `claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001`.

The critical point, and the one most frequently misread, is that a dateless 4.6+ ID is **not** an alias. It is the canonical identifier for exactly one fixed snapshot. Anthropic does not update the weights or configuration behind an existing ID; a new release ships under a new ID. So `claude-opus-5-5` today and `claude-opus-5-5` in six months are the same model.

Aliases existed only for pre-4.6 models on the Claude API. There, `claude-sonnet-4-5` pointed at the most recent dated snapshot of that minor version and could therefore move under you when a new snapshot shipped. If you still have pre-4.6 strings in your codebase, the dated form is the pinned form and the bare form is not.

``` {.sourceCode .python}
import anthropic

client = anthropic.Anthropic()

# 4.6 and later: the dateless ID is already a pinned snapshot.
MODEL = "claude-opus-5-5"

response = client.messages.create(
    model=MODEL,
    max_tokens=2048,
    messages=[{"role": "user", "content": "Summarize this incident report."}],
)
```

Why pinning matters even now that dateless IDs are fixed snapshots:

1.  **Upgrades become explicit code changes.** Because a new model arrives under a new ID, moving from `claude-opus-5-5` to a successor is a diff you can review, canary, and roll back. Nothing shifts silently.
2.  **Each ID retires on its own schedule.** Pinning does not exempt you from lifecycle management; it makes the lifecycle legible.
3.  **Weights are fixed, but serving is not.** Request routing, safety classifiers, and sampling infrastructure can change under a stable ID, which can produce small behavioral drift. Anthropic’s own guidance is that if a previously stable ID starts behaving differently, suspect infrastructure and re-run your evaluations. Pinning plus a regression suite is the complete answer; pinning alone is not.

Platform spellings differ. On Amazon Bedrock IDs are prefixed `anthropic.claude-...` and dated IDs end in `-v1:0`; Opus 4.6 is the last Bedrock ID carrying the `-v1` suffix. On Google Cloud, dates attach with `@`, as in `claude-haiku-4-5@20251001`. Centralize the mapping in one configuration module rather than scattering provider-specific strings through your code.

For discovery, the Models API returns `max_input_tokens`, `max_tokens`, and a `capabilities` object per model, and exposes a `line` field. Group by `line` rather than parsing the ID string — naming conventions have changed once already.

## Context window size and the economics of filling it

A 1M-token context window is an invitation to a specific mistake: stuffing everything in because it fits. Three economic facts should discipline that.

**First, for Claude 4.6 and later other than Haiku 5.5, long context carries no premium.** A 900K-token request is billed at the same per-token rate as a 9K-token request, and caching and batch discounts apply across the whole window. There is no pricing cliff to engineer around. There is, however, a linear cost: 900K input tokens on Opus 5.5 is \$3.60 before you have generated a single output token, and you pay it again on every uncached turn.

**Second, Haiku 5.5 is the exception, and the exception is sharp.** Haiku 5.5 has tiered pricing with a 100,000-token threshold.

  Haiku 5.5 prompt size   Input    Output   5m cache write   Cache read
  ----------------------- -------- -------- ---------------- ------------
  ≤ 100K tokens           \$0.10   \$0.50   \$0.125          \$0.01
  \> 100K tokens          \$0.50   \$2.50   \$0.625          \$0.05

Three details make this trap easy to fall into. The threshold counts *all* input tokens, cache reads and cache writes included. Pricing is per request, so a request that crosses the line pays the higher rate on its entire prompt even if most of that prompt was a cache hit. And crossing the threshold is a 5x jump. A 100K-token prompt costs \$0.01 in input; a 101K-token prompt costs about \$0.05, because all 101K tokens are billed at the higher rate, not just the extra thousand. That can erase the entire reason you chose Haiku. If you run Haiku against large documents, measure your prompt size distribution and know what fraction of traffic lands above 100K.

**Third, long contexts cost latency and attention, not just money.** Time to first token scales with prompt size. And a model asked to find one relevant clause in 800K tokens of boilerplate is doing a harder task than one handed the three relevant clauses. Retrieval that narrows 800K tokens to 20K usually improves both cost and quality. The 1M window is best understood as headroom for agent runs that genuinely accumulate state, not as a substitute for retrieval.

## Pricing structure: four different token prices

Every Claude request bills tokens in categories priced differently. Reasoning about cost without this decomposition produces estimates that are wrong by an order of magnitude.

**Input tokens** are the cheapest baseline. **Output tokens** cost 5x input across the lineup — \$4 in, \$20 out on Opus 5.5; \$2 in, \$10 out on Sonnet 5.5. Thinking tokens are billed as output tokens, which is why effort level is a cost lever and not just a quality lever.

**Cache writes** cost more than plain input: 1.25x base input for the 5-minute TTL, 2x for the 1-hour TTL. **Cache reads** are dramatically cheaper, and the multiplier now varies by model: 0.1x base input generally, but 0.05x on Opus 5.5 and Sonnet 5.5, and 0.025x on Fable 5.1.

  ------------------------------------------------------------------------------------------
  Model               Input       Output      5m cache write   1h cache write   Cache read
  ------------------- ----------- ----------- ---------------- ---------------- ------------
  Fable 5.1           \$10        \$50        \$12.50          \$20             \$0.25

  Opus 5.5            \$4         \$20        \$5              \$8              \$0.20

  Sonnet 5.5          \$2         \$10        \$2.50           \$4              \$0.10

  Haiku 5.5 (≤100K)   \$0.10      \$0.50      \$0.125          \$0.20           \$0.01
  ------------------------------------------------------------------------------------------

On Opus 5.5 a cached input token costs \$0.20 per million against \$4.00 uncached — a 20x reduction. For an agent that re-sends a large system prompt and tool schema on every one of thirty turns, caching is not an optimization, it is the difference between viable and not. Caching requires a minimum prompt length, which for all four current models is 512 tokens; shorter prompts are processed uncached with no error raised. You get up to four explicit `cache_control` breakpoints per request, cache reads look back up to 20 blocks for a prior write, and the invalidation hierarchy runs tools → system → messages, so a change at one level invalidates everything after it.

**Batch tokens** are 50% off both input and output. The Message Batches API accepts up to 100,000 requests or 256 MB per batch, most batches complete within an hour (not guaranteed), and anything unfinished at 24 hours expires. Results stay downloadable for 29 days from creation. Streaming, Fast mode, and `max_tokens: 0` cache pre-warming are rejected. Batch and caching discounts stack.

The decision rule for batch is simple: if no human is waiting for the response, use it. Nightly enrichment, backfills, evaluation suite runs, document classification over an existing corpus — all of these are batch workloads being paid for at interactive rates in most codebases.

Two further modifiers to know. `inference_geo: "us"` adds 1.1x across all token categories on 4.6 and later. Fast mode on Opus 5.5 is \$8 input / \$40 output, double standard rates, and is unavailable on the Batches API. Regional and multi-region endpoints on Bedrock and Google Cloud carry a 10% premium over global endpoints.

## Extended thinking: what it costs and when it earns it

On the current generation, thinking is adaptive and always available. You do not enable it; you steer it with `output_config.effort`.

  ---------------------------------------------------------------------------------------------------------------
  Effort                              Behavior
  ----------------------------------- ---------------------------------------------------------------------------
  `max`                               Thinks most readily and deeply, with no constraint on thinking length

  `xhigh`                             More readily and deeply than `high`; extended exploration

  `high`                              Default on Sonnet 5.5 and Fable 5.1; thinks on most requests that benefit

  `medium`                            Default on Opus 5.5 and Haiku 5.5; moderate, may skip on simple queries

  `low`                               Minimizes thinking; skips it where speed dominates
  ---------------------------------------------------------------------------------------------------------------

``` {.sourceCode .python}
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=8192,
    output_config={"effort": "low"},   # note: NOT inside the thinking object
    messages=[{"role": "user", "content": "Which of these two log lines is the error?"}],
)

print(response.usage.output_tokens)
print(response.usage.output_tokens_details.thinking_tokens)
```

Several properties of effort have direct engineering consequences.

**Effort is soft guidance.** No level guarantees a thinking block. At every level the model decides per request. Code that assumes `response.content[0].type == "thinking"` will break.

**Thinking counts toward `max_tokens`.** `max_tokens` is a hard ceiling on thinking plus answer combined. A `max_tokens` value sized for responses without thinking is often too small once you raise effort, and the symptom is `stop_reason: "max_tokens"` with a truncated or missing answer. When you see that, the diagnostic question is whether those responses actually needed the reasoning: if yes, raise `max_tokens`; if the model was over-thinking a simple task, lower the effort.

**Thinking tokens bill as output tokens, and they also bill as input later.** On Opus 4.5 and all models 4.6 and above, prior turns’ thinking blocks stay in context and are billed as input on subsequent turns. Sonnet 4.5, Haiku 4.5, and earlier strip them. On a long agent run with a model that preserves thinking, reasoning from turn 3 is still being paid for at turn 30. Read `usage.output_tokens_details.thinking_tokens` to see what reasoning actually costs you; `output_tokens` remains the authoritative billing total.

**Changing effort invalidates the prompt cache,** because the resolved effort value is rendered into the prompt. Setting it explicitly to the model’s default is equivalent to omitting it and does not break the cache. Keep effort constant for the life of a cached conversation; where you need a one-off change, there is a per-message effort beta on supported models.

**Thinking decays as conversations grow.** In tool-use loops, follow-up requests that merely process a tool result often skip thinking entirely, even at `xhigh` or `max`. Do not budget as though every turn in a thirty-turn agent run will think at full depth.

**Lower effort before you try prompt steering.** Effort is a calibrated control. Instructions like “answer directly” are wording-sensitive and, on Sonnet 5.5 and Haiku 5.5, do not reliably reduce thinking.

When does thinking earn its cost? When the task has a verifiable right answer that requires multiple dependent inference steps — mathematical derivation, multi-constraint scheduling, root-cause analysis across several log sources, code that must satisfy several interacting invariants. When does it not? Extraction, classification, formatting, summarization, translation, and anything where the answer is a transformation of the input rather than a derivation from it. For those, `low` effort on a small model usually matches or beats `high` effort on a large one, at a tiny fraction of the cost.

If you maintain pre-4.6 code, the manual form still applies there: `thinking: {"type": "enabled", "budget_tokens": N}` with a minimum of 1,024 tokens, a value strictly below `max_tokens`, and a documented starting point of 1,024 for simple tasks or 16,000+ for complex ones. Budgets above 32k should go through the Batches API to avoid timeouts. Changing `budget_tokens` mid-conversation invalidates cache breakpoints for the same reason effort changes do. Migration to adaptive thinking means removing `budget_tokens`, setting `thinking: {"type": "adaptive"}`, setting an effort level, dropping the `interleaved-thinking-2025-05-14` beta header, and expecting a one-time cache miss plus a genuine behavior change: fixed budgets thought on every request, adaptive thinking decides per request.

## Latency, quality, and cost as a three-way tradeoff

The honest framing is that you can usually optimize two of the three. What makes this tractable is that the three are not controlled by one dial. You have at least four, and they interact.

  -------------------------------------------------------------------------------------------------------------------------------
  Lever                          Effect on quality                Effect on latency             Effect on cost
  ------------------------------ -------------------------------- ----------------------------- ---------------------------------
  Larger model tier              Higher ceiling                   Slower                        Higher per token

  Higher effort                  Better on multi-step reasoning   Slower, sometimes much        Higher (thinking is output)

  Prompt caching                 Neutral                          Faster TTFT on hits           Much lower on repeated prefixes

  Batch API                      Neutral                          Worse by design (up to 24h)   50% lower

  Smaller prompt via retrieval   Often higher                     Faster                        Lower
  -------------------------------------------------------------------------------------------------------------------------------

A decision matrix for common production shapes:

  -----------------------------------------------------------------------------------------------------------------------------------------
  Workload                                     Start with                 Effort               Notes
  -------------------------------------------- -------------------------- -------------------- --------------------------------------------
  Ticket/intent classification, high volume    Haiku 5.5                  `low`                Watch the 100K prompt threshold

  Structured extraction from documents         Haiku 5.5                  `low`–`medium`       Escalate on schema-validation failure

  User-facing chat with tools                  Sonnet 5.5                 `medium`             Cache system prompt and tool schemas

  Long-running agentic coding                  Opus 5.5                   `medium`–`high`      The documented default for this shape

  Hard reasoning where Opus evals fall short   Fable 5.1                  `high`+              Only after measuring Opus at higher effort

  Nightly corpus enrichment                    Haiku or Sonnet 5.5        `low`                Batch API, non-negotiable

  Evaluation suite runs                        Same model as production   Same as production   Batch API; evals must match prod config
  -----------------------------------------------------------------------------------------------------------------------------------------

Two anti-patterns to name explicitly. **Choosing a model by benchmark instead of by workload** produces Opus deployments on classification tasks where Haiku was indistinguishable at a fortieth of the price. **Choosing by price alone** produces Haiku deployments on multi-step reasoning tasks where the retry rate, the human review burden, and the downstream error cost dwarf the token savings. The resolution to both is the same: a small evaluation set drawn from real traffic, scored by whatever your application actually cares about, run across candidate model-and-effort combinations.

## Routing: let a cheap model handle most traffic

The highest-leverage cost optimization in most Claude applications is not picking a cheaper model for everything. It is recognizing that your traffic is not homogeneous and routing accordingly.

Three routing patterns, in increasing order of cost and capability.

**Escalate on validation failure.** The cheap model attempts the task; a programmatic check decides whether the answer is acceptable; failures go to the expensive model. This works beautifully when correctness is machine-checkable — JSON that must parse against a schema, code that must compile, arithmetic that must reconcile, an extracted value that must appear in the source. Requests that pass pay only the cheap price; requests that fail pay the cheap price and then the expensive one. At a 90% pass rate with Haiku primary and Opus fallback, nine requests in ten cost \$0.10 per million input tokens and one in ten costs \$0.10 + \$4.00. The blended input cost is 0.9 × \$0.10 + 0.1 × \$4.10, roughly \$0.09 + \$0.41 = \$0.50 per million, against \$4.00 for Opus everywhere.

**Escalate on self-reported uncertainty.** Ask the cheap model to classify difficulty or flag low confidence alongside its answer, and route on that. Cheaper to implement than a separate classifier but less reliable, because small models are imperfectly calibrated. Measure the false-confident rate before trusting it.

**Classify first, then route.** A dedicated cheap classification call decides which downstream path handles the request. This costs one extra round trip but gives you a clean seam for per-category prompts, per-category tools, and per-category models. It is the right pattern when categories differ in more than difficulty.

``` {.sourceCode .python}
PRIMARY = "claude-haiku-5-5"
ESCALATION = "claude-opus-5-5"

def extract_invoice(document: str, schema_validator) -> dict:
    """Try the cheap model; escalate only when the output fails validation."""
    for model, effort in ((PRIMARY, "low"), (ESCALATION, "medium")):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            output_config={"effort": effort},
            system=[{
                "type": "text",
                "text": EXTRACTION_INSTRUCTIONS,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": document}],
        )
        candidate = parse_json_blocks(response)
        if candidate is not None and schema_validator(candidate):
            record_cost(model, response.usage)
            return candidate
        record_escalation(from_model=model)
    raise ExtractionFailed("both tiers failed validation")
```

Two implementation notes that determine whether a router actually saves money. **Instrument the escalation rate as a first-class metric.** A router whose escalation rate has crept from 8% to 55% is more expensive than no router at all, because you are paying for both calls on most requests, and nothing in your dashboard will say so unless you measure it. **Cache the shared prefix on both paths.** The system prompt and tool definitions are usually identical across tiers; caches are per model, so you want a breakpoint on each path.

## Measure cost per task, not cost per token

Token prices are the input to a cost model, not the cost model. The number that matters is cost per successfully completed unit of work, and the two diverge in ways that routinely invert the ranking of options.

Four factors drive the wedge:

**Retries.** A model that fails validation 30% of the time costs 1.3x its nominal price before you count the escalation.

**Output verbosity and thinking.** Output is 5x input. A model that reasons for 2,000 tokens before a 200-token answer bills 2,200 output tokens. That is 11x the 200 tokens billed by a model that answers directly, at the same nominal rate.

**Turn count on agent tasks.** This dominates everything else. A more capable model that completes a task in 8 turns can be cheaper in absolute terms than a weaker model that takes 25 turns, because every turn resends the accumulated conversation. The expensive model’s higher per-token rate is multiplied by far fewer tokens.

**Human review.** If a cheaper model’s output requires a person to check it, the token savings are rounding error against the labor cost.

A workable instrumentation shape: log, per task, the model, effort level, the full `usage` object including `cache_read_input_tokens`, `cache_creation_input_tokens`, and `output_tokens_details.thinking_tokens`, the turn count, the terminal outcome, and whether escalation occurred. Then compute dollars per successful task per model configuration. Most teams that do this discover one of two things: a workload where a cheaper tier is indistinguishable and nobody had tried, or an agent loop where a more capable model is cheaper because it converges faster. Both findings are invisible from per-token pricing.

## Temperature and sampling parameters

This is the section most likely to surprise an engineer returning to the API after a year.

**`temperature`, `top_p`, and `top_k` are deprecated on Claude 4.7 and later.** Setting a non-default value returns a 400 error. The Python SDK from v1.0 removes the parameters entirely, so passing them raises a `TypeError` before a request is ever sent. The documented replacement is to omit them and steer behavior through prompting.

This is a real change in how you control output variability. The habits it retires:

-   Lowering temperature to make extraction deterministic. Instead, constrain the output format in the prompt, give examples, and validate the result programmatically.
-   Raising temperature for creative variety. Instead, ask for several distinct options in one response, or vary the prompt across calls.
-   Sweeping temperature as a tuning knob in evaluations. That axis no longer exists; effort level is the tuning axis now.

On pre-4.7 models these parameters still function, and one legacy interaction is worth remembering if you maintain such code: manual extended thinking constrains which sampling parameters you can combine with it, so verify against the Messages API reference rather than assuming.

The broader point: output steering has moved from sampling parameters into the prompt, the effort level, and output validation. If your codebase still treats temperature as the primary determinism lever, that code will not run on current models.

## Migration and deprecation

Anthropic’s model lifecycle has four states: **active** (supported and recommended), **legacy** (no longer updated, may be deprecated later), **deprecated** (functional but not recommended, with a named replacement and an assigned retirement date), and **retired** (requests fail).

The notice commitment is **at least 60 days** before retirement of a publicly released model, for customers with active deployments, delivered by email and posted in the documentation. Sixty days is not long enough to discover a deprecation by reading release notes; it is long enough to execute a migration you already have a process for.

As of October 2026, the deprecation state of the world:

  ----------------------------------------------------------------------------------------------
  Model                          Status                  Retirement        Replacement
  ------------------------------ ----------------------- ----------------- ---------------------
  `claude-sonnet-4-5-20250929`   Deprecated 2026-09-30   2026-11-30        `claude-sonnet-5-5`

  `claude-mythos-preview`        Deprecated 2026-06-09   To be announced   Not specified

  `claude-opus-4-1-20250805`     Retired 2026-08-05      —                 `claude-opus-4-8`

  `claude-opus-4-20250514`       Retired 2026-06-15      —                 `claude-opus-4-8`

  `claude-sonnet-4-20250514`     Retired 2026-06-15      —                 `claude-sonnet-5-5`
  ----------------------------------------------------------------------------------------------

Note the compressed window on `claude-sonnet-4-5-20250929`: deprecated at the end of September, retiring at the end of November. If that string is in your production code today, you have weeks, not quarters.

Lifecycle dates apply to the Claude API, Claude Platform on AWS, and Microsoft Foundry. **Amazon Bedrock and Google Cloud set their own schedules**, so a multi-cloud deployment has more than one calendar to track.

A migration process that works:

1.  **Inventory.** Export the CSV from the Usage page in the Claude Console, which breaks usage down by API key and model. This finds the forgotten cron job and the internal tool nobody owns, which is exactly where stale model strings live.
2.  **Centralize model strings** in configuration rather than scattering them through call sites. Migration then touches one file.
3.  **Maintain a regression evaluation suite** you can run against a candidate model in an afternoon, scored on your application’s real success criteria. Without this, every migration is a leap of faith and you will discover regressions in production.
4.  **Migrate before the deadline, not at it.** Deprecated models are documented as likely to be less reliable than active ones, so the quality cost of waiting begins before the hard cutoff.
5.  **Expect behavior changes, not just string changes.** Defaults move between releases — Opus 5.5 defaults to `medium` effort while Opus 5 defaults to `high`, so a straight string swap silently changes how much the model reasons. Re-tune effort as part of the migration and re-run your evals.
6.  **Canary and roll back.** Because a new model is a new ID, you can route a traffic percentage to it and compare on live data before committing.

The teams that find deprecations painless are the ones for whom a model change is a config change plus an eval run. The teams for whom it is a fire drill are the ones who hardcoded strings, never built evals, and discovered the retirement from a 404.

## Practice Questions

**Q6.1** Your team runs a document-extraction pipeline on Claude Haiku 5.5. It has been inexpensive for months. After onboarding a client whose contracts average 140,000 tokens, your Haiku spend per document increases by roughly 5x even though the documents are only about 40% longer than the previous average. What is the most likely cause?

A. Haiku 5.5’s context window is exceeded, so requests are being automatically retried on a larger model B. Output tokens scale with input length, so longer documents produce proportionally more expensive output C. Long prompts disable prompt caching, so you are paying full input price on every request D. The prompts now exceed Haiku 5.5’s 100,000-token pricing threshold, so each request is billed at the higher long-prompt rate across its entire prompt

**Q6.2** A service calls `claude-sonnet-4-5` (no date suffix) in production. A code reviewer argues this is unsafe and should be changed to `claude-sonnet-4-5-20250929`. Is the reviewer right, and why?

A. Yes — for pre-4.6 models the bare string is an alias that can point to a newer snapshot, so it is not pinned B. No — all Claude model IDs are pinned snapshots, so the two strings are equivalent C. Yes — but only because the bare string is slower to route, not because it is unpinned D. No — the dated form is the alias and the bare form is canonical for all generations

**Q6.3** You are migrating an agent from Claude Sonnet 4.5 to Claude Opus 5.5. The existing code sets `thinking={"type": "enabled", "budget_tokens": 12000}`. After the change, every request returns a 400 error. What is the correct fix?

A. Raise `budget_tokens` above 16,000, the minimum on Opus-class models B. Keep `budget_tokens` but also add `thinking: {"type": "adaptive"}` C. Remove `budget_tokens`, set `thinking: {"type": "adaptive"}`, and set `output_config.effort` D. Add the `interleaved-thinking-2025-05-14` beta header, which is required for thinking on 5.x models

**Q6.4** An agent task currently takes Claude Haiku 5.5 an average of 26 tool-use turns to complete, with a 35% failure rate. A colleague proposes trying Opus 5.5, and another objects that Opus costs 40x more per input token so it cannot possibly be cheaper. What is the strongest reason the objection might be wrong?

A. Opus 5.5 charges a lower rate for cache reads, which offsets the per-token difference entirely B. Opus 5.5 defaults to `medium` effort, so it produces fewer output tokens than Haiku at any effort C. Opus 5.5 has a larger context window, so it needs less retrieval D. Each turn resends the accumulated conversation, so a model that converges in far fewer turns can process far fewer total tokens and also avoid retry cost

**Q6.5** Your nightly job enriches 400,000 archived records with Claude-generated summaries. It currently runs through the standard Messages API over about six hours. Which change gives the largest cost reduction with no quality impact?

A. Lower the effort level to `low` and accept shorter summaries B. Add a 1-hour-TTL cache breakpoint on the system prompt C. Switch from Sonnet 5.5 to Haiku 5.5 and add an escalation path D. Move the job to the Message Batches API

**Q6.6** You add a routing layer: Haiku 5.5 attempts each request, and output that fails schema validation is retried on Opus 5.5. Three months later total spend is higher than before the router was introduced, when everything ran on Opus. What should you check first?

A. Whether the Opus fallback is using a higher effort level than the original implementation B. Whether the escalation rate has risen to the point where most requests are paying for both calls C. Whether the cache breakpoints on the Haiku path are below the 512-token minimum D. Whether schema validation is rejecting output that Opus would also have produced

**Q6.7** An engineer writes a cost model for a chat feature by multiplying expected tokens per conversation by the model’s input price. Actual spend comes in at roughly four times the estimate. Which omission most likely accounts for the bulk of the gap?

A. Cache write tokens are billed at 1.25x base input rather than 1x B. The 1.1x multiplier for US-only inference was not included C. Output tokens — including thinking tokens — are priced at 5x input, and were costed at the input rate D. Regional cloud endpoints carry a 10% premium over global endpoints

**Q6.8** A latency-sensitive autocomplete endpoint running Sonnet 5.5 has acceptable quality but p95 latency that users complain about. The prompt is small and the output is short. Which change is most likely to reduce latency without a quality regression?

A. Set `output_config.effort` to `low` B. Raise `max_tokens` so the model does not truncate C. Move the endpoint to the Message Batches API for the 50% discount D. Add `temperature=0` to make generation more deterministic and therefore faster

**Q6.9** Your team maintains a conversational agent on Opus 5.5 with prompt caching on a large system prompt. An engineer adds a feature that raises effort to `high` for requests classified as complex and leaves it at the default for everything else. Cache hit rates collapse. Why?

A. Effort changes invalidate message-level cache breakpoints because the resolved effort value is rendered into the prompt B. Opus 5.5 does not support caching above `medium` effort C. Higher effort produces thinking blocks that push the prompt past the cacheable maximum D. The classifier call between turns breaks the cache by inserting an extra message

**Q6.10** You are asked to justify deploying Fable 5.1 for a complex legal-analysis workload. Which justification matches Anthropic’s documented guidance for choosing Fable?

A. The workload is important and customer-facing, so the most capable model is appropriate B. The documents are large, and Fable has the largest context window in the lineup C. Evaluations on Opus 5.5 at higher effort levels still fall short of the required quality bar D. Fable’s adaptive thinking is always on, unlike the other tiers

**Q6.11** A long-running agent on Opus 5.5 shows input token counts that grow faster than the visible conversation text would suggest, even with caching in place. Which mechanism best explains the extra input tokens?

A. Thinking blocks from prior assistant turns are preserved in context on this model and billed as input B. Tool definitions are re-tokenized on every turn and are never cacheable C. Cache reads are counted twice, once as `cache_read_input_tokens` and once as `input_tokens` D. Adaptive thinking appends a summary of each prior turn to the system prompt

**Q6.12** An engineer upgrading from `claude-opus-5` to `claude-opus-5-5` changes only the model string. Quality on multi-step reasoning tasks drops measurably. What is the most likely explanation?

A. Opus 5.5 is a smaller model than Opus 5 and has a lower quality ceiling B. The default effort level differs between the two models, so the same request now reasons less C. Opus 5.5 requires the manual thinking configuration that Opus 5 did not D. The cache read multiplier changed, so cached content is now partially re-processed

**Q6.13** You need deterministic, schema-conformant JSON extraction from Claude Haiku 5.5. A junior engineer’s implementation sets `temperature=0` and fails with a `TypeError` from the SDK before any request is sent. What should the implementation do instead?

A. Downgrade the SDK to a version that still accepts sampling parameters B. Pass `temperature` inside `output_config` rather than at the top level C. Omit sampling parameters, constrain the output format through prompting and examples, and validate the result programmatically D. Set `output_config.effort` to `max` so the model reasons its way to a consistent format

**Q6.14** An internal tool has been calling a model string for eight months with no changes. One morning every request returns an error and the tool is down. The team had received no alerts. Which process failure most directly caused this outage?

A. The team did not pin a dated model string, so an alias moved under them B. The team never inventoried model usage across API keys, so a deprecation notice for a model nobody owned went unnoticed through the 60-day window C. The team’s cache breakpoints expired after the 5-minute TTL D. The team used a global endpoint instead of a regional one, which has a different retirement schedule

**Q6.15** Your application has three distinct request categories: short factual lookups, structured extraction from mid-size documents, and open-ended multi-step analysis. All three currently go to Opus 5.5 at default effort. Which restructuring is most consistent with the cost and quality guidance in this chapter?

A. Move everything to Haiku 5.5 at `low` effort and add an Opus escalation path for validation failures B. Classify the request first, then route lookups and extraction to Haiku 5.5 at low effort, keep analysis on Opus 5.5, and instrument cost per successful task per category C. Keep Opus 5.5 for all three but lower effort to `low` across the board to cut output token spend D. Move all three to the Message Batches API, since the 50% discount applies regardless of category
