"""Firmware source facts for the manual generators: per-target compile flags (from make),
preprocessing (to resolve #ifdef per target), and evaluation of nanovna.h constants."""
import glob, os, re, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGETS = {"F072": "H", "F303": "H4"}

_PRINTVARS = 'printvars:\n\t@echo "DEFS=$(DEFS) $(UDEFS) $(DDEFS) $(MCFLAGS)"\n\t@echo "ALLINC=$(ALLINC) $(INCDIR) $(UINCDIR)"\n'


def find_gcc():
    p = shutil.which("arm-none-eabi-gcc")
    if p:
        return p
    for d in sorted(glob.glob("/usr/local/gcc-arm-none-eabi-*/bin") + glob.glob("/opt/gcc-arm-none-eabi-*/bin")):
        c = os.path.join(d, "arm-none-eabi-gcc")
        if os.access(c, os.X_OK):
            return c
    raise RuntimeError("arm-none-eabi-gcc not found (install the firmware toolchain)")


def compile_flags(target):
    if target not in TARGETS:
        raise ValueError("unknown target %r" % target)
    with tempfile.NamedTemporaryFile("w", suffix=".mk", delete=False) as f:
        f.write(_PRINTVARS)
        mk = f.name
    try:
        env = dict(os.environ, PATH=os.path.dirname(find_gcc()) + os.pathsep + os.environ.get("PATH", ""))
        out = subprocess.run(["make", "-s", "-f", "Makefile", "-f", mk, "TARGET=" + target, "printvars"],
                             cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(mk)
    defs = allinc = None
    for line in out.splitlines():
        if line.startswith("DEFS="):
            defs = line[5:].split()
        elif line.startswith("ALLINC="):
            allinc = line[7:].split()
    if defs is None or allinc is None:
        raise RuntimeError("could not read DEFS/ALLINC from make for " + target)
    flags = []
    for d in defs:
        if d.startswith("-DVERSION") or d in flags:
            continue
        flags.append(d)
    flags += ["-I.", "-INANOVNA_STM32_" + target]
    flags += ["-I" + d for d in allinc if d]
    return flags


def preprocess(target, source="ui.c"):
    cmd = [find_gcc(), "-E", "-P"] + compile_flags(target) + [os.path.join(ROOT, source)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("preprocess failed for %s %s:\n%s" % (target, source, r.stderr))
    return r.stdout


_EXPR_OK = re.compile(r"^[\d\s()+\-*/<>|&~%]+$")


def eval_constants(target, names):
    """Evaluate integer #define expressions from nanovna.h for a target."""
    probe = "#include \"nanovna.h\"\n" + "".join("@@CONST_%s@@ %s\n" % (n, n) for n in names)
    with tempfile.NamedTemporaryFile("w", suffix=".c", dir=ROOT, delete=False) as f:
        f.write(probe)
        path = f.name
    try:
        text = preprocess(target, os.path.basename(path))
    finally:
        os.unlink(path)
    out = {}
    for n in names:
        m = re.search(r"@@CONST_%s@@ (.*)" % re.escape(n), text)
        if not m:
            raise RuntimeError("constant %s not found in preprocessed output" % n)
        expr = m.group(1).strip()
        if expr == n or not _EXPR_OK.match(expr):
            raise RuntimeError("constant %s did not expand to an integer expression: %r" % (n, expr))
        out[n] = int(eval(expr.replace("/", "//"), {"__builtins__": {}}, {}))
    return out
