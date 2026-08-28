#!/usr/bin/env python3
"""Reference implementation of the NanoVNA SD-card guide format (a CommonMark subset), see
docs/manual/07-sd-card.md "Guides". The firmware viewer (vna_modules/vna_guide.c) follows the
same rules; keep them identical.

    guide.py check FILE...                       lint (exit 1 on errors)
    guide.py render FILE --target H4|H [--out DIR] [--page N]
    guide.py pack [--out docs/manual/guides]     build the shipped pack
"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

Doc = collections.namedtuple("Doc", "title pages")
Block = collections.namedtuple("Block", "kind data")       # text | heading | blank | verbatim | table
Table = collections.namedtuple("Table", "rows sep aligns")  # rows: [[runs...]...]; sep: bool; aligns: 'l'|'r'|'c'

GLYPHS = {"Ω": "\x1e", "°": "\x1f", "µ": "\x1d", "μ": "\x1d"}   # S_OHM S_DEGREE S_MICRO (and Greek mu)
MAX_COLS = 8


# ---------------------------------------------------------------- parsing
def to_glyphs(s):
    return "".join(GLYPHS.get(c, c if ord(c) < 0x80 else "?") for c in s)


def _literal(s):
    """Text with only code/escape processing (used when an emphasis marker is never closed)."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i] == "\\" and i + 1 < n: out.append(s[i + 1]); i += 2
        elif s[i] == "`": i += 1
        else: out.append(s[i]); i += 1
    return [("".join(out), False)]


def inline(s):
    """Inline markup -> list of (text, emphasis). Unclosed markers stay literal."""
    runs, buf, emph, i, n = [], [], False, 0, len(s)
    def flush():
        if buf:
            runs.append(("".join(buf), emph)); buf.clear()
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            buf.append(s[i + 1]); i += 2; continue
        if c == "`":
            i += 1; continue
        if c == "[":
            m = re.match(r"\[([^\]]*)\]\([^)]*\)", s[i:])
            if m:
                buf.append(m.group(1)); i += m.end(); continue
        if c in "*_":
            mark = s[i:i + 2] if s[i:i + 2] in ("**", "__") else c
            if not emph:
                j = s.find(mark, i + len(mark))
                ok = j > i + len(mark) and not s[i + len(mark)].isspace() and not s[j - 1].isspace()
                if ok:
                    flush(); emph = True; i += len(mark); continue
            elif s[i:i + len(mark)] == mark and buf and not buf[-1].isspace():
                flush(); emph = False; i += len(mark); continue
            buf.append(mark); i += len(mark); continue
        buf.append(c); i += 1
    if emph:
        return _literal(s)
    flush()
    return [(t, e) for t, e in runs if t]


def split_cells(line):
    body = line.strip()
    if body.startswith("|"): body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"): body = body[:-1]
    cells, cur, i = [], [], 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            cur.append("|"); i += 2
        elif body[i] == "|":
            cells.append("".join(cur).strip()); cur = []; i += 1
        else:
            cur.append(body[i]); i += 1
    cells.append("".join(cur).strip())
    return cells


def is_separator(cells):
    return len(cells) > 0 and all(re.fullmatch(r":?-+:?", c) for c in cells)


def aligns_of(cells):
    return ["c" if c.startswith(":") and c.endswith(":") else "r" if c.endswith(":") else "l" for c in cells]


def parse(text, filename="guide"):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "": lines.pop()
    title = os.path.splitext(os.path.basename(filename))[0]
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip(); lines = lines[1:]
    pages, page, fence, i = [], [], False, 0
    while i < len(lines):
        ln = lines[i]
        if fence:
            if ln.strip().startswith("```"): fence = False
            else: page.append(Block("verbatim", ln))
            i += 1; continue
        if ln.strip().startswith("```"):
            fence = True; i += 1; continue
        if ln.rstrip() == "---":
            if page: pages.append(page)
            page = []; i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_cells(lines[i])); i += 1
            sep = len(rows) > 1 and is_separator(rows[1])
            aligns = aligns_of(rows[1]) if sep else []
            if sep: del rows[1]
            ncol = max(len(r) for r in rows)
            aligns = (aligns + ["l"] * ncol)[:ncol]
            page.append(Block("table", Table([[inline(c) for c in r] + [[]] * (ncol - len(r)) for r in rows], sep, aligns)))
            continue
        if ln == "":
            page.append(Block("blank", None))
        elif re.match(r"#{1,6} ", ln):
            page.append(Block("heading", ln.lstrip("#").strip()))
        else:
            page.append(Block("text", inline(ln)))
        i += 1
    if page: pages.append(page)
    return Doc(title, pages)


# ---------------------------------------------------------------- geometry (real glyph widths)
import fonts, layout

Geom = collections.namedtuple("Geom", "target dev width rows font row_h")
_TARGET = {"H4": "F303", "H": "F072"}
ROWS = 28                                   # text rows below the header, both devices


def geom(dev):
    L = layout.get_layout(_TARGET[dev])
    f = fonts.load_font(L.sfont_name)
    return Geom(_TARGET[dev], dev, L.lcd_w, min(L.lcd_h // L.sfont_str_h - 1, ROWS), f, L.sfont_str_h)


def run_width(runs, font):
    return sum(font.text_width(to_glyphs(t)) for t, _ in runs)


def layout_table(table, font):
    """Column pixel widths (widest cell) and the gutter (one space) for a table."""
    ncol = min(len(table.aligns), MAX_COLS)
    widths = [0] * ncol
    for row in table.rows:
        for c, cell in enumerate(row[:ncol]):
            widths[c] = max(widths[c], run_width(cell, font))
    return widths, font.glyph(ord(" "))[0]


def page_rows(page):
    return sum(len(b.data.rows) + (1 if b.data.sep else 0) if b.kind == "table" else 1 for b in page)


# ---------------------------------------------------------------- lint
GUIDE_CHARS = 60           # author guidance per line
GUIDE_ROWS = 27            # author guidance per page


def _line_width(block, font):
    if block.kind == "text": return run_width(block.data, font)
    if block.kind in ("heading", "verbatim"): return font.text_width(to_glyphs(block.data))
    return 0


def check(text, filename):
    """Lint -> sorted list of (line, level, message); line 0 = file level."""
    out = []
    g4, gh = geom("H4"), geom("H")
    raw = text.replace("\r\n", "\n").split("\n")
    titled = bool(raw) and raw[0].startswith("# ")
    if not titled:
        out.append((1, "warning", "no title: first line is not '# Title'"))
    fence = False
    for n, ln in enumerate(raw, 1):
        if ln.strip().startswith("```"): fence = not fence; continue
        if fence: continue
        for ch in ln:
            if ord(ch) >= 0x80 and ch not in GLYPHS:
                out.append((n, "error", "non-drawable character U+%04X" % ord(ch))); break
        if len(ln) > GUIDE_CHARS: out.append((n, "warning", "%d characters (guidance: %d)" % (len(ln), GUIDE_CHARS)))
        if "![" in ln: out.append((n, "error", "image syntax is not supported"))
        if re.search(r"<[A-Za-z/]", ln): out.append((n, "error", "HTML is not supported"))
        if re.match(r"\s{2,}([-*]|\d+\.) ", ln): out.append((n, "error", "nested list is not supported"))
    if fence: out.append((len(raw), "error", "fence opened and never closed"))
    # per page: first source line of each page, for messages
    body_start = 2 if titled else 1
    starts, cur, fence = [], None, False
    for i, ln in enumerate(raw[body_start - 1:]):
        if ln.strip().startswith("```"): fence = not fence
        if not fence and ln.rstrip() == "---": cur = None; continue
        if cur is None: cur = i + body_start; starts.append(cur)
    doc = parse(text, filename)
    for p, page in enumerate(doc.pages):
        at = starts[p] if p < len(starts) else 0
        rows = page_rows(page)
        if rows > ROWS: out.append((at, "error", "page has %d rows (max %d)" % (rows, ROWS)))
        elif rows > GUIDE_ROWS: out.append((at, "warning", "page has %d rows (guidance: %d)" % (rows, GUIDE_ROWS)))
        for b in page:
            for dev, g in (("H4", g4), ("H", gh)):
                lvl = "error" if dev == "H4" else "warning"
                if b.kind == "table":
                    if dev == "H4" and len(b.data.aligns) > MAX_COLS:
                        out.append((at, "error", "table has %d columns (max %d)" % (len(b.data.aligns), MAX_COLS)))
                    w, gut = layout_table(b.data, g.font); total = sum(w) + gut * (len(w) - 1)
                    if total > g.width: out.append((at, lvl, "table is %d px on %s (max %d)" % (total, dev, g.width)))
                else:
                    w = _line_width(b, g.font)
                    if w > g.width: out.append((at, lvl, "line is %d px on %s (max %d)" % (w, dev, g.width)))
    return sorted(set(out))


# ---------------------------------------------------------------- CLI
def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("files", nargs="+")
    r = sub.add_parser("render"); r.add_argument("file"); r.add_argument("--target", default="H4", choices=["H4", "H"])
    r.add_argument("--out", default="."); r.add_argument("--page", type=int)
    p = sub.add_parser("pack"); p.add_argument("--out", default=os.path.join(ROOT, "docs", "manual", "guides"))
    a = ap.parse_args(argv)
    if a.cmd == "check":
        errors = 0
        for path in a.files:
            for n, lvl, msg in check(open(path, encoding="utf-8").read(), path):
                print("%s:%d: %s: %s" % (path, n, lvl, msg)); errors += lvl == "error"
        return 1 if errors else 0
    if a.cmd == "render":
        print("\n".join(render(open(a.file, encoding="utf-8").read(), a.file, a.target, a.out, a.page))); return 0
    if a.cmd == "pack":
        files = pack(a.out); print("wrote %d guides to %s" % (len(files), os.path.relpath(a.out, ROOT))); return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
