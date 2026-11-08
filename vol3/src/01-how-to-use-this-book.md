# How to Use This Book

This volume is twelve full-length CCDV-F practice exams and nothing else. No teaching, no reference material — Volumes I and II carry those. What you have here is 636 questions, every one of them written to the real exam’s domain blueprint, with complete answer keys.

## What each exam looks like

Every exam is 53 questions in 120 minutes, matching the real thing, and every one distributes its questions the same way:

  Domain                             Questions per exam
  ---------------------------------- --------------------
  Applications and Integration       18
  Model Selection and Optimization   9
  Agents and Workflows               8
  Prompt and Context Engineering     6
  Tools and MCPs                     5
  Security and Safety                4
  Claude Code                        2
  Eval, Testing, and Debugging       1

Within each exam, 44 questions are single-answer and 9 are multiple-response, marked “(Select TWO)” or “(Select THREE)”.

## The twelve exams

Each exam is set in a different world. This is deliberate: twelve exams drawn from the same handful of scenarios would teach you those scenarios rather than the underlying engineering. A candidate who can reason about prompt caching in a document pipeline, a chat assistant, a nightly batch job and a latency-critical mobile backend understands caching. One who has only seen it in a document pipeline understands document pipelines.

  \#   Setting                                Tier
  ---- -------------------------------------- ----------
  1    Document processing at scale           Entry
  2    Conversational systems                 Entry
  3    Batch and pipeline workloads           Middle
  4    Developer tooling and code agents      Middle
  5    Regulated and high-assurance systems   Hard
  6    Scale and latency                      Hard
  7    Commerce and catalogue systems         Middle
  8    Content operations at volume           Middle
  9    Enterprise knowledge and retrieval     Hard
  10   Multimodal and document systems        Hard
  11   Research and analytical systems        Hardest
  12   Migration and modernisation            Capstone

Every exam in this book is harder than the real CCDV-F. That is the point of a practice exam: one you have over-prepared for leaves you calm on the day, one you have exactly prepared for does not. Expect roughly 70–80% on the entry tier, 60–70% in the middle, and 50–60% on the hard tier if you are genuinely ready to sit the certification.

Do not read a score here as a predicted exam result. Read it as a map of what you do not yet know.

## A suggested order

Do not work through all twelve back to back. Spaced over a fortnight or more, with reading between them, they are worth several times what they are worth in a weekend.

1.  **Exam 1**, untimed and open-book, to see the shape of the questions.
2.  **Exams 2–4**, timed and closed-book, one every few days. Re-read the weak domains between attempts.
3.  **Exams 5–8** once the middle tier stops producing surprises.
4.  **Exams 9–11** in the week before the real exam, strictly timed.
5.  **Exam 12** last. It is the capstone, drawing on all eight domains at once, and makes a good final rehearsal.

## Sitting an exam properly

Set a 120-minute timer and honour it. Close the documentation, close Volumes I and II, and put your phone away — the real exam is proctored and closed-book, and practising under easier conditions trains a skill you cannot use on the day.

Write your answers down separately rather than marking the book, so you can re-sit an exam months later without seeing your old attempt.

Flag every question you guessed, even the ones you got right. A lucky guess is a gap that the real exam will find.

## The answer keys

All twelve keys sit together at the back, after the last exam. Attempt a full exam before opening any of them.

Each entry gives the correct option, the domain it tests, and an explanation covering both why the answer is right and why the most tempting wrong option fails. For calculation questions, the arithmetic is worked in full.

The explanation of the attractive wrong answer is usually the more valuable half. Those distractors are built from real mistakes engineers make in production, not from invented errors, and recognising why one appealed to you is worth more than memorising the right letter.

Each key ends with a per-domain scoring table. Fill it in. Across several exams the pattern in those tables tells you far more than any single score — the closing chapter explains how to read it.

## A note on one figure

Several questions involve the number of tokens the tool-use system prompt adds to a request, using 286 tokens for `tool_choice` of `auto` or `none` and 406 for `any` or `tool`.

Treat those as given constants supplied by the question, not as facts to memorise. During compilation one research pass reported them as documented and two later passes could not find them on any current Anthropic page; third-party write-ups cite a different figure again. The arithmetic inside each affected question is internally consistent and the reasoning it tests — that forcing tool choice costs extra context on every request, that the overhead is per-request rather than per-tool, and that at volume it is a real line item — is sound regardless of the exact constant.

Rewriting that arithmetic across every affected question would have risked introducing worse errors than the uncertainty it removed, so the figures stand with this disclosure instead. If a real exam question turns on the precise number, take it from that question’s own stem.

## What this book is not

It was compiled from public documentation, not from Anthropic’s official Exam Guide v1.0, which sits behind the partner login. The domain weights come from third-party sources. These questions are original work calibrated against the published blueprint; they are not retired exam items and no one outside Anthropic has seen the real ones.

API details also change. Where the current documentation has moved past what a July 2026 exam guide would contain — deprecated sampling parameters, the shift from prefill to first-class structured output, forced tool choice now returning an error — these exams follow the convention of the earlier volumes and test the reasoning rather than the version-specific detail, flagging the version where it matters. Verify anything load-bearing against platform.claude.com before you rely on it in production.
