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


if __name__ == "__main__":
    unittest.main()
