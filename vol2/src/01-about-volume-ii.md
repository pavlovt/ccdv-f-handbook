# About Volume II

Volume I covered the whole CCDV-F blueprint — all eight domains, in proportion to their exam weight. This volume does something narrower and deeper.

Three domains decide whether you pass:

  Domain                             Share of exam
  ---------------------------------- ---------------
  Applications and Integration       33.1%
  Model Selection and Optimization   16.8%
  Agents and Workflows               14.7%
  **Combined**                       **64.6%**

Get these three right and the remaining 35% rarely decides the outcome. Get them wrong and no amount of Claude Code trivia rescues the score.

This volume assumes you have read Volume I and does not repeat it. Where Volume I explained what prompt caching is, this one works out the arithmetic of when a cache write pays for itself. Where Volume I showed the shape of an agent loop, this one builds one with budget enforcement, cancellation and failure policy, and analyses why cost grows superlinearly with turn count.

## How the difficulty is pitched

The questions here are harder than the real exam, deliberately. Many require a calculation from figures in the stem. Many present a design that looks reasonable and ask what is wrong with it. In several, every option is a true statement and only one addresses the actual problem.

That is the point. An exam you have over-prepared for feels calm; one you have exactly prepared for does not.

The advanced mock exam in the final chapter is narrower than the real thing — 60 questions across three domains instead of 53 across eight. Treat its score as a depth diagnostic, not a predicted exam result.

## A standing caveat

Everything in Volume I’s limitations section still applies. This was built from public documentation rather than the official Exam Guide v1.0, which sits behind the partner login. API details change; verify anything load-bearing against platform.claude.com before you rely on it in production.

Where the current documentation has moved past what a July 2026 exam guide would contain — deprecated sampling parameters, the shift from prefill to first-class structured output, forced tool choice now returning 400 — this volume follows Volume I’s convention of teaching both, labelled by version. An exam question assuming the older behaviour is testing the older API, not making a mistake.
