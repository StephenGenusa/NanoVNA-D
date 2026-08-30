"""Workflow panels: the reference sweep (vna_modules/vna_workref.c) - CCM-RAM header and
value-based staleness - plus a pure-Python width check on the TUNE and CHOKE panel rows in
measure.c."""
import os, re, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The workflow panels invalidate 5 * STR_MEASURE_WIDTH = 5 * 10 characters (measure.c
# prepare_tune / prepare_choke), so every row draw_tune() / draw_choke() can print must fit in
# 50 columns in its widest possible form.
MEASURE_ROW_COLUMNS = 50
FLOAT_COLUMNS = 7          # %F / %q / %f worst case, e.g. "-123.45"
INT_COLUMNS = 5            # %d / %u worst case with no explicit field width


def _read(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return f.read()


def _unescape(s):
    return s.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def _literals(expr):
    """Every C string literal in an expression, unescaped."""
    return [_unescape(m.group(1)) for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', expr)]


def _split_top_level(s):
    """Split a C argument list on commas that are not inside (), [], {} or a string."""
    out, depth, cur, i, in_str = [], 0, "", 0, False
    while i < len(s):
        c = s[i]
        if in_str:
            if c == "\\":
                cur += s[i:i + 2]; i += 2; continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            out.append(cur); cur = ""; i += 1; continue
        cur += c; i += 1
    out.append(cur)
    return out


def _function_body(src, signature):
    start = src.index(signature)
    return src[start:src.index("\n}\n", start)]


def _cell_printf_calls(body):
    """Argument lists of every cell_printf() in a function body."""
    calls = []
    for m in re.finditer(r"cell_printf\(", body):
        i = m.end(); depth = 1; in_str = False; j = i
        while depth:
            c = body[j]
            if in_str:
                if c == "\\":
                    j += 2; continue
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        calls.append(_split_top_level(body[i:j - 1]))
    return calls


def _render_format(token):
    """Concatenated string literals and S_* macros -> the text the display shows.
    S_Hz is the two characters "Hz"; every other S_* macro is one glyph."""
    out, i = "", 0
    while i < len(token):
        c = token[i]
        if c.isspace():
            i += 1; continue
        if c == '"':
            j, buf = i + 1, ""
            while token[j] != '"':
                if token[j] == "\\":
                    buf += token[j:j + 2]; j += 2; continue
                buf += token[j]; j += 1
            out += _unescape(buf); i = j + 1; continue
        m = re.match(r"[A-Za-z_]\w*", token[i:])
        if not m:
            raise AssertionError("unexpected character in format: %r" % token[i:i + 20])
        name = m.group(0)
        if name == "S_Hz":
            out += "Hz"
        elif name.startswith("S_"):
            out += "\x01"
        else:
            raise AssertionError("unexpected token in format string: " + name)
        i += m.end()
    return out


_CONVERSION = re.compile(r"%([-+ #0]*)([0-9]*)(\.[0-9]+)?([a-zA-Z%])")


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gcc = shutil.which("gcc")
        if not cls.gcc: return
        cls.tmp = tempfile.mkdtemp(); cls.exe = os.path.join(cls.tmp, "workref_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-Wextra", "-O1", "-I", ROOT, "-o", cls.exe,
                            os.path.join(ROOT, "tests", "host", "workref_host.c"), "-lm"], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        cls.build_stderr = r.stderr
        cls.tune_exe = os.path.join(cls.tmp, "tune_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-Wextra", "-O1", "-I", ROOT, "-o", cls.tune_exe,
                            os.path.join(ROOT, "tests", "host", "tune_host.c")], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        cls.tune_build_stderr = r.stderr
        cls.choke_exe = os.path.join(cls.tmp, "choke_host")
        r = subprocess.run([cls.gcc, "-std=c11", "-Wall", "-Wextra", "-O1", "-I", ROOT, "-o", cls.choke_exe,
                            os.path.join(ROOT, "tests", "host", "choke_host.c"), "-lm"], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        cls.choke_build_stderr = r.stderr

    def test_build_is_warning_free(self):
        if not self.gcc: self.skipTest("gcc not available")
        self.assertEqual(self.build_stderr, "", "host build produced warnings:\n" + self.build_stderr)

    def test_tune_build_is_warning_free(self):
        if not self.gcc: self.skipTest("gcc not available")
        self.assertEqual(self.tune_build_stderr, "", "tune_host build produced warnings:\n" + self.tune_build_stderr)

    def test_choke_build_is_warning_free(self):
        if not self.gcc: self.skipTest("gcc not available")
        self.assertEqual(self.choke_build_stderr, "", "choke_host build produced warnings:\n" + self.choke_build_stderr)

    def test_choke_arithmetic(self):
        if not self.gcc: self.skipTest("gcc not available")
        r = subprocess.run([self.choke_exe], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(r.stdout.strip().endswith("OK"), r.stdout)

    def test_reference_sweep_state_machine(self):
        if not self.gcc: self.skipTest("gcc not available")
        r = subprocess.run([self.exe], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.rstrip("\n").endswith("OK"), r.stdout + r.stderr)

    def _assert_rows_fit(self, func_name, extra_symbols, min_rows=8):
        """Every row the named draw_*() can print stays within 50 columns in its widest form.

        extra_symbols maps a substring of a %s argument expression (a helper call or a table
        name) to the widest string it can yield; local `const char *x = ...` variables and
        inline literals / two-literal ternaries are sized from the function body itself."""
        measure = _read("measure.c")
        body = _function_body(measure, func_name)
        symbols = {m.group(1): max(len(l) for l in _literals(m.group(2)))
                   for m in re.finditer(r"const char \*(\w+)\s*=\s*([^;]+);", body)}

        def string_width(expr):
            lits = _literals(expr)
            if lits: return max(len(l) for l in lits)          # inline literal or ternary of two
            for key, width in extra_symbols.items():
                if key in expr: return width
            name = expr.strip()
            self.assertIn(name, symbols, "cannot size %s argument: " + expr)
            return symbols[name]

        calls = _cell_printf_calls(body)
        self.assertGreater(len(calls), min_rows, func_name + " rows not found in measure.c")
        for args in calls:
            text, varargs, n, out, pos = _render_format(args[2]), args[3:], 0, "", 0
            for m in _CONVERSION.finditer(text):
                out += text[pos:m.start()]; pos = m.end()
                conv, field = m.group(4), m.group(2)
                if conv == "%":
                    out += "%"; continue
                if conv == "s":     out += "x" * string_width(varargs[n])
                elif conv in "FqfeEg": out += "x" * FLOAT_COLUMNS
                # An explicit field width on an integer is the author pinning the column count
                # of a value known to fit it (the uint8_t band label in "%3dm"); without one,
                # assume the INT_COLUMNS worst case.
                elif conv in "diu":    out += "x" * (int(field) if field else INT_COLUMNS)
                else: self.fail("unhandled conversion %%%s in %s" % (conv, args[2]))
                n += 1
            out += text[pos:]
            self.assertLessEqual(len(out), MEASURE_ROW_COLUMNS,
                                 "%s row is %d columns (max %d): %s"
                                 % (func_name, len(out), MEASURE_ROW_COLUMNS, args[2].strip()))

    def _wref_state_width(self):
        names = re.search(r"names\[\]\s*=\s*\{([^}]*)\}",
                          _read(os.path.join("vna_modules", "vna_workref.c"))).group(1)
        return max(len(l) for l in _literals(names))

    def test_tune_panel_rows_fit_the_measure_area(self):
        # %s arguments: local const char * variables (the "per leg" suffix and the
        # [measured] / [loaded?] tag), the antenna names, and the reference-state names.
        measure = _read("measure.c")
        ant_names = re.search(r"tune_ant_names\[TUNE_ANT_COUNT\]\s*=\s*\{([^}]*)\}", measure).group(1)
        self._assert_rows_fit("static void draw_tune",
                              {"tune_ant_names": max(len(l) for l in _literals(ant_names)),
                               "wref_state_str": self._wref_state_width()})

    def test_choke_panel_rows_fit_the_measure_area(self):
        # %s arguments: the verdict names and the fixture-state names.
        measure = _read("measure.c")
        verdicts = re.search(r"choke_verdict_names\[CHOKE_VERDICT_COUNT\]\s*=\s*\{([^}]*)\}", measure).group(1)
        self._assert_rows_fit("static void draw_choke",
                              {"choke_verdict_names": max(len(l) for l in _literals(verdicts)),
                               "wref_state_str": self._wref_state_width()})

    def test_tune_arithmetic(self):
        if not self.gcc: self.skipTest("gcc not available")
        r = subprocess.run([self.tune_exe], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "", "tune_host stderr should be empty:\n" + r.stderr)
        self.assertTrue(r.stdout.rstrip("\n").endswith("OK"), r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
