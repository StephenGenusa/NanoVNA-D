#!/usr/bin/env python3
"""Validate a PNG written by vna_modules/vna_png.c: chunk CRCs, IHDR/PLTE, zlib inflate, and
(optionally) that the decoded palette indices equal a raw .idx file (width*height bytes).
    python3 tests/check_png.py FILE.png [FILE.idx]
"""
import struct, sys, zlib


def chunks(d):
    p = 8
    while p < len(d):
        n = struct.unpack(">I", d[p:p + 4])[0]; tag = d[p + 4:p + 8]; body = d[p + 8:p + 8 + n]
        crc = struct.unpack(">I", d[p + 8 + n:p + 12 + n])[0]
        yield tag, body, crc
        p += 12 + n


def check(path, raw_path=None):
    with open(path, "rb") as f: d = f.read()
    info = {"ok": False, "error": "", "width": 0, "height": 0, "palette": 0, "size": len(d)}
    if d[:8] != b"\x89PNG\r\n\x1a\n": info["error"] = "bad signature"; return info
    idat = b""; ihdr = None; plte = None
    for tag, body, crc in chunks(d):
        if zlib.crc32(tag + body) & 0xFFFFFFFF != crc: info["error"] = "bad CRC in " + tag.decode(); return info
        if tag == b"IHDR": ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE": plte = body
        elif tag == b"IDAT": idat += body
        elif tag == b"IEND": break
    if not ihdr: info["error"] = "no IHDR"; return info
    w, h, depth, ctype, comp, filt, inter = ihdr
    info["width"], info["height"] = w, h
    if (depth, ctype, comp, filt, inter) != (8, 3, 0, 0, 0): info["error"] = "IHDR fields %r" % (ihdr,); return info
    if not plte or len(plte) % 3 or len(plte) > 768: info["error"] = "bad PLTE"; return info
    info["palette"] = len(plte) // 3
    try: raw = zlib.decompress(idat)
    except zlib.error as e: info["error"] = "inflate: %s" % e; return info
    if len(raw) != h * (w + 1): info["error"] = "decoded size %d != %d" % (len(raw), h * (w + 1)); return info
    rows = [raw[y * (w + 1) + 1:(y + 1) * (w + 1)] for y in range(h)]
    if any(raw[y * (w + 1)] != 0 for y in range(h)): info["error"] = "non-zero filter byte"; return info
    if max(max(r) for r in rows) >= info["palette"]: info["error"] = "index beyond PLTE"; return info
    if raw_path:
        with open(raw_path, "rb") as f: want = f.read()
        if b"".join(rows) != want: info["error"] = "indices differ from source"; return info
    info["ok"] = True
    return info


def idat_bytes(path):
    with open(path, "rb") as f: d = f.read()
    return b"".join(body for tag, body, _ in chunks(d) if tag == b"IDAT")


def write_dynamic_huffman_png(path, w=480, h=320):
    """A PNG the device decoder must reject (dynamic Huffman, 32 KB window)."""
    raw = b"".join(b"\x00" + bytes((x * y) & 0xFF for x in range(w)) for y in range(h))
    def chunk(tag, body): return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    plte = b"".join(bytes((i, i, i)) for i in range(256))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0)) + chunk(b"PLTE", plte)
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f: f.write(png)


if __name__ == "__main__":
    i = check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print("OK %dx%d, %d colours, %d bytes" % (i["width"], i["height"], i["palette"], i["size"]) if i["ok"] else "FAIL: " + i["error"])
    sys.exit(0 if i["ok"] else 1)
