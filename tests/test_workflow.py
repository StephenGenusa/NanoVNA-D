"""Workflow reference sweep (vna_modules/vna_workref.c): CCM-RAM header, value-based staleness."""
import os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gcc = shutil.which("gcc")
        if not cls.gcc: return
        cls.tmp = tempfile.mkdtemp(); cls.exe = os.path.join(cls.tmp, "workref_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-Wextra", "-O1", "-I", ROOT, "-o", cls.exe,
                            os.path.join(ROOT, "tests", "host", "workref_host.c")], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        cls.build_stderr = r.stderr
        cls.tune_exe = os.path.join(cls.tmp, "tune_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-Wextra", "-O1", "-I", ROOT, "-o", cls.tune_exe,
                            os.path.join(ROOT, "tests", "host", "tune_host.c")], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        cls.tune_build_stderr = r.stderr

    def test_build_is_warning_free(self):
        if not self.gcc: self.skipTest("gcc not available")
        self.assertEqual(self.build_stderr, "", "host build produced warnings:\n" + self.build_stderr)

    def test_tune_build_is_warning_free(self):
        if not self.gcc: self.skipTest("gcc not available")
        self.assertEqual(self.tune_build_stderr, "", "tune_host build produced warnings:\n" + self.tune_build_stderr)

    def test_reference_sweep_state_machine(self):
        if not self.gcc: self.skipTest("gcc not available")
        r = subprocess.run([self.exe], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.rstrip("\n").endswith("OK"), r.stdout + r.stderr)

    def test_tune_arithmetic(self):
        if not self.gcc: self.skipTest("gcc not available")
        r = subprocess.run([self.tune_exe], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "", "tune_host stderr should be empty:\n" + r.stderr)
        self.assertTrue(r.stdout.rstrip("\n").endswith("OK"), r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
