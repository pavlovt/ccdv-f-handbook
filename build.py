#!/usr/bin/env python3
"""Build the CCDV-F handbook EPUBs from Markdown sources.

Usage:
    python build.py            # build all three volumes
    python build.py vol3       # build one volume
    python build.py --check    # run preflight.py first, stop on defects

Each volume folder holds meta.yaml (title page and EPUB metadata, plus the
output file name) and src/*.md. Files are assembled in filename order, so the
two-digit prefix decides where a file sits in the book. Every file must start
with a level-1 heading; each level-1 heading becomes a new EPUB chapter.
Output goes to dist/. Requires pandoc on PATH (2.9 or later).
"""
import os, re, subprocess, sys, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
VOLUMES = ["vol1", "vol2", "vol3"]


def output_name(vol):
    meta = open(os.path.join(ROOT, vol, "meta.yaml"), encoding="utf-8").read()
    m = re.search(r"^output:\s*(.+)$", meta, re.M)
    return m.group(1).strip() if m else vol + ".epub"


def build(vol):
    files = sorted(glob.glob(os.path.join(ROOT, vol, "src", "*.md")))
    if not files:
        print(f"{vol}: no source files, skipped")
        return False
    for f in files:
        first = open(f, encoding="utf-8").readline()
        if not first.startswith("# "):
            print(f"{vol}: WARNING {os.path.basename(f)} does not start with a '# ' heading")
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", output_name(vol))
    cmd = ["pandoc", "-f", "markdown-smart", "-t", "epub3",
           "--metadata-file", os.path.join(ROOT, vol, "meta.yaml"),
           "--css", os.path.join(ROOT, "style.css"),
           "--toc", "--toc-depth=2", "--epub-chapter-level=1",
           "-o", out] + files
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{vol}: pandoc failed\n{r.stderr}")
        return False
    if r.stderr.strip():
        print(r.stderr.strip())
    words = sum(len(open(f, encoding="utf-8").read().split()) for f in files)
    print(f"{vol}: {len(files)} files, ~{words:,} words -> dist/{os.path.basename(out)}")
    return True


def main(argv):
    check = "--check" in argv
    vols = [a for a in argv if a in VOLUMES] or VOLUMES
    if check:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "preflight.py")] + vols)
        if r.returncode != 0:
            print("preflight found defects; build stopped")
            return 1
    ok = all([build(v) for v in vols])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
