#!/usr/bin/env python3
"""Render a ground-truth capture's sweep state with screen.py and diff it against the real
screenshot pixel by pixel. Writes <id>-render.png and <id>-diff.png next to the capture in
the scratch dir given by --out, prints the mismatch count and where the mismatches cluster.

    python3 tools/manual/compare_capture.py gt-logmag [--out DIR] [--no-status]
"""
import argparse, json, os, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.path.join(ROOT, "docs", "manual", "captures")


def read_png(path):
    d = open(path, "rb").read()
    p = 8; w = h = None; pal = []; idat = b""
    while p < len(d):
        n = struct.unpack(">I", d[p:p + 4])[0]; tag = d[p + 4:p + 8]; body = d[p + 8:p + 8 + n]
        if tag == b"IHDR": w, h = struct.unpack(">II", body[:8])
        elif tag == b"PLTE": pal = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif tag == b"IDAT": idat += body
        p += 12 + n
    raw = zlib.decompress(idat)
    rows = [raw[y * (w + 1) + 1:(y + 1) * (w + 1)] for y in range(h)]
    return w, h, pal, rows


def state_from_capture(cid, smith_format=None):
    j = json.load(open(os.path.join(CAP, cid + ".json")))
    w, h, pal, rows = read_png(os.path.join(CAP, cid + ".png"))
    traces = []
    for line in j["trace"]:                 # "0 LOGMAG S11 10.000000000 7.000000000"
        n, typ, ch, scale, refpos = line.split()
        tr = {"type": typ, "channel": 0 if ch == "S11" else 1, "scale": float(scale), "refpos": float(refpos)}
        if smith_format is not None: tr["smith_format"] = smith_format   # the `trace` listing does not report it
        traces.append(tr)
    markers = []
    for line in j["marker"]:                # "1 50 15500000"
        n, idx, f = line.split()
        markers.append({"n": int(n), "index": int(idx)})
    markers.sort(key=lambda m: m["n"])
    state = {"frequencies": j["frequencies"], "s11": j["s11"], "s21": j["s21"], "traces": traces,
             "markers": markers, "active_marker": len(markers) - 1 if markers else None,
             "previous_marker": None,   # console-enabled markers do not set previous_marker: trace mode
             "palette": pal, "bandwidth_hz": 1000, "cal_letters": ["c0", "D", "R", "S", "T", "X"], "power": "Pa"}
    if j.get("vbat"):
        try: state["vbat_mv"] = int("".join(ch for ch in j["vbat"][0] if ch.isdigit()))
        except ValueError: pass
    return state, (w, h, pal, rows)


SMITH_FORMAT = {"gt-smith": 2}     # marker format the capture was made with (captures.json setup): 2 = Re+Im


def compare(cid, target="F303", out=None):
    """Render the capture's state and diff it against the real screenshot.
    Returns (mismatched, total, {row: mismatches}); writes <id>-render.png and <id>-diff.png in out."""
    state, (w, h, pal, rows) = state_from_capture(cid, SMITH_FORMAT.get(cid))
    if out: os.makedirs(out, exist_ok=True)
    R = screen.render(target, state, os.path.join(out, cid + "-render.png") if out else None)
    diff = screen.Raster(w, h, [(0, 0, 0), (255, 0, 0), (0, 80, 0), (60, 60, 60)])
    bad = 0; rowsbad = {}
    for y in range(h):
        real = rows[y]
        for x in range(w):
            a_, b_ = pal[real[x]], R.pal[R.px[y * w + x]]      # compare colours, not palette slots
            if "vbat_mv" not in state and x < 12 and y < 32:      # battery icon unknown: masked
                continue
            if a_ != b_:
                bad += 1; rowsbad[y] = rowsbad.get(y, 0) + 1
                diff.set(x, y, 1)
            elif a_ != (0, 0, 0):
                diff.set(x, y, 2)
    if out: diff.png(os.path.join(out, cid + "-diff.png"))
    return bad, w * h, rowsbad


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("id"); ap.add_argument("--out", default=os.path.join(ROOT, "docs", "manual", "dist"))
    ap.add_argument("--target", default="F303")
    a = ap.parse_args(argv)
    bad, total, rowsbad = compare(a.id, a.target, a.out)
    print("%s: %d mismatched pixels of %d (%.2f%%)" % (a.id, bad, total, 100.0 * bad / total))
    worst = sorted(rowsbad.items(), key=lambda kv: -kv[1])[:8]
    print("worst rows:", ", ".join("y=%d:%d" % kv for kv in worst))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
