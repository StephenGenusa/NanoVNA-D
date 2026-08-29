#!/usr/bin/env python3
"""Reference implementation of the NanoVNA SD-card guide format (a CommonMark subset), see
docs/manual/07-sd-card.md "Guides". The firmware viewer (vna_modules/vna_guide.c) follows the
same rules; keep them identical.

    guide.py check FILE...                       lint (exit 1 on errors)
    guide.py render FILE --target H4|H [--out DIR] [--page N]
    guide.py pack [--out GUIDES]                 build the shipped pack (project GUIDES/ folder)
"""
import argparse, collections, json, os, re, sys
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


# ---------------------------------------------------------------- render (pixel-exact preview)
import screen

X0 = 2                                      # left margin, px (GUIDE_X in vna_guide.c)
screen.PAL["HEAD"] = screen.PAL["TRACE_2"]   # headings and table header rows: LCD_TRACE_2_COLOR


def _row_y(g, row):                         # GUIDE_ROW_Y
    return g.row_h * (row + 1) + 1


def _draw_runs(R, font, runs, x, y, base_colour):
    for text, emph in runs:
        x += R.text(font, to_glyphs(text), x, y, screen.PAL["TRACE_1"] if emph else base_colour)
    return x


def render_page(doc, page_no, dev):
    g = geom(dev); L = layout.get_layout(g.target)
    R = screen.Raster(g.width, L.lcd_h, screen.default_palette(L))
    R.fill(0, 0, g.width, L.lcd_h, screen.PAL["BG"])
    R.fill(0, 0, g.width, g.row_h, screen.PAL["MENU"])
    R.text(g.font, to_glyphs(doc.title), X0, 1, screen.PAL["MENU_TEXT"])
    pn = "%d/%d" % (page_no, max(1, len(doc.pages)))
    R.text(g.font, pn, g.width - X0 - g.font.text_width(pn), 1, screen.PAL["MENU_TEXT"])
    page = doc.pages[page_no - 1] if doc.pages else []
    row = 0
    for b in page:
        if row >= g.rows: break
        y = _row_y(g, row)
        if b.kind == "blank": row += 1
        elif b.kind == "heading": R.text(g.font, to_glyphs(b.data), X0, y, screen.PAL["HEAD"]); row += 1
        elif b.kind == "verbatim": R.text(g.font, to_glyphs(b.data), X0, y, screen.PAL["FG"]); row += 1
        elif b.kind == "text": _draw_runs(R, g.font, b.data, X0, y, screen.PAL["FG"]); row += 1
        else:
            t = b.data; widths, gutter = layout_table(t, g.font)
            xs = [X0 + sum(widths[:c]) + gutter * c for c in range(len(widths))]
            for ri, cells in enumerate(t.rows):
                if row >= g.rows: break
                y = _row_y(g, row)
                colour = screen.PAL["HEAD"] if ri == 0 else screen.PAL["FG"]
                for c, cell in enumerate(cells[:len(widths)]):
                    w = run_width(cell, g.font); a = t.aligns[c]
                    x = xs[c] + (widths[c] - w if a == "r" else (widths[c] - w) // 2 if a == "c" else 0)
                    _draw_runs(R, g.font, cell, x, y, colour)
                row += 1
                if ri == 0 and t.sep and row < g.rows:
                    y = _row_y(g, row)
                    R.fill(X0, y + g.row_h // 2, sum(widths) + gutter * (len(widths) - 1), 1, screen.PAL["FG"]); row += 1
    return R


def render(text, filename, dev, out_dir, page=None):
    doc = parse(text, filename); os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(filename))[0]; paths = []
    for p in range(1, max(1, len(doc.pages)) + 1):
        if page and p != page: continue
        path = os.path.join(out_dir, "%s-%s-p%02d.png" % (stem, dev, p))
        render_page(doc, p, dev).png(path); paths.append(path)
    return paths


# ---------------------------------------------------------------- pack (the shipped GUIDES set)
import math, shutil
import gen_formats, menus, srcinfo   # gen_formats: format names checked by the tests

SRC_DIR = os.path.join(ROOT, "docs", "manual", "guides-src")
OUT_DIR = os.path.join(ROOT, "GUIDES")
HAMBANDS = os.path.join(ROOT, "vna_modules", "vna_hambands.c")
COAX = os.path.join(ROOT, "vna_modules", "vna_coax.c")
README = """# NanoVNA guides
Copy this GUIDES folder to the SD card root. On the device:
SD CARD -> LOAD -> GUIDE. Wheel or tap left/right = page,
push or tap the header = back.

Files are grouped by prefix: ant- antennas, pota-/sota- field
operating, choke-, coax-, cal-, ref- tables and formulas,
dev- the instrument itself, prop- propagation.

## Writing your own (.md or .txt)
- First line `# Title`; `---` on its own line = page break
- Keep lines under 60 characters and pages under 27 rows;
  the device clips, it does not wrap or scroll
- `## Heading`, **bold** / *emphasis*, `code`, [text](url)
- Tables: | a | b | rows, second row |---|--:| sets alignment
- Ω ° µ are drawn; other non-ASCII shows as ?
- Check on a PC: python3 tools/manual/guide.py check FILE
- Preview: python3 tools/manual/guide.py render FILE --target H4
---
## Sources
- The NanoVNA-D fork manual, docs/manual/ (device guides are
  generated from the firmware source)
- ARRL Antenna Book for Radio Communications (coax loss
  Vol 3 Table 23.4; radial voltages Vol 1 Fig 3.27)
- N6LF (R. Severns) QEX 3/2009 and 3-4/2012, QST 3/2010:
  radials
- K9YC (J. Brown) "RFI, Ferrites, and Common Mode Chokes"
  and the 2018 Choke Cookbook: k9yc.com/publish.htm
- G3TXQ choke charts: karinya.net/g3txq/chokes/
- Fair-Rite Products catalog (14th ed.) and material data
  sheets: fair-rite.com; Palomar Engineers mix-selection table
- Parks on the Air rules and guides: docs.pota.app;
  SOTA General Rules: sota.org.uk
- "Portable HF Vertical Antennas", S. Genusa 2026 (the
  portvert reference, with its claims ledger)
"""


def _table(header, aligns, rows):
    return (["| " + " | ".join(header) + " |", "|" + "|".join({"l": "---", "r": "--:", "c": ":-:"}[a] for a in aligns) + "|"]
            + ["| " + " | ".join(r) + " |" for r in rows])


def _paged(title, header, aligns, rows, per_page, intro=(), footer=()):
    out = ["# " + title] + list(intro)
    for i in range(0, len(rows), per_page):
        if i: out.append("---")
        out += _table(header, aligns, rows[i:i + per_page])
    out += list(footer)
    return "\n".join(out) + "\n"


def gen_ref_swr():
    rows = []
    for s in (1.05, 1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.5, 3.0, 4.0, 5.0, 10.0):
        g = (s - 1) / (s + 1)
        rows.append(["%.2f" % s if s < 10 else "10", "%.1f" % (-20 * math.log10(g)), "%.3f" % g,
                     "%.1f" % (100 * g * g), "%.2f" % (-10 * math.log10(1 - g * g))])
    return _paged("SWR / return loss", ["SWR", "RL dB", "\\|G\\|", "% refl", "ML dB"], "rrrrr", rows, 30,
                  footer=["", "RL 20 dB or better: done. 10-20: usable. Under 10:", "investigate before anything else. RL = -20 log10 |G|."])


def gen_ref_db():
    rows = [["%g" % d, "%.2f" % (10 ** (d / 10)), "%.2f" % (10 ** (d / 20))] for d in (0.5, 1, 2, 3, 6, 10, 13, 20, 30, 40)]
    return _paged("dB table", ["dB", "power x", "voltage x"], "rrr", rows, 30,
                  footer=["", "-3 dB = half power, -6 dB = half voltage. Loss in dB", "adds; ratios multiply. 1 S-unit = 6 dB."])


_BANDS = None


def _bands():
    global _BANDS
    if _BANDS is None:
        src = open(HAMBANDS, encoding="utf-8").read()
        body = src[src.index("ham_bands_usa[]"):]; body = body[:body.index("};")]
        _BANDS = [(m.group(3), int(m.group(1)), int(m.group(2)))
                  for m in re.finditer(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}\s*,?\s*//\s*(\S+)", body)]
    return _BANDS


def gen_ref_reactance():
    rows = []
    for name, a, b in _bands():
        if a < 1.8e6 or a > 148e6: continue
        f = (a + b) / 2
        xl1 = 2 * math.pi * f * 1e-6; xl10 = xl1 * 10
        xc100 = 1 / (2 * math.pi * f * 100e-12); xc10 = 1 / (2 * math.pi * f * 10e-12)
        rows.append([name, "%.1f" % (f / 1e6), "%.0f" % xl1, "%.0f" % xl10, "%.0f" % xc100, "%.0f" % xc10])
    return _paged("Reactance sanity", ["Band", "MHz", "1 uH", "10 uH", "100 pF", "10 pF"], "lrrrrr", rows, 24,
                  intro=["Ohms at the band centre. Judge whether an Ls/Cs or X", "reading is believable before trusting it."])


def gen_ant_lengths():
    rows = []
    for name, a, b in _bands():
        if a < 1.8e6 or a > 54e6: continue
        fc = (a + b) / 2 / 1e6
        rows.append([name, "%.3f" % fc, "%.1f" % (468 / fc), "%.1f" % (234 / fc), "%.2f" % (142.65 / fc)])
    return _paged("Antenna lengths", ["Band", "MHz", "Dipole ft", "1/4 ft", "Dipole m"], "lrrrr", rows, 24,
                  footer=["", "Starting lengths; cut 2-3% long and trim (ant-trim).", "Radials above 20 m run shorter than 234/f."])


def gen_ant_bands():
    rows = []
    for name, a, b in _bands():
        if a > 148e6: continue
        span = b - a; lo = a - span * 0.5; hi = b + span * 0.5
        rows.append([name, "%.4g" % (a / 1e6), "%.4g" % (b / 1e6), "%.4g" % (lo / 1e6), "%.4g" % (hi / 1e6)])
    return _paged("Band edges and sweeps", ["Band", "Start", "Stop", "Sweep from", "to"], "lrrrr", rows, 24,
                  intro=["US limits (MHz), from the firmware's band table; sweep", "is the band plus half a band each side."],
                  footer=["", "Source: vna_hambands.c (USA); ARRL band plan"])


def gen_coax():
    src = open(COAX, encoding="utf-8").read()
    freqs = [int(x) for x in re.search(r"coax_freq_10khz\[COAX_FREQS\]\s*=\s*\{([^}]*)\}", src).group(1).split(",")]
    names = re.findall(r'"([^"]+)"', re.search(r"coax_name\[[^\]]*\]\s*=\s*\{([^}]*)\}", src).group(1))[1:]
    names = [n.split("/")[0] for n in names]
    table = re.search(r"coax_loss_100m\[COAX_TYPES\]\[COAX_FREQS\]\s*=\s*\{(.*?)\n\};", src, re.S).group(1)
    loss = [[int(x) for x in re.findall(r"\d+", row.split("//")[0])] for row in re.findall(r"\{([^}]*)\}", table)]
    rows = [["%.1f" % (f / 100)] + ["%.2f" % (loss[t][i] / 100 / 3.28084) for t in range(len(names))] for i, f in enumerate(freqs)]
    out = ["# Coax VF and loss", "## Velocity factor",
           "| Cable | VF |", "|---|--:|",
           "| RG-58, RG-213, RG-8 (solid PE) | 0.66 |", "| RG-174, RG-316, RG-142 (PTFE) | 0.69-0.70 |",
           "| RG-8X, LMR-240 (foam PE) | 0.78-0.82 |", "| LMR-400, 9913 (foam) | 0.84-0.85 |",
           "| 1/2 in hardline, air core | 0.88-0.90 |", "| 300 ohm twin lead | 0.82 |",
           "| 450 ohm window line | 0.91 (0.88-0.95) |", "| open-wire line | 0.95-0.98 |", "",
           "Set it: DISPLAY -> TRANSFORM -> VELOCITY FACTOR. Better:", "MEASURE -> CABLE measures your cable's VF and loss.",
           "---", "## Matched loss, dB per 100 ft (new, dry cable)"]
    out += _table(["MHz"] + names, "r" * (len(names) + 1), rows)
    # percent of power lost at 25 and 50 ft on 20 m (index of 14.2 MHz)
    i20 = freqs.index(1420)
    pct = []
    for t, n in enumerate(names):
        db100ft = loss[t][i20] / 100 / 3.28084
        pct.append("%s %d/%d" % (n, round(100 * (1 - 10 ** (-db100ft * 0.25 / 10))), round(100 * (1 - 10 ** (-db100ft * 0.5 / 10)))))
    out += ["", "% power lost at 25/50 ft on 20 m:", "  " + " . ".join(pct[:3]), "  " + " . ".join(pct[3:]),
            "On 10 m roughly double. Loss rises with SWR on the line.", "",
            "Source: ARRL Antenna Book Vol 3 Table 23.4 (vna_coax.c)"]
    return "\n".join(out) + "\n"


def _label(it):
    return " ".join(menus.plain_label(it.label).replace("%s", "").split())


def gen_dev_menu_map():
    m = menus.parse_menus(srcinfo.preprocess("F303"))
    out = ["# Menu map"]; first = True
    for it in m["menu_top"].items:
        if it.kind != "submenu" or it.ref not in m: continue
        if not first: out.append("---")
        out.append("## " + _label(it)); first = False
        for sub in m[it.ref].items:
            lab = _label(sub)
            if lab: out.append("- " + lab)
    return "\n".join(out) + "\n"


GENERATED = (("ref-swr-table.md", gen_ref_swr), ("ref-db.md", gen_ref_db), ("ref-reactance.md", gen_ref_reactance),
             ("ant-lengths.md", gen_ant_lengths), ("ant-bands.md", gen_ant_bands), ("coax-vf-loss.md", gen_coax),
             ("dev-menu-map.md", gen_dev_menu_map), ("README.md", lambda: README))


def pack(out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True); written = []
    for p in sorted(os.listdir(SRC_DIR)):
        if p.endswith(".md"):
            shutil.copyfile(os.path.join(SRC_DIR, p), os.path.join(out_dir, p)); written.append(os.path.join(out_dir, p))
    for name, fn in GENERATED:
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(fn())
        written.append(path)
    bad = 0
    for path in written:
        for n, lvl, msg in check(open(path, encoding="utf-8").read(), path):
            if lvl == "error": print("%s:%d: error: %s" % (path, n, msg)); bad += 1
    if bad: raise SystemExit(1)
    return written


# ---------------------------------------------------------------- CLI
def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("files", nargs="+")
    r = sub.add_parser("render"); r.add_argument("file"); r.add_argument("--target", default="H4", choices=["H4", "H"])
    r.add_argument("--out", default="."); r.add_argument("--page", type=int)
    p = sub.add_parser("pack"); p.add_argument("--out", default=os.path.join(ROOT, "GUIDES"))
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
