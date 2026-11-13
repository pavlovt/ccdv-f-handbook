# Before You Begin

This book prepares you for CCDV-F, the Claude Certified Developer – Foundations exam. It is written for engineers who build production applications on Claude. Read this chapter in full before you spend money or schedule anything. The eligibility rules decide whether the rest of the book is useful to you right now.

## What the certification is

The Claude Certification Program has four certifications:

-   Claude Certified Associate – Foundations
-   Claude Certified Developer – Foundations (CCDV-F, the subject of this book)
-   Claude Certified Architect – Foundations
-   Claude Certified Architect – Professional

The names are close. Confirm the exam code, CCDV-F, on the registration page before you pay. Do not rely on a name you remember.

CCDV-F tests whether you can build with the Claude API in production code. That covers making Messages API calls correctly, streaming and caching responses, requesting structured output, handling failures, choosing and configuring a model, designing tool use and agent workflows, engineering prompts and context, integrating MCP servers, applying security controls, and evaluating and debugging the results. It assumes you write code daily, have called a REST API, and can read JSON. It does not test model training, research methods, or chat-only use of Claude.

## Eligibility: check this first

Exam registration and the official prep course are gated to people employed by an organization in the Claude Partner Network (CPN). The gate works like this:

-   You must register with a company email address on a recognized domain. Personal addresses such as Gmail will not work.
-   You must be 18 or older. Your identity is verified against a government ID.
-   Domain linking, which connects your company email domain to the partner program, takes 7–10 days via partner-support\@anthropic.com.

Find your situation in the table below and act on it before anything else.

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Your situation                                                                  What it means                          What to do
  ------------------------------------------------------------------------------- -------------------------------------- -----------------------------------------------------------------------------------------------------
  Employed by a CPN organization, company email on a recognized domain            You are eligible                       Register. If your domain is not yet linked, request linking now, because it takes 7–10 days

  Employed by a company that is not a CPN member                                  You cannot register through the gate   Study with the free Anthropic Academy. Ask your employer whether it plans to join CPN

  Freelance, self-employed, student, or career-switching, with a personal email   You cannot register                    Study with the free material. Revisit the question once you have a company affiliation

  Work email on a domain the program does not recognize                           Registration fails the domain check    Ask your employer’s administrator whether the domain can be linked, and allow the 7–10 day timeline
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Do not try to work around the gate with a personal address or someone else’s company account. The gate exists to confirm identity and affiliation. A workaround puts the registration at risk.

Because the official prep course is also gated, this book is written to be usable without it. Everything in it is drawn from public documentation. The most useful free resource for anyone is the Anthropic Academy. It is open to any email address and has around 21 free courses, including developer deep-dives on the API, MCP, and Claude Code. The Resources appendix lists the links.

## Exam mechanics

  ---------------------------------------------------------------------------------------------------------------------
  Item                                Detail
  ----------------------------------- ---------------------------------------------------------------------------------
  Exam code                           CCDV-F

  Question types                      Multiple choice, and scenario-based multiple response

  Questions                           53

  Testing time                        120 minutes

  Total seat time                     About 135 minutes, including check-in and the survey

  Scoring                             Scaled score from 100 to 1000. 720 is a pass

  Price                               \$125 USD before any partner-tier discount

  Delivery                            Pearson VUE, either online-proctored (OnVUE) or at a test center

  Conditions                          Closed book. No notes, no documentation, no AI assistants, no translation tools

  Validity                            12 months from passing

  Renewal                             Free, non-proctored assessment

  Retake waits                        14 days after a first fail, 30 days after a second, 90 days after a third

  Attempt limit                       4 attempts per rolling 12 months

  On passing                          A Credly digital badge

  Registration validity               5 years once purchased

  Name rule                           The name on your Pearson VUE profile must match your government ID exactly
  ---------------------------------------------------------------------------------------------------------------------

Three points in this table affect how you plan.

**Pacing.** 120 minutes for 53 questions is about 2.3 minutes per question. Aim for roughly two minutes per question. That uses about 106 minutes and leaves around 14 for a final pass on items you flagged. Scenario-based multiple response items describe a situation and ask you to select more than one answer. Read the full stem and every option. Do not stop at the first answer that looks right when the item asks for several.

**Scoring.** A scaled score is not a percentage. Your raw result is converted onto the 100–1000 scale, and the conversion can differ from one version of the exam to another, so the number of correct answers that equals 720 is not published and is not fixed. Do not try to work out a raw pass mark from practice scores. Aim instead for consistent accuracy, well above guessing, in every domain.

**Name and cancellation.** A name correction must be requested at least 24 hours before your appointment, through certifications-support\@anthropic.com. Corrections take 24–48 business hours, so a late request may not finish in time. You may reschedule or cancel free of charge up to 24 hours before the appointment. Inside that window, or if you do not show up, the fee is forfeited.

## Domain weights

The exam is organized into eight domains. The weights below come from the Exam Guide v1.0 (July 2026) as reported publicly by third parties. They are not taken from the guide itself. Verify them against the official guide, which sits behind the partner login, before you rely on them for planning.

  Domain                             Weight   Book chapters
  ---------------------------------- -------- ---------------
  Applications and Integration       33.1%    3, 4, 5
  Model Selection and Optimization   16.8%    6
  Agents and Workflows               14.7%    7
  Prompt and Context Engineering     11.0%    8
  Tools and MCPs                     10.6%    9
  Security and Safety                8.1%     11
  Claude Code                        3.1%     10
  Eval, Testing and Debugging        2.6%     12

The weights total 100.0%. Nearly a third of the questions come from one domain, so Chapters 3 to 5 deserve the most attention. Chapters 1, 2, and 13 are not mapped to a domain. Chapter 2 underpins all the others, and Chapter 13 is the final check.

## How to use this book

-   Each chapter covers its concepts, works through examples, and ends with practice questions.
-   The answers to all practice questions are collected in the Answer Key at the back, not printed under the questions. Attempt each question without looking ahead. Looking ahead teaches you less, and the exam will not show you the answer.
-   Mark the questions you guessed, not just the ones you got wrong. A guessed correct answer is a gap that will cost you on the exam.
-   Chapter 13 is a full-length mock exam of 53 questions in 120 minutes, closed book. Take it in one sitting under exam conditions. Then review every miss against the chapter it came from.
-   The Glossary defines the terms used across the book. Use it as a checklist. If you cannot define a term in one sentence, go back to the chapter that introduces it.
-   Code examples use the Messages API and current SDK patterns. Check the documentation before you copy any code into production.

## Study plan

The official estimate is 40 to 80 hours of study. The table below assumes 60 hours and gives a range for each chapter. For a 40-hour plan, use the low end of each range. For an 80-hour plan, use the high end.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Chapter        Topic                                                       Domain weight                      Suggested hours (60-hour plan)   Range (40–80 hours)
  -------------- ----------------------------------------------------------- ---------------------------------- -------------------------------- ---------------------
  1              Before You Begin                                            Not mapped                         1                                1

  2              How Claude Works                                            Foundation                         2                                1–3

  3              The Messages API                                            Applications and Integration       6                                4–8

  4              Streaming, Caching, and Batching                            Applications and Integration       5                                3–7

  5              Structured Output, Multimodal Input, and Failure Handling   Applications and Integration       6                                4–8

  6              Choosing and Optimizing a Model                             Model Selection and Optimization   9                                6–12

  7              Agents and Workflows                                        Agents and Workflows               8                                5–11

  8              Prompt and Context Engineering                              Prompt and Context Engineering     6                                4–8

  9              Tools and the Model Context Protocol                        Tools and MCPs                     6                                4–8

  10             Claude Code                                                 Claude Code                        2                                1–3

  11             Security and Safety                                         Security and Safety                4                                3–5

  12             Evaluation, Testing, and Debugging                          Eval, Testing and Debugging        2                                1–3

  13             Full-Length Mock Exam                                       Whole exam                         3                                2–4
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------

Chapters 1, 2, and 13 take 6 of the 60 hours. The remaining 54 follow the domain weights, with two adjustments. Chapters 3 to 5 and Chapter 11 get slightly less time than their weights suggest, because their concepts reappear in Chapters 6 to 9 and in the mock. If the Messages API is new to you, add time to Chapter 3 first. Chapter 10 is light because Claude Code is 3.1% of the questions.

## Build two projects alongside the reading

Reading alone is not enough for this exam. Questions describe production situations, and you answer them correctly only if you have hit the failure modes yourself. Build these two projects as you go. They are not in the table above, so budget roughly 8 to 15 hours for both on top of the chapter hours.

**Project A: an MCP server (Chapters 9 and 10).** Write a server using the stdio transport, so a client launches it as a subprocess and talks to it over stdin and stdout. Expose at least two tools with JSON schemas and one resource. Validate inputs. Return tool errors with `isError` set rather than crashing the server. Connect it to a client, then watch the initialization handshake and the tool listing in the logs.

**Project B: a multi-turn agent (Chapters 7 and 5).** Write a loop that calls the Messages API with a set of tools. Execute each `tool_use` block, return the results as `tool_result` blocks in the next user turn, and branch on `stop_reason`. Cap the number of iterations. Add a confirmation gate before any write action, so a human approves it. Log every turn, including token usage and stop reasons.

## Exam-day logistics

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Delivery                            What to prepare
  ----------------------------------- -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Online (OnVUE)                      A private room, a clear desk, a working webcam and microphone, and your government ID. Run Pearson VUE’s system test several days ahead, on the device you will use. Stay in view of the camera for the whole session

  Test center                         Check the address and the arrival time. Bring the government ID that matches your profile name exactly

  Both                                Closed book. No notes, documentation, AI assistants, or translation tools. Check-in and the survey count against the 135-minute seat time, so start early
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Limitations of this book

-   It is written from public documentation. It is not based on the official Exam Guide v1.0, which is behind the partner login. Where the guide and this book differ, the guide governs.
-   The domain weights are third-party sourced, as noted above.
-   The API changes. Model names, parameters, SDK syntax, pricing, and rate-limit behavior will drift. Verify every API detail against the current documentation at platform.claude.com before you rely on it.
-   The practice questions are written to test understanding. They are not drawn from the live exam, and they will not match its wording or difficulty exactly.
-   The study-hour estimates are a planning guide, not a promise. Your background decides how long each chapter takes you.
