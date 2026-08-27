"""Per-target screen layout, fonts and palette, taken from nanovna.h via the preprocessor."""
import os, re
from dataclasses import dataclass, field
import srcinfo

_NAMES = ["LCD_WIDTH", "LCD_HEIGHT", "OFFSETX", "OFFSETY", "WIDTH", "HEIGHT", "NGRIDY", "CELLOFFSETX",
          "AREA_WIDTH_NORMAL", "AREA_HEIGHT_NORMAL", "MENU_BUTTON_WIDTH", "MENU_BUTTON_MIN", "MENU_BUTTON_MAX",
          "MENU_BUTTON_Y_OFFSET", "MENU_BUTTON_BORDER", "MENU_ICON_OFFSET", "MENU_TEXT_OFFSET",
          "FONT_WIDTH", "FONT_GET_HEIGHT", "FONT_STR_HEIGHT", "sFONT_WIDTH", "sFONT_GET_HEIGHT", "sFONT_STR_HEIGHT",
          "_USE_FONT_", "_USE_SMALL_FONT_"]
_FONT_BY_ID = {0: "x5x7", 1: "x6x10", 2: "x7x11b", 3: "x11x14"}


@dataclass
class Layout:
    target: str
    device: str
    lcd_w: int; lcd_h: int; offset_x: int; offset_y: int; width: int; height: int; ngridy: int
    cell_offset_x: int; area_w: int; area_h: int
    menu_w: int; menu_min: int; menu_max: int; menu_y_off: int; menu_border: int; menu_icon_off: int; menu_text_off: int
    icon_size: int; icon_w: int; icon_h: int
    font_name: str; font_w: int; font_h: int; font_str_h: int
    sfont_name: str; sfont_w: int; sfont_h: int; sfont_str_h: int
    palette: dict = field(default_factory=dict)
    palette_order: list = field(default_factory=list)

    def button_height(self, n_items):
        n = max(self.menu_min, min(n_items, self.menu_max - 1)) if n_items < self.menu_max else self.menu_max
        return self.area_h // n

    def rgb(self, name):
        r, g, b = self.palette[name]
        return "#%02x%02x%02x" % (r, g, b)

    def palette_index(self, name):
        return self.palette_order.index(name)


def _palette():
    """Parse LCD_DEFAULT_PALETTE and the palette enum from nanovna.h."""
    with open(os.path.join(srcinfo.ROOT, "nanovna.h"), encoding="utf-8") as f:
        src = f.read()
    enum = src[src.index("LCD_BG_COLOR = 0"):src.index("LCD_DEFAULT_PALETTE")]
    order = [m for m in re.findall(r"^\s*LCD_([A-Z0-9_]+)_COLOR\b", enum, re.M)]
    pal = {}
    for name, r, g, b in re.findall(r"\[LCD_([A-Z0-9_]+)_COLOR\s*\]\s*=\s*RGB565\(\s*(\d+),\s*(\d+),\s*(\d+)\)", src):
        pal[name] = (int(r), int(g), int(b))
    missing = [n for n in order if n not in pal]
    if missing or len(order) < 20:
        raise RuntimeError("palette parse failed; missing %r, order %d" % (missing, len(order)))
    return pal, order


_cache = {}


def get_layout(target):
    if target in _cache:
        return _cache[target]
    c = srcinfo.eval_constants(target, _NAMES)
    pal, order = _palette()
    font = _FONT_BY_ID[c["_USE_FONT_"]]
    sfont = _FONT_BY_ID[c["_USE_SMALL_FONT_"]]
    # icons_menu.c: ICON_SIZE 14 (11x11 icons) for fonts below x11x14, else ICON_SIZE 18 (14x14 icons)
    icon_w = icon_h = 11 if c["_USE_FONT_"] < 3 else 14
    L = Layout(target=target, device=srcinfo.TARGETS[target],
               lcd_w=c["LCD_WIDTH"], lcd_h=c["LCD_HEIGHT"], offset_x=c["OFFSETX"], offset_y=c["OFFSETY"],
               width=c["WIDTH"], height=c["HEIGHT"], ngridy=c["NGRIDY"], cell_offset_x=c["CELLOFFSETX"],
               area_w=c["AREA_WIDTH_NORMAL"], area_h=c["AREA_HEIGHT_NORMAL"],
               menu_w=c["MENU_BUTTON_WIDTH"], menu_min=c["MENU_BUTTON_MIN"], menu_max=c["MENU_BUTTON_MAX"],
               menu_y_off=c["MENU_BUTTON_Y_OFFSET"], menu_border=c["MENU_BUTTON_BORDER"],
               menu_icon_off=c["MENU_ICON_OFFSET"], menu_text_off=c["MENU_TEXT_OFFSET"],
               icon_size=14 if c["_USE_FONT_"] < 3 else 18, icon_w=icon_w, icon_h=icon_h,
               font_name=font, font_w=c["FONT_WIDTH"], font_h=c["FONT_GET_HEIGHT"], font_str_h=c["FONT_STR_HEIGHT"],
               sfont_name=sfont, sfont_w=c["sFONT_WIDTH"], sfont_h=c["sFONT_GET_HEIGHT"], sfont_str_h=c["sFONT_STR_HEIGHT"],
               palette=pal, palette_order=order)
    _cache[target] = L
    return L
