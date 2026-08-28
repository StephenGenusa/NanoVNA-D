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


if __name__ == "__main__":
    unittest.main()
