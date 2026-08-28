"""The device-look renderer (tools/manual/screen.py) against the real H4 screenshots in
docs/manual/captures/gt-*.png, whose sweep state was recorded beside them. Pixel parity is
expected; the only tolerated differences are last-digit / sign noise in readouts of values that
the 9-digit `data` dump cannot reproduce exactly (e.g. -0.00dB vs 0.00dB at an open port)."""
import glob, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "manual"))
import compare_capture

LIMIT = {}                          # percent of pixels per capture; default below


class RenderMatchesCapture(unittest.TestCase):
    def test_ground_truth_captures(self):
        caps = sorted(glob.glob(os.path.join(compare_capture.CAP, "gt-*.json")))
        self.assertTrue(caps, "no ground-truth captures found")
        for path in caps:
            cid = os.path.basename(path)[:-5]
            with self.subTest(capture=cid):
                bad, total, _ = compare_capture.compare(cid)
                pct = 100.0 * bad / total
                self.assertLessEqual(pct, LIMIT.get(cid, 0.15), "%s: %d px (%.2f%%) differ" % (cid, bad, pct))


if __name__ == "__main__":
    unittest.main()
