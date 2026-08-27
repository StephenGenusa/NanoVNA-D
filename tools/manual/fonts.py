"""Parse the firmware's bitmap fonts (fonts/*.c) and render text to pixels / SVG."""
import os, re
import srcinfo

_FILES = {"x5x7": "Font5x7.c", "x6x10": "Font6x10.c", "x7x11b": "Font7x11b.c"}
_HEIGHT = {"x5x7": 7, "x6x10": 10, "x7x11b": 11}
_WIDTH = {"x5x7": 5, "x6x10": 6, "x7x11b": 7}
_ROW = re.compile(r"^\s*(0b[01]{8})(?:\s*\|\s*CW_(\d\d))?\s*,", re.M)


class Font:
    def __init__(self, name, width, height, glyphs):
        self.name, self.width, self.height, self.glyphs, self.start = name, width, height, glyphs, 0x16

    def glyph(self, ch):
        i = ch - self.start
        if 0 <= i < len(self.glyphs):
            return self.glyphs[i]
        return (self.width, [0] * self.height)

    def text_width(self, s):
        width = 0
        i = 0
        while i < len(s):
            if ord(s[i]) < 0x09:              # colour-escape byte consumes next byte too
                i += 2                        # skip both escape and colour index
            else:
                width += self.glyph(ord(s[i]))[0]
                i += 1
        return width

    def pixels(self, s, x, y):
        out = []
        i = 0
        while i < len(s):
            if ord(s[i]) < 0x09:              # colour-escape byte consumes next byte too; neither drawn, x doesn't advance
                i += 2                        # skip both escape and colour index
            else:
                w, rows = self.glyph(ord(s[i]))
                for dy, row in enumerate(rows):
                    for dx in range(w):
                        if row & (0x80 >> dx):
                            out.append((x + dx, y + dy))
                x += w
                i += 1
        return out

    def rows_text(self, s):
        """Debug aid: glyph bitmaps as strings."""
        return ["".join("#" if r & (0x80 >> i) else "." for i in range(8)) for c in s for r in self.glyph(ord(c))[1]]


def _parse(name):
    path = os.path.join(srcinfo.ROOT, "fonts", _FILES[name])
    with open(path, encoding="utf-8") as f:
        src = f.read()
    start = src.index("const uint8_t %s_bits[] =" % name)
    body = src[start:src.index("};", start)]
    # drop the '#if 0 ... #endif' block of unused glyphs
    body = re.sub(r"#if 0.*?#endif", "", body, flags=re.S)
    rows = []
    for bits, cw in _ROW.findall(body):
        rows.append(int(bits, 2) | ((8 - int(cw)) if cw else 0))
    h = _HEIGHT[name]
    if len(rows) % h:
        raise RuntimeError("%s: %d rows is not a multiple of height %d" % (name, len(rows), h))
    glyphs = []
    for i in range(0, len(rows), h):
        g = rows[i:i + h]
        width = 8 - (g[0] & 7)
        glyphs.append((width, [r & 0xFF for r in g]))
    if len(glyphs) != 0x7F - 0x16:
        raise RuntimeError("%s: expected %d glyphs, parsed %d" % (name, 0x7F - 0x16, len(glyphs)))
    return Font(name, _WIDTH[name], h, glyphs)


_cache = {}


def load_font(name):
    if name not in _cache:
        _cache[name] = _parse(name)
    return _cache[name]


def svg_text(font, s, x, y, color):
    px = font.pixels(s, x, y)
    if not px:
        return ""
    d = "".join("M%d %dh1v1h-1z" % p for p in px)
    return '<path fill="%s" d="%s"/>' % (color, d)
