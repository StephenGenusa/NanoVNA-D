#!/usr/bin/env python3
"""Build the manual: docs/manual/*.md -> dist/NanoVNA-manual.html (self-contained) and
dist/NanoVNA-manual.pdf (XeLaTeX). Cross-chapter links (NN-name.md) become in-document
anchors; SVG images are inlined in the HTML and converted for the PDF by pandoc/rsvg-convert.

    python3 tools/manual/build.py [--html] [--pdf] [--out DIR]     (default: both, docs/manual/dist)
"""
import argparse, glob, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "docs", "manual")
CHAPTERS = ["00-front.md", "01-orientation.md", "02-sweep-and-traces.md", "02-trace-formats.md",
            "03-calibration.md", "04-markers.md", "05-measure.md", "06-fork-features.md",
            "07-sd-card.md", "08-console.md", "09-menu-map.md", "10-firmware-update.md",
            "A-fork-only.md", "B-references.md"]
FROM = "markdown+footnotes+pipe_tables+backtick_code_blocks+raw_html+auto_identifiers+implicit_header_references"
FONTS = ["DejaVu Sans", "Noto Sans", "Liberation Sans", "FreeSans", "Noto Sans CJK JP"]
MONO = ["DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono", "FreeMono", "Noto Sans Mono CJK JP"]


def pandoc_id(title):
    """pandoc's auto identifier for a heading (gfm-style, as pandoc 2.9 produces it)."""
    t = title.lower()
    t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", "-", t.strip())
    return t.lstrip("-0123456789") or "section"


def first_heading(path):
    for line in open(path, encoding="utf-8"):
        if line.startswith("# "):
            return line[2:].strip()
    raise RuntimeError("no H1 in " + path)


def version():
    m = re.search(r'#define VERSION\s+"([^"]+)"', open(os.path.join(ROOT, "main.c"), encoding="utf-8").read())
    return m.group(1) if m else "unknown"


def git_describe():
    try:
        return subprocess.run(["git", "describe", "--tags", "--always"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def have_font(name):
    try:
        out = subprocess.run(["fc-list", "--format=%{family}\n"], capture_output=True, text=True).stdout
    except OSError:
        return False
    return any(name.lower() == fam.strip().lower() for line in out.splitlines() for fam in line.split(","))


def pick(fonts):
    for f in fonts:
        if have_font(f):
            return f
    return None


def prepare(tmp):
    """Copy chapters into tmp with cross-links rewritten to anchors; return the file list."""
    present = [c for c in CHAPTERS if os.path.exists(os.path.join(SRC, c))]
    extra = sorted(set(os.path.basename(p) for p in glob.glob(os.path.join(SRC, "*.md"))) - set(present))
    if extra:
        print("note: chapters not in build order, skipped: %s" % ", ".join(extra), file=sys.stderr)
    anchors = {c: "#" + pandoc_id(first_heading(os.path.join(SRC, c))) for c in present}
    files = []
    for c in present:
        text = open(os.path.join(SRC, c), encoding="utf-8").read()
        for name, anchor in anchors.items():
            text = text.replace("(%s)" % name, "(%s)" % anchor).replace("(%s#" % name, "(#")
        text = re.sub(r"\]\((0[0-9]|10|[AB])-[a-z-]+\.md\)", "](#missing-chapter)", text)   # unknown chapter
        dst = os.path.join(tmp, c)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        files.append(dst)
    # images are referenced as img/... relative to the chapter directory
    os.symlink(os.path.join(SRC, "img"), os.path.join(tmp, "img"))
    cap = os.path.join(SRC, "captures")
    if os.path.isdir(cap):
        os.symlink(cap, os.path.join(tmp, "captures"))
    return files


def build(out_dir, html=True, pdf=True):
    os.makedirs(out_dir, exist_ok=True)
    ver, desc = version(), git_describe()
    title = "NanoVNA-H / NanoVNA-H4 User Manual"
    subtitle = "Firmware %s (%s)" % (ver, desc) if desc else "Firmware " + ver
    with tempfile.TemporaryDirectory() as tmp:
        files = prepare(tmp)
        common = ["pandoc", "--file-scope", "-f", FROM, "--toc", "--toc-depth=2",
                  "--metadata", "title=" + title, "--metadata", "subtitle=" + subtitle,
                  "--metadata", "lang=en"]
        if html:
            css = os.path.join(HERE, "manual.css")
            out = os.path.join(out_dir, "NanoVNA-manual.html")
            cmd = common + ["-t", "html5", "--standalone", "--self-contained", "--css", css, "-o", out] + files
            subprocess.run(cmd, cwd=tmp, check=True)
            print("wrote", out, os.path.getsize(out), "bytes")
        if pdf:
            main, mono = pick(FONTS), pick(MONO)
            if not main or not shutil.which("xelatex"):
                raise RuntimeError("PDF needs xelatex and one of the fonts %s" % FONTS)
            out = os.path.join(out_dir, "NanoVNA-manual.pdf")
            cmd = common + ["--pdf-engine=xelatex", "-V", "mainfont=" + main, "-V", "monofont=" + mono,
                            "-V", "geometry:margin=2cm", "-V", "papersize=a4", "-V", "colorlinks=true",
                            "-V", "fontsize=10pt", "-o", out] + files
            subprocess.run(cmd, cwd=tmp, check=True)
            print("wrote", out, os.path.getsize(out), "bytes")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--html", action="store_true"); ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--out", default=os.path.join(SRC, "dist"))
    a = ap.parse_args(argv)
    both = not a.html and not a.pdf
    build(a.out, html=a.html or both, pdf=a.pdf or both)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
