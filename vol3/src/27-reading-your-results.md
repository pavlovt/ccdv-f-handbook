# Reading Your Results

A score tells you little. The pattern across several exams tells you almost everything.

## Build the grid

Transfer each exam’s per-domain table into a single grid: twelve rows, eight columns, percentage correct in each cell. Four or five exams in, the grid starts to say things a single score never could.

Read it two ways.

**Down a column.** A domain that is weak in every exam is a knowledge gap — you do not know the material, and no amount of further practice will fix it. Go back to the relevant chapters.

**Across a row.** A domain that is fine in most exams but collapses in one or two is not a knowledge gap. It is a *context* gap: you know the mechanism but cannot apply it in an unfamiliar setting. That is a different problem with a different fix, covered below.

## Weight by domain size

Applications and Integration is 18 questions; Eval, Testing and Debugging is one. Losing 30% of Applications costs you five or six marks. Losing the single Eval question costs you one. Candidates routinely over-invest in small domains because a percentage looks alarming in isolation.

A quick way to see the real cost: multiply the proportion you got wrong by the number of questions in that domain, and rank the domains by that figure. That ranking, not the percentage, is your study order.

  Domain                             Questions   Losing a third costs
  ---------------------------------- ----------- -----------------------
  Applications and Integration       18          6 marks
  Model Selection and Optimization   9           3 marks
  Agents and Workflows               8           between 2 and 3 marks
  Prompt and Context Engineering     6           2 marks
  Tools and MCPs                     5           between 1 and 2 marks
  Security and Safety                4           between 1 and 2 marks
  Claude Code                        2           roughly 1 mark
  Eval, Testing, and Debugging       1           0 or 1 mark

A candidate at 60% in Applications and 0% in Claude Code should spend every available hour on Applications. The instinct to clear the zero first is strong and wrong.

## Sort your misses by cause

Percentages hide the thing that matters most, which is *why* you missed. Go back through every wrong answer and put it in one of four piles.

**Did not know it.** The concept was genuinely unfamiliar. Honest, and the easiest to fix: read the chapter.

**Knew it, misread the question.** You understood the mechanism but missed a constraint in the stem — the model was already chosen, the budget was fixed, the data could not leave the region. This is the most common cause of failure among well-prepared candidates, and it is a reading-under-pressure problem, not a knowledge problem.

**Knew it, picked the plausible wrong answer.** You understood the mechanism but chose an option that was true yet did not address the problem. This means your understanding is one level too shallow: you know what a feature *is* but not what it is *for*.

**Ran out of time.** You never properly reached the question.

Each pile has a different remedy, and the piles are usually very uneven. A candidate with thirty misses, twenty of them in the second pile, does not need to study more — they need to slow down and read the constraints. Studying harder would be wasted effort aimed at the wrong problem.

## If the problem is time

120 minutes for 53 questions is about 135 seconds each, and the calculation questions take longer than that while the recall questions take far less.

Make one pass and answer everything you are confident about, flagging anything that needs real work. Then make a second pass over the flagged ones. This stops a single hard question eating ten minutes you needed at the end, and it means that if time runs short, what you lose is the hard questions rather than easy ones you never reached.

Never leave anything blank. There is no penalty for a wrong answer, so an eliminated-down guess is free expected value.

## If the problem is context gaps

If your grid shows a domain that is fine everywhere except one or two exams, find what those exams have in common. Usually it is the setting — caching made sense to you in a batch pipeline but not in a conversational system, or cost modelling worked in the abstract but not under a latency constraint.

The fix is to re-sit those specific exams, not to re-read the chapter. You already know the mechanism; what you need is to meet it somewhere unfamiliar until the setting stops mattering.

## When you are ready

The real exam needs 720 out of 1000, roughly 70%. Since every exam in this book is deliberately harder, treat these as the signals:

-   **Consistently above 75% on the hard tier** (Exams 5, 6, 9, 10, 11) — comfortably ready.
-   **Around 70% on the middle tier** (Exams 3, 4, 7, 8) — likely ready, but check your misses are spread rather than concentrated in Applications.
-   **Below 60% on the entry tier** (Exams 1, 2) — not ready. Go back to the handbook rather than grinding more questions; practice exams diagnose gaps, they do not fill them.

One caution about the capstone. Exam 12 draws on all eight domains at once and is the closest thing here to a dress rehearsal, so save it until you believe you are ready. Used early it tells you little; used last it tells you whether to book the exam.

A final honest word on calibration. These are not retired exam items — no one outside Anthropic has seen the real ones. The questions are written to the published blueprint and pitched deliberately hard, so the scores above are reasonable heuristics rather than measurements. If your grid is strong and your misses are spread thin, you are in good shape regardless of what any single number says.
