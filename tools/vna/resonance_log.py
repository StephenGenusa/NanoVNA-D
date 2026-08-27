#!/usr/bin/env python3
"""Log an antenna's resonance (f0 and R at X = 0) over a series of ground-system changes,
reading the NanoVNA over USB, and report each step's gain in dB against the first reading.

The method (portable-vertical reference, §6.11): with the radiator untouched, feedpoint
resistance R_feed = R_rad + R_ground, so the improvement between two ground systems is
    delta_dB = 10 * log10(R_before / R_after)
taken at the frequency where X = 0. No R_rad or soil constants needed.

Usage:
    python3 tools/vna/resonance_log.py                      # autodetect /dev/ttyACM*
    python3 tools/vna/resonance_log.py --port /dev/ttyACM0 --csv run.csv
    python3 tools/vna/resonance_log.py --s1p file.s1p       # offline: analyse a saved sweep

Each time you press Enter the current sweep is read (calibrated data, as displayed) and
analysed; type a label first ("bare", "cloth", "4 radials", ...). Type "q" to finish. Take a
closing repeat of the first condition: if it differs from the opening reading, conditions
drifted and the run is not comparable. Requires pyserial (pip install pyserial).
"""
import argparse, csv, glob, math, sys, time

Z0 = 50.0


def z_from_gamma(re, im):
    """Series impedance from a reflection coefficient, reference Z0."""
    d = (1 - re) ** 2 + im ** 2
    if d == 0:
        return float("inf"), 0.0
    r = Z0 * (1 - re * re - im * im) / d
    x = Z0 * (2 * im) / d
    return r, x


def analyse(freqs, gammas):
    """Return a list of (f0, R, X) at every X zero crossing (linear interpolation)."""
    z = [z_from_gamma(re, im) for re, im in gammas]
    out = []
    for i in range(1, len(z)):
        x0, x1 = z[i - 1][1], z[i][1]
        if (x0 < 0) != (x1 < 0) and x0 != x1:
            k = x0 / (x0 - x1)
            f0 = freqs[i - 1] + (freqs[i] - freqs[i - 1]) * k
            r0 = z[i - 1][0] + (z[i][0] - z[i - 1][0]) * k
            out.append((f0, r0, 0.0))
    if not out:  # no crossing: report the point of smallest |X|
        i = min(range(len(z)), key=lambda j: abs(z[j][1]))
        out.append((freqs[i], z[i][0], z[i][1]))
    return out


class NanoVNA:
    PROMPT = b"ch> "

    def __init__(self, port):
        import serial  # pyserial
        self.ser = serial.Serial(port, 115200, timeout=2)
        self.cmd("")  # sync to the prompt

    def cmd(self, text):
        self.ser.reset_input_buffer()
        self.ser.write((text + "\r").encode())
        buf = b""
        t0 = time.time()
        while not buf.endswith(self.PROMPT):
            chunk = self.ser.read(4096)
            if chunk:
                buf += chunk
            elif time.time() - t0 > 10:
                raise TimeoutError("no prompt after %r" % text)
        body = buf[:-len(self.PROMPT)].decode(errors="replace")
        lines = body.replace("\r", "").split("\n")
        if lines and lines[0].strip() == text.strip():
            lines = lines[1:]           # echo
        return [l for l in lines if l.strip()]

    def sweep(self):
        """Read frequencies and calibrated S11 for the current sweep."""
        self.cmd("pause")
        try:
            freqs = [float(l) for l in self.cmd("frequencies")]
            data = [tuple(map(float, l.split()[:2])) for l in self.cmd("data 0")]
        finally:
            self.cmd("resume")
        if len(freqs) != len(data) or not freqs:
            raise RuntimeError("bad sweep: %d frequencies, %d points" % (len(freqs), len(data)))
        return freqs, data


def read_s1p(path):
    freqs, data = [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if not s or s[0] in "!#":
            continue
        f, re, im = s.split()[:3]
        freqs.append(float(f)); data.append((float(re), float(im)))
    return freqs, data


def fmt_f(f):
    return "%.6f MHz" % (f / 1e6)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", help="serial port (default: first /dev/ttyACM* or /dev/cu.usbmodem*)")
    ap.add_argument("--csv", help="append results to this CSV file")
    ap.add_argument("--s1p", help="analyse a saved .s1p file instead of the device")
    a = ap.parse_args()

    if a.s1p:
        for f0, r, x in analyse(*read_s1p(a.s1p)):
            print("resonance %s  R = %.2f Ω  X = %.2f Ω" % (fmt_f(f0), r, x))
        return 0

    port = a.port or next(iter(glob.glob("/dev/ttyACM*") + glob.glob("/dev/cu.usbmodem*")), None)
    if not port:
        print("no NanoVNA serial port found; use --port", file=sys.stderr)
        return 1
    vna = NanoVNA(port)
    print("connected to %s: %s" % (port, " ".join(vna.cmd("version"))))
    print("Calibration should be ON (the device shows C0..C6). Enter a label and press Enter to read;")
    print("q to quit. Finish with a repeat of the first condition as a drift check.")

    writer = None
    if a.csv:
        fh = open(a.csv, "a", newline="")
        writer = csv.writer(fh)
        if fh.tell() == 0:
            writer.writerow(["time", "label", "f0_Hz", "R_ohm", "X_ohm", "delta_dB_vs_first"])
    first_r = None
    while True:
        try:
            label = input("label> ").strip()
        except EOFError:
            break
        if label.lower() in ("q", "quit", "exit"):
            break
        freqs, data = vna.sweep()
        res = analyse(freqs, data)
        f0, r, x = res[0]
        if first_r is None:
            first_r = r
        delta = 10 * math.log10(first_r / r) if r > 0 and first_r > 0 else float("nan")
        note = "" if abs(x) < 0.5 else "  (no X=0 crossing in sweep; nearest |X|)"
        print("%-20s f0 %s  R %.2f Ω  X %.2f Ω  delta vs first %+.2f dB%s"
              % (label or "-", fmt_f(f0), r, x, delta, note))
        for f1, r1, x1 in res[1:]:
            print("%-20s also resonant at %s  R %.2f Ω" % ("", fmt_f(f1), r1))
        if writer:
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), label, "%.0f" % f0, "%.3f" % r, "%.3f" % x, "%.3f" % delta])
    return 0


if __name__ == "__main__":
    sys.exit(main())
