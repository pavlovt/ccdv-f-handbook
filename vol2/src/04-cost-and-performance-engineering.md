# Cost and Performance Engineering

Volume I gave you the vocabulary: tiers, caching, batching, the effort dial, escalation routing. This chapter is the engineering.

Almost every costly mistake in production model selection is not a mistake about *which model is better*. It is a mistake about arithmetic. Teams migrate to a cheaper tier and watch spend go up. They add prompt caching to a Haiku workload and the bill quintuples. They build a cascade more expensive than the model it was meant to avoid. They buy Fast mode for a workload where it cannot possibly help. Each is a failure to write down a formula and substitute numbers into it.

So we write down the formula, substitute numbers, and keep doing that until the decisions fall out.

## 3.1 The price surface, as of a date

Every number in this chapter derives from one table. State it once, date it, and reason symbolically everywhere else — because the table will change and your mental model should not.

**Table 3.1 — Published per-MTok rates, verified 2026-10-17.** Rates in USD per million tokens.

  --------------------------------------------------------------------------------------------------------------------------
  Model                ID                    Input   Output   Write 5m   Write 1h   Read    Read multiple   Default effort
  -------------------- --------------------- ------- -------- ---------- ---------- ------- --------------- ----------------
  Fable 5.1            `claude-fable-5-1`    10.00   50.00    12.50      20.00      0.25    0.025x          high

  Opus 5.5             `claude-opus-5-5`     4.00    20.00    5.00       8.00       0.20    0.05x           medium

  Sonnet 5.5           `claude-sonnet-5-5`   2.00    10.00    2.50       4.00       0.10    0.05x           high

  Haiku 5.5 (≤100K)    `claude-haiku-5-5`    0.10    0.50     0.125      0.20       0.01    0.1x            medium

  Haiku 5.5 (\>100K)   `claude-haiku-5-5`    0.50    2.50     0.625      1.00       0.05    0.1x            medium
  --------------------------------------------------------------------------------------------------------------------------

All four carry a 1M-token context window, a 128K maximum output, and a June 2026 reliable knowledge cutoff. Opus 5.5 is the documented recommended default. A Mythos family appears in the pricing and effort tables at Fable-equivalent rates, but it is absent from the models overview and its intended positioning is not documented; this chapter makes no claims about it.

Three structural facts about this surface matter more than the individual numbers:

1.  **Cache write multipliers are uniform.** 1.25x base input for a 5-minute entry, 2x for a one-hour entry, on every model. You can reason about write cost without a lookup.
2.  **Cache read multipliers are not uniform.** The general rule is 0.1x, but Opus 5.5 and Sonnet 5.5 read at 0.05x and Fable 5.1 reads at 0.025x. The *more expensive* models have the *deeper* read discount. This inverts the usual intuition about where caching pays and we will exploit it in §3.4.
3.  **Long context is free except on one model.** From 4.6 onward a 900K-token prompt bills at the same per-token rate as a 9K one. Haiku 5.5 is the sole exception and the only tiered model in the lineup. Everything strange about Haiku economics flows from that one asterisk.

## 3.2 Deriving the cost model

A single request’s billed input decomposes into four disjoint categories. Let:

-   `f` = fresh (uncached) input tokens
-   `w5`, `w1` = tokens written to a 5-minute and one-hour cache entry
-   `r` = tokens served from cache
-   `o` = output tokens, inclusive of thinking tokens

and let `pᵢ`, `pₒ` be the base input and output rates and `ρ` the model’s cache-read multiple. Then

    C = (f·pᵢ + w5·1.25pᵢ + w1·2pᵢ + r·ρ·pᵢ + o·pₒ) / 10⁶ · g · b

where `g` is the data-residency multiplier (1.0 for `inference_geo: "global"`, 1.1 for `"us"`, and effectively 1.1 for Bedrock and Google Cloud regional endpoints) and `b` is the batch multiplier (0.5 on the Batch API, 1.0 otherwise). Fast mode does not multiply; it substitutes a different `pᵢ`/`pₒ` pair and forbids `b = 0.5`.

Two subtleties that bite:

**Prompt length for tiering is the sum of all four input categories.** On Haiku 5.5 the threshold test is `f + w5 + w1 + r > 100,000`, evaluated per request. Cache reads count. Cache writes count. Nothing about caching lets you duck under the line.

**`o` includes thinking tokens.** Effort does not add a separate billing category; it changes how many output tokens the model emits. Attribute it with `usage.output_tokens_details.thinking_tokens` or you will have no idea what an effort sweep cost you.

For a workload you need the per-request expectation, not a single request. With cache hit rate `h` on a static prefix of `S` tokens, variable suffix `V`, and expected output `O`:

    E[f]  = V
    E[w]  = (1-h)·S
    E[r]  = h·S
    E[o]  = O

In code — note the tier test applies to *total* input, and the rates are data, not literals buried in logic.

``` {.sourceCode .python}
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Rates:
    """Base per-MTok rates for one billing tier of one model."""
    inp: float
    out: float
    read_multiple: float = 0.10
    write_5m_multiple: float = 1.25
    write_1h_multiple: float = 2.00

@dataclass(frozen=True)
class Model:
    name: str
    base: Rates
    # Only Haiku 5.5 populates these; everything else is flat-rate.
    tier_threshold: int | None = None
    tier_rates: Rates | None = None

    def rates_for(self, total_input: int) -> Rates:
        if self.tier_threshold is not None and total_input > self.tier_threshold:
            return self.tier_rates
        return self.base

@dataclass
class Shape:
    """Expected token counts for one request of a workload."""
    fresh: float = 0.0
    write_5m: float = 0.0
    write_1h: float = 0.0
    read: float = 0.0
    output: float = 0.0

    @property
    def total_input(self) -> float:
        return self.fresh + self.write_5m + self.write_1h + self.read

MTOK = 1_000_000.0

def cost(model: Model, s: Shape, *, geo: str = "global",
         batch: bool = False) -> float:
    r = model.rates_for(int(round(s.total_input)))
    billed = (
        s.fresh * r.inp
        + s.write_5m * r.write_5m_multiple * r.inp
        + s.write_1h * r.write_1h_multiple * r.inp
        + s.read * r.read_multiple * r.inp
        + s.output * r.out
    )
    c = billed / MTOK
    if geo == "us":
        c *= 1.10
    if batch:
        c *= 0.50
    return c

def cached_shape(static: int, variable: int, output: int,
                 hit_rate: float, ttl: str = "5m") -> Shape:
    """Expected shape for a workload with a reusable static prefix."""
    written = (1.0 - hit_rate) * static
    return Shape(
        fresh=variable,
        write_5m=written if ttl == "5m" else 0.0,
        write_1h=written if ttl == "1h" else 0.0,
        read=hit_rate * static,
        output=output,
    )

# Table 3.1, as data.
FABLE_51 = Model("Fable 5.1", Rates(10.0, 50.0, read_multiple=0.025))
OPUS_55 = Model("Opus 5.5", Rates(4.0, 20.0, read_multiple=0.05))
SONNET_55 = Model("Sonnet 5.5", Rates(2.0, 10.0, read_multiple=0.05))
HAIKU_55 = Model(
    "Haiku 5.5",
    base=Rates(0.10, 0.50, read_multiple=0.10),
    tier_threshold=100_000,
    tier_rates=Rates(0.50, 2.50, read_multiple=0.10),
)
```

The `read_multiple` on the Haiku tier rates stays at 0.1x because its tier-2 read rate of \$0.05 is exactly one tenth of its tier-2 input rate of \$0.50. The multiplier is invariant; the base it multiplies is not.

## 3.3 Three workloads, fully costed

### Case A — High-volume classification

Support-ticket triage. A 3,200-token system prompt carrying the label taxonomy and routing rules, stable across all requests. A 450-token ticket body. A 60-token output: one label plus a one-line rationale. 8,000,000 requests per month, arriving as a steady stream, so a 5-minute cache entry stays warm and the hit rate is 95%.

Expected shape per request: `read = 3,040`, `write_5m = 160`, `fresh = 450`, `output = 60`. Total input 3,650 — comfortably under the Haiku threshold.

**Table 3.2 — Case A, cost per request.**

  Component          Haiku 5.5         Sonnet 5.5       Opus 5.5
  ------------------ ----------------- ---------------- ----------------
  Read (3,040)       \$0.0000304       \$0.000304       \$0.000608
  Write 5m (160)     \$0.0000200       \$0.000400       \$0.000800
  Fresh (450)        \$0.0000450       \$0.000900       \$0.001800
  Output (60)        \$0.0000300       \$0.000600       \$0.001200
  **Per request**    **\$0.0001254**   **\$0.002204**   **\$0.004408**
  **Monthly (8M)**   **\$1,003**       **\$17,632**     **\$35,264**

Haiku is 17.6x cheaper than Sonnet here. That is a little below the 20x ratio of the headline prices. Three of the four lines do differ by exactly 20x, but the cache read — the largest token category — is discounted to 0.1x on Haiku and to 0.05x on Sonnet, which narrows the gap on that line to 10x and pulls the overall ratio down.

A naive reading ships Haiku here. Suppose your eval set puts Haiku at 94% and Sonnet at 97% on this taxonomy. The question is not “is 3 points worth \$16,629/month” in the abstract. It is: **what does one misclassification cost downstream?**

Let `c` be the fully-loaded cost of a single misroute. Total monthly cost of ownership is inference plus error cost:

    TCO(Haiku)  = 1,003  + 0.06 · 8,000,000 · c  = 1,003  + 480,000c
    TCO(Sonnet) = 17,632 + 0.03 · 8,000,000 · c  = 17,632 + 240,000c

Setting them equal: `240,000c = 16,629`, so `c* = $0.0693`.

**If a single misclassification costs more than about seven cents to clean up, Sonnet is cheaper than Haiku.** Seven cents is five seconds of an agent’s time. If the misroute triggers an automatic retry on a cheap path, `c ≈ $0.02` and Haiku wins comfortably (\$10,603 vs \$22,432). If a human has to move the ticket, `c` is a dollar or more, and at exactly \$1 Sonnet already beats Haiku by about \$223,000 a month (`240,000 × $1 − $16,629`); at \$3 the gap is about \$700,000.

This is the single most important discipline in this chapter: **the inference bill is often not the dominant term.** Model your error cost before you model your token cost, because at high volume the error term has a multiplier of eight million on it and the token term has the same multiplier but a much smaller coefficient. We will come back to Case A in §3.6 and find a third option that beats both.

### Case B — Long-context document assistant

A regulatory-review assistant. Each session loads a 180,000-token corpus — a filing plus the applicable rule text — then takes roughly twelve turns against it. The corpus is written to a one-hour cache entry on turn 1 and read on turns 2–12. Each turn adds about 150 tokens of user text and 700 tokens of answer, so the uncached suffix grows; summing the triangular series gives 57,900 fresh input tokens across the session, and 8,400 output tokens.

Per session: `write_1h = 180,000`, `read = 11 × 180,000 = 1,980,000`, `fresh = 57,900`, `output = 8,400`.

Every single request in this session has a prompt length of at least 180,000 tokens. **On Haiku 5.5, every request in this workload is billed at the \>100K tier.** There is no configuration that avoids it, because the cached corpus counts toward the threshold.

**Table 3.3 — Case B, cost per session.**

  -----------------------------------------------------------------------------------
  Component         Haiku 5.5 (tier 2)   Sonnet 5.5     Opus 5.5       Fable 5.1
  ----------------- -------------------- -------------- -------------- --------------
  Write 1h (180K)   \$0.1800             \$0.7200       \$1.4400       \$3.6000

  Read (1.98M)      \$0.0990             \$0.1980       \$0.3960       \$0.4950

  Fresh (57.9K)     \$0.0290             \$0.1158       \$0.2316       \$0.5790

  Output (8.4K)     \$0.0210             \$0.0840       \$0.1680       \$0.4200

  **Per session**   **\$0.3290**         **\$1.1178**   **\$2.2356**   **\$5.0940**
  -----------------------------------------------------------------------------------

Haiku’s advantage over Sonnet has collapsed from 17.6x in Case A to **3.40x** here. Nothing about the models changed. The workload crossed the tier boundary, and a 5x rate increase on the dominant model ate most of the gap.

Look at the read line. Fable 5.1 reads 1.98M cached tokens for \$0.495 while Sonnet reads the same tokens for \$0.198 — only 2.5x more, despite Fable’s base input rate being 5x Sonnet’s. That is the 0.025x read multiple at work. **In a read-dominated workload the effective price ratio between tiers is much flatter than the headline ratio.** At 40 turns instead of 12, reads dominate harder and Fable’s premium over Sonnet keeps shrinking toward 2.5x. Read-heavy long-context work is the one regime where reaching for the top tier is economically defensible without agonising.

The practical consequence for Case B: Haiku saves \$0.79 per session over Sonnet. At 50,000 sessions a month that is \$39,440 — real money, but now in the same order of magnitude as the accuracy risk on regulatory text, and the decision has become a genuine judgement call rather than an obvious one. Run the eval.

### Case C — Low-volume high-stakes reasoning

Contract risk analysis. 400 requests per month. Each one: a 4,000-token static rubric (cacheable, 90% hit), a 25,000-token contract body (never repeated, always fresh), and a long reasoned output whose length depends on effort.

Assume, from your own effort sweep, output lengths of roughly 5,000 tokens at `medium`, 9,000 at `high`, and 18,000 at `max` on Opus 5.5, with Fable 5.1 running a little longer at each level.

**Table 3.4 — Case C, cost per request and per month.**

  Configuration      Output   Per request   Monthly (400)
  ------------------ -------- ------------- ---------------
  Sonnet 5.5, high   9,000    \$0.1414      \$56.54
  Opus 5.5, medium   5,000    \$0.2027      \$81.09
  Opus 5.5, high     9,000    \$0.2827      \$113.09
  Opus 5.5, max      18,000   \$0.4627      \$185.09
  Fable 5.1, high    11,000   \$0.8059      \$322.36
  Fable 5.1, max     22,000   \$1.3559      \$542.36

Work one of these by hand to check the method. Opus 5.5 at `high`: reads `0.9 × 4,000 = 3,600` at \$0.20/MTok = \$0.00072; writes `400` at \$5.00/MTok = \$0.0020; fresh 25,000 at \$4.00/MTok = \$0.1000; output 9,000 at \$20.00/MTok = \$0.1800. Sum \$0.28272.

The **entire monthly spread between cheapest and most expensive configuration is \$486** — roughly three hours of a senior engineer’s fully-loaded time, or well under an hour of outside counsel. One missed indemnity cap costs more than running Fable at `max` effort for a year.

**At low volume, cost modelling is the wrong exercise.** The correct move is to pick the most capable configuration your evals support, spend zero further engineering effort on cost, and redirect that effort into eval coverage — because the only thing that can actually hurt you here is a quality failure, and your evidence about quality is almost certainly thinner than your evidence about price.

The generalisable rule: compute `monthly_spread / cost_of_one_bad_output`. In Case A that ratio is enormous and optimisation pays. In Case C it is far below 1 and optimisation is theatre.

## 3.4 The Haiku 100K cliff, worked

Haiku 5.5 is the only tiered model, so it is the only place where cost is non-linear in prompt length. Understanding the discontinuity precisely is worth more than memorising the rates.

### The cliff itself

Take a 1,000-token output and vary the prompt.

  Prompt tokens   Tier   Input cost   Output cost   Total
  --------------- ------ ------------ ------------- -----------
  99,000          1      \$0.00990    \$0.00050     \$0.01040
  100,000         1      \$0.01000    \$0.00050     \$0.01050
  100,001         2      \$0.05000    \$0.00250     \$0.05250
  101,000         2      \$0.05050    \$0.00250     \$0.05300

Going from 99,000 to 101,000 prompt tokens — a 2% increase — raises the bill 5.1x. The marginal cost of those 2,000 tokens is \$0.0426, an **effective marginal rate of \$21.30 per MTok** — 213 times Haiku’s tier-1 input rate and more than double Fable 5.1’s. Those 2,000 tokens are the most expensive tokens available anywhere in the lineup, by a wide margin. There is no other discontinuity like it in the price surface, and the whole of Haiku capacity planning consists of staying on the correct side of it.

### Where Haiku stops being cheaper than Sonnet

Compare tier-2 Haiku to Sonnet 5.5 on identical token counts:

    input:  0.50 / 2.00  = 0.25
    output: 2.50 / 10.00 = 0.25

The ratio is exactly 0.25 on both axes. **Tier-2 Haiku is always precisely 4x cheaper than Sonnet 5.5 for identical token counts, on every component.** It can never cost more on a like-for-like basis. The cliff does not reverse the ordering of the two models.

So when does Haiku actually cost more than Sonnet? Only when it consumes more than four times the tokens. That happens for real reasons:

-   **Retries and self-check loops.** If a Haiku pipeline needs `k` attempts per accepted output and Sonnet needs one, the crossover is at `k = 4`. Below the cliff the same calculation gives a crossover at `k = 20` (tier-1 Haiku is 20x cheaper on input, 20x on output). The cliff shrinks your retry budget by a factor of five.
-   **Effort inflation.** If `low` effort on Haiku is insufficient and you push to `high`, output tokens can easily multiply by three or four on reasoning-heavy inputs, while Sonnet at `medium` holds. Four is the magic number again.
-   **Chunking overhead** — the big one, below.

A 120,000-token extraction with a 2,000-token output costs `120,000 × 0.50/10⁶ + 2,000 × 2.50/10⁶ = $0.0650` on Haiku and `120,000 × 2.00/10⁶ + 2,000 × 10.00/10⁶ = $0.2600` on Sonnet. If Haiku’s acceptance rate on this task is 25% and you retry until you get a clean parse, expected attempts `1/0.25 = 4`, expected cost `4 × $0.0650 = $0.2600`. Dead level. At a 20% acceptance rate Haiku is more expensive, and it is also slower and more complex. Measure your acceptance rate before you commit to the cheap tier on long inputs.

### The chunking trap

You have a 400,000-token corpus to process. Three designs:

**Design 1 — one request.** Prompt 400,000, output 4,000. Tier 2. `400,000 × 0.50/10⁶ + 4,000 × 2.50/10⁶ = $0.2000 + $0.0100 = $0.2100`

**Design 2 — five chunks of 80,000, no shared context.** Each chunk 80,000 + 1,000 output, tier 1. `5 × (80,000 × 0.10/10⁶ + 1,000 × 0.50/10⁶) = 5 × $0.00850 = $0.0425`

Chunking is 4.9x cheaper. Now add reality:

**Design 3 — five chunks, each carrying a 30,000-token shared rubric.** Each chunk is now 110,000 tokens. Tier 2, every one. `5 × (110,000 × 0.50/10⁶ + 1,000 × 2.50/10⁶) = 5 × $0.05750 = $0.2875`

**Chunking made it 37% more expensive than the single monolithic request.** The per-chunk overhead pushed every chunk over the cliff, so you paid the 5x rate five times instead of once. The fan-out looked like an obvious optimisation and was a regression.

**Design 4 — compress the rubric to 18,000 tokens** so each chunk totals 98,000 and stays in tier 1. `5 × (98,000 × 0.10/10⁶ + 1,000 × 0.50/10⁶) = 5 × $0.01030 = $0.0515`

A 12,000-token prompt-engineering exercise moved the bill from \$0.2875 to \$0.0515, a 5.6x improvement, and the only thing that changed was which side of a threshold each chunk landed on. **On Haiku, the budget line in your prompt design is 100,000 tokens, not “as short as reasonable.”**

### Caching and the threshold

Cache reads and cache writes both count toward prompt length. Three consequences follow.

**Caching does not get you under the cliff.** A 90,000-token cached prefix plus 15,000 fresh tokens is a 105,000-token prompt. Tier 2. `90,000 × 0.05/10⁶ + 15,000 × 0.50/10⁶ + 1,000 × 2.50/10⁶ = $0.0045 + $0.0075 + $0.0025 = $0.0145` The same token counts hypothetically in tier 1 would cost `$0.0009 + $0.0015 + $0.0005 = $0.0029` — exactly 5x less, as the uniform rate step guarantees.

**Cache writes are punished hardest.** The request that creates that 90,000-token 5-minute entry pays `90,000 × 0.625/10⁶ = $0.05625`, versus `$0.01125` in tier 1. If your cache churns — short sessions, cold starts, scaling events — you pay this repeatedly. On a tiered model, a low cache hit rate on a large prefix is the worst configuration available.

**Caching can push you over the cliff.** This is the trap worth remembering. Suppose your request is 95,000 tokens and sits in tier 1 at `95,000 × 0.10/10⁶ + 1,000 × 0.50/10⁶ = $0.0100`. Someone adds a 10,000-token boilerplate block and caches it “because caching is cheap.” Prompt length is now 105,000. Tier 2. The bill becomes `10,000 × 0.05/10⁶ + 95,000 × 0.50/10⁶ + 1,000 × 2.50/10⁶ = $0.0005 + $0.0475 + $0.0025 = $0.0505`. **A caching optimisation raised cost 5x.** The cached tokens themselves were nearly free; they just moved the whole request into a more expensive rate class.

Guard this in code, not in a wiki page:

``` {.sourceCode .python}
HAIKU_CLIFF = 100_000

def cliff_check(s: Shape, headroom: float = 0.08) -> str | None:
    """Warn when a Haiku workload is near or over the tiering threshold."""
    total = s.total_input
    if total > HAIKU_CLIFF:
        over = total - HAIKU_CLIFF
        return (f"OVER by {over:,.0f} tokens: whole request bills at 5x. "
                f"Shed {over:,.0f} tokens or accept tier 2 deliberately.")
    margin = (HAIKU_CLIFF - total) / HAIKU_CLIFF
    if margin < headroom:
        return (f"Within {margin:.1%} of the cliff at {total:,.0f} tokens. "
                f"Any prompt growth is a 5x cost event.")
    return None
```

Instrument the real thing too: alert on the *fraction of Haiku requests billed in tier 2*, derived from `cache_read_input_tokens + cache_creation_input_tokens + input_tokens`. Tier 2 costs 5x, so a share `s` of requests in tier 2 multiplies the bill by `1 + 4s`. A drift from 2% to 30% takes that factor from 1.08 to 2.2, roughly doubling the bill in a way that no dashboard tracking request counts will show you.

## 3.5 Effort as a cost and latency dial

Effort is set as `output_config: {"effort": ...}` with levels `low`, `medium`, `high`, `xhigh`, and `max`. It is not inside the `thinking` object. On 4.7 and later, `thinking: {"type": "enabled", "budget_tokens": N}` returns a 400; the migration is `thinking: {"type": "adaptive"}` plus `output_config.effort`. Defaults are `medium` on Opus 5.5 and Haiku 5.5, `high` elsewhere. `temperature`, `top_p` and `top_k` are deprecated on 4.7+, so effort is the dial you have.

Effort is a behavioural signal, not a token budget. Three cost mechanisms follow from that:

1.  **Thinking token volume.** The direct effect. Higher effort means more thinking tokens, billed as output.
2.  **Tool-call count.** Higher effort produces more tool calls, more planning, and more summarisation. In an agentic loop this compounds: each extra tool call adds a full round trip whose input includes the entire accumulated context. This effect frequently dominates the thinking-token effect and almost nobody measures it.
3.  **Skipped thinking at low effort.** At `low`, adaptive thinking may skip thinking entirely on easy inputs, so cost drops superlinearly on easy traffic and barely at all on hard traffic. The savings from stepping down are concentrated in the part of your traffic you were not worried about.

Two operational hazards. First, **changing top-level effort between requests restarts the prompt cache.** An effort sweep run naively against a long cached prefix pays a full cache write for every level you test; on a 180,000-token prefix on Sonnet that is \$0.45 per level in 5-minute writes before you measure anything. The `mid-conversation-output-config-2026-07-01` beta allows per-message effort and preserves the cache. Second, **thinking cannot be disabled at `xhigh` or `max`** on Opus 5 and Haiku 5.5, and not at any level on Opus 5.5; `thinking: {"type": "disabled"}` returns 400.

### Measuring whether higher effort buys anything

The default assumption — more effort is better, just costlier — is wrong often enough to be dangerous. The documentation itself notes that `max` on Opus 4.7 adds significant cost for relatively small quality gains, and that Sonnet 5 at `medium` is comparable to Sonnet 4.6 at `high`. Effort response curves are task-specific and frequently flat or non-monotonic. Run the sweep as a measurement, not an intuition:

``` {.sourceCode .python}
import statistics, time
from collections import defaultdict

LEVELS = ["low", "medium", "high", "xhigh", "max"]

def effort_sweep(client, model, items, grade, *, levels=LEVELS, max_tokens=32_000):
    """items: [(prompt, reference)]. grade: (output, reference) -> float in [0,1]."""
    rows = defaultdict(list)
    for level in levels:
        for prompt, ref in items:
            t0 = time.perf_counter()
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                output_config={"effort": level},
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
            wall = time.perf_counter() - t0
            text = "".join(b.text for b in resp.content if b.type == "text")
            det = getattr(resp.usage, "output_tokens_details", None)
            rows[level].append({
                "score": grade(text, ref),
                "seconds": wall,
                "out_tokens": resp.usage.output_tokens,
                "thinking_tokens": getattr(det, "thinking_tokens", 0) or 0,
                "tool_calls": sum(1 for b in resp.content if b.type == "tool_use"),
            })
    return rows

def sweep_report(rows, model, cost_fn):
    """cost_fn: (out_tokens) -> dollars, holding input constant."""
    out = []
    for level, recs in rows.items():
        n = len(recs)
        acc = statistics.mean(r["score"] for r in recs)
        se = (statistics.pstdev([r["score"] for r in recs]) / n ** 0.5) if n > 1 else 0.0
        mean_out = statistics.mean(r["out_tokens"] for r in recs)
        out.append({
            "effort": level,
            "accuracy": acc,
            "ci95_halfwidth": 1.96 * se,
            "mean_out_tokens": mean_out,
            "mean_thinking": statistics.mean(r["thinking_tokens"] for r in recs),
            "mean_tool_calls": statistics.mean(r["tool_calls"] for r in recs),
            "p50_seconds": statistics.median(r["seconds"] for r in recs),
            "cost_per_item": cost_fn(mean_out),
        })
    out.sort(key=lambda d: LEVELS.index(d["effort"]))
    # Marginal cost per accuracy point gained over the previous level.
    for prev, cur in zip(out, out[1:]):
        d_acc = cur["accuracy"] - prev["accuracy"]
        d_cost = cur["cost_per_item"] - prev["cost_per_item"]
        cur["marginal_cost_per_point"] = (d_cost / d_acc) if d_acc > 1e-9 else float("inf")
    return out
```

The column that decides is `marginal_cost_per_point`, and the column that stops you from fooling yourself is `ci95_halfwidth`. If stepping from `high` to `max` moves accuracy by 0.8 points with a 95% half-width of 2.1 points, you have measured nothing; you have paid for noise. Do not step up on a difference smaller than your confidence interval, no matter how much you want the accuracy.

Expect saturation. A typical shape on a well-specified extraction task is `low` 0.88, `medium` 0.95, `high` 0.96, `xhigh` 0.96, `max` 0.96, with cost roughly doubling at each step above `medium`: the whole decision sits at the `low`→`medium` boundary and everything above is waste. On an open-ended analysis task the curve can keep climbing to `xhigh`. You cannot know which you have without running it.

## 3.6 Cascades and routing, worked numerically

A *cascade* sends every request to a cheap model first and passes on (*escalates*) only the requests it cannot handle well to an expensive model. The decision to escalate is made by a *gate*: a schema check, a validator, or a confidence signal. Volume I introduced the pattern. Here is when it actually pays.

### Break-even escalation fraction

In the standard cascade the cheap stage runs on **every** request and the expensive stage runs on the escalated fraction `p`. So

    C_cascade = c_cheap + p·c_exp          (+ routing overhead)

Compare against sending everything to the expensive model. Setting `c_cheap + p·c_exp = c_exp`:

    p* = 1 − c_cheap/c_exp

That is the whole theory. The cascade stops paying when the escalation fraction exceeds one minus the cost ratio of the two stages.

**Table 3.5 — Break-even escalation fractions from the case studies.**

  ---------------------------------------------------------------------------------------------
  Cheap stage          Expensive stage       c\_cheap      c\_exp       ratio       p\*
  -------------------- --------------------- ------------- ------------ ----------- -----------
  Haiku (Case A)       Sonnet (Case A)       \$0.0001254   \$0.002204   0.0569      **94.3%**

  Haiku (Case B)       Sonnet (Case B)       \$0.3290      \$1.1178     0.2943      **70.6%**

  Sonnet (Case B)      Fable (Case B)        \$1.1178      \$5.0940     0.2195      **78.1%**

  Opus high (Case C)   Fable high (Case C)   \$0.2827      \$0.8059     0.3508      **64.9%**
  ---------------------------------------------------------------------------------------------

In Case A the cascade survives escalating 94% of traffic — the cheap stage is so nearly free you could route almost everything upward and still come out ahead. In Case C the margin is 65%, still generous. **The break-even fraction is almost always far higher than the escalation rates people actually build.** A cascade escalating 15% of traffic is nowhere near its economic limit.

Which means: **if your cascade is not paying off, cost ratio is rarely the reason.** The reasons are operational — routing overhead, complexity, and tail latency.

### A cascade that beats both single-model options

Return to Case A with real confidence gating. Haiku’s overall accuracy is 94%. Suppose a calibrated confidence signal lets it keep the 85% of traffic it is sure about, where it scores 98.5%, and escalate the hard 15%, where it would have scored 68%. Check consistency: `0.85 × 0.985 + 0.15 × 0.68 = 0.83725 + 0.102 = 0.93925 ≈ 94%`. Good — the gate is a partition of the same traffic, not a new model.

Now route the hard 15% to Sonnet, which scores 92% on that genuinely difficult subset (below its 97% overall, as you would expect).

    Cascade accuracy = 0.85 × 0.985 + 0.15 × 0.92 = 0.83725 + 0.138 = 0.97525
    Cascade cost     = $0.0001254 + 0.15 × $0.002204 = $0.0001254 + $0.0003306
                     = $0.000456 per request

**97.5% accuracy at \$0.000456 per request, against Sonnet-only’s 97.0% at \$0.002204.** The cascade is 4.8x cheaper *and* half a point more accurate. Monthly: \$3,648 versus \$17,632, a saving of \$13,984, with better outcomes.

The accuracy gain is not magic: the two models’ error sets are not identical, and the confidence gate is a cheap way to find Haiku’s error set and hand it to a model that fails differently. **The value of a cascade is the quality of its gate, not the price of its stages.** A cascade with a random 15% escalation gets you `0.85 × 0.94 + 0.15 × 0.97 = 0.9445` — worse than Sonnet-only, for the same cost as the calibrated version. Build the gate, measure the gate, and report gate precision and recall as first-class metrics.

### Escalation triggers in practice

Confidence is not a single thing, and a self-reported probability from a model is the weakest of the available signals. Rank them by how much you should trust them:

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Trigger                                                  Signal            Cheap to compute              Notes
  -------------------------------------------------------- ----------------- ----------------------------- ----------------------------------------------------------------------------
  Schema/parse failure                                     Hard              Yes                           Deterministic, zero false positives. Always include.

  Validator or business-rule violation                     Hard              Yes                           Checks the answer against known constraints. Very strong.

  Abstention — model emits an explicit “uncertain” label   Soft              Yes                           Needs the label in the taxonomy and prompt support for using it.

  Self-reported confidence score                             Soft              Yes                           Poorly calibrated; useful only after you fit a threshold on held-out data.

  Self-consistency across `n` cheap samples                Soft              No — costs `n`x cheap stage   Strong, but `n·c_cheap` must stay well under `c_exp`.

  Input features (length, language, entity density)        Soft              Yes                           Routes before inference. Only lever that reduces cheap-stage cost too.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Self-consistency deserves its own arithmetic. Running the cheap stage three times and escalating on disagreement costs `3·c_cheap + p·c_exp`. In Case A: `3 × $0.0001254 + 0.15 × $0.002204 = $0.0003762 + $0.0003306 = $0.000707`. Still 3.1x cheaper than Sonnet-only, and triple-sampling typically catches more of the error set than a self-reported score does. The break-even on `n` is where `n·c_cheap = c_exp`, i.e. `n = 17.6` here. You have enormous headroom for sampling when the tier gap is 20x and almost none when it is 2x.

``` {.sourceCode .python}
def cascade_economics(c_cheap, c_exp, escalate_frac, *, cheap_samples=1,
                      overhead=0.0, l_cheap_ms=0.0, l_exp_ms=0.0):
    cost = cheap_samples * c_cheap + escalate_frac * c_exp + overhead
    return {
        "cost_per_request": cost,
        "vs_expensive_only": cost / c_exp,
        "breakeven_escalation": 1.0 - (cheap_samples * c_cheap + overhead) / c_exp,
        "mean_latency_ms": l_cheap_ms + escalate_frac * l_exp_ms,
        # Worst realistic path: cheap stage runs, then escalates.
        "escalated_latency_ms": l_cheap_ms + l_exp_ms,
    }
```

### What the cascade costs you in latency

Mean latency improves; tail latency gets worse. With a 400 ms cheap stage, a 3,200 ms expensive stage and `p = 0.15`:

    Expensive-only:  mean 3,200 ms,  p99 ≈ 3,200 ms-ish (one path)
    Cascade:         mean 400 + 0.15 × 3,200 = 880 ms
                     escalated path = 400 + 3,200 = 3,600 ms

Mean latency fell 3.6x. The escalated path is 12.5% slower than expensive-only, and since 15% of traffic takes it, **everything above the 85th percentile is now worse than before you built the cascade.** If your SLO is on p95 or p99, the cascade may have failed one objective while succeeding on another. Decide which percentile you are optimising before you build, and consider hedging: fire both stages concurrently on inputs predicted to escalate, paying double on that slice to remove the serialisation.

## 3.7 Batch economics

The Batch API bills at 50% of standard rates on both input and output, stacks with prompt caching, accepts up to 100,000 requests or 256 MB per batch, and expires anything unfinished at 24 hours. Results are retained 29 days from `created_at`. Requests that expire are not billed. `stream: true`, `speed` (Fast mode), and `max_tokens: 0` are rejected.

The naive model says batch halves your bill. It does not, when caching is in play, because **cache hits in batch are best-effort** with typical hit rates ranging from roughly 30% to 98%.

Work Case A three ways with a 3,200-token cacheable prefix:

**Real-time, 5-minute TTL, 95% hit:**

    read 3,040 × 0.01 + write 160 × 0.125 + fresh 450 × 0.10 + out 60 × 0.50  (per MTok)
    = $0.0000304 + $0.0000200 + $0.0000450 + $0.0000300 = $0.0001254

**Batch, 5-minute TTL, hit rate degrades to 60%:**

    read 1,920 × 0.01 = $0.0000192
    write 1,280 × 0.125 = $0.0001600
    fresh 450 × 0.10 = $0.0000450
    out 60 × 0.50 = $0.0000300
    subtotal = $0.0002542  ×  0.50  =  $0.0001271

**\$0.0001271 versus \$0.0001254. The batch run is 1.4% more expensive than real-time.** The 50% discount was entirely consumed by cache-write churn, because the write multiplier is 1.25x and a 35-point hit-rate drop moved 1,120 tokens per request from the 0.1x column to the 1.25x column — a 12.5x rate increase on those tokens.

**Batch, one-hour TTL, hit rate recovers to 90%:**

    read 2,880 × 0.01 = $0.0000288
    write 1h 320 × 0.20 = $0.0000640
    fresh 450 × 0.10 = $0.0000450
    out 60 × 0.50 = $0.0000300
    subtotal = $0.0001678  ×  0.50  =  $0.0000839

Now batch is 33% cheaper than real-time. The one-hour TTL costs 2x on writes instead of 1.25x, but it survives batch queueing delays, and surviving is what matters. **Use the one-hour TTL in batch workloads; identical `cache_control` placement and a steady submission stream are what actually produce the hit rate.**

### When 24 hours is acceptable

The question is not “can we wait?” It is “what is the cost of the staleness window, and does it exceed the discount?” Make it concrete: `saving = 0.5 × C_realtime` against `staleness_cost = decay_rate × latency_hours × value_per_item`.

Batch fits cleanly when the output’s value does not decay inside a day and nobody is blocked: backfills and re-processing after a prompt change, nightly enrichment and classification of the day’s records, eval runs and regression suites, synthetic data generation, bulk summarisation for search indexes, periodic compliance scans.

It does not fit when a human or a request is waiting, when the input itself expires inside 24 hours (a live conversation, a session), when the output feeds a decision with a deadline sooner than tomorrow, or when you need Fast mode or streaming.

Two operational facts burn people. **Parameter validation is asynchronous** — a malformed `params` surfaces only after processing ends, so dry-run one request through the Messages API before submitting 100,000. And **results return in arbitrary order**; `custom_id` is the only join key, it must be unique within the batch, and it must match `^[a-zA-Z0-9_-]{1,64}$`. Encode your primary key there, not an array index.

A reasonable hybrid for a classification service: batch the bulk nightly reprocessing at 50% off, keep a real-time path for the live tail, and size that path for peak rather than mean, because the batch path absorbs none of your spikes.

## 3.8 Latency engineering

Latency decomposes, and the decomposition tells you which lever applies.

    total = queue + prefill(prompt_tokens) + output_tokens / OTPS
    TTFT  ≈ queue + prefill

In this section `prefill` means the time the model spends processing the prompt before it can emit the first token. It has nothing to do with prefilling an assistant turn. Each term has one effective lever:

  --------------------------------------------------------------------------------------------------------------------------------
  Term                    Driven by                                 Lever
  ----------------------- ----------------------------------------- --------------------------------------------------------------
  `queue`                 Rate limits, capacity, 429/529 retries    Concurrency control, Priority Tier, backoff

  `prefill`               Prompt tokens, cache hit or miss          Prompt caching (a hit skips most prefill), prompt shortening

  `output / OTPS`         Output length, effort, model, Fast mode   Lower effort, shorter outputs, Fast mode, smaller model
  --------------------------------------------------------------------------------------------------------------------------------

### What streaming does and does not fix

Streaming changes **when the user sees the first token.** It does not change total time, does not change token count, and does not change cost. It converts a dead wait into progressive disclosure, which is a genuine and large improvement in perceived latency and no improvement at all in measured latency.

It therefore fixes nothing for a non-interactive consumer. If a downstream service must parse a complete JSON object before acting, streaming buys exactly zero — the last token arrives at the same moment either way. Teams add streaming to backend pipelines and are then baffled that p99 did not move. Streaming is a UX lever: use it where a human is reading, and everywhere else reduce prompt-processing time (shorter or cached prompts) or output length.

It has one hard engineering benefit: it makes long generations observable, so you can detect a stall and abort instead of discovering at a 10-minute timeout that you paid for 100,000 tokens you will discard. For outputs near the 128K ceiling that alone makes it close to mandatory.

### Fast mode, costed

Fast mode is `speed: "fast"` at the top level, available on Opus 5.5 (generally available, no beta header), and on Opus 5 and Opus 4.8 in research preview behind `fast-mode-2026-02-01` and an access request. It delivers up to 2.5x higher output tokens per second. Opus 5.5 Fast mode bills at \$8/\$40 per MTok against the standard \$4/\$20. It is unavailable with the Batch API and with a Priority Tier commitment, unavailable on Claude Platform on AWS, and switching between fast and standard **invalidates the prompt cache**, so the two speeds do not share cached prefixes. `usage.speed` reports which you actually got.

The critical constraint: **the gain is on output throughput, not TTFT.** So the time saved is

    saved = (o / OTPS) × (1 − 1/2.5) = 0.6 × o / OTPS

and the extra money is a function of the whole request, input included.

**Long input, short output.** 200,000 input, 2,000 output, 60 OTPS standard. - Generation: 33.3 s standard, 13.3 s fast. Saved 20.0 s = 0.333 min. - Cost: standard `$0.800 + $0.040 = $0.840`; fast `$1.600 + $0.080 = $1.680`. Delta \$0.840. - **\$0.840 / 0.333 min = \$2.52 per minute saved.**

**Short input, long output.** 25,000 input, 60,000 output, 60 OTPS standard. - Generation: 1,000 s standard, 400 s fast. Saved 600 s = 10.0 min. - Cost: standard `$0.100 + $1.200 = $1.300`; fast `$0.200 + $2.400 = $2.600`. Delta \$1.300. - **\$1.300 / 10.0 min = \$0.13 per minute saved.**

A 19x difference in the price of a minute, from the same feature on the same model. Generalising with `o` output tokens at 60 OTPS, saved time is `o/6000` minutes and the premium is `pᵢ·i/10⁶ + 2×10⁻⁵·o`, so

    $/min saved = (pᵢ·i/10⁶) · 6000/o  +  0.12

The second term is a floor you cannot beat. The first is **the input premium divided by output length** — a fixed overhead that only saved generation time amortises. **Fast mode’s economics improve with output length and degrade with input length**, which is exactly backwards from where long-context workloads sit.

Is \$0.13/min worth it? A senior engineer at €90/hour costs about €1.50 ≈ \$1.63 per minute, so on the long-output request Fast mode is roughly 12x cheaper than the human time it unblocks. On the long-input short-output request, at \$2.52/min, it costs more than that engineer’s time and is not worth buying to shave 20 seconds. Fast mode is justified where latency has superlinear value — a conversion funnel with a measured abandonment curve, an SLA with credits attached, a pipeline where a long generation blocks a scarce resource — or where the output is long. It is not a general-purpose “make it faster” switch, and on a cached workload the first fast request also throws away the cached prefix.

### p50 versus p99, and why the tail sets the architecture

A single request’s latency distribution is right-skewed: `queue` has a fat tail from retries and capacity, and output length varies. If p50 is 2 s and p99 is 9 s, the p99 is not an edge case you can ignore, because **fan-out turns the tail into the median.**

A request that issues 20 independent subcalls and waits for all of them finishes at the maximum of 20 draws. Assuming independence:

    P(all 20 under the 1-call p99) = 0.99²⁰ = 0.818

So **18% of fan-outs exceed the single-call p99.** And `0.5²⁰ ≈ 1 × 10⁻⁶` — the aggregate essentially never achieves the single-call median. The median of the maximum of 20 draws is the single-call percentile `q` that solves `q²⁰ = 0.5`, which is about the 96.6th: your fan-out’s p50 *is* your single call’s p96.6.

Three consequences:

1.  **Never size a timeout from p50.** A timeout at 2x p50 kills a large share of legitimate requests. Size from p99 plus margin, and measure p99 on the aggregate, not the leaf.
2.  **Reduce the fan-out width or cap the wait.** Twenty parallel subcalls with an all-or-nothing join is a latency amplifier. Accept partial results where the task allows, or hedge the slowest subcalls with duplicate requests after a delay — duplicating the slowest 5% costs 5% more tokens and can cut aggregate p99 substantially.
3.  **Cascades and retries both lengthen the tail while shortening the mean.** A retry-on-validator-failure loop with `p = 0.15` has a mean of `1.15` attempts and a p99 of 2 or 3 attempts. Report both.

Measure throughput-relevant quantities alongside wall time: TTFT, output tokens per second, total, and `usage.speed` if you use Fast mode. Record them per request with model, effort and cache-hit state attached — a p99 regression is almost always a shift in one of those three, and you cannot diagnose it from a latency number alone.

## 3.9 Benchmark methodology

A model choice is evidence-based when you can state the decision rule, the sample size and the confidence interval before running anything. Most model choices are not.

### Build the set first

-   **Stratify over the dimensions that matter**, not uniformly over your traffic. Your traffic is 90% easy; a uniform sample will show every model at 95% and distinguish nothing. Over-sample hard strata and reweight when reporting.
-   **Include adversarial and malformed inputs** in proportion to their real rate, and track them as their own stratum. Robustness differences between tiers are much larger than accuracy differences on clean inputs, and they are where cheap tiers actually fail.
-   **Freeze it and version it.** A benchmark you edit after seeing results is not a benchmark.
-   **Hold out a slice you never look at** until the final decision. Everything you iterate against is a dev set and your estimate on it is optimistic.
-   **Grade programmatically wherever possible.** Exact match, schema validation, numeric tolerance, business-rule checks. Reserve human or model-graded rubrics for genuinely open-ended output, and when you use a model as judge, validate the judge against human labels on a subsample and report its agreement rate.

### Size it so it can answer the question

To detect a difference between two models you need enough items. For two independent samples at 94% and 97%, pooled `p̄ = 0.955`:

    SE = sqrt(2 · p̄(1−p̄) / n) = sqrt(0.08595 / n)
    Require 1.96 · SE < 0.03  →  SE < 0.01531  →  n > 366.7

**About 370 items per arm** for an independent comparison of 94% versus 97%. Teams routinely try this with 50 and declare a winner.

But you should not run independent arms. **Run both models on the same items** and use a paired test, which is far more efficient because only the items where the models disagree carry information. If both models get an item right, or both get it wrong, that item says nothing about which model is better. The evidence is entirely in the *discordant* items: the ones the candidate gets right and the incumbent gets wrong, and the reverse. If the two models were really equally good, those two counts would be roughly equal, the way heads and tails come out roughly equal over many coin tosses. McNemar’s test asks whether the split between them is too lopsided to be chance. Its statistic is `(|b − c| − 1)² / (b + c)`, where `b` and `c` are the two discordant counts, and a value above 3.841 means the split would happen by chance less than 5% of the time.

With 400 paired items, suppose the candidate is right where the incumbent is wrong on 18 items and wrong where the incumbent is right on 6. McNemar’s test:

    χ² = (|18 − 6| − 1)² / (18 + 6) = 11² / 24 = 121/24 = 5.04   →  p ≈ 0.025

Significant at the 5% level on 24 informative items out of 400. The paired design extracted a decision from a sample an unpaired design would have called a wash.

### Score the decision, not the accuracy

The output of a benchmark should be a cost-per-quality figure, not a leaderboard. For each candidate configuration record accuracy with its interval, cost per item from §3.2, p50 and p99 latency, and then the quantity that actually decides: **total cost of ownership including the error term from §3.3**.

``` {.sourceCode .python}
import json, math, statistics, concurrent.futures as cf

def run_arm(client, model, items, grade, *, effort=None, concurrency=8, **kw):
    def one(item):
        prompt, ref = item["prompt"], item["reference"]
        req = dict(model=model, max_tokens=kw.get("max_tokens", 8192),
                   messages=[{"role": "user", "content": prompt}])
        if effort:
            req["output_config"] = {"effort": effort}
        resp = client.messages.create(**req)
        text = "".join(b.text for b in resp.content if b.type == "text")
        u = resp.usage
        return {
            "id": item["id"],
            "stratum": item.get("stratum", "default"),
            "correct": grade(text, ref),
            "input_tokens": u.input_tokens,
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "output_tokens": u.output_tokens,
        }
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        return list(ex.map(one, items))

def mcnemar(incumbent, candidate):
    """Paired comparison on matching item ids. Returns (b, c, chi2, verdict)."""
    a = {r["id"]: bool(r["correct"]) for r in incumbent}
    b_ = {r["id"]: bool(r["correct"]) for r in candidate}
    shared = a.keys() & b_.keys()
    cand_only = sum(1 for i in shared if b_[i] and not a[i])
    inc_only = sum(1 for i in shared if a[i] and not b_[i])
    disc = cand_only + inc_only
    if disc == 0:
        return cand_only, inc_only, 0.0, "identical on shared items"
    chi2 = (abs(cand_only - inc_only) - 1) ** 2 / disc
    verdict = ("candidate better" if chi2 > 3.841 and cand_only > inc_only
               else "incumbent better" if chi2 > 3.841
               else f"inconclusive (n_discordant={disc}; need more items)")
    return cand_only, inc_only, chi2, verdict

def tco(records, model, cost_model, *, volume, error_cost):
    """Project monthly TCO from a benchmark arm."""
    n = len(records)
    acc = sum(1 for r in records if r["correct"]) / n
    per_item = statistics.mean(
        cost_model(Shape(fresh=r["input_tokens"], write_5m=r["cache_write"],
                         read=r["cache_read"], output=r["output_tokens"]))
        for r in records)
    half = 1.96 * math.sqrt(acc * (1 - acc) / n)
    return {
        "model": model, "n": n,
        "accuracy": round(acc, 4), "ci95": round(half, 4),
        "cost_per_item": per_item,
        "monthly_inference": per_item * volume,
        "monthly_error_cost": (1 - acc) * volume * error_cost,
        "monthly_tco": per_item * volume + (1 - acc) * volume * error_cost,
    }
```

Pre-register the decision rule: *adopt the candidate if McNemar’s χ² exceeds 3.841 in its favour on the held-out set, p99 latency does not regress by more than 15%, and projected monthly TCO does not increase.* Writing that down before you see numbers is the whole of the methodology; everything else is plumbing.

## 3.10 Migration engineering

Model IDs are dateless from 4.6 onward, and **a dateless 4.6+ ID is a fixed snapshot, not a moving alias** — weights and configuration for an existing ID are not updated, and new versions ship under new IDs. Pre-4.6 undated strings like `claude-sonnet-4-5` *are* floating aliases to the latest dated snapshot. This reverses the usual instinct: on the current lineup the short-looking ID is the safe one.

Even on a fixed snapshot, expect occasional behavioural drift from serving-infrastructure changes — routing, safety classifiers, sampling logic. A stable ID guarantees stable weights, not stable observed behaviour, so monitor production outputs.

### The deprecation clock

The commitment is **at least 60 days’ notice** before retirement of a publicly released model. Requests to a retired model fail. Deprecated-but-live models still work and are described as likely to be less reliable than active ones.

The worked example: `claude-sonnet-4-5-20250929` was deprecated 2026-09-30 with a tentative retirement of 2026-11-30. That is 61 days. Budget backwards from the retirement date, not forward from the announcement:

  ---------------------------------------------------------------------------------------------------------
  Phase                                                     Duration                Cumulative
  --------------------------------------------------------- ----------------------- -----------------------
  Build or refresh the benchmark set                        7 days                  7

  Offline paired comparison, effort sweep                   7 days                  14

  Shadow run at 5–10% mirror, collect ≥370 paired items     14 days                 28

  Decide; fix prompts for the new model’s effort defaults   7 days                  35

  Staged rollout 5% → 25% → 100% with rollback              14 days                 49

  Buffer for the thing you did not plan for                 12 days                 61
  ---------------------------------------------------------------------------------------------------------

The 60-day floor is adequate, not generous. The failure mode is spending the first 30 days deciding whether to migrate.

Migration is not only a model-string change. On the 4.6→5.5 path you must also: remove `thinking.budget_tokens` (400 on 4.7+) and replace it with `thinking: {"type": "adaptive"}` plus `output_config.effort`; remove `temperature`, `top_p` and `top_k`, which are deprecated on 4.7+ — remove the field rather than retuning the number; drop the `interleaved-thinking-2025-05-14` header, which is ignored; and **re-check effort explicitly**, because Opus 5.5 defaults to `medium` where Opus 5 defaulted to `high`, so a request that omits `effort` silently runs one level lower than it used to. That last one is the quiet quality regression that gets blamed on the new model.

### Shadow comparison

Run the incumbent in production and mirror a sampled fraction of real traffic to the candidate, comparing offline. The shadow path must never affect the response.

``` {.sourceCode .python}
import random, threading, queue

class ShadowRouter:
    def __init__(self, client, primary, candidate, *, sample_rate=0.05,
                 sink=None, candidate_overrides=None):
        self.client, self.primary, self.candidate = client, primary, candidate
        self.sample_rate = sample_rate
        self.sink = sink or (lambda rec: None)
        self.overrides = candidate_overrides or {}
        self._q: "queue.Queue[dict]" = queue.Queue(maxsize=2000)
        threading.Thread(target=self._drain, daemon=True).start()

    def complete(self, **req):
        resp = self.client.messages.create(model=self.primary, **req)
        if random.random() < self.sample_rate:
            try:
                self._q.put_nowait({"req": req, "primary": resp})
            except queue.Full:
                pass          # Shedding shadow load is always correct.
        return resp           # Never blocked by, or affected by, the shadow.

    def _drain(self):
        while True:
            job = self._q.get()
            try:
                shadow_req = {**job["req"], **self.overrides}
                alt = self.client.messages.create(model=self.candidate, **shadow_req)
                self.sink({
                    "primary_model": self.primary,
                    "candidate_model": self.candidate,
                    "primary_text": _text(job["primary"]),
                    "candidate_text": _text(alt),
                    "primary_usage": _usage(job["primary"]),
                    "candidate_usage": _usage(alt),
                })
            except Exception as e:                  # noqa: BLE001
                self.sink({"error": repr(e), "candidate_model": self.candidate})

def _text(resp):
    return "".join(b.text for b in resp.content if b.type == "text")

def _usage(resp):
    u = resp.usage
    return {"input": u.input_tokens, "output": u.output_tokens,
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0}
```

Four design points separate a useful shadow from a misleading one:

**Cost the shadow explicitly.** Shadow spend is `sample_rate × c_candidate × volume`. Mirroring 5% of Case A traffic to Opus 5.5 while Haiku serves production costs `0.05 × 8,000,000 × $0.004408 = $1,763/month` on top of Haiku’s \$1,003 — the shadow is 1.8x the production bill. The right sample rate is the smallest one that reaches your required `n` in your available window: for 370 paired items at 8M requests/month that is 0.005%, not 5%.

**Shadow the candidate’s configuration, not just its name.** If the candidate needs a different effort level or a different prompt, mirror *that* request. A shadow of the new model running the old model’s settings measures something nobody will ship.

**Watch the cache.** The shadow runs its own prompts, so it writes its own cache entries at its own sample rate, and a 5% sample rate on a 5-minute TTL will mostly miss. Shadow cost per request is therefore higher than production cost per request for the same model, and you must not read the shadow’s cost figures as a production projection. Project cost from the token *counts* and your production hit rate, not from the shadow’s bill.

**Compare on items, not aggregates.** Store `custom_id`-style joins and run McNemar. “Candidate accuracy 96.8% vs incumbent 96.1%” over different request populations is not evidence of anything.

### The inference\_geo decision

`inference_geo: "us"` applies a 1.1x multiplier to every token category — input, output, cache writes, cache reads — including Haiku 5.5’s tier-2 rates. `"global"` is the default. Models before 4.6 do not support the parameter and return 400. Bedrock and Google Cloud regional endpoints carry a comparable 10% premium over global endpoints.

This is not an optimisation; it is a compliance control with a price tag. The arithmetic is `0.1 × C`, and for Case A on Sonnet that is `$17,632 × 0.1 = $1,763/month`, about \$21,000 a year. The relevant comparison is not against zero but against the alternatives for the same residency requirement — a self-managed deployment, a regional cloud endpoint with its own 10%, or losing the contract. Against those, 10% is cheap, and the engineering question is only whether you can scope it: since it is a per-request parameter, apply `"us"` to the regulated workload rather than globally.

Check one thing before enabling it broadly: the multiplier applies to cache reads too, so a read-dominated long-context workload pays 10% on its largest line item. In Case B on Sonnet that is `$1.1178 × 0.1 = $0.112` per session, on the same order as the entire fresh-input line, and no cache-based trick avoids it.

## 3.11 A decision procedure

The chapter as an order of operations:

1.  **Estimate the cost of one bad output.** Everything else is conditional on this number. If you cannot estimate it, you cannot make this decision and should default to the most capable configuration you can afford.
2.  **Compute `monthly_spread / cost_of_one_bad_output`.** Far below 1 (Case C): stop optimising, buy capability, spend the time on evals. Far above 1 (Case A): continue.
3.  **Build the benchmark set** before touching a model string. Stratified, frozen, with a held-out slice, programmatically graded, sized from §3.9.
4.  **Sweep effort on the strongest candidate first.** Effort is often a better lever than the model, and a cheaper experiment.
5.  **Work the token arithmetic per candidate** using the §3.2 formula with your measured cache hit rate — not the hit rate you hope for. On Haiku, check the cliff.
6.  **Project TCO, not inference cost.** Inference plus `error_rate × volume × error_cost`.
7.  **If the tier gap is large and your gate can be calibrated, cost the cascade.** Check `p*`; it is usually generous. Check whether the escalated path breaks your p99 SLO.
8.  **Decide latency separately from cost.** Decompose into queue, prefill and generation, and apply the one lever that matches the dominant term. Streaming for humans; prefill reduction for machines; Fast mode only for long outputs with superlinear latency value.
9.  **Batch whatever can tolerate a day**, with a one-hour cache TTL, and re-derive the saving at your realistic batch hit rate rather than assuming 50%.
10. **Instrument so the next decision is cheaper.** Per-request model, effort, speed, all four token categories, latency percentiles and validator outcomes. The team with this data makes the next model decision in a day; the team without it repeats this entire chapter.

## Practice Questions

**V3.1** A workload sends 2,000,000 requests per month. Each request has a 6,000-token cacheable prefix with a measured 80% hit rate using 5-minute entries, 1,000 fresh tokens, and 200 output tokens. An engineer proposes switching the prefix to one-hour cache entries, which raises the hit rate to 97%. Using a model whose base input rate is `p` and cache read multiple is 0.1x, what happens to the monthly input-side cost attributable to the prefix?

A. It falls, because the reduction in write volume outweighs the higher write multiplier. B. It stays within 1%, because write and read multipliers offset exactly. C. It rises, because the 2x write multiplier applies to all cached tokens. D. It cannot be determined without knowing the output rate.

**V3.2** A Haiku 5.5 request consists of a 94,000-token cached prefix, 4,000 fresh tokens, and a 2,000-token output. A new compliance requirement adds an 8,000-token static disclaimer to the system prompt, which will also be cached and will hit reliably. What is the primary cost consequence?

A. Negligible, since the disclaimer is cached and cache reads are billed at 0.1x. B. The entire request moves to the \>100K tier, multiplying every token category’s rate by 5. C. Only the 8,000 added tokens are billed at the higher tier rate. D. The cache write multiplier increases from 1.25x to 2x because the prefix exceeded 100K.

**V3.3** You are comparing a candidate model against an incumbent on a frozen 500-item benchmark, running both on the same items. The candidate is correct on 31 items the incumbent got wrong; the incumbent is correct on 14 items the candidate got wrong. The two models agree on the remaining 455 items. Which statement best describes what you can conclude?

A. Nothing, because 45 informative items is far below the \~370 per arm required for a 3-point difference. B. The candidate is better, but only if the 455 agreements are also counted as evidence. C. The comparison is invalid because paired designs cannot establish significance. D. McNemar’s statistic on the 45 discordant items is about 5.7, which exceeds 3.841, so the candidate is better at the 5% level.

**V3.4** A cascade uses a cheap stage costing \$0.00040 per request and an expensive stage costing \$0.00250 per request, with a routing overhead of \$0.00002 per request. Above what escalation fraction does the cascade cost more than sending all traffic to the expensive model?

A. About 83% B. About 84% C. About 16% D. About 94%

**V3.5** Your agentic pipeline fans out each user request into 15 independent model subcalls and returns only when all 15 complete. A single subcall has p50 latency of 1.8 s and p99 of 7.5 s. Which conclusion is best supported?

A. The aggregate p50 will be close to 1.8 s because the calls run in parallel. B. The aggregate p99 will be close to 7.5 s because the calls run in parallel. C. Roughly 14% of aggregate requests will exceed 7.5 s, so a timeout sized on the single-call p99 is too tight. D. Hedging the slowest subcall cannot help, because the join requires all 15 results.

**V3.6** A team migrates a production service from Opus 5 to Opus 5.5 by changing only the model string. Quality on their internal rubric drops noticeably. Their request body includes `thinking: {"type": "adaptive"}` and no `output_config`. What is the most likely cause?

A. Opus 5.5 is less capable than Opus 5 on rubric-graded tasks. B. Omitting `effort` now yields `medium` rather than `high`, so the request runs one level lower. C. The dateless model ID floated to a newer snapshot with different behaviour. D. `thinking: {"type": "adaptive"}` is not supported on Opus 5.5 and is silently ignored.

**V3.7 (Select TWO)** A long-context assistant keeps a 200,000-token cached corpus and serves 30 turns per session. You are deciding between a mid-tier and a top-tier model. Which two factors most increase the relative affordability of the top-tier model in this workload?

A. The top-tier model’s deeper cache-read multiple compresses the price gap on the dominant token category. B. Long context carries no per-token premium on current non-Haiku models, so the corpus bills at standard rates on both. C. Cache write multipliers are lower on top-tier models, reducing the cost of the initial write. D. Read-dominated sessions shift spend away from fresh input, where the headline price ratio applies in full. E. The Batch API discount is larger on top-tier models, offsetting their base rates.

**V3.8** A Haiku 5.5 extraction task uses a 130,000-token prompt and a 3,000-token output. Outputs fail schema validation 70% of the time and are retried until they pass. Sonnet 5.5 passes on the first attempt. Using Table 3.1, which is cheaper per accepted output and by roughly what factor?

A. Haiku, by about 4x B. Sonnet, by about 1.2x C. Haiku, by about 1.2x D. They are within 1% of each other

**V3.9** You need to process a 300,000-token corpus on Haiku 5.5. Each of six 50,000-token chunks must also carry a shared 55,000-token reference document. Compared with sending one 300,000-token request, what is the effect of the chunked design?

A. It is more expensive, because each chunk exceeds 100K and pays the 5x rate six times. B. It is about 6x cheaper, because each chunk is well under the 100K threshold. C. It is about 5x cheaper, because the reference document is cached across chunks. D. Cost is unchanged, because total token volume is what is billed.

**V3.10** A real-time classification workload achieves a 96% cache hit rate on a 5,000-token prefix with 5-minute entries. Moved to the Batch API, the hit rate falls to 55% with 5-minute entries. Variable input is 400 tokens and output is 80 tokens. Which statement is most likely true?

A. Batch is exactly 50% cheaper, because the discount applies to all token categories. B. Batch is cheaper by less than 50%, because cache reads are not discounted in batch. C. Batch is more expensive, because the Batch API does not support prompt caching. D. Batch may be no cheaper or even more expensive, because tokens moved from the 0.1x read column to the 1.25x write column.

**V3.11 (Select TWO)** Which two statements about Fast mode are correct?

A. It raises time-to-first-token proportionally to the throughput gain. B. Switching a request between fast and standard speed invalidates the prompt cache. C. It can be combined with the Batch API to stack discounts against the premium. D. It changes model weights, so quality must be re-benchmarked. E. Its cost-per-minute-saved improves as output length grows.

**V3.12** A triage service handles 5,000,000 requests per month. Model X costs \$0.00018 per request with a 5% error rate; Model Y costs \$0.00190 per request with a 2% error rate. At what per-error cleanup cost are the two equal on total cost of ownership?

A. About \$0.0057 B. About \$0.0573 C. About \$0.115 D. About \$0.344

**V3.13** You want to measure whether stepping from `high` to `max` effort improves accuracy on your task. You run 80 items at each level and observe 91.3% at `high` and 93.8% at `max`. What is the correct conclusion?

A. `max` is better; adopt it and absorb the cost. B. The 2.5-point difference is smaller than the roughly ±6-point confidence half-width at n=80, so no conclusion is supported. C. `high` is better, because the extra cost of `max` is not justified by 2.5 points. D. The comparison is invalid because effort levels cannot be compared on the same item set.

**V3.14** An engineer adds streaming to a backend service in which a downstream component parses a complete JSON object before acting. Measured p99 end-to-end latency does not improve. Why?

A. Streaming increases total latency because of per-chunk overhead. B. Streaming only works when `output_config.effort` is set to `low`. C. Streaming is incompatible with structured output, so it was silently disabled. D. Streaming changes when the first token arrives, not when the last one does, and the consumer needs the last one.

**V3.15 (Select TWO)** A cascade escalates 20% of traffic from a cheap to an expensive stage. The cheap stage has p50 latency 350 ms, the expensive stage 2,900 ms. Which two statements are correct?

A. The cascade’s p99 improves because 80% of traffic never reaches the expensive stage. B. The cascade cannot break a p99 SLO, since no request is slower than the expensive stage alone. C. Mean latency improves to roughly 930 ms, a large gain over expensive-only. D. The escalated path takes about 2,900 ms, exactly matching expensive-only. E. Percentiles above roughly the 80th are worse than they were under expensive-only.

**V3.16** A shadow comparison mirrors 4% of a 10,000,000-request-per-month workload to a candidate model costing \$0.00310 per request. Production runs on a model costing \$0.00021 per request. Which statement about this setup is most accurate?

A. The shadow costs about \$1,240/month against production’s \$2,100, and the sample rate is far higher than needed to reach a few hundred paired items. B. The shadow costs about \$31,000/month, which is unavoidable if you want statistical power. C. Shadow cost equals production cost, because the same requests are sent to both models. D. Shadow cost cannot be estimated until the candidate’s cache hit rate is known.

**V3.17** A Haiku 5.5 request currently totals 97,500 input tokens and is in tier 1. Product wants to add a feature requiring 5,000 more prompt tokens. Which framing best captures the cost decision?

A. The addition raises cost by about 5%, proportional to the token increase. B. The addition is free because the new tokens will be cached. C. The 5,000 tokens carry an effective marginal rate far above any published per-MTok rate, because they reprice the entire request. D. Cost rises 5x only for the 5,000 added tokens; the first 97,500 stay in tier 1.

**V3.18** Your team pins production to `claude-sonnet-4-6` and a colleague argues you should switch to a dated ID “for safety, since dateless IDs float.” What is the correct response?

A. They are right; dateless IDs resolve to the latest snapshot and should be avoided in production. B. They are right for 4.6+ models but wrong for pre-4.6 models. C. Both forms float, so neither offers pinning and only a proxy-level lock helps. D. From 4.6 onward a dateless ID maps to a single fixed snapshot; pre-4.6 undated strings are the ones that float.

**V3.19 (Select TWO)** You must choose escalation triggers for a cascade whose cheap stage costs 1/20th of its expensive stage. Which two choices are best supported by the economics and reliability characteristics described?

A. A model’s self-reported confidence score used without threshold fitting, because it is cheapest. B. Hard signals such as schema-parse and validator failures, which have essentially no false positives. C. Self-consistency over three cheap samples, since 3x the cheap stage remains far below the expensive stage’s cost. D. Escalating a fixed random 15% of traffic, to guarantee predictable spend. E. Routing purely on input length, because it avoids running the cheap stage at all.

**V3.20** A contract-analysis workload runs 300 requests per month. The cheapest viable configuration costs \$0.14 per request and the most capable costs \$1.35. A single missed material risk is estimated to cost €20,000. What does the chapter’s decision procedure recommend?

A. Build a cascade so most requests take the cheap path. B. Choose the most capable configuration your evals support and spend the engineering effort on eval coverage. C. Choose the cheapest configuration and add a validator loop. D. Batch the workload to halve the cost of the capable configuration.

**V3.21** A Haiku 5.5 workload and a Sonnet 5.5 workload process identical token counts, both with prompts above 100,000 tokens. Which statement is true?

A. Haiku remains exactly 4x cheaper on every billed category, so the tier change does not reverse the ordering. B. Haiku becomes more expensive than Sonnet on output but remains cheaper on input. C. The ordering reverses entirely above 100K tokens. D. The comparison depends on the cache read multiple, which differs between the two tiers.

**V3.22 (Select TWO)** A batch job of 60,000 requests is submitted with a 5-minute cache TTL and no `custom_id` values assigned by the caller. Which two problems should you expect?

A. Cache hit rates will be poor because batch queueing delays frequently exceed a 5-minute TTL. B. The batch will be rejected because it exceeds the 100,000-request limit. C. Any malformed `params` will surface immediately at submission time, blocking the batch. D. Results cannot be reliably matched back to inputs, because batch results return in arbitrary order. E. Expired requests will still be billed at the full standard rate.

**V3.23** Your p99 latency regressed from 4.1 s to 9.8 s with no code change. Your telemetry records only end-to-end wall time per request. What is the most useful next step?

A. Enable streaming, which will reduce p99. B. Lower `output_config.effort` by one level and redeploy. C. Decompose the measurement into queue, prefill and generation by recording TTFT, output tokens, OTPS and cache-hit state per request. D. Enable Fast mode, which addresses queueing and prefill.

**V3.24 (Select TWO)** An `inference_geo: "us"` requirement lands on a read-dominated long-context workload. Which two statements are correct?

A. Switching to one-hour cache entries avoids the multiplier on read tokens. B. Setting `inference_geo` on a pre-4.6 model is a safe no-op fallback. C. The 1.1x multiplier applies to cache reads as well as input, output and writes, so the dominant line item is affected. D. Because `inference_geo` is a per-request parameter, you can scope the 1.1x to only the regulated slice of traffic. E. Regional endpoints on partner clouds avoid the premium entirely.

**V3.25** A `claude-sonnet-4-5-20250929` deployment receives a deprecation notice on 2026-09-30 with retirement on 2026-11-30. The team plans to spend the first five weeks deciding whether migrating is worthwhile. What is the strongest objection?

A. Deprecated models stop working immediately, so there is no window at all. B. The 60-day notice is a soft target and retirement commonly happens earlier. C. Migration is a model-string change, so five weeks of deliberation is harmless. D. The window is only 61 days and must cover benchmarking, a shadow run long enough to reach adequate paired sample size, prompt and effort adjustments, and a staged rollout.
