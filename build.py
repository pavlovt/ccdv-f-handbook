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
import os, re, subprocess, sys, glob, zipfile, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
VOLUMES = ["vol1", "vol2", "vol3"]


def output_name(vol):
    meta = open(os.path.join(ROOT, vol, "meta.yaml"), encoding="utf-8").read()
    m = re.search(r"^output:\s*(.+)$", meta, re.M)
    return m.group(1).strip() if m else vol + ".epub"


# Longest code line, in characters, before it is broken onto the next line.
CODE_WIDTH = 62
_ATOM = re.compile(r"<[^>]*>|&[#\w]+;|[^<&]", re.S)
_PRE = re.compile(r"(<pre\b[^>]*>)(.*?)(</pre>)", re.S)


def _wrap_line(line, width=CODE_WIDTH):
    """Hard-wrap one line of (possibly highlighted) code markup.

    Tags take no width and entities count as one character. Breaks go after
    the last space that fits; a continuation line is indented four spaces
    past the original line's indent.
    """
    atoms = _ATOM.findall(line)
    visible = [a for a in atoms if not a.startswith("<")]
    if len(visible) <= width:
        return line
    indent = 0
    for a in visible:
        if a != " ":
            break
        indent += 1
    cont = " " * min(indent + 4, width // 2)
    out, col, brk = [], 0, None  # brk: (index in out, col) just after a space
    for a in atoms:
        if a.startswith("<"):
            out.append(a)
            continue
        if col >= width:
            if brk and brk[1] > len(cont):
                i, c = brk
                out.insert(i, "\n" + cont)
                col = len(cont) + (col - c)
            else:
                out.append("\n" + cont)
                col = len(cont)
            brk = None
        out.append(a)
        col += 1
        if a == " " and col > indent:
            brk = (len(out), col)
    return "".join(out)


def _wrap_pre(m):
    body = "\n".join(_wrap_line(l) for l in m.group(2).split("\n"))
    return m.group(1) + body + m.group(3)


def wrap_code(epub):
    """Rewrite the EPUB in place so code blocks wrap instead of being cut off.

    Long code lines get real line breaks, because some readers (SumatraPDF's
    ebook view among them) ignore CSS wrapping on <pre>. For readers that do
    follow CSS, pandoc's injected `white-space: pre` on highlighted code is
    turned into pre-wrap, and style.css inside the book is refreshed.
    """
    css = open(os.path.join(ROOT, "style.css"), encoding="utf-8").read()
    tmp = epub + ".tmp"
    with zipfile.ZipFile(epub) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            name = item.filename
            if name.endswith(".xhtml"):
                text = data.decode("utf-8")
                text = re.sub(r"(pre > code\.sourceCode \{[^}]*?)white-space:\s*pre;",
                              r"\1white-space: pre-wrap;", text)
                text = re.sub(r"(pre > code\.sourceCode > span \{[^}]*?)display:\s*inline-block;(?! max-width)",
                              r"\1display: inline-block; max-width: 100%;", text)
                text = _PRE.sub(_wrap_pre, text)
                data = text.encode("utf-8")
            elif name.endswith(".css") and "stylesheet" in os.path.basename(name):
                data = css.encode("utf-8")
            comp = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(item, data, compress_type=comp)
    shutil.move(tmp, epub)


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
           "--toc", "--toc-depth=2", "--epub-chapter-level=1"]
    # Embed the body font so readers never substitute a system font for it.
    for font in sorted(glob.glob(os.path.join(ROOT, "fonts", "*.ttf"))):
        cmd += ["--epub-embed-font", font]
    cmd += ["-o", out] + files
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{vol}: pandoc failed\n{r.stderr}")
        return False
    if r.stderr.strip():
        print(r.stderr.strip())
    wrap_code(out)
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
