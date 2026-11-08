#!/usr/bin/env python3
"""Check every question in the CCDV-F handbook against its answer key.

Usage:  python preflight.py [vol1 vol2 vol3]      (default: all volumes)
Exit code 0 = no defects, 1 = defects found. Warnings never fail the run.

Defects:
  - a question with no answer-key entry, or a key entry with no question
  - a question ID that appears twice
  - a keyed letter that is not one of the question's options
  - answer count not matching the (Select TWO/THREE) marker, or a
    single-answer question keyed with several letters
  - a domain label in the key that differs from the section the question
    sits in (only where exams are split into "Section N — Domain" headings)
  - an explanation that calls a keyed-correct option wrong
Warnings:
  - correct-letter balance skew within one question file
"""
import glob, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
VOLUMES = ["vol1", "vol2", "vol3"]
QID = r"[A-Z]+\d+(?:\.\d+)?"
Q_RE = re.compile(r"^\*\*(" + QID + r")\.?(?: \((Select (?:TWO|THREE|FOUR))\))?\.?\*\*(.*)$")
K_RE = re.compile(r"^\*\*(" + QID + r")\.? — ([A-H](?:(?:, and |, | and )[A-H])*)\.\*\*\s*(?:\*\(([^)]*)\)\*)?(.*)$")
SECTION_RE = re.compile(r"^## Section \d+ — (.+?)\s*$")
OPT_LIST_RE = re.compile(r"^-\s+(?:\*\*)?([A-H])\.(?:\*\*)?\s")
NUM = {"TWO": 2, "THREE": 3, "FOUR": 4}


def inline_options(line):
    """Letters of an inline 'A. ... B. ... C. ...' option paragraph."""
    if not line.startswith("A. "):
        return []
    letters, want = [], "A"
    for m in re.finditer(r"(?:^|\s)([A-H])\.\s", line):
        if m.group(1) == want:
            letters.append(want)
            want = chr(ord(want) + 1)
    return letters


def parse_questions(path):
    qs, cur, section = {}, None, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        s = SECTION_RE.match(line)
        if s:
            section = s.group(1)
        m = Q_RE.match(line)
        if m:
            sel = m.group(2) or (re.search(r"\((Select (?:TWO|THREE|FOUR))\)", m.group(3)) or [None, None])[1]
            cur = {"id": m.group(1), "select": NUM[sel.split()[1]] if sel else 1,
                   "options": [], "section": section, "file": os.path.basename(path)}
            if cur["id"] in qs:
                cur["dup"] = True
            qs.setdefault(cur["id"], cur)
            if cur.get("dup"):
                qs[cur["id"]]["dup"] = True
            continue
        if cur is None:
            continue
        sel = re.search(r"\(Select (TWO|THREE|FOUR)\)", line)
        if sel and not cur["options"]:
            cur["select"] = NUM[sel.group(1)]
        o = OPT_LIST_RE.match(line)
        if o:
            cur["options"].append(o.group(1))
        elif not cur["options"]:
            cur["options"] = inline_options(line)
        if line.startswith("#"):
            cur = None
    return qs


def letters_of(s):
    return re.findall(r"[A-H]", s)


def wrong_claims(text):
    """Letters an explanation explicitly calls wrong/incorrect."""
    out = set()
    for m in re.finditer(r"((?:(?:Option |option )?\b[A-H]\b(?: \([^)]*\))?(?:, | and |, and )?)+)\s+(?:is|are) (?:wrong|incorrect|false)", text):
        out.update(re.findall(r"\b([A-H])\b", m.group(1)))
    for m in re.finditer(r"\b(?:Option |option )([A-H]) (?:is wrong|is incorrect|fails)", text):
        out.add(m.group(1))
    return out


def check(vol):
    files = sorted(glob.glob(os.path.join(ROOT, vol, "src", "*.md")))
    qs, keys, defects, warnings = {}, {}, [], []
    for f in files:
        first = open(f, encoding="utf-8").readline()
        if first.startswith("# Answer Key"):
            for line in open(f, encoding="utf-8"):
                m = K_RE.match(line.rstrip("\n"))
                if m:
                    if m.group(1) in keys:
                        defects.append(f"{m.group(1)}: answer key entry appears twice")
                    keys[m.group(1)] = {"letters": letters_of(m.group(2)), "domain": m.group(3),
                                        "text": m.group(4), "file": os.path.basename(f)}
        else:
            for qid, q in parse_questions(f).items():
                if qid in qs or q.get("dup"):
                    defects.append(f"{qid}: question ID appears twice")
                qs[qid] = q
    for qid in qs.keys() - keys.keys():
        defects.append(f"{qid}: question has no answer-key entry ({qs[qid]['file']})")
    for qid in keys.keys() - qs.keys():
        defects.append(f"{qid}: answer-key entry has no question ({keys[qid]['file']})")
    balance = defaultdict(Counter)
    for qid in sorted(qs.keys() & keys.keys(), key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s)]):
        q, k = qs[qid], keys[qid]
        if not q["options"]:
            defects.append(f"{qid}: could not find the options")
        else:
            bad = [l for l in k["letters"] if l not in q["options"]]
            if bad:
                defects.append(f"{qid}: keyed {','.join(bad)} but options are {''.join(q['options'])}")
        if len(k["letters"]) != q["select"]:
            defects.append(f"{qid}: expects {q['select']} answer(s), key gives {len(k['letters'])}")
        scored = k["domain"].split("scored under ")[-1].strip() if k["domain"] else None
        if q["section"] and scored and q["section"] != scored:
            defects.append(f"{qid}: key domain '{k['domain']}' but question is in section '{q['section']}'")
        contradicted = wrong_claims(k["text"]) & set(k["letters"])
        if contradicted:
            defects.append(f"{qid}: explanation calls keyed option {','.join(sorted(contradicted))} wrong")
        if q["select"] == 1:
            balance[q["file"]][k["letters"][0]] += 1
    for f, c in balance.items():
        n = sum(c.values())
        if n >= 12:
            top, cnt = c.most_common(1)[0]
            missing = [l for l in "ABCD" if c[l] == 0]
            if cnt / n > 0.40 or missing:
                warnings.append(f"{f}: letter balance {dict(sorted(c.items()))}")
    print(f"{vol}: {len(qs)} questions, {len(keys)} key entries, {len(defects)} defects, {len(warnings)} warnings")
    for d in defects:
        print("  DEFECT  " + d)
    for w in warnings:
        print("  warning " + w)
    return len(defects)


if __name__ == "__main__":
    vols = [a for a in sys.argv[1:] if a in VOLUMES] or VOLUMES
    sys.exit(1 if sum(check(v) for v in vols) else 0)
