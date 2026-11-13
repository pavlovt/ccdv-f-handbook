# Evaluation, Testing, and Debugging

This domain is a small part of the exam, so the chapter is compact. The core ideas are that you cannot assert exact outputs from a model, that you must decide what “good” means before you build, and that debugging means isolating which layer failed instead of rewording the prompt until something changes.

## Why Conventional Unit Tests Break

A traditional test pins an input to one correct output. Model output is non-deterministic in practice: sampling introduces variation, wording differs run to run even when meaning does not, and a prompt or model change can shift behavior in ways no single assertion captures. Pinning an exact string produces tests that fail constantly for irrelevant reasons and pass when quality is poor.

What replaces them is evaluation: a fixed set of representative inputs, a scoring method for each, and an aggregate metric compared across versions.

  --------------------------------------------------------------------------------------------------------------------
  Conventional test                   Evaluation
  ----------------------------------- --------------------------------------------------------------------------------
  One input, one expected output      Many inputs, a score distribution

  Pass or fail per case               Rate of success across the set

  Fails on any deviation              Tolerates harmless variation, flags real regressions

  Run at commit time, deterministic   Run on each prompt, model or retrieval change, repeated where variance matters
  --------------------------------------------------------------------------------------------------------------------

Unit tests still belong around the deterministic parts of your system: parsers, schema validators, tool executors, permission checks, retry logic. Test the code around the model conventionally and the model’s behavior statistically.

## Define Success Criteria First

Write down what success means before writing the prompt. Without it you cannot tell whether a change helped, and you will optimize for whichever examples you looked at last. Good criteria are specific, measurable, achievable and relevant to the application’s purpose.

Weak: “The classifier should work well.” Strong: “At least 90% label accuracy on the held-out set, fewer than 1% of outputs failing schema validation, p95 latency under 1.5 seconds, and under 0.5 cents per request.”

Most real applications need several criteria at once:

  -----------------------------------------------------------------------------------------------------
  Dimension                           Example criterion
  ----------------------------------- -----------------------------------------------------------------
  Task fidelity                       Correct category on at least 90% of cases

  Consistency                         Same ticket phrased three ways yields the same category

  Format                              100% of outputs parse against the schema

  Safety and privacy                  No PII in outputs; refusal on a defined set of harmful requests

  Tone                                Judged on-brand by a rubric

  Latency                             p95 under a stated bound

  Cost                                Under a stated amount per request
  -----------------------------------------------------------------------------------------------------

## Building an Eval Set

**Mirror reality.** The set should reflect the real distribution of inputs, including the ugly parts: typos, mixed languages, very long inputs, empty inputs, ambiguous requests where reasonable people disagree, off-topic and adversarial inputs. A set made only of clean, tidy examples will report success right up until launch.

**Sourcing cases.**

-   Real production traffic, sampled and anonymized (the strongest source, subject to the privacy rules in the previous chapter).
-   Domain experts writing hard cases and known past failures.
-   Bug reports: every production failure becomes a permanent test case.
-   Model-generated cases. A model can expand a seed set into variations, which is useful for volume but should be reviewed, since generated cases tend to be more uniform than real ones.

**Size.** Favor volume of automatically graded cases over a few lovingly hand-graded ones. There is no universal number; start with tens to get signal, move to hundreds for decisions between close alternatives, and size by how small a difference you need to detect. A rare failure class (say, 2% of traffic) needs enough examples of that class specifically, so stratify rather than relying on the overall count.

**Hold out a test set.** Split into a development set you iterate against and a held-out set you consult rarely. Every time you tweak a prompt to fix a visible failure, you fit it a little more to that set. The held-out score is your honest estimate of production behavior. If you peek and tune against it repeatedly, it stops being held out and you need a fresh one.

## Grading Methods

Choose the fastest, most reliable and most scalable method that actually measures what you care about.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Method                            Best for                                                                                                                                           Strengths                        Weaknesses
  --------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------- -------------------------------- -----------------------------------------------------------------------
  Exact or string match             Classification labels, extraction of fixed fields, multiple choice                                                                                 Fast, free, perfectly reliable   Brittle for free text; normalize case and whitespace

  Code-based assertion              Valid JSON, schema conformance, required fields, length limits, regex checks, “response mentions the order number”, unit tests on generated code   Deterministic, scalable          Cannot judge quality or nuance

  Embedding or overlap similarity   Paraphrase consistency, summarization against references                                                                                           Cheap, graded                    Measures similarity, not correctness; can reward fluent wrong answers

  LLM-as-judge                      Tone, helpfulness, faithfulness to source, rubric-based quality                                                                                    Flexible, scales to nuance       Needs validation; has biases; costs money

  Human review                      Calibrating judges, subjective or high-stakes domains, final launch checks                                                                         Highest quality                  Slow, expensive, inconsistent between raters
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### Making LLM judges trustworthy

-   Write a detailed rubric with concrete pass conditions, rather than asking “is this good?”
-   Ask for a constrained verdict (correct/incorrect, a 1-5 scale, a label) instead of open commentary.
-   Let the judge reason before it scores; a reasoning step improves accuracy on complex judgments. Parse the verdict from a delimited field.
-   Prefer a different model from the one that produced the output, to avoid favoring its own style.
-   Calibrate: have humans grade a sample, compare to the judge, and fix the rubric until agreement is acceptable. An unvalidated judge is just another unexamined prompt.
-   Watch for known biases such as preferring longer answers.

## Regression Testing

Every prompt edit, model upgrade, retrieval tweak, tool schema change or parameter adjustment is a code change and can regress behavior. Treat the eval set as your regression suite.

1.  Pin a baseline: the current prompt, model and settings with their scores on the full set.
2.  Make one change at a time, so you can attribute the effect.
3.  Rerun the full set, not just the cases you were trying to fix. Compare per-category, not just in aggregate; a gain of three points overall can hide a ten-point drop in a critical segment.
4.  Gate releases on thresholds for your success criteria, in CI where possible.
5.  When migrating models, run the same eval against both. Prompts tuned for one model often behave differently on another, and a newer model is not automatically better on your specific task.
6.  Add every new bug as a test case.

Where output varies run to run, repeat cases several times and look at the rate, not a single sample.

## Cost and Latency Alongside Quality

A change that improves accuracy by two points but triples cost may be the wrong change. Record, for every eval run:

  --------------------------------------------------------------------------------------------------
  Metric                                                     Why
  ---------------------------------------------------------- ---------------------------------------
  Input and output tokens per request                        Drives cost; shows prompt bloat

  Cost per request and per successful task                   Failures that need retries cost more

  Latency: time to first token and total, with p50 and p95   Averages hide the tail users notice

  Retry and error rate                                       Reliability signal

  Cache hit rate, if you use prompt caching                  Large effect on both cost and latency
  --------------------------------------------------------------------------------------------------

Compare candidates on the frontier: the cheapest and fastest configuration that meets the quality bar wins. Often a smaller model with a better prompt, or a smaller model for easy cases and a larger one for hard ones, meets the bar at a fraction of the cost. Only measurement tells you.

## Observability

In production you need enough information to reconstruct what happened without becoming a privacy liability.

  ------------------------------------------------------------------------------------------------------------------
  Log by default                                                  Avoid logging by default
  --------------------------------------------------------------- --------------------------------------------------
  Request ID and trace ID linking all calls in one task           Raw prompts and completions containing user data

  Tenant or user pseudonym, feature, prompt version, model        Credentials, tokens, secrets in tool arguments

  Token counts, latency, stop reason                              Full documents retrieved from private stores

  Tool calls: name, validated argument shape, duration, outcome   Unredacted personal data

  Retrieval: which document IDs were returned, with scores        

  Validation failures, refusals, guardrail triggers               

  User feedback signals (thumbs, edits, abandonment)              
  ------------------------------------------------------------------------------------------------------------------

For agentic flows, log each step of the loop as a span in a trace so you can see the sequence of model calls and tool calls. When content is needed for debugging, capture a small redacted sample under access controls and short retention. Record the prompt version with every request; without it you cannot connect a metric shift to a change.

## Debugging a Misbehaving Application

The common failure is to treat every bad output as a prompt problem and keep editing the wording. Isolate the layer first.

**Step 1: Capture the failing case exactly.** Get the full request as the model saw it: system prompt, history, retrieved context, tool definitions and results, parameters. Reproduce it, ideally several times to see whether the failure is consistent or occasional.

**Step 2: Locate the fault.**

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Layer                   Symptom                                                                                                             Test to isolate
  ----------------------- ------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------
  Context                 Answer is wrong because the needed fact is missing, stale or buried; or conflicting content is present              Read what was actually retrieved. Paste the ideal context by hand. If the answer is right, the retrieval or assembly is the bug.

  Prompt                  Context is fine, but the model misreads the task, ignores a format rule, or handles an edge case unspecified        Run the same context with a simplified or clarified prompt. Add an example. If behavior changes predictably, the prompt is the cause.

  Tool layer              Wrong tool chosen, malformed arguments, tool errors fed back as confusing text, results truncated                   Inspect the tool definitions and descriptions, the arguments emitted, and what your executor returned. Call the tool directly without the model.

  Model choice            Correct context, clear prompt, working tools, yet the task is beyond the model’s capability or too slow or costly   Run the identical request on a stronger model. If it succeeds, you have a capability gap and can choose between a better model or decomposing the task.

  Parameters or limits    Truncated output, odd randomness, ignored stop conditions                                                           Check `max_tokens`, stop reason, effort level, temperature (on older models that still accept it), and token budget.

  Your own code           Parsing errors, off-by-one in history assembly, dropped messages                                                    Unit test the deterministic code with the captured payload.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Step 3: Change one variable at a time** and rerun your eval set, not just the failing case, so that a fix does not move the problem elsewhere.

**Step 4: Add the case to the regression set.**

## A/B Testing Prompts in Production

Offline evals tell you whether a candidate is plausibly better. Production tests tell you whether it is better for real users and real outcomes.

-   **Randomize by user or session**, not by request, so a user does not see inconsistent behavior mid-conversation. Keep assignment sticky.
-   **Define the primary metric in advance**: task completion, escalation rate, edit distance on drafts, user rating, conversion. Add guardrail metrics such as error rate, refusals, latency and cost so a win on one cannot hide a loss on another.
-   **Start with a small exposure** and ramp up while watching guardrails.
-   **Tag every request with the variant** and prompt version in your logs.
-   **Run long enough** to cover weekly cycles and reach adequate sample size; avoid stopping at the first favorable reading.
-   **Do not skip the offline eval.** Production is for confirming, not for discovering that the candidate leaks data or breaks format.
-   **Plan rollback.** Prompt versions should be switchable by configuration so reverting does not require a deploy.

## Practice Questions

**Q12.1** A team writes unit tests that assert a summarization prompt returns an exact expected paragraph. The tests fail on about 40% of runs even though reviewers say the summaries are fine. What is the best fix?

A. Replace them with an eval over many cases using graders suited to the property being checked, such as a rubric-based judge for faithfulness and code checks for length and format. B. Set temperature to 0 and keep the exact-match assertions. C. Loosen the tests to accept any non-empty string. D. Run each test five times and require at least one pass.

**Q12.2** You are about to build a ticket-routing feature. Which of the following is the best way to start?

A. Write the prompt, try it on a few tickets you invent, and ship if it looks right. B. Define measurable criteria such as routing accuracy on a representative held-out set, latency and cost bounds, then build an eval set and a first prompt. C. Pick the largest available model to avoid needing evaluation. D. Wait for user complaints to learn what matters.

**Q12.3** After ten rounds of prompt tweaks guided by failures on your 150-case set, accuracy rose from 71% to 93%. Production accuracy is 80%. What is the most likely explanation and remedy?

A. Production has more traffic; add servers. B. The model degrades under load. C. The prompt overfit the visible set; evaluate on a held-out set not used during iteration, and refresh it with recent production samples. D. The eval set is too large.

**Q12.4** You need to grade whether chatbot answers adopt an empathetic, professional tone. Which grading approach is most appropriate to scale?

A. Exact string match against a reference answer. B. A regex looking for the words “sorry” and “thank you.” C. An LLM judge with a detailed rubric and constrained scores, validated against a sample of human ratings. D. Count characters per response.

**Q12.5** Your LLM judge gives high scores to every long answer, including padded ones. What is the best response?

A. Accept it; longer answers are usually better. B. Increase the judge’s temperature. C. Remove the judge and use human review for all cases. D. Test the judge with deliberately weak but long answers, tighten the rubric to penalize padding and compare against human labels, and consider a different judge model.

**Q12.6** You migrate from one model to a newer one. Aggregate eval accuracy rises by two points, but the “refund disputes” category, 5% of traffic with high business value, drops from 92% to 81%. What should you do?

A. Treat the regression as a release blocker for that segment, investigate prompt or model behavior on those cases, and adjust before shipping. B. Ship, since the aggregate improved. C. Remove the refund category from the eval set. D. Ship and revisit if customers complain.

**Q12.7** A change improves quality by three points but increases mean cost per request by 180% and p95 latency from 1.2s to 4.5s. The success criteria set a latency bound of 2s. What is the best course?

A. Adopt it because quality is the main goal. B. Reject it as specified, then look for cheaper ways to reach the target, such as a smaller model with improved prompting or routing only hard cases to the larger configuration. C. Report average latency instead of p95. D. Remove the latency criterion.

**Q12.8** A retrieval-augmented assistant gives wrong answers on a specific question. Which first step is the best way to locate the fault?

A. Rewrite the system prompt to say “be accurate.” B. Increase `max_tokens`. C. Switch immediately to the strongest model. D. Capture the exact request and inspect the retrieved context; then supply the ideal context by hand to see whether the answer becomes correct.

**Q12.9** An agent frequently calls a search tool with malformed arguments, and the executor returns a stack trace as the tool result. The model then loops. Which diagnosis fits best?

A. A tool-layer problem; improve the tool schema and description, validate arguments, and return concise actionable error messages. B. A model capability limit; upgrade the model. C. A temperature problem; set it to zero. D. A logging problem; log more.

**Q12.10** You want to compare two prompt variants in production for a drafting assistant. Which design is most sound?

A. Alternate variants request by request for each user. B. Randomly assign users sticky to a variant, predefine a primary metric and guardrail metrics for cost, latency and error rate, tag logs with the variant, and ramp gradually after passing offline evals. C. Deploy variant B to everyone and compare to last month’s numbers. D. Test on internal staff only and decide on opinion.
