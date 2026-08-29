"""tools/manual/guide.py: the reference implementation of the SD-card guide format."""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "manual"))
import guide


class ParseTests(unittest.TestCase):
    def test_title_is_first_line_h1_and_not_drawn(self):
        d = guide.parse("# Cal checklist\nline one\n")
        self.assertEqual(d.title, "Cal checklist")
        self.assertEqual(len(d.pages), 1)
        self.assertEqual([b.kind for b in d.pages[0]], ["text"])

    def test_no_h1_first_line_uses_filename_and_draws_h1(self):
        d = guide.parse("intro\n# Later heading\n", filename="notes.md")
        self.assertEqual(d.title, "notes")
        self.assertEqual([b.kind for b in d.pages[0]], ["text", "heading"])
        self.assertEqual(d.pages[0][1].data, "Later heading")

    def test_pages_split_on_rule_and_empty_pages_skipped(self):
        d = guide.parse("# T\na\n---\n---\nb\n---\n")
        self.assertEqual(len(d.pages), 2)
        self.assertEqual(d.pages[1][0].data, [("b", False)])

    def test_blank_heading_fence(self):
        d = guide.parse("# T\n\n## Sub\n```\n**raw**\n```\n")
        kinds = [b.kind for b in d.pages[0]]
        self.assertEqual(kinds, ["blank", "heading", "verbatim"])
        self.assertEqual(d.pages[0][2].data, "**raw**")

    def test_crlf(self):
        d = guide.parse("# T\r\nx\r\n")
        self.assertEqual(d.pages[0][0].data, [("x", False)])


class InlineTests(unittest.TestCase):
    def test_emphasis_runs(self):
        self.assertEqual(guide.inline("a **b** c"), [("a ", False), ("b", True), (" c", False)])
        self.assertEqual(guide.inline("*x*"), [("x", True)])
        self.assertEqual(guide.inline("__x__ _y_"), [("x", True), (" ", False), ("y", True)])

    def test_unclosed_marker_is_literal(self):
        self.assertEqual(guide.inline("a **b"), [("a **b", False)])
        self.assertEqual(guide.inline("2 * 3"), [("2 * 3", False)])

    def test_code_link_escape(self):
        self.assertEqual(guide.inline("run `sweep` now"), [("run sweep now", False)])
        self.assertEqual(guide.inline("see [ch 3](03-calibration.md)"), [("see ch 3", False)])
        self.assertEqual(guide.inline(r"5\*3 and \\"), [("5*3 and \\", False)])

    def test_glyph_mapping(self):
        self.assertEqual(guide.to_glyphs("50Ω 90° 3µH é"), "50\x1e 90\x1f 3\x1dH ?")

    def test_cells(self):
        self.assertEqual(guide.split_cells("| a | b\\|c |"), ["a", "b|c"])
        self.assertEqual(guide.split_cells("|a|b"), ["a", "b"])
        self.assertTrue(guide.is_separator(["---", ":--:", "--:"]))
        self.assertFalse(guide.is_separator(["---", "x"]))
        self.assertEqual(guide.aligns_of(["---", ":--:", "--:", ":--"]), ["l", "c", "r", "l"])


class LayoutTests(unittest.TestCase):
    def test_geometry(self):
        g4, gh = guide.geom("H4"), guide.geom("H")
        self.assertEqual((g4.width, g4.rows, g4.row_h), (480, 28, 11))
        self.assertEqual((gh.width, gh.rows, gh.row_h), (320, 28, 8))

    def test_run_width_uses_real_glyphs(self):
        f = guide.geom("H").font
        self.assertEqual(guide.run_width([("iii", False)], f), 3 * f.glyph(ord("i"))[0])
        self.assertEqual(guide.run_width([("W", False), ("W", True)], f), 2 * f.glyph(ord("W"))[0])
        self.assertEqual(guide.run_width([("Ω", False)], f), f.glyph(0x1e)[0])

    def test_table_widths_and_gutter(self):
        t = guide.parse("|a|bbb|\n|---|--:|\n|cc|d|\n").pages[0][0].data
        f = guide.geom("H4").font
        widths, gutter = guide.layout_table(t, f)
        self.assertEqual(widths, [f.text_width("cc"), f.text_width("bbb")])
        self.assertEqual(gutter, f.glyph(ord(" "))[0])
        self.assertEqual(t.aligns, ["l", "r"])

    def test_page_rows(self):
        p = guide.parse("# T\nx\n\n|a|\n|-|\n|b|\n").pages[0]
        self.assertEqual(guide.page_rows(p), 2 + 3)


class CheckTests(unittest.TestCase):
    def test_clean_file(self):
        self.assertEqual(guide.check("# T\nshort line\n|a|b|\n|-|-|\n|1|2|\n", "t.md"), [])

    def test_errors(self):
        bad = ("no title\n" + "W" * 70 + "\n" + "\n" * 29 + "---\n![img](x.png)\n<b>x</b>\n  - nested\n"
               "café\n```\nopen fence\n")
        msgs = guide.check(bad, "bad.md")
        text = "\n".join(m for _, _, m in msgs)
        self.assertIn("no title", text.lower())
        self.assertIn("px on H4", text)
        self.assertIn("rows", text)
        self.assertIn("image", text)
        self.assertIn("HTML", text)
        self.assertIn("nested list", text)
        self.assertIn("U+00E9", text)
        self.assertIn("fence", text)
        self.assertTrue(any(lvl == "error" for _, lvl, _ in msgs))

    def test_table_too_many_columns(self):
        msgs = guide.check("# T\n|1|2|3|4|5|6|7|8|9|\n", "t.md")
        self.assertTrue(any("columns" in m and lvl == "error" for _, lvl, m in msgs))

    def test_cli_exit_code(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.md"); open(p, "w").write("# T\n" + "W" * 90 + "\n")
            self.assertEqual(guide.main(["check", p]), 1)
            open(p, "w").write("# T\nfine\n")
            self.assertEqual(guide.main(["check", p]), 0)


class RenderTests(unittest.TestCase):
    SRC = "# Title\nplain **bold**\n## Sub\n|k|v|\n|-|-:|\n|SWR|1.5|\n---\npage two\n"

    def test_page_count_and_size(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            paths = guide.render(self.SRC, "t.md", "H4", d)
            self.assertEqual([os.path.basename(p) for p in paths], ["t-H4-p01.png", "t-H4-p02.png"])
            self.assertTrue(all(os.path.getsize(p) > 100 for p in paths))

    def test_header_and_colours(self):
        import screen
        R = guide.render_page(guide.parse(self.SRC), 1, "H4")
        g = guide.geom("H4")
        self.assertEqual(R.px[0], screen.PAL["MENU"])                       # header background
        used = set(R.px)
        self.assertIn(screen.PAL["TRACE_1"], used)                         # emphasis drawn
        self.assertIn(screen.PAL["FG"], used)
        sep_y = g.row_h * (3 + 1) + 1 + g.row_h // 2                       # rows: text, heading, table hdr, sep
        self.assertEqual(R.px[sep_y * R.w + 2], screen.PAL["FG"])          # separator rule

    def test_right_alignment(self):
        src = "# T\n|a|bbbbbb|\n|-|-:|\n|x|1|\n"
        R = guide.render_page(guide.parse(src), 1, "H")
        g = guide.geom("H"); t = guide.parse(src).pages[0][0].data
        widths, gutter = guide.layout_table(t, g.font)
        y = g.row_h * (2 + 1) + 1                                          # third table row
        col1 = 2 + widths[0] + gutter
        left_px = [R.px[(y + dy) * R.w + col1] for dy in range(g.row_h)]
        self.assertTrue(all(p == 0 for p in left_px))                       # right-aligned '1' leaves the cell's left empty


class SourceFilesTests(unittest.TestCase):
    def test_sources_lint_clean(self):
        import glob
        src = glob.glob(os.path.join(ROOT, "docs", "manual", "guides-src", "*.md"))
        self.assertEqual(len(src), 21)
        for p in src:
            errs = [m for m in guide.check(open(p, encoding="utf-8").read(), p) if m[1] == "error"]
            self.assertEqual(errs, [], p)


class PackTests(unittest.TestCase):
    HAND = ["cal-checklist", "dev-status", "ant-workflow", "ant-swr-diag", "ant-radials", "ant-trim", "ant-tune-workflow",
            "ant-loading", "ant-decide",
            "pota-rules", "sota-rules", "pota-deploy", "pota-safety", "prop-skip", "choke-recipe", "choke-measure", "choke-ferrite",
            "ref-formulas", "dev-measure", "dev-console", "dev-formats"]
    GEN = ["ref-swr-table", "ref-db", "ref-reactance", "ant-lengths", "ant-bands", "coax-vf-loss", "dev-menu-map"]
    NAMES = sorted([n + ".md" for n in HAND + GEN] + ["README.md"])

    def test_dev_formats_lists_every_trace_format(self):
        import gen_formats
        text = open(os.path.join(ROOT, "docs", "manual", "guides-src", "dev-formats.md"), encoding="utf-8").read()
        for r in gen_formats.parse_formats():
            name = r["name"].replace("|", "")
            self.assertIn("| %s |" % name, text, "dev-formats.md lacks " + r["name"])

    def test_pack_builds_and_lints(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            files = guide.pack(d)
            self.assertEqual(sorted(os.path.basename(f) for f in files), self.NAMES)
            for f in files:
                errs = [m for m in guide.check(open(f, encoding="utf-8").read(), f) if m[1] == "error"]
                self.assertEqual(errs, [], f)
            swr = open(os.path.join(d, "ref-swr-table.md"), encoding="utf-8").read()
            self.assertIn("| 2.00 | 9.5 | 0.333 | 11.1 | 0.51 |", swr)
            coax = open(os.path.join(d, "coax-vf-loss.md"), encoding="utf-8").read()
            self.assertIn("| 14.2 |", coax); self.assertIn("0.46", coax)          # LMR-400 at 14.2 MHz
            ant = open(os.path.join(d, "ant-lengths.md"), encoding="utf-8").read()
            self.assertIn("| 20m |", ant); self.assertIn("33.0", ant)              # 468/14.175
            bands = open(os.path.join(d, "ant-bands.md"), encoding="utf-8").read()
            self.assertIn("| 20m | 14 | 14.35 |", bands)

    def test_committed_pack_is_current(self):
        import tempfile, filecmp
        out = os.path.join(ROOT, "GUIDES")
        with tempfile.TemporaryDirectory() as d:
            guide.pack(d)
            for f in os.listdir(d):
                self.assertTrue(filecmp.cmp(os.path.join(d, f), os.path.join(out, f), shallow=False), f + " is stale: run make -C docs/manual guides")


class HostViewerTests(unittest.TestCase):
    """The real C viewer (vna_modules/vna_guide.c) run on the host must draw exactly the text
    guide.py parses, page for page, for every shipped guide."""
    @classmethod
    def setUpClass(cls):
        import shutil, subprocess, tempfile
        cls.gcc = shutil.which("gcc")
        if not cls.gcc: return
        cls.tmp = tempfile.mkdtemp(); cls.exe = os.path.join(cls.tmp, "guide_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-I", ROOT, "-o", cls.exe, os.path.join(ROOT, "tests", "host", "guide_host.c")],
                           capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)

    @staticmethod
    def expected_pages(doc):
        pages = []
        for page in doc.pages or [[]]:
            lines = []
            for b in page:
                if b.kind == "text": lines.append("".join(t for t, _ in b.data))
                elif b.kind in ("heading", "verbatim"): lines.append(b.data)
                elif b.kind == "table":
                    for row in b.data.rows:
                        lines += ["".join(t for t, _ in cell) for cell in row[:guide.MAX_COLS]]
            pages.append([l for l in lines if l != ""])
        return pages

    def host_pages(self, path, keys):
        import re, subprocess
        out = subprocess.run([self.exe, path, keys], capture_output=True, text=True).stdout
        pages, cur = [], None
        for ln in out.split("\n"):
            if ln.startswith("=== page"): cur = []; pages.append(cur); continue
            m = re.match(r"\s*(\d+) @(\d+)\s*\|(.*)$", ln)
            if not m or cur is None: continue
            y, text = int(m.group(1)), re.sub(r"\{c\d+\}", "", m.group(3))
            if y == 1: continue                      # header bar
            cur.append(text)
        return [p for p in pages[:-1]]                 # the last "page draw" is the exit clear

    def test_pack_matches_reference(self):
        import glob
        if not self.gcc: self.skipTest("gcc not available")
        for path in sorted(glob.glob(os.path.join(ROOT, "GUIDES", "*.md"))):
            with self.subTest(guide=os.path.basename(path)):
                text = open(path, encoding="utf-8").read()
                doc = guide.parse(text, path)
                want = self.expected_pages(doc)
                got = self.host_pages(path, "n" * (len(want) + 2) + "x")
                self.assertEqual(len(got), len(want), "page count")
                for p, (g, w) in enumerate(zip(got, want)):
                    self.assertEqual(g, [guide.to_glyphs(x).replace("\x1e", "Ω").replace("\x1f", "°").replace("\x1d", "µ") for x in w], "page %d" % (p + 1))


if __name__ == "__main__":
    unittest.main()
