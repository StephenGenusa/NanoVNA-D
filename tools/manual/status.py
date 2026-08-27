#!/usr/bin/env python3
"""Report what the manual still lacks: menu items without a description, console commands
without a description, menu labels without a sample value, `[verify on hardware]` markers,
and `[describe]` occurrences in hand-written chapters. Exit code 0 always; this is a report."""
import glob, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_menus, gen_console

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "manual")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        gen_menus.generate(tmp)
        menus_missing = gen_menus.status()
        gen_console.generate(tmp)
        console_missing = gen_console.status()["describe"]
    print("Menu items without a description: %d" % len(menus_missing["describe"]))
    for k in menus_missing["describe"]:
        print("  ", k)
    print("Menu labels without a sample value: %d" % len(menus_missing.get("samples", [])))
    for k in menus_missing.get("samples", []):
        print("  ", k)
    print("Console commands without a description: %d" % len(console_missing))
    for k in console_missing:
        print("  ", k)
    marks = []
    for path in sorted(glob.glob(os.path.join(SRC, "*.md"))):
        name = os.path.basename(path)
        if name in ("08-console.md", "09-menu-map.md"):
            continue
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            if "[verify on hardware" in line or "[describe]" in line:
                marks.append("%s:%d: %s" % (name, n, line.strip()[:100]))
    print("Markers in hand-written chapters: %d" % len(marks))
    for m in marks:
        print("  ", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
