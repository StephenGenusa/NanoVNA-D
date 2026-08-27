"""Checks for the manual generators (tools/manual). Run: python3 -m unittest tests.test_manual_gen"""
import os, sys, unittest
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
        rc = gen_menus.main([])
        self.assertEqual(rc, 0)
        md = open("docs/manual/09-menu-map.md", encoding="utf-8").read()
        self.assertTrue(md.startswith("<!-- generated by tools/manual/gen_menus.py"))
        self.assertIn("## Top level", md)
        self.assertIn("## DISPLAY › FORMAT", md)
        self.assertIn("img/menu-formatS11-H4.svg", md)
        self.assertIn("img/menu-formatS11-H.svg", md)
        self.assertIn("| SWR ANT | select |", md)
        self.assertIn("H4 only.", md)                                   # CABLE TYPE row
        self.assertIn("[describe]", md)
        for t in ("H", "H4"):
            self.assertTrue(os.path.exists("docs/manual/img/menu-top-%s.svg" % t))
            self.assertTrue(os.path.exists("docs/manual/img/menu-formatS11-%s.svg" % t))
        self.assertFalse(os.path.exists("docs/manual/img/menu-measure_swr_bw-H.svg"))  # F303-only table
        self.assertEqual(md.count("\n## "), 43)                          # one section per reachable table
        svgs = [f for f in os.listdir("docs/manual/img") if f.startswith("menu-") and f.endswith(".svg")]
        self.assertEqual(len(svgs), 85)                                  # 43 H4 + 42 H
        self.assertEqual(len([f for f in svgs if f.endswith("-H4.svg")]), 43)
        self.assertEqual(len([f for f in svgs if f.endswith("-H.svg")]), 42)
        self.assertNotRegex(md.replace("\n", "").replace("\t", ""), "[\x00-\x1f]")  # no raw control bytes
        self.assertIn("‹IARU R1›", md)                                   # per-row sample, not a flat "OFF"
        self.assertIn("## DISPLAY › FORMAT › MORE  (`menu_format2`)", md)   # breadcrumb drops the arrow, row keeps it
        self.assertNotIn("› ›", md)                                # no doubled arrow in breadcrumbs
        st = gen_menus.status()
        self.assertIn("describe", st)
        self.assertNotIn("menu_formatS11/SWR ANT", st["describe"])


class GeneratedUpToDateTests(unittest.TestCase):
    def test_menu_map_matches_source(self):
        """The checked-in chapter must equal a fresh generation (regenerate after ui.c changes)."""
        before = open("docs/manual/09-menu-map.md", encoding="utf-8").read()
        gen_menus.main([])
        after = open("docs/manual/09-menu-map.md", encoding="utf-8").read()
        self.assertEqual(before, after, "docs/manual/09-menu-map.md is stale: run python3 tools/manual/gen_menus.py")


if __name__ == "__main__":
    unittest.main()
