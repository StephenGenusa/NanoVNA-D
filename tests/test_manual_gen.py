"""Checks for the manual generators (tools/manual). Run: python3 -m unittest tests.test_manual_gen"""
import os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "manual"))
os.chdir(ROOT)

import srcinfo


class SrcInfoTests(unittest.TestCase):
    def test_flags_have_target_define_and_board_include(self):
        f = srcinfo.compile_flags("F303")
        self.assertIn("-DNANOVNA_F303", f)
        self.assertIn("-INANOVNA_STM32_F303", f)
        self.assertNotIn("-DNANOVNA_F303", srcinfo.compile_flags("F072"))
        self.assertTrue(all(not x.startswith("-DVERSION") for x in f))

    def test_preprocess_resolves_guards(self):
        h4 = srcinfo.preprocess("F303")
        h = srcinfo.preprocess("F072")
        self.assertIn("const menuitem_t menu_top[] = {", h4)
        self.assertIn("MEASURE_S11_SWR_BW", h4)      # F303-only feature present
        self.assertNotIn("MEASURE_S11_SWR_BW", h)    # and absent on F072

    def test_eval_constants(self):
        c = srcinfo.eval_constants("F303", ["LCD_WIDTH", "LCD_HEIGHT", "MENU_BUTTON_WIDTH", "AREA_HEIGHT_NORMAL"])
        self.assertEqual(c["LCD_WIDTH"], 480)
        self.assertEqual(c["LCD_HEIGHT"], 320)
        self.assertEqual(c["MENU_BUTTON_WIDTH"], 7 + 12 * 7)
        self.assertEqual(c["AREA_HEIGHT_NORMAL"], 305)
        c = srcinfo.eval_constants("F072", ["LCD_WIDTH", "MENU_BUTTON_WIDTH", "AREA_HEIGHT_NORMAL"])
        self.assertEqual(c["LCD_WIDTH"], 320)
        self.assertEqual(c["MENU_BUTTON_WIDTH"], 7 + 12 * 6)
        self.assertEqual(c["AREA_HEIGHT_NORMAL"], 233)


import layout


class LayoutTests(unittest.TestCase):
    def test_h4(self):
        L = layout.get_layout("F303")
        self.assertEqual((L.lcd_w, L.lcd_h, L.offset_x, L.width, L.height), (480, 320, 15, 455, 304))
        self.assertEqual(L.menu_w, 91)
        self.assertEqual(L.button_height(3), 305 // 8)   # fewer than MENU_BUTTON_MIN items -> min applies
        self.assertEqual(L.button_height(12), 305 // 12)
        self.assertEqual(L.button_height(40), 305 // 16)
        self.assertEqual((L.font_name, L.font_w, L.font_h, L.font_str_h), ("x7x11b", 7, 11, 11))
        self.assertEqual(L.sfont_name, "x7x11b")
        self.assertEqual(L.icon_w, 11)

    def test_h(self):
        L = layout.get_layout("F072")
        self.assertEqual((L.lcd_w, L.lcd_h, L.offset_x, L.width, L.height), (320, 240, 10, 300, 232))
        self.assertEqual(L.menu_w, 79)
        self.assertEqual((L.font_name, L.font_w, L.font_h, L.font_str_h), ("x6x10", 6, 10, 11))
        self.assertEqual((L.sfont_name, L.sfont_w, L.sfont_h, L.sfont_str_h), ("x5x7", 5, 7, 8))

    def test_palette(self):
        L = layout.get_layout("F303")
        self.assertEqual(L.palette["MENU"], (230, 230, 230))
        self.assertEqual(L.palette["LINK"], (0, 0, 192))
        self.assertEqual(L.palette["RISE_EDGE"], (255, 255, 255))
        self.assertEqual(L.rgb("BG"), "#000000")
        self.assertEqual(L.palette_index("LINK"), 25)


import fonts


class FontTests(unittest.TestCase):
    def test_glyph_tables(self):
        for name, w, h in (("x5x7", 5, 7), ("x6x10", 6, 10), ("x7x11b", 7, 11)):
            f = fonts.load_font(name)
            self.assertEqual((f.width, f.height, f.start), (w, h, 0x16), name)
            self.assertEqual(len(f.glyphs), 0x7F - 0x16, name)          # 0x16..0x7E
            for gw, rows in f.glyphs:
                self.assertTrue(1 <= gw <= 8, name)
                self.assertEqual(len(rows), h, name)
            self.assertEqual(f.pixels(" ", 0, 0), [], name)             # space is blank
            self.assertGreater(sum(bin(r).count("1") for r in f.glyph(ord("W"))[1]),
                               sum(bin(r).count("1") for r in f.glyph(ord("I"))[1]), name)

    def test_width_and_pixels(self):
        f = fonts.load_font("x6x10")
        self.assertEqual(f.text_width("AB"), f.glyph(ord("A"))[0] + f.glyph(ord("B"))[0])
        px = f.pixels("A", 10, 20)
        self.assertTrue(all(10 <= x < 18 and 20 <= y < 30 for x, y in px))
        self.assertGreater(len(px), 5)
        self.assertEqual(f.pixels("\x05", 0, 0), [])                 # control byte: blank
        self.assertIn("<path", fonts.svg_text(f, "Hi", 0, 0, "#000000"))

    def test_control_byte_escape_sequences(self):
        # Control bytes < 0x09 are colour escapes that consume the next byte
        f = fonts.load_font("x6x10")
        # Escape sequence + colour index + 'A' should have width of only 'A'
        self.assertEqual(f.text_width("\x02\x19A"), f.glyph(ord("A"))[0])
        # Pixels with escape should start at x=0 (A at origin, escape consumes no space)
        px = f.pixels("\x02\x19A", 0, 0)
        self.assertGreater(len(px), 0)
        self.assertEqual(min(x for x, y in px), 0)
        # Single escape byte with no following byte should render nothing
        self.assertEqual(f.pixels("\x05", 0, 0), [])


import menus


class MenuParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h4 = srcinfo.preprocess("F303")
        cls.h = srcinfo.preprocess("F072")

    def test_decode_c_string(self):
        self.assertEqual(menus.decode_c_string('"\\x1B" " MORE"'), "\x1b MORE")
        self.assertEqual(menus.decode_c_string('"CABLE LOSS\\n " "\\x02" "\\x19" "%b.3F" "dB"'), "CABLE LOSS\n \x02\x19%b.3FdB")
        self.assertEqual(menus.decode_c_string('"a\\"b\\\\c"'), 'a"b\\c')
        self.assertEqual(menus.plain_label("X\x02\x19%s"), "X%s")

    def test_counts_match_source(self):
        m4 = menus.parse_menus(self.h4)
        m = menus.parse_menus(self.h)
        self.assertEqual(len(m4), 44)  # definitions only; forward declarations excluded
        self.assertEqual(len(m), 43)   # definitions only; forward declarations excluded
        n4 = sum(len([i for i in mm.items if i.kind != "next"]) for mm in m4.values())
        n = sum(len([i for i in mm.items if i.kind != "next"]) for mm in m.values())
        # 324 / 310 '{ MT_' entries in the preprocessed source include the MT_NEXT sentinels
        # (one per table) and the BACK item each continuation appends; check the raw count instead:
        self.assertEqual(self.h4.count("{ MT_"), 324)
        self.assertEqual(self.h.count("{ MT_"), 310)
        self.assertGreater(n4, n)

    def test_top_and_continuation(self):
        m4 = menus.parse_menus(self.h4)
        top = m4["menu_top"]
        self.assertEqual([i.label for i in top.items][:5], ["DISPLAY", "MARKER", "STIMULUS", "CALIBRATE", "RECALL"])
        fmt = m4["menu_formatS11"]
        self.assertEqual(fmt.items[-1].label, "\x1a BACK")            # menu_back continuation expanded
        self.assertEqual(fmt.items[-1].kind, "callback")
        self.assertTrue(any(i.label == "SWR ANT" for i in fmt.items))
        self.assertTrue(any(i.kind == "submenu" and i.ref == "menu_format2" for i in fmt.items))

    def test_links_and_tree(self):
        m4 = menus.parse_menus(self.h4)
        links = menus.callback_links(self.h4)
        self.assertIn("menu_measure_cb", links)
        self.assertIn("menu_measure", links["menu_measure_cb"])          # via menu_measure_list[...]
        self.assertIn("menu_measure_swr_bw", links["menu_measure_cb"])
        self.assertEqual(links["menu_ham_bands_sel_acb"], ["menu_ham_bands"])
        tree = menus.build_tree(m4, links)
        names = [t for t, _ in tree]
        self.assertEqual(names[0], "menu_top")
        self.assertIn("menu_formatS11", names)
        self.assertIn("menu_measure_swr_bw", names)
        unreachable = sorted(set(m4) - set(names) - {"menu_back"})
        self.assertEqual(unreachable, [], "tables not reachable from menu_top: %r" % unreachable)
        path = dict(tree)["menu_formatS11"]
        self.assertEqual(path[:2], ["DISPLAY", "FORMAT"])

    def test_variant_breadcrumbs_no_invented_hierarchy(self):
        """I2: a callback shared by several items, or dispatching through a
        menu_*_list[] array, must not make build_tree invent a breadcrumb out of
        whichever sibling item happened to trigger the walk first."""
        m4 = menus.parse_menus(self.h4)
        links = menus.callback_links(self.h4)
        variant = menus.variant_tables(m4, links)
        # menu_format_acb is shared by every FORMAT row but only actually pushes on
        # SMITH; both smith tables must be flagged variant and not share a heading path.
        self.assertIn("menu_marker_s11smith", variant)
        self.assertIn("menu_marker_s21smith", variant)
        tree = dict(menus.build_tree(m4, links))
        self.assertNotEqual(tree["menu_marker_s11smith"], tree["menu_marker_s21smith"])
        # menu_measure_acb/_cb dispatch through menu_measure_list[]; every measure-mode
        # table must be reachable without an accumulating chain of "OFF" segments. The
        # table actually reached directly by the top-level MEASURE button in its default
        # (MEASURE_NONE) state -- menu_measure itself, first in menu_measure_list[] --
        # keeps the plain "MEASURE" path and is *not* variant; only the other,
        # state-dependent tables need a mode-name segment to tell them apart from it.
        self.assertNotIn("menu_measure", variant)
        self.assertEqual(tree["menu_measure"], ["MEASURE"])
        for name in ("menu_measure_swr_bw", "menu_measure_cable"):
            self.assertIn(name, variant)
            self.assertNotIn("OFF", tree[name])
            self.assertNotIn("L/C MATCH ›", " › ".join(tree[name]))
        # a callback shared by many items but resolving to exactly one target (every
        # calibration step in menu_calop pushes menu_save) is not ambiguous -- its own
        # item label ("DONE") is kept, not replaced.
        self.assertNotIn("menu_save", variant)
        self.assertIn("DONE", tree["menu_save"])
        # global sanity the finding calls out explicitly: no heading path anywhere
        # contains a repeated "OFF" segment or an invented "L/C MATCH ›" prefix, and
        # every table gets a distinct heading once its own name is included.
        headings = ["%s (%s)" % (" › ".join(path) if path else "Top level", name)
                    for name, path in tree.items()]
        self.assertEqual(len(headings), len(set(headings)))
        for path in tree.values():
            self.assertNotIn("OFF › OFF", " › ".join(path))
            self.assertNotIn("L/C MATCH ›", " › ".join(path))
        self.assertEqual("## MEASURE  (`menu_measure`)", "## %s  (`%s`)%s" % (
            " › ".join(tree["menu_measure"]), "menu_measure", " (variant)" if "menu_measure" in variant else ""))
        self.assertEqual("## MEASURE › SWR BW  (`menu_measure_swr_bw`) (variant)", "## %s  (`%s`)%s" % (
            " › ".join(tree["menu_measure_swr_bw"]), "menu_measure_swr_bw",
            " (variant)" if "menu_measure_swr_bw" in variant else ""))


import json, re, render_menu


class RenderMenuTests(unittest.TestCase):
    def test_label_text(self):
        samples = {"MARKER %d": ["3"], "X\n %s": ["OFF"]}
        it = menus.Item("adv", "0", "MARKER %d", "cb", "t")
        self.assertEqual(render_menu.label_text(it, samples), "MARKER 3")
        it = menus.Item("adv", "0", "X\n \x02\x19%s", "cb", "t")
        self.assertEqual(render_menu.label_text(it, samples), "X\n \x02\x19OFF")
        it = menus.Item("adv", "0", "Y %d", "cb", "t")            # no sample -> placeholder
        self.assertEqual(render_menu.label_text(it, {}), "Y --")
        # firmware printf flags, and %%%% collapsing to a single "%" (two printf passes)
        it = menus.Item("adv", "0", "CABLE LOSS\n \x02\x19%b.3FdB", "cb", "t")
        self.assertEqual(render_menu.label_text(it, {"CABLE LOSS\n %b.3FdB": ["1.20"]}),
                          "CABLE LOSS\n \x02\x191.20dB")
        it = menus.Item("adv", "0", "VELOCITY F.\n \x02\x19%d%%%%", "cb", "t")
        self.assertEqual(render_menu.label_text(it, {"VELOCITY F.\n %d%%%%": ["70"]}),
                          "VELOCITY F.\n \x02\x1970%")

    def test_row_sample_derives_from_data(self):
        """I3: menu_trace's "TRACE %d" and menu_save/recall's "Empty %d" show item.data
        itself, so row_sample should derive the sample directly rather than needing a
        hand-authored list in menu_samples.json -- but only for the repeated-slot pattern
        this is meant for (>=2 adv rows in the table sharing the label), never for a
        one-off selector row that merely displays live state through the same shape
        (new breakage #1: IF BANDWIDTH/SWEEP POINTS/IF OFFSET/SERIAL SPEED must not come
        out as a fabricated "0")."""
        it = menus.Item("adv", "2", "TRACE %d", "cb", "menu_trace")
        self.assertEqual(render_menu.label_text(it, render_menu.row_sample({}, it, occ=2, total=4)), "TRACE 2")
        it = menus.Item("adv", "5", "Empty %d", "cb", "menu_save")
        self.assertEqual(render_menu.label_text(it, render_menu.row_sample({}, it, occ=5, total=7)), "Empty 5")
        # menu_power's value (2 + data*2 mA) is a function of data, not data itself, and
        # its data literals are C bit-shift expressions rather than plain decimals -- must
        # not be auto-derived (it needs the hand list in menu_samples.json instead, I3)
        it = menus.Item("adv", "(1<<0)", "%u mA", "cb", "menu_power")
        self.assertEqual(render_menu.label_text(it, render_menu.row_sample({}, it, occ=0, total=4)), "-- mA")

    def test_row_sample_does_not_derive_a_one_off_live_state_selector(self):
        """New breakage #1: a selector row that is the *only* row in its table using a
        given "%u"/"%d" label (IF BANDWIDTH, SWEEP POINTS, IF OFFSET, SERIAL SPEED all
        push into a real sub-table via a callback that ignores their data=0 placeholder
        and shows the current global setting) must not be auto-derived from item.data --
        that would fabricate a "0" for genuinely unknown live state. total=1 (or
        unspecified) must yield no sample at all."""
        it = menus.Item("adv", "0", "IF BANDWIDTH\n %u" + "Hz", "menu_bandwidth_sel_acb", "menu_scale")
        self.assertEqual(render_menu.label_text(it, render_menu.row_sample({}, it, occ=0, total=1)),
                          "IF BANDWIDTH\n --Hz")
        self.assertEqual(render_menu.label_text(it, render_menu.row_sample({}, it)), "IF BANDWIDTH\n --Hz")

    def test_row_sample_table_scoped_length_mismatch_raises(self):
        """I4: a table-scoped sample list whose length doesn't match the number of rows
        on this target using that label must fail loudly, not render a wrong/short row."""
        it = menus.Item("adv", "0", "%s", "cb", "menu_x")
        samples = {"menu_x": {"%s": ["A", "B"]}}
        with self.assertRaises(RuntimeError):
            render_menu.row_sample(samples, it, occ=0, total=3)
        # matching length is fine
        self.assertEqual(render_menu.row_sample(samples, it, occ=1, total=2)["%s"], ["B"])

    def test_label_positions_ignores_interleaved_unrelated_items(self):
        """I4: occurrence position must be counted per (table, label), not by raw
        position in the table -- menu_save's SD-card row (a different label) precedes
        its "Empty %d" rows and must not shift their sample-list alignment."""
        items = [
            menus.Item("callback", "0", "SAVE TO\n SD CARD", "cb", "menu_save"),
            menus.Item("adv", "0", "Empty %d", "cb", "menu_save"),
            menus.Item("adv", "1", "Empty %d", "cb", "menu_save"),
        ]
        positions, counts = render_menu.label_positions(items)
        self.assertEqual(positions[id(items[1])], 0)
        self.assertEqual(positions[id(items[2])], 1)
        self.assertEqual(counts[("menu_save", "Empty %d")], 2)
        self.assertNotIn(id(items[0]), positions)          # not an adv item -> not tracked

    def test_svg_geometry(self):
        L = layout.get_layout("F303")
        m4 = menus.parse_menus(srcinfo.preprocess("F303"))
        svg = render_menu.render_menu_svg(m4["menu_top"], L, {})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('viewBox="0 0 480 320"', svg)
        n = len(m4["menu_top"].items)
        h = L.button_height(n)
        # one filled button body per item at the expected y positions
        for i in range(n):
            self.assertIn('y="%d"' % (L.menu_y_off + i * h + L.menu_border), svg)
        self.assertIn(L.rgb("MENU"), svg)
        self.assertIn(L.rgb("RISE_EDGE"), svg)
        self.assertIn("<path", svg)                                   # glyph pixels present

    def test_small_font_fallback(self):
        L = layout.get_layout("F072")
        items = [menus.Item("callback", "0", "LINE1\nLINE2\nLINE3", None, "t")] * 16
        items.append(menus.Item("next", "0", "", None, "t"))
        m = menus.Menu("menu_x", items[:-1], False)
        svg = render_menu.render_menu_svg(m, L, {})
        self.assertIn('data-font="x5x7"', svg)

    def test_icons(self):
        L = layout.get_layout("F303")
        m4 = menus.parse_menus(srcinfo.preprocess("F303"))
        top = m4["menu_top"]
        svg = render_menu.render_menu_svg(top, L, {"icons": {"DISPLAY": "checked"}})
        x0, bw = L.lcd_w - L.menu_w, L.menu_border
        h = L.button_height(len(top.items))
        ix, iy = x0 + bw + L.menu_icon_off, L.menu_y_off + (h - L.icon_h) // 2
        # 11x11 checkbox outline
        self.assertIn('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="1"/>'
                       % (ix, iy, L.icon_w - 1, L.icon_h - 1, L.rgb("MENU_TEXT")), svg)
        # filled inner square (checked state)
        self.assertIn('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                       % (ix + 3, iy + 3, L.icon_w - 6, L.icon_h - 6, L.rgb("MENU_TEXT")), svg)
        # the icon button's label (DISPLAY, item 0) starts strictly right of a plain
        # button's label (MARKER, item 1) -- icon_off + icon_size vs. plain text_off
        groups = re.findall(r'<g data-font="[^"]*">(.*?)</g>', svg, re.S)
        starts = [int(re.search(r'M(-?\d+) ', g).group(1)) for g in groups if "<path" in g]
        self.assertGreater(starts[0], starts[1])


import gen_menus


class GenMenusTests(unittest.TestCase):
    def test_generate(self):
        # C1: generate into a scratch directory, never into the tracked docs/manual tree
        # -- otherwise running the suite regenerates the checked-in files as a side
        # effect and GeneratedUpToDateTests below could never fail.
        with tempfile.TemporaryDirectory() as tmp:
            rc = gen_menus.main(["--out", tmp])
            self.assertEqual(rc, 0)
            with open(os.path.join(tmp, "09-menu-map.md"), encoding="utf-8") as f:
                md = f.read()
            self.assertTrue(md.startswith("<!-- generated by tools/manual/gen_menus.py"))
            self.assertIn("## Top level", md)
            self.assertIn("## DISPLAY › FORMAT", md)
            self.assertIn("img/menu-formatS11-H4.svg", md)
            self.assertIn("img/menu-formatS11-H.svg", md)
            self.assertIn("| SWR ANT | select |", md)
            self.assertIn("H4 only.", md)                                   # CABLE TYPE row
            self.assertNotIn("[describe]", md)                               # every item described
            for t in ("H", "H4"):
                self.assertTrue(os.path.exists(os.path.join(tmp, "img", "menu-top-%s.svg" % t)))
                self.assertTrue(os.path.exists(os.path.join(tmp, "img", "menu-formatS11-%s.svg" % t)))
            self.assertFalse(os.path.exists(os.path.join(tmp, "img", "menu-measure_swr_bw-H.svg")))  # F303-only
            self.assertEqual(md.count("\n## "), 43)                          # one section per reachable table
            svgs = [f for f in os.listdir(os.path.join(tmp, "img")) if f.startswith("menu-") and f.endswith(".svg")]
            self.assertEqual(len(svgs), 85)                                  # 43 H4 + 42 H
            self.assertEqual(len([f for f in svgs if f.endswith("-H4.svg")]), 43)
            self.assertEqual(len([f for f in svgs if f.endswith("-H.svg")]), 42)
            self.assertNotRegex(md.replace("\n", "").replace("\t", ""), "[\x00-\x1f]")  # no raw control bytes
            self.assertIn("‹IARU R1›", md)                                   # per-row sample, not a flat "OFF"
            self.assertIn("## DISPLAY › FORMAT › MORE  (`menu_format2`)", md)   # breadcrumb drops the arrow, row keeps it
            self.assertNotIn("› ›", md)                                # no doubled arrow in breadcrumbs
            # I2: variant tables get a distinguishing suffix, and never an invented
            # "OFF" chain or a duplicate heading.
            self.assertIn(" (variant)", md)
            self.assertNotIn("OFF › OFF", md)
            headings = re.findall(r"^## .*$", md, re.M)
            self.assertEqual(len(headings), len(set(headings)))
            # I3: per-row samples for the tables the finding calls out by name.
            for needle in ("‹1›", "‹2›", "‹3›", "‹4›", "‹5›", "‹6›", "‹7›", "‹8›"):  # MARKER
                self.assertIn(needle, md)
            self.assertIn("‹2 mA›", md); self.assertIn("‹8 mA›", md)          # POWER
            self.assertIn("‹51 point›", md); self.assertIn("‹401 point›", md)  # SWEEP POINTS (H4)
            self.assertIn("TRACE ‹0›", md); self.assertIn("Empty ‹0›", md)     # derived straight from data
            # no leading double space before a bare ‹...› value (the smith tables: a
            # label with no static text before its "%s" must not render " ‹LIN›")
            self.assertNotIn("|  ‹", md)
            # the "\n " (newline + label's own indent space) join collapses to one
            # space -- a genuine double space inside a label (e.g. "POWER  AUTO") is
            # untouched, so check the specific \n-join case instead of banning "  " outright
            self.assertIn("CABLE LOSS ‹1.20dB›", md)
        st = gen_menus.status()
        self.assertIn("describe", st)
        self.assertIn("samples", st)
        self.assertNotIn("menu_formatS11/SWR ANT", st["describe"])
        # I6: a genuinely unfillable label (no sample list reaches it at all) is tracked
        self.assertEqual(st["samples"], [])                                # every value button has a sample
        # minor: glyph translation applied before keys are built -- no raw control bytes
        for key in st["describe"] + st["samples"]:
            self.assertNotRegex(key, "[\x00-\x1f]")

    def test_row_order_never_drops_a_target_only_item(self):
        """I5: a table present on both targets must union its rows rather than only
        iterating the reference device's items. There is no real H-only item in the
        current firmware to exercise this against, so fabricate one directly against
        the helper."""
        h4_items = [menus.Item("adv", "0", "SHARED", "cb", "menu_x"),
                    menus.Item("next", "0", "", "menu_back", "menu_x")]
        h_items = [menus.Item("adv", "0", "SHARED", "cb", "menu_x"),
                   menus.Item("adv", "0", "H ONLY ITEM", "cb", "menu_x"),
                   menus.Item("next", "0", "", "menu_back", "menu_x")]
        data = {"H4": ({"menu_x": menus.Menu("menu_x", h4_items, False)}, {}, [], None, set()),
                "H": ({"menu_x": menus.Menu("menu_x", h_items, False)}, {}, [], None, set())}
        rows = gen_menus._row_order("menu_x", data, {"H4": True, "H": True})
        labels = [(gen_menus._first_line(it), dev, avail) for it, dev, avail in rows]
        self.assertIn(("SHARED", "H4", "both"), labels)
        self.assertIn(("H ONLY ITEM", "H", "H"), labels)
        # H4's own order comes first, the H-only item is appended after it
        self.assertLess(labels.index(("SHARED", "H4", "both")), labels.index(("H ONLY ITEM", "H", "H")))

    def test_localize_samples_per_target_override(self):
        """I3/I4: a table-scoped list may be a per-target dict; resolving for a target
        it doesn't cover must fail loudly rather than silently dropping the row."""
        samples = {"menu_x": {"%d": {"H4": ["1", "2"]}}}
        self.assertEqual(gen_menus._localize_samples(samples, "H4")["menu_x"]["%d"], ["1", "2"])
        with self.assertRaises(RuntimeError):
            gen_menus._localize_samples(samples, "H")


class GeneratedUpToDateTests(unittest.TestCase):
    def test_menu_map_matches_source(self):
        """The checked-in chapter and images must equal a fresh generation into a
        scratch directory (regenerate after a ui.c change with
        python3 tools/manual/gen_menus.py). Comparing fresh-to-fresh would never fail
        -- and never writes into the tracked docs/manual tree as a side effect of
        running the suite (C1)."""
        with tempfile.TemporaryDirectory() as tmp:
            gen_menus.main(["--out", tmp])
            with open(os.path.join(tmp, "09-menu-map.md"), encoding="utf-8") as f:
                fresh_md = f.read()
            fresh_imgs = sorted(f for f in os.listdir(os.path.join(tmp, "img"))
                                 if f.startswith("menu-") and f.endswith(".svg"))
            checked_imgs = sorted(f for f in os.listdir("docs/manual/img")
                                   if f.startswith("menu-") and f.endswith(".svg"))
            self.assertEqual(checked_imgs, fresh_imgs,
                              "docs/manual/img/*.svg set is stale: run python3 tools/manual/gen_menus.py")
            with open("docs/manual/09-menu-map.md", encoding="utf-8") as f:
                checked_md = f.read()
            self.assertEqual(checked_md, fresh_md,
                              "docs/manual/09-menu-map.md is stale: run python3 tools/manual/gen_menus.py")
            for name in checked_imgs:
                with open(os.path.join("docs/manual/img", name), encoding="utf-8") as f:
                    a = f.read()
                with open(os.path.join(tmp, "img", name), encoding="utf-8") as f:
                    b = f.read()
                self.assertEqual(a, b, "docs/manual/img/%s is stale" % name)


import gen_console, gen_formats


class GenConsoleTests(unittest.TestCase):
    def test_generate(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = gen_console.generate(tmp)
            self.assertEqual(r["commands"], 49)                      # H4 (H has the same set today)
            md = open(os.path.join(tmp, "08-console.md"), encoding="utf-8").read()
        self.assertTrue(md.startswith("<!-- generated by tools/manual/gen_console.py"))
        self.assertIn("| `save` | `save 0..6` |", md)                 # %s/%d substituted, prefix stripped
        self.assertIn("`power {0-3}\\|{255 - auto}`", md)              # pipes escaped inside table cells
        self.assertIn("sweep {start\\|stop\\|center", md)              # list constant substituted
        self.assertIn("| `*IDN?` |", md)
        self.assertNotIn("usage:", md)
        self.assertNotIn("current:", md)
        self.assertEqual(md.count("\n| `"), 49)
        self.assertNotRegex(md.replace("\n", "").replace("\t", ""), "[\\x00-\\x1f]")

    def test_parse_helpers(self):
        self.assertEqual(gen_console._split_args('"a, b", x, (1, 2)'), ['"a, b"', "x", "(1, 2)"])
        self.assertEqual(gen_console._int_expr("7 -1"), 6)
        with self.assertRaises(ValueError):
            gen_console._int_expr("__import__('os')")


class GenFormatsTests(unittest.TestCase):
    def test_generate(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = gen_formats.generate(tmp)
            self.assertEqual(r["formats"], 31)
            md = open(os.path.join(tmp, "02-trace-formats.md"), encoding="utf-8").read()
        self.assertTrue(md.startswith("<!-- generated by tools/manual/gen_formats.py"))
        self.assertEqual(md.count("\n| "), 31 + 1)                    # rows + header (separator starts with |-)
        self.assertIn("| \\|Z\\| | `z` | ✓ |  | Ω | 50 Ω |", md)         # pipes escaped, console name, S11 only
        self.assertIn("| DELAY | `delay` | ✓ | ✓ | s | 1 ns |", md)     # SI prefix on the scale
        self.assertIn("| SWR ANT | `swrant` | ✓ |", md)
        self.assertIn("| Rser | `rser` |  | ✓ |", md)                   # S21-only format
        self.assertNotIn("[describe]", md)                              # every format described
        self.assertNotRegex(md.replace("\n", ""), "[\\x00-\\x1f]")


class GeneratedConsoleFormatsUpToDateTests(unittest.TestCase):
    def test_chapters_match_source(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            gen_console.generate(tmp)
            gen_formats.generate(tmp)
            for name in ("08-console.md", "02-trace-formats.md"):
                fresh = open(os.path.join(tmp, name), encoding="utf-8").read()
                committed = open(os.path.join("docs", "manual", name), encoding="utf-8").read()
                self.assertEqual(committed, fresh, "docs/manual/%s is stale: run the generator" % name)


if __name__ == "__main__":
    unittest.main()
