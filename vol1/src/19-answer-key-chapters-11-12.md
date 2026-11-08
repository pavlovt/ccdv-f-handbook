# Answer Key: Chapters 11–12

## Chapter 11

**Q11.1 — A.** Identity must come from the authenticated session and be enforced by the executor, so the model has no way to supply another customer’s ID. Option B is the tempting one, but a louder prompt is still a request the model can be talked out of, and test failures already show it is not holding.

**Q11.2 — C.** SQL has a structural fix (parameterization) that gives code and data separate channels. Models consume everything as one token stream, so no equivalent guarantee exists. Option B describes attacker convenience, not the root cause.

**Q11.3 — D.** Indirect injection arrives inside third-party content the agent processes for a legitimate user. Option A is direct injection, and the others are misuse or a credential leak, not injection through processed content.

**Q11.4 — C.** A key in client code can be extracted no matter how it is obfuscated, so a backend must hold it, authenticate users and enforce quotas. Option A fails because a client-side domain check runs in the attacker’s environment; option B shortens exposure but leaves the key public.

**Q11.5 — B.** An allowlist enforced in the tool executor holds even if the model is fully manipulated. Options A and C are prompt-level defenses that reduce probability only, and D is probabilistic and depends on detecting every malicious PDF.

**Q11.6 — D.** Full-prompt logs copy sensitive user data into a broadly accessible, long-lived store that is hard to purge on deletion requests. Cost and latency are real but minor next to the privacy exposure.

**Q11.7 — A.** A confirmation that lives only in the conversation is model behavior, and injected or mistaken output can skip it or fabricate approval. The application should require an approval it controls, showing the concrete action. Option B is a UX argument, not a security one.

**Q11.8 — B.** Filtering in the retrieval query with the session’s tenant ID keeps other tenants’ data out of the context entirely. Options A, C and D all leave foreign data in the context and rely on the model to ignore it, which is the original flaw.

**Q11.9 — D.** Model output is untrusted, so constrain it to enumerated commands and allowlisted targets and avoid shell interpretation by using argument arrays. Option A asks the model to sanitize, which is not enforcement, and D detects abuse only after it has happened.

**Q11.10 — A.** A refusal from the screening model signals the input is harmful, so it should count as a failed screen and return your fixed response. Retrying (C) or passing through (B, D) lets exactly the inputs you meant to block reach the main model.

**Q11.11 — C.** Production practice layers defenses, monitors flagged traffic and acts on abusive accounts, which only your application can do. Option B is the tempting one, but keyword blocklists are defeated by paraphrase and encoding.

**Q11.12 — B.** Breaking the combination of private data, untrusted content and an outbound channel shrinks the worst-case outcome structurally. Options A and C are prompt-level hardening, and D is irrelevant to the risk.

**Q11.13 — A.** Untrusted content belongs in a tool result, delimited, with the system prompt stating its status and your own instructions kept outside the result. Placing it in the system prompt (B) elevates attacker text to the highest authority.

**Q11.14 — C.** Image-based exfiltration is closed by controlling rendering in code, for example by allowlisting or proxying image hosts. Option A is tempting but a manipulated model will ignore it; C and D have no bearing on the channel.

**Q11.15 — B.** A database role without billing access still holds if the model is fully compromised, which is the test for a real control. Options A and D rely on model behavior, and B is a probabilistic detector that misses some cases.

## Chapter 12

**Q12.1 — A.** Non-deterministic output calls for evaluation across many cases, with graders matched to each property. Option B is tempting, but even at temperature 0 exact match tests fail on harmless wording differences and give no insight into quality.

**Q12.2 — B.** Success criteria and a representative eval set come before the prompt so changes can be judged. Option A tests on invented, tidy examples and has no way to measure improvement.

**Q12.3 — C.** Repeated tuning against the same visible set overfits it, and the gap to production shows it. A held-out set refreshed with real samples gives an honest estimate. Option D is backwards, since larger sets reduce overfitting risk.

**Q12.4 — C.** Tone is a subjective property that a rubric-driven judge handles at scale, provided it is calibrated against human ratings. Keyword checks like option B are cheap but easy to satisfy without being empathetic.

**Q12.5 — D.** Length bias is a known judge weakness, so probe it with weak long answers, fix the rubric and verify against human labels. Option C abandons scalability when calibration would suffice.

**Q12.6 — A.** Aggregate gains can hide a serious drop in a critical segment, so per-category comparison should gate the release. Option B is the tempting one, but it ignores that the failing segment carries the most business value.

**Q12.7 — B.** The change violates the stated latency bound and costs far more, so look for cheaper routes to the same quality. Option C hides the tail that users feel, and D changes the criteria to fit the result.

**Q12.8 — D.** Inspect what the model actually received, then substitute ideal context to split retrieval faults from prompt or model faults. Options A and C change things before locating the layer at fault.

**Q12.9 — A.** The symptoms, malformed arguments and an unhelpful tool error, point to the tool layer: schemas, descriptions, validation and readable errors. Upgrading the model (B) is the tempting guess, but it does not fix a stack trace the model cannot act on.

**Q12.10 — B.** Sticky assignment, a predefined primary metric, guardrail metrics, variant-tagged logs and gradual ramping after offline evals make a sound test. Option A causes inconsistent per-user behavior, and C compares across time periods, which confounds the result.
