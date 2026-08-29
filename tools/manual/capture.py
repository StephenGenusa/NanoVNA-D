#!/usr/bin/env python3
"""Screenshot checklist runner for the manual: walks tools/manual/captures.json, sends each
entry's setup commands to the NanoVNA over USB, prompts you to do the hands-on part, and
saves the screen with the firmware's `capture rle` command (RLE8 + palette, decoded here)
as docs/manual/captures/<id>.png. Skips entries that already have a file.

    python3 tools/manual/capture.py [--port /dev/ttyACM0] [--list] [--only ID] [--redo ID|all]
    python3 tools/manual/capture.py --selftest        # offline: PackBits/PNG round trip

Standard library only (pyserial optional for the device: pip install pyserial).
"""
import argparse, glob, json, os, struct, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "docs", "manual", "captures")
LIST = os.path.join(HERE, "captures.json")


# --- image handling -------------------------------------------------------------------

def unpackbits(data, n):
    """Apple PackBits as written by the firmware's packbits() (common.c)."""
    out = bytearray(); i = 0
    while len(out) < n and i < len(data):
        h = data[i]; i += 1
        if h < 128:                      # h+1 literal bytes
            out += data[i:i + h + 1]; i += h + 1
        elif h > 128:                    # repeat next byte 257-h times
            out += bytes([data[i]]) * (257 - h); i += 1
    return bytes(out[:n])


def packbits(src):
    """Reference encoder (same block rules as the firmware) — used by --selftest only."""
    out = bytearray(); i = 0; n = len(src)
    while i < n:
        run = 1
        while i + run < n and run < 128 and src[i + run] == src[i]:
            run += 1
        if run >= 3:
            out += bytes([257 - run, src[i]]); i += run; continue
        j = i
        while j < n and j - i < 128 and not (j + 2 < n and src[j] == src[j + 1] == src[j + 2]):
            j += 1
        out += bytes([j - i - 1]) + src[i:j]; i = j
    return bytes(out)


def rgb565_to_rgb(v):
    """Palette word -> (r, g, b). The firmware stores RGB565 in the LCD's byte order (nanovna.h
    RGB565(): g low bits in 13-15, b in 8-12, r in 3-7, g high bits in 0-2), not the textbook layout."""
    return v & 0xF8, ((v & 7) << 5) | ((v >> 11) & 0x1C), (v >> 5) & 0xF8


def rgb_to_rgb565(r, g, b):
    return ((g & 0x1C) << 11) | ((b & 0xF8) << 5) | (r & 0xF8) | ((g & 0xE0) >> 5)


def write_png(path, width, height, palette_rgb, rows):
    """Indexed 8-bit PNG (stdlib only)."""
    def chunk(tag, body):
        c = tag + body
        return struct.pack(">I", len(body)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + r for r in rows)
    plte = b"".join(bytes(c) for c in palette_rgb)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
           + chunk(b"PLTE", plte) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# --- device ---------------------------------------------------------------------------

class NanoVNA:
    PROMPT = b"ch> "

    def __init__(self, port):
        import serial
        self.ser = serial.Serial(port, 115200, timeout=3)
        self.cmd("")

    def _read_until_prompt(self, limit=20.0):
        buf = b""; t0 = time.time()
        while not buf.endswith(self.PROMPT):
            chunk = self.ser.read(65536)
            if chunk:
                buf += chunk
            elif time.time() - t0 > limit:
                raise TimeoutError("no prompt")
        return buf

    def cmd(self, text):
        self.ser.reset_input_buffer()
        self.ser.write((text + "\r").encode())
        return self._read_until_prompt()

    def capture(self):
        """Screen as (width, height, palette_rgb[], rows[]) via `capture rle`."""
        self.ser.reset_input_buffer()
        self.ser.write(b"capture rle\r")
        buf = self._read_until_prompt(60.0)
        i = buf.find(b"BM")                       # header magic 0x4D42 little-endian = 'BM'
        if i < 0:
            raise RuntimeError("no screenshot header in reply")
        hdr = buf[i:i + 8]
        magic, width, height, bpp, comp = struct.unpack("<HHHBB", hdr)
        if bpp != 8 or comp != 1:
            raise RuntimeError("unexpected screenshot format bpp=%d comp=%d" % (bpp, comp))
        p = i + 8
        psize = struct.unpack("<H", buf[p:p + 2])[0]; p += 2
        pal = [rgb565_to_rgb(v) for v in struct.unpack("<%dH" % (psize // 2), buf[p:p + psize])]; p += psize
        rows = []
        for y in range(height):
            n = struct.unpack("<H", buf[p:p + 2])[0]; p += 2
            rows.append(unpackbits(buf[p:p + n], width)); p += n
        return width, height, pal, rows


# --- checklist ------------------------------------------------------------------------

def load_list():
    return json.load(open(LIST, encoding="utf-8"))["captures"]


def status(entries):
    return [(e["id"], os.path.exists(os.path.join(OUT, e["id"] + ".png"))) for e in entries]


def selftest():
    import random
    rnd = random.Random(1)
    w, h = 480, 320
    rows = []
    for y in range(h):
        r = bytearray(w)
        for x in range(w):
            r[x] = 0 if (x // 40 + y // 40) % 2 else 6
        if y % 50 == 0:
            for x in range(w): r[x] = rnd.randrange(8)
        rows.append(bytes(r))
    for r in rows:
        assert unpackbits(packbits(r), w) == r
    pal = [(0, 0, 0), (255, 255, 255), (128, 128, 128), (230, 230, 230), (0, 0, 0), (210, 210, 210), (255, 255, 0), (0, 255, 255)]
    tmp = os.path.join(HERE, "_selftest.png")
    write_png(tmp, w, h, pal, rows)
    with open(tmp, "rb") as f:
        d = f.read()
    os.unlink(tmp)
    assert d[:8] == b"\x89PNG\r\n\x1a\n" and b"PLTE" in d and b"IEND" in d
    # decode the IDAT back and compare
    p = d.find(b"IDAT") - 4
    n = struct.unpack(">I", d[p:p + 4])[0]
    raw = zlib.decompress(d[p + 8:p + 8 + n])
    assert raw == b"".join(b"\x00" + r for r in rows)
    print("selftest ok: packbits round trip and PNG encode/decode on a %dx%d image" % (w, h))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--only"); ap.add_argument("--redo", help="ID or 'all'")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    entries = load_list()
    if a.list:
        for cid, done in status(entries):
            print("%s  %s" % ("done   " if done else "pending", cid))
        return 0
    port = a.port or next(iter(glob.glob("/dev/ttyACM*") + glob.glob("/dev/cu.usbmodem*")), None)
    if not port:
        print("no NanoVNA serial port found; use --port", file=sys.stderr); return 1
    os.makedirs(OUT, exist_ok=True)
    vna = NanoVNA(port)
    print("connected:", vna.cmd("version").decode(errors="replace").strip().split("\n")[-2:])
    for e in entries:
        cid = e["id"]; path = os.path.join(OUT, cid + ".png")
        if a.only and cid != a.only:
            continue
        if os.path.exists(path) and a.redo not in ("all", cid):
            print("skip (exists):", cid); continue
        print("\n=== %s: %s" % (cid, e["title"]))
        for c in e.get("setup", []):
            vna.cmd(c)
        if e.get("prompt"):
            try:
                input("   " + e["prompt"] + "\n   ...then press Enter to capture (s to skip): ")
            except EOFError:
                return 0
        vna.cmd("pause")                      # freeze the sweep so the screenshot and the data dump below agree
        w, h, pal, rows = vna.capture()
        write_png(path, w, h, pal, rows)
        # the sweep behind the picture, so a renderer can be checked against the real screen
        def lines(c):   # reply lines minus the echo and the prompt
            out = vna.cmd(c).decode(errors="replace").replace("\r", "").split("\n")
            return [l for l in out[1:] if l.strip() and not l.startswith("ch>")]
        state = {"frequencies": [float(x) for x in lines("frequencies")],
                 "s11": [[float(v) for v in l.split()[:2]] for l in lines("data 0")],
                 "s21": [[float(v) for v in l.split()[:2]] for l in lines("data 1")],
                 "sweep": lines("sweep"), "trace": lines("trace"), "marker": lines("marker"),
                 "vbat": lines("vbat"),
                 "width": w, "height": h}
        with open(path[:-4] + ".json", "w", encoding="utf-8") as f:
            json.dump(state, f)
        vna.cmd("resume")
        print("   saved %s (%dx%d) + .json sweep state" % (os.path.relpath(path, ROOT), w, h))
        for c in e.get("teardown", []):
            vna.cmd(c)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
