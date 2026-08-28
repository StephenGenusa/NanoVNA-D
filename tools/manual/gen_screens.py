#!/usr/bin/env python3
"""Rendered sweep screens for the manual. Each entry below is a small circuit model swept
over a frequency range; screen.py draws the result with the firmware's own drawing rules
(grid, traces, markers, readouts, status column) for the H (320x240) and H4 (480x320).
Output: docs/manual/img/screen-<id>-<H|H4>.png. Chapters reference the files by name.

    python3 tools/manual/gen_screens.py [--only ID]
"""
import argparse, cmath, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "manual", "img")
Z0 = 50.0
CAL = ["C0", "D", "R", "S", "T", "X"]
POINTS = {"F072": 101, "F303": 401}


# --- circuit models: Z(f) in ohms ----------------------------------------------------
def series_rlc(r, l, c):
    return lambda f: complex(r, 2 * math.pi * f * l - 1 / (2 * math.pi * f * c))


def dipole(f0=14.2e6, r=52.0, q=12.0):
    """A dipole near resonance: series RLC with radiation resistance r, tuned to f0."""
    l = q * r / (2 * math.pi * f0); c = 1 / ((2 * math.pi * f0) ** 2 * l)
    return series_rlc(r, l, c)


def load_with_stub(r=49.3, c=0.4e-12):
    return lambda f: 1 / (1 / complex(r, 0) + complex(0, 2 * math.pi * f * c))


def gamma(z):
    return (z - Z0) / (z + Z0)


def lowpass_abcd(fc=30e6):
    """3rd-order Butterworth LC low-pass (pi: C L C) -> (S11, S21) at f."""
    w0 = 2 * math.pi * fc
    c = 1.0 / (Z0 * w0); l = 2 * Z0 / w0
    def s(f):
        w = 2 * math.pi * f
        yc = complex(0, w * c); zl = complex(0, w * l)
        # ABCD of shunt C, series L, shunt C
        A, B, C, D = 1, 0, yc, 1
        A, B, C, D = A, A * zl + B, C, C * zl + D
        A, B, C, D = A + B * yc, B, C + D * yc, D
        den = A + B / Z0 + C * Z0 + D
        return (A + B / Z0 - C * Z0 - D) / den, 2 / den
    return s


def sweep(fstart, fstop, points, s11_of_f, s21_of_f=None):
    freqs = [fstart + (fstop - fstart) * i / (points - 1) for i in range(points)]
    s11 = [s11_of_f(f) for f in freqs]
    s21 = [s21_of_f(f) for f in freqs] if s21_of_f else [complex(0, 0)] * points
    return freqs, [[g.real, g.imag] for g in s11], [[g.real, g.imag] for g in s21]


def idx_of(freqs, f):
    return min(range(len(freqs)), key=lambda i: abs(freqs[i] - f))


def idx_min(vals):
    return min(range(len(vals)), key=lambda i: vals[i])


# --- the screens -----------------------------------------------------------------------
def scr_antenna_swr(points):
    z = dipole()
    freqs, s11, s21 = sweep(10e6, 20e6, points, lambda f: gamma(z(f)))
    swr = [screen._swr(v) for v in s11]
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "SWR", "channel": 0, "scale": 1.0, "refpos": 0},
                       {"type": "|Z|", "channel": 0, "scale": 50.0, "refpos": 0}],
            "markers": [{"index": idx_min(swr)}], "cal_letters": CAL, "power": "Pa"}


def scr_antenna_rx(points):
    z = dipole()
    freqs, s11, s21 = sweep(10e6, 20e6, points, lambda f: gamma(z(f)))
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "R", "channel": 0, "scale": 100.0, "refpos": 0},
                       {"type": "X", "channel": 0, "scale": 100.0, "refpos": 4}],
            "markers": [{"index": idx_of(freqs, 14.2e6)}], "cal_letters": CAL, "power": "Pa"}


def scr_antenna_smith(points):
    z = dipole()
    freqs, s11, s21 = sweep(10e6, 20e6, points, lambda f: gamma(z(f)))
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "SMITH", "channel": 0, "scale": 1.0, "refpos": 0, "smith_format": 3}],
            "markers": [{"index": idx_of(freqs, 14.2e6)}], "cal_letters": CAL, "power": "Pa"}


def scr_antenna_delta(points):
    """Two markers on the SWR dip's 2:1 edges: marker mode with the delta line."""
    z = dipole()
    freqs, s11, s21 = sweep(10e6, 20e6, points, lambda f: gamma(z(f)))
    swr = [screen._swr(v) for v in s11]; m = idx_min(swr)
    lo = max(i for i in range(m) if swr[i] >= 2.0); hi = min(i for i in range(m, points) if swr[i] >= 2.0)
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "SWR", "channel": 0, "scale": 1.0, "refpos": 0}],
            "markers": [{"index": lo}, {"index": hi}], "active_marker": 1, "previous_marker": 0,
            "cal_letters": CAL, "power": "Pa"}


def scr_load_check(points):
    zl = load_with_stub()
    freqs, s11, s21 = sweep(50e3, 900e6, points, lambda f: gamma(zl(f)))
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "LOGMAG", "channel": 0, "scale": 10.0, "refpos": 7},
                       {"type": "SMITH", "channel": 0, "scale": 1.0, "refpos": 0, "smith_format": 3}],
            "markers": [{"index": idx_of(freqs, 450e6)}], "cal_letters": CAL, "power": "Pa"}


def scr_filter_s21(points):
    s = lowpass_abcd()
    freqs, s11, s21 = sweep(1e6, 100e6, points, lambda f: s(f)[0], lambda f: s(f)[1])
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "LOGMAG", "channel": 0, "scale": 10.0, "refpos": 7},
                       {"type": "LOGMAG", "channel": 1, "scale": 10.0, "refpos": 7},
                       {"type": "PHASE", "channel": 1, "scale": 90.0, "refpos": 4}],
            "markers": [{"index": idx_of(freqs, 30e6)}], "current_trace": 1, "cal_letters": CAL, "power": "Pa"}


def scr_filter_delay(points):
    s = lowpass_abcd()
    freqs, s11, s21 = sweep(1e6, 100e6, points, lambda f: s(f)[0], lambda f: s(f)[1])
    return {"frequencies": freqs, "s11": s11, "s21": s21,
            "traces": [{"type": "LOGMAG", "channel": 1, "scale": 10.0, "refpos": 7},
                       {"type": "DELAY", "channel": 1, "scale": 10e-9, "refpos": 4}],
            "markers": [{"index": idx_of(freqs, 20e6)}], "cal_letters": CAL, "power": "Pa"}


SCREENS = {
    "antenna-swr": scr_antenna_swr, "antenna-rx": scr_antenna_rx, "antenna-smith": scr_antenna_smith,
    "antenna-delta": scr_antenna_delta, "load-check": scr_load_check,
    "filter-s21": scr_filter_s21, "filter-delay": scr_filter_delay,
}


def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument("--only"); ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    n = 0
    for sid, fn in SCREENS.items():
        if a.only and sid != a.only:
            continue
        for target, dev in (("F303", "H4"), ("F072", "H")):
            path = os.path.join(a.out, "screen-%s-%s.png" % (sid, dev))
            screen.render(target, fn(POINTS[target]), path); n += 1
    print("wrote %d screens to %s" % (n, os.path.relpath(a.out, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
