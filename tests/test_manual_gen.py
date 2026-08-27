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


if __name__ == "__main__":
    unittest.main()
