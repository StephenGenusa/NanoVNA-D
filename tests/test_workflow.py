"""Workflow panels: the reference sweep (vna_modules/vna_workref.c) - CCM-RAM header and
value-based staleness - plus a pure-Python width check on the TUNE panel rows in measure.c."""
import os, re, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The TUNE panel invalidates 5 * STR_MEASURE_WIDTH = 5 * 10 characters (measure.c prepare_tune),
# so every row draw_tune() can print must fit in 50 columns in its widest possible form.
MEASURE_ROW_COLUMNS = 50
FLOAT_COLUMNS = 7          # %F / %q / %f worst case, e.g. "-123.45"
INT_COLUMNS = 5            # %d / %u worst case


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

    def test_tune_panel_rows_fit_the_measure_area(self):
        """Every row draw_tune() can print stays within 50 columns in its widest form."""
        measure = _read("measure.c")
        body = _function_body(measure, "static void draw_tune")
        # Widths of the %s arguments: local const char * variables (the "per leg" suffix and the
        # [measured] / [loaded?] tag), the antenna names, and the reference-state names.
        symbols = {m.group(1): max(len(l) for l in _literals(m.group(2)))
                   for m in re.finditer(r"const char \*(\w+)\s*=\s*([^;]+);", body)}
        ant_names = re.search(r"tune_ant_names\[TUNE_ANT_COUNT\]\s*=\s*\{([^}]*)\}", measure).group(1)
        ant_width = max(len(l) for l in _literals(ant_names))
        wref_names = re.search(r"names\[\]\s*=\s*\{([^}]*)\}",
                               _read(os.path.join("vna_modules", "vna_workref.c"))).group(1)
        wref_width = max(len(l) for l in _literals(wref_names))

        def string_width(expr):
            lits = _literals(expr)
            if lits: return max(len(l) for l in lits)          # inline literal or ternary of two
            if "tune_ant_names" in expr: return ant_width
            if "wref_state_str" in expr: return wref_width
            name = expr.strip()
            self.assertIn(name, symbols, "cannot size %s argument: " + expr)
            return symbols[name]

        calls = _cell_printf_calls(body)
        self.assertGreater(len(calls), 8, "draw_tune rows not found in measure.c")
        for args in calls:
            text, varargs, n, out, pos = _render_format(args[2]), args[3:], 0, "", 0
            for m in _CONVERSION.finditer(text):
                out += text[pos:m.start()]; pos = m.end()
                conv = m.group(4)
                if conv == "%":
                    out += "%"; continue
                if conv == "s":     out += "x" * string_width(varargs[n])
                elif conv in "FqfeEg": out += "x" * FLOAT_COLUMNS
                elif conv in "diu":    out += "x" * INT_COLUMNS
                else: self.fail("unhandled conversion %%%s in %s" % (conv, args[2]))
                n += 1
            out += text[pos:]
            self.assertLessEqual(len(out), MEASURE_ROW_COLUMNS,
                                 "TUNE row is %d columns (max %d): %s"
                                 % (len(out), MEASURE_ROW_COLUMNS, args[2].strip()))

    def test_tune_arithmetic(self):
        if not self.gcc: self.skipTest("gcc not available")
        r = subprocess.run([self.tune_exe], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "", "tune_host stderr should be empty:\n" + r.stderr)
        self.assertTrue(r.stdout.rstrip("\n").endswith("OK"), r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
