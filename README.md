# CCDV-F Study Handbook — sources

Markdown sources for the three-volume study handbook for the **Claude Certified Developer – Foundations (CCDV-F)** exam, and the scripts that build them into EPUB.

| Folder | Book | Contents |
|---|---|---|
| `vol1/` | *A Study Handbook for the CCDV-F Exam* | 12 chapters across the eight exam domains, chapter questions, a 53-question mock exam, answer keys, glossary, resources |
| `vol2/` | *Volume II — Depth in the Heavy Domains* | 5 advanced chapters, a 60-question advanced mock exam, answer keys |
| `vol3/` | *Volume III — Twelve Advanced Mock Exams* | 12 full-length exams of 53 questions each, answer keys, results guide |

1,007 questions in total, every one checked against its answer key by `preflight.py`.

Study compilation built from public documentation. Not affiliated with or endorsed by Anthropic.

## Layout

```
style.css            shared stylesheet for all three books
build.py             builds the EPUBs into dist/
preflight.py         checks questions against answer keys
volN/meta.yaml       title page, EPUB metadata, output file name
volN/src/NN-*.md     one file per chapter, exam or answer key
dist/                build output (not committed)
```

The two-digit prefix sets a file's position in the book; it is the build order, not the chapter number. Every file starts with a `# ` heading, and each `# ` heading becomes one EPUB chapter. The table of contents shows `#` and `##` headings.

## Building

Requires [pandoc](https://pandoc.org/installing.html) 2.9 or later and Python 3.

```
python build.py              # all three volumes
python build.py vol2         # one volume
python build.py --check      # run preflight first; stop if it finds defects
```

## Question and answer-key format

Questions are written as a bold ID followed by the stem, then the options:

```
**E1.6** Which TWO statements are correct? **(Select TWO)**

-   A. ...
-   B. ...
```

(Volume I chapter questions keep their options inline in one paragraph: `A. ... B. ... C. ...`.)

Answer-key entries live in files whose heading begins `# Answer Key`:

```
**E1.6 — A and C.** *(Applications and Integration)* Explanation...
```

ID prefixes: `Q<ch>.<n>` Volume I chapters, `M<n>` Volume I mock, `V<ch>.<n>` Volume II chapters, `A<n>` Volume II mock, `E<exam>.<n>` Volume III.

## Checking

```
python preflight.py          # exit code 0 = no defects
```

It reports questions without a key entry (and the reverse), duplicate IDs, keyed letters that aren't among the options, answer counts that don't match the **(Select TWO/THREE)** marker, domain labels that differ from the question's `## Section N — Domain` heading, and explanations that call a keyed-correct option wrong. It warns when the correct letters in one file are unbalanced.

## Editing conventions

- After reordering options, remap every by-letter reference in the explanation ("B is wrong because…"). This was the most common defect while the books were written.
- Keep correct letters balanced within each chapter or exam, and check it with `preflight.py`, not by eye.
- Prices appear only in clearly dated tables; general reasoning uses symbols, so it survives price changes.
- Recompute every calculation question independently after changing any figure it depends on.
- Don't edit the same file from two places at once; commit after each set of changes.
