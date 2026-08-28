"""The device-look renderer (tools/manual/screen.py) against the real H4 screenshots in
docs/manual/captures/gt-*.png, whose sweep state was recorded beside them. Pixel parity is
expected: the only tolerated differences are the readout digits on the noisy open-port SMITH
screen (screenshot and data dump were separate sweeps) and one unexplained 7 px shift of a
positive PHASE value [verify on hardware]."""
import glob, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "manual"))
import compare_capture

LIMIT = {"gt-smith": 0.30}        # percent of pixels; default below


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
