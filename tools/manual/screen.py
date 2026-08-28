#!/usr/bin/env python3
"""Device-look renderer: draw the NanoVNA sweep screen (rectangular formats) exactly as the
firmware draws it, from sweep data and a display state, into a paletted raster.

Everything here mirrors plot.c / chprintf.c: grid spacing (update_grid), trace→pixel mapping
(trace_into_index), the modified Bresenham of cell_drawline, marker plates and numbers
(icons_marker.c), the top readouts (cell_draw_marker_info), the frequency line
(draw_frequencies) and the status column (draw_cal_status), with the firmware's %q / %F
number formatting. Fonts come from fonts.py, geometry from layout.py.

State dict keys (all optional except frequencies/s11):
  frequencies [Hz], s11 [[re,im]...], s21 [[re,im]...], traces [{type, channel, scale,
  refpos, enabled}], markers [{index, enabled}], active_marker, previous_marker,
  lever_mode ("marker"), points, bandwidth_hz, cal_letters ["cH","D",...], power ("Pa"),
  smooth, palette [[r,g,b] x32] (defaults to the firmware default palette).
"""
import math, os, re, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srcinfo, layout, fonts

# ---------------------------------------------------------------- formatting (chprintf.c)
_BIG = " kMGTPEZY"
_SMALL = "mµnpfazy"


def fmt_freq(freq, precision=0):
    """ulong_freq(): digits grouped by 3 with spaces, first group separator becomes '.',
    SI prefix from the group count; precision 0 = all digits and a space before the prefix."""
    freq = int(freq)
    pset, pspace = True, precision == 0
    if precision == 0 or precision > 14:
        precision = 14
    digits, s = [], 0
    fmt = 0b100100100100100
    while True:
        digits.append(chr(freq % 10 + 48)); freq //= 10
        if freq == 0:
            break
        if fmt & 1:
            digits.append(" "); s += 1
        fmt >>= 1
    q = "".join(reversed(digits))
    out, i = "", 0
    pre = precision
    while i < len(q):
        c = q[i]; i += 1
        if c == " ":
            if pset:
                c = "."; pset = False
            elif not pspace:
                c = q[i]; i += 1
        if not pset:
            pre -= 1
            if pre < 0:
                break
        out += c
    prefix = _BIG[s]
    if pspace and prefix != " ":
        out += " "
    return out + prefix


def _ftoa(num, precision):
    precision = min(precision, 9)
    multi = 10 ** precision
    l = int(num)
    k = int((num - l) * multi + 0.5)
    if k >= multi:
        k -= multi; l += 1
    s = str(l)
    if precision:
        s += "." + str(k).rjust(precision, "0")
    return s


def fmt_F(num, precision=0, plus=False):
    """ftoaS(): SI-prefixed float with auto precision reduction and trailing zeros removed."""
    sign = ""
    if num < 0:
        sign, num = "-", -num
    elif plus:
        sign = "+"
    prefix = ""
    if num >= 1000.0:
        i = 1
        while i < len(_BIG) - 1 and num >= 1000.0:
            num /= 1000.0; i += 1
        prefix = _BIG[i - 1]
    elif num < 1.0 and num > 0:
        i = 0
        while i < len(_SMALL) and num < 1.0:
            num *= 1000.0; i += 1
        prefix = _SMALL[i - 1] if num > 1e-3 else ""
    if prefix:
        precision -= 1
    l = int(num)
    if l >= 100: precision -= 2
    elif l >= 10: precision -= 1
    if precision < 0: precision = 0
    s = _ftoa(num, precision)
    if precision:
        s = s.rstrip("0").rstrip(".")
    return sign + s + prefix


def fmt_f(num, precision, plus=False):
    sign = "-" if num < 0 else ("+" if plus else "")
    return sign + _ftoa(abs(num), precision)


# ---------------------------------------------------------------- trace value callbacks (plot.c)
def _logmag(v):  return 20 * math.log10(max(math.hypot(v[0], v[1]), 1e-30))
def _phase(v):   return math.degrees(math.atan2(v[1], v[0]))
def _linear(v):  return math.hypot(v[0], v[1])
def _swr(v):
    x = _linear(v)
    return float("inf") if x > 0.99 else (1 + x) / (1 - x)
def _z(v, z0=50.0):
    d = (1 - v[0]) ** 2 + v[1] ** 2
    if d == 0: return float("inf"), 0.0
    return z0 * (1 - v[0] ** 2 - v[1] ** 2) / d, z0 * 2 * v[1] / d
def _r(v): return _z(v)[0]
def _x(v): return _z(v)[1]
def _modz(v): r, x = _z(v); return math.hypot(r, x)

FORMATS = {   # name -> (value fn, printf format, unit symbol, default refpos rows, default scale)
    "LOGMAG": (_logmag, "%.2f", "dB", 7, 10.0), "PHASE": (_phase, "%.2f", "°", 4, 90.0),
    "LINEAR": (_linear, "%.4F", "", 0, 0.125), "SWR": (_swr, "%.3f", "", 0, 0.25),
    "REAL": (lambda v: v[0], "%.6f", "", 4, 0.25), "IMAG": (lambda v: v[1], "%.6fj", "", 4, 0.25),
    "R": (_r, "%.3F", "Ω", 0, 100.0), "X": (_x, "%.3F", "Ω", 4, 100.0), "|Z|": (_modz, "%.3F", "Ω", 0, 50.0),
    "SMITH": (None, None, "", 0, 1.0), "POLAR": (None, None, "", 0, 1.0),      # round grid, custom value formats
}
ROUND = ("SMITH", "POLAR")

# marker_info_list (plot.c): smith_format index -> (name, printer)   [subset: LIN, LOG, Re+Im, R+jX]
def _cplx(v):                        # "%+jF": sign, then 'j', then the SI number (chprintf.c COMPLEX flag)
    return ("-" if v < 0 else "+") + "j" + fmt_F(abs(v), 3)
SMITH_FORMATS = {
    0: ("LIN",     lambda v: "%s %s°" % (fmt_f(_linear(v), 2), fmt_f(_phase(v), 1, plus=True))),
    1: ("LOG",     lambda v: "%sdB %s°" % (fmt_f(_logmag(v), 1), fmt_f(_phase(v), 1, plus=True))),
    2: ("Re + Im", lambda v: fmt_F(v[0], 3) + _cplx(v[1])),
    3: ("R + jX",  lambda v: fmt_F(_r(v), 3) + _cplx(_x(v)) + "Ω"),
}


def value_string(t, v):
    """trace_print_value_string(): the marker readout text for trace t at sweep value v."""
    fn, fmtstr, unit, _, _ = FORMATS[t["type"]]
    if fn is None:
        return SMITH_FORMATS[t.get("smith_format", 3) if t["type"] == "SMITH" else 2][1](v)   # trace 0 default MS_RX (main.c trace table)
    return format_value(fmtstr, fn(v), unit)


def format_value(fmt, v, unit):
    m = re.match(r"%(\.\d+)?([fF])(j?)", fmt)
    prec = int(m.group(1)[1:]) if m.group(1) else 0
    if math.isinf(v):
        s = "\x19 "                      # chprintf.c: S_INFINITY then a space, unit still follows
    elif m.group(2) == "F":
        s = fmt_F(v, prec)
    else:
        s = fmt_f(v, prec)
    return s + m.group(3) + unit


# ---------------------------------------------------------------- round grids (plot.c smith_grid / polar_grid)
def smith_grid(x, y, r):
    _r = x * x + y * y; d = _r
    if d > r * r + r: return 0
    if d > r * r - r: return 1                       # outer circle
    if y == 0: return 1                              # horizontal axis
    if y < 0: y = -y
    r_y = r * y
    if x >= 0:
        if x >= r // 2:
            d = _r - 2 * r * x - r_y + r * r + r // 2
            if 0 <= d <= r: return 1                 # reactance 2j
            d = _r - (3 * r // 2) * x + r * r // 2 + r // 4
            if d < 0: return 0
            if d <= r // 2: return 1                 # resistance 3
        d = _r - 2 * r * x - 2 * r_y + r * r + r
        if 0 <= d <= 2 * r: return 1                 # reactance 1j
        d = _r - r * x + r // 2
        if d < 0: return 0
        if d <= r: return 1                          # resistance 1
    d = _r - 2 * r * x - 4 * r_y + r * r + r * 2
    if 0 <= d <= r * 4: return 1                     # reactance 1/2j
    d = _r - x * (r // 2) - r * r // 2 + r * 3 // 4
    if 0 <= d <= r * 3 // 2: return 1                # resistance 1/3
    return 0


def polar_grid(x, y, r):
    d = x * x + y * y
    if d > r * r + r: return 0
    if d > r * r - r: return 1
    if x == 0 or y == 0: return 1
    for k in (1, 2):
        if d < r * r * k * k // 25 - r * k // 5: return 0
        if d < r * r * k * k // 25 + r * k // 5: return 1
    if x == y or x == -y: return 1
    for k in (3, 4):
        if d < r * r * k * k // 25 - r * k // 5: return 0
        if d < r * r * k * k // 25 + r * k // 5: return 1
    return 0


# ---------------------------------------------------------------- marker bitmaps (icons_marker.c)
_marker_cache = {}


def marker_bitmaps(marker_set):
    """(width, height, xoff, yoff, plates[i] rows, rplates[i] rows) for markers 0(plate)..8."""
    if marker_set in _marker_cache:
        return _marker_cache[marker_set]
    src = open(os.path.join(srcinfo.ROOT, "icons_marker.c"), encoding="utf-8").read()
    m = re.search(r"#(?:el)?if _USE_MARKER_SET_ == %d(.*?)(?=#elif|#endif)" % marker_set, src, re.S)
    if not m:
        raise RuntimeError("marker set %d not found" % marker_set)
    blk = m.group(1)
    w = int(re.search(r"MARKER_WIDTH\s+(\d+)", blk).group(1)); h = int(re.search(r"MARKER_HEIGHT\s+(\d+)", blk).group(1))
    xo = int(re.search(r"X_MARKER_OFFSET\s+(\d+)", blk).group(1)); yo = int(re.search(r"Y_MARKER_OFFSET\s+(\d+)", blk).group(1))
    rows = [int(b, 2) for b in re.findall(r"_BMP(?:8|16)\(0b([01]+)\)", blk)]
    per = 2 * h                                   # normal + reversed variant per glyph
    glyphs = [(rows[i * per:i * per + h], rows[i * per + h:i * per + per]) for i in range(len(rows) // per)]
    bits = 16 if "_BMP16" in blk else 8
    _marker_cache[marker_set] = (w, h, xo, yo, glyphs, bits)
    return _marker_cache[marker_set]


# ---------------------------------------------------------------- raster
class Raster:
    def __init__(self, w, h, palette):
        self.w, self.h = w, h
        self.pal = palette
        self.px = bytearray(w * h)       # palette indices

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def fill(self, x, y, w, h, c):
        for yy in range(max(0, y), min(self.h, y + h)):
            row = yy * self.w
            for xx in range(max(0, x), min(self.w, x + w)):
                self.px[row + xx] = c

    def text(self, font, s, x, y, c, shadow=None):
        """lcd text; with shadow=colour it is cell_printf()'s put_normal() under _USE_SHADOW_TEXT_:
        each glyph is blitted with cell_blit_bitmap_shadow(), which paints the 3x3 dilation of the
        glyph in the shadow colour first (so a glyph's shadow overwrites its left neighbour's edge)."""
        if shadow is None:
            for px, py in font.pixels(s, x, y):
                self.set(px, py, c)
            return font.text_width(s)
        i = 0; x0 = x
        while i < len(s):
            if ord(s[i]) < 0x09:
                i += 2; continue
            pts = font.pixels(s[i], x, y)
            for px, py in pts:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        self.set(px + dx, py + dy, shadow)
            for px, py in pts:
                self.set(px, py, c)
            x += font.glyph(ord(s[i]))[0]; i += 1
        return x - x0

    def blit(self, x, y, w, h, rows, bits, c):
        for dy, row in enumerate(rows):
            for dx in range(w):
                if row & (1 << (bits - 1 - dx)):
                    self.set(x + dx, y + dy, c)

    def line(self, x0, y0, x1, y1, c):
        """cell_drawline() without the cell clipping (whole-screen coordinates)."""
        if y1 < y0:
            x0, x1, y0, y1 = x1, x0, y1, y0
        dx = x0 - x1; sx = 1
        if dx > 0: dx, sx = -dx, -1
        dy = y1 - y0
        err = int((-dx if (dy + dx) < 0 else -dy) / 2)
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = err
            if e2 > dx: err -= dy; x0 += sx
            if e2 < dy: err -= dx; y0 += 1

    def png(self, path):
        def chunk(tag, body):
            c = tag + body
            return struct.pack(">I", len(body)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w:(y + 1) * self.w]) for y in range(self.h))
        plte = b"".join(bytes(p) for p in self.pal)
        data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 3, 0, 0, 0))
                + chunk(b"PLTE", plte) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
        with open(path, "wb") as f:
            f.write(data)


# ---------------------------------------------------------------- the screen
PAL = {n: i for i, n in enumerate(["BG", "FG", "GRID", "MENU", "MENU_TEXT", "MENU_ACTIVE", "TRACE_1", "TRACE_2", "TRACE_3",
       "TRACE_4", "TRACE_5", "TRACE_6", "NORMAL_BAT", "LOW_BAT", "SPEC_INPUT", "RISE_EDGE", "FALLEN_EDGE", "SWEEP_LINE",
       "BW_TEXT", "INPUT_TEXT", "INPUT_BG", "MEASURE", "GRID_VALUE", "INTERP_CAL", "DISABLE_CAL", "LINK", "TXT_SHADOW"])}
_EXTRA = ["GRIDY", "FREQUENCIES_XPOS1", "FREQUENCIES_XPOS2", "FREQUENCIES_XPOS3", "FREQUENCIES_YPOS",
          "CALIBRATION_INFO_POSX", "CALIBRATION_INFO_POSY", "BATTERY_ICON_POSX", "BATTERY_ICON_POSY", "_USE_MARKER_SET_"]
MARKER_FREQ_SIZE = {"F072": 67, "F303": 116}     # plot.c
_extra_cache = {}


def constants(target):
    if target not in _extra_cache:
        _extra_cache[target] = srcinfo.eval_constants(target, _EXTRA)
    return _extra_cache[target]


def default_palette(L):
    return [L.palette[n] for n in L.palette_order]


def grid_params(fstart, fstop, width):
    """update_grid(): 1-2-5 grid step; returns (offset, width) in 1/128 px fixed point."""
    fspan = fstop - fstart
    if fspan == 0:
        return 0, 0
    dgrid = 1000000000; N = 4
    while True:
        grid = dgrid; k = fspan // grid
        if k >= N * 5: grid *= 5; break
        if k >= N * 2: grid *= 2; break
        if k >= N * 1: grid *= 1; break
        dgrid //= 10
        if dgrid == 0:
            grid = 1; break
    GRID_BITS = 7
    return ((fstart % grid) * (width << GRID_BITS)) // fspan, (grid * (width << GRID_BITS)) // fspan


def render(target, state, out_png=None):
    L = layout.get_layout(target); C = constants(target)
    pal = [tuple(p) for p in state.get("palette")] if state.get("palette") else default_palette(L)
    R = Raster(L.lcd_w, L.lcd_h, pal)
    R.fill(0, 0, L.lcd_w, L.lcd_h, PAL["BG"])
    nfont, sfont = fonts.load_font(L.font_name), fonts.load_font(L.sfont_name)
    freqs = state["frequencies"]; points = len(freqs)
    fstart, fstop = int(freqs[0]), int(freqs[-1])
    data = {0: state.get("s11", []), 1: state.get("s21", [])}
    traces = [t for t in state.get("traces", []) if t.get("enabled", True)]
    markers = state.get("markers", [])
    active = state.get("active_marker", 0 if markers else None)
    previous = state.get("previous_marker")
    GRIDY = C["GRIDY"]; OX, OY, W, H, COX = L.offset_x, L.offset_y, L.width, L.height, L.cell_offset_x

    # --- grid (rectangular_grid_x / _y), drawn over the plot area
    goff, gw = grid_params(fstart, fstop, W)
    types = set(t["type"] for t in traces)
    if types - set(ROUND):
        for y in range(0, H + 1):
            for x in range(0, W + 1):
                gx = x == 0 or x == W or (gw and (((x << 7) + goff) % gw) < (1 << 7))
                gy = (y % GRIDY) == 0
                if gx or gy:
                    R.set(OX + COX + x, OY + y, PAL["GRID"])
    PCX, PCY, PR = COX + W // 2, H // 2, H // 2          # P_CENTER_X / P_CENTER_Y / P_RADIUS
    if "SMITH" in types or "POLAR" in types:
        f = smith_grid if "SMITH" in types else polar_grid
        for y in range(H + 1):
            for x in range(COX, COX + W + 1):
                if f(x - PCX, y - PCY, PR):
                    R.set(OX + x, OY + y, PAL["GRID"])

    # --- traces (trace_into_index + cell_drawline)
    idx = {}
    dx = (W << 16) // (points - 1)
    for ti, t in enumerate(traces):
        fn, fmtstr, unit, refdef, scaledef = FORMATS[t["type"]]
        scale = float(t.get("scale", scaledef)); refpos = float(t.get("refpos", refdef))
        if t["type"] in ROUND:
            rscale = PR / scale; pts = []
            for i in range(points):
                v = data[t.get("channel", 0)][i]
                x = PCX + int(v[0] * rscale + 0.5); y = PCY - int(v[1] * rscale + 0.5)
                x = min(max(x, COX), COX + W); y = min(max(y, 0), H)
                pts.append((x, y))
            idx[ti] = pts; c = PAL["TRACE_1"] + ti
            for i in range(points - 1):
                R.line(OX + pts[i][0], OY + pts[i][1], OX + pts[i + 1][0], OY + pts[i + 1][1], c)
            continue
        ref = H - refpos * GRIDY + 0.5
        dscale = GRIDY / scale
        if t["type"] == "SWR":
            ref += dscale
        pts = []
        x = (COX << 16) + 0x8000
        for i in range(points):
            v = fn(data[t.get("channel", 0)][i])
            if math.isinf(v):
                y = 0
            else:
                y = int(ref - v * dscale)
                y = 0 if y < 0 else (H if y > H else y)
            pts.append((x >> 16, y)); x += dx
        idx[ti] = pts
        c = PAL["TRACE_1"] + ti
        for i in range(points - 1):
            R.line(OX + pts[i][0], OY + pts[i][1], OX + pts[i + 1][0], OY + pts[i + 1][1], c)

    # --- reference position marks (cell_draw_all_refpos): 6x5 triangle at the plot's left edge
    REF = [0b11000000, 0b11110000, 0b11111100, 0b11110000, 0b11000000]
    for ti, t in enumerate(traces):
        fn, fmtstr, unit, refdef, scaledef = FORMATS[t["type"]]
        if t["type"] in ROUND: continue
        ry = H - int(float(t.get("refpos", refdef)) * GRIDY) - 2
        R.blit(OX + COX - 5, OY + ry, 6, 5, REF, 8, PAL["TRACE_1"] + ti)

    # --- battery icon (draw_battery_status), 8 px wide bitmap column at BATTERY_ICON_POS
    vbat = state.get("vbat_mv")
    if vbat:
        rows_ = [0b00000000, 0b00111100, 0b00111100, 0b11111111]
        power = 4100
        while power > 3200:
            if (len(rows_) & 3) == 0:
                rows_.append(0b10000001); continue
            rows_.append(0b10000001 if power > vbat else 0b10111101); power -= 100
        rows_ += [0b10000001, 0b11111111]
        R.blit(C["BATTERY_ICON_POSX"], C["BATTERY_ICON_POSY"], 8, len(rows_), rows_, 8, PAL["LOW_BAT" if vbat < 3300 else "NORMAL_BAT"])

    # --- marker symbols
    mw, mh, mxo, myo, glyphs, bits = marker_bitmaps(C["_USE_MARKER_SET_"])
    for mi, m in enumerate(markers):
        if not m.get("enabled", True):
            continue
        for ti in range(len(traces)):
            px, py = idx[ti][m["index"]]
            x = px - mxo
            if py < mh * 2:
                y = py + 1; plate, num = glyphs[0][1], glyphs[mi + 1][1]
            else:
                y = py - myo; plate, num = glyphs[0][0], glyphs[mi + 1][0]
            R.blit(OX + x, OY + y, mw, mh, plate, bits, PAL["TRACE_1"] + ti)
            R.blit(OX + x, OY + y, mw, mh, num, bits, PAL["TXT_SHADOW"])

    # --- top readouts (cell_draw_marker_info); positions are absolute screen coordinates
    FW, FSH = L.font_w, L.font_str_h
    if markers and active is not None:
        aidx = markers[active]["index"]
        j = 0
        if previous is not None:
            t = state.get("current_trace", 0)
            for mi, m in enumerate(markers):
                if not m.get("enabled", True): continue
                xpos = (1 + (W // 2 if j % 2 else 0) + COX) + OX; ypos = 1 + (j // 2) * FSH + OY; j += 1
                col = PAL["TRACE_1"] + t
                if mi == active: R.text(nfont, "\x18", xpos, ypos, col, shadow=PAL["TXT_SHADOW"])
                xpos += FW
                R.text(nfont, "M%d" % (mi + 1), xpos, ypos, col, shadow=PAL["TXT_SHADOW"]); xpos += 3 * FW - 2
                R.text(nfont, fmt_freq(freqs[m["index"]], 0 if target == "F303" else 3) + "Hz", xpos, ypos, col, shadow=PAL["TXT_SHADOW"])
                xpos += MARKER_FREQ_SIZE[target]
                R.text(nfont, value_string(traces[t], data[traces[t].get("channel", 0)][m["index"]]), xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"])
            xpos = 21 + W // 2 + COX + OX; ypos = 1 + ((j + 1) // 2) * FSH + OY
            if previous != active:
                f, f1 = freqs[aidx], freqs[markers[previous]["index"]]
                n = R.text(nfont, "\x17%d-%d:" % (active + 1, previous + 1), xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"])
                xpos += 5 * FW + 2
                R.text(nfont, ("+" if f >= f1 else "-") + fmt_freq(abs(f - f1)) + "Hz", xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"])
        else:
            for ti, t in enumerate(traces):
                xpos = (1 + (W // 2 if j % 2 else 0) + COX) + OX; ypos = 1 + (j // 2) * FSH + OY; j += 1
                col = PAL["TRACE_1"] + ti
                if ti == state.get("current_trace", 0): R.text(nfont, "\x18", xpos, ypos, col, shadow=PAL["TXT_SHADOW"])
                xpos += FW
                R.text(nfont, "S%d1" % (1 + t.get("channel", 0)), xpos, ypos, col, shadow=PAL["TXT_SHADOW"]); xpos += 4 * FW - 2
                fn, fmtstr, unit, _, scaledef = FORMATS[t["type"]]
                scale = float(t.get("scale", scaledef))
                if t["type"] in ROUND:              # trace_print_info(): "%s %0.1fFS" or "%s "
                    info = "%s %sFS" % (t["type"], fmt_f(scale, 1)) if scale != 1.0 else "%s " % t["type"]
                else:
                    info = "%s %s%s/" % (t["type"], fmt_F(scale), unit)
                n = R.text(nfont, info, xpos, ypos, col, shadow=PAL["TXT_SHADOW"])
                xpos += (len(info) + 1) * FW - 5
                R.text(nfont, value_string(t, data[t.get("channel", 0)][aidx]), xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"])
            xpos = 21 + W // 2 + COX + OX; ypos = 1 + ((j + 1) // 2) * FSH + OY
            if state.get("lever_mode", "marker") == "marker": R.text(nfont, "\x18", xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"])
            xpos += FW
            R.text(nfont, "M%d:" % (active + 1), xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"]); xpos += 3 * FW + 4
            R.text(nfont, fmt_freq(freqs[aidx]) + "Hz", xpos, ypos, PAL["FG"], shadow=PAL["TXT_SHADOW"])

    # --- frequency line (draw_frequencies), small font
    yp = C["FREQUENCIES_YPOS"]
    R.text(sfont, " START %s" % fmt_freq(fstart).rjust(15) + "Hz", C["FREQUENCIES_XPOS1"], yp, PAL["FG"])
    R.text(sfont, " STOP %s" % fmt_freq(fstop).rjust(15) + "Hz", C["FREQUENCIES_XPOS2"], yp, PAL["FG"])
    R.text(sfont, "BW:%dHz %dp" % (state.get("bandwidth_hz", 1000), points), C["FREQUENCIES_XPOS3"], yp, PAL["BW_TEXT"])

    # --- status column (draw_cal_status)
    x, y = C["CALIBRATION_INFO_POSX"], C["CALIBRATION_INFO_POSY"]
    for i, s in enumerate(state.get("cal_letters", [])):
        col = PAL["INTERP_CAL"] if (i == 0 and s[:1] == "c") else PAL["FG"]
        R.text(sfont, s, x, y, col); y += L.sfont_str_h
    if state.get("power"):
        R.text(sfont, state["power"], x, y, PAL["FG"]); y += L.sfont_str_h
    if state.get("smooth"):
        y += L.font_str_h
        R.text(sfont, "s%d" % state["smooth"], x, y, PAL["FG"])
    if out_png:
        R.png(out_png)
    return R
