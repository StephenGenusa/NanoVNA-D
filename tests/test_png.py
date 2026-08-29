"""PNG screenshot codec (vna_modules/vna_png.c): host round trip + stdlib validation."""
import os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import check_png

SCREENS = ("flat", "palette", "gradient", "c256", "c300", "noise")


class PngTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gcc = shutil.which("gcc")
        if not cls.gcc: return
        cls.tmp = tempfile.mkdtemp(); cls.exe = os.path.join(cls.tmp, "png_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-Wextra", "-O1", "-I", ROOT, "-o", cls.exe,
                            os.path.join(ROOT, "tests", "host", "png_host.c")], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        r = subprocess.run([cls.exe, cls.tmp, "encode"], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stdout + r.stderr)
        cls.encode_log = r.stdout

    def run_host(self, *args):
        if not self.gcc: self.skipTest("gcc not available")
        return subprocess.run([self.exe, self.tmp] + list(args), capture_output=True, text=True)

    def test_encode_all_screens_and_validate(self):
        if not self.gcc: self.skipTest("gcc not available")
        for name in SCREENS:
            info = check_png.check(os.path.join(self.tmp, name + ".png"), os.path.join(self.tmp, name + ".idx"))
            self.assertEqual((info["width"], info["height"]), (480, 320))
            self.assertTrue(info["ok"], name + ": " + info["error"])
        noise = os.path.getsize(os.path.join(self.tmp, "noise.png"))
        self.assertLess(noise, 1.5 * 480 * 320, "noise screen must stay under 1.5x raw")

    def test_compression_ratio(self):
        if not self.gcc: self.skipTest("gcc not available")
        flat = os.path.getsize(os.path.join(self.tmp, "flat.png"))
        pal = os.path.getsize(os.path.join(self.tmp, "palette.png"))
        self.assertLess(flat, 3000, "flat screen must compress to a few KB (got %d)" % flat)
        self.assertLess(pal, 480 * 320 // 8, "32-colour block screen must compress at least 8x (got %d)" % pal)

    def test_stream_is_fixed_huffman(self):
        if not self.gcc: self.skipTest("gcc not available")
        idat = check_png.idat_bytes(os.path.join(self.tmp, "palette.png"))
        self.assertEqual(idat[:2], b"\x78\x01")
        self.assertEqual((idat[2] >> 1) & 3, 1, "first deflate block must be BTYPE=01 (fixed Huffman)")

    def test_decode_round_trip(self):
        for name in SCREENS:
            r = self.run_host("decode", name)
            self.assertEqual(r.returncode, 0, name + ": " + r.stdout + r.stderr)
            self.assertIn("match", r.stdout)

    def test_dynamic_huffman_rejected(self):
        if not self.gcc: self.skipTest("gcc not available")
        check_png.write_dynamic_huffman_png(os.path.join(self.tmp, "dyn.png"))
        r = self.run_host("reject", "dyn")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Unsupported PNG", r.stdout)


if __name__ == "__main__":
    unittest.main()
