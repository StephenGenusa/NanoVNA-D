"""Render one firmware menu as an SVG mockup, following ui.c menu_draw_buttons / ui_draw_button."""
import re
import fonts
from menus import plain_label

_FMT = re.compile(r"%[-+ 0jb]*\d*(?:\.\d+)?[a-zA-Z]")


def label_text(item, samples):
    key = plain_label(item.label)
    subs = list(samples.get(key, []))
    def repl(m):
        return subs.pop(0) if subs else "--"
    text = _FMT.sub(repl, item.label)
    # ADV labels go through plot_printf then lcd_printf (two printf passes), so a
    # source "%%%%" collapses to a single literal "%".
    text = text.replace("%%%%", "%").replace("%%", "%")
    return text


def row_sample(samples, item, i):
    """Table-scoped sample lists (samples[item.table][key]) take precedence over the
    global key and are consumed in item order: row i of item.table gets table_list[i].
    Returns the flat samples view label_text should see for this one item."""
    table_samples = samples.get(item.table)
    key = plain_label(item.label)
    if not isinstance(table_samples, dict) or key not in table_samples:
        return samples
    row_list = table_samples[key]
    out = dict(samples)
    out[key] = [row_list[i]] if i < len(row_list) else []
    return out


def _rect(x, y, w, h, color):
    return '<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x, y, w, h, color)


def _draw_text(L, font, text, x, y, str_h, color_default, start_x):
    """Draw text with \\n and colour escapes; returns SVG fragments."""
    out = []
    color = color_default
    cx, cy = x, y
    i = 0
    run = ""
    def flush():
        nonlocal run, cx
        if run:
            out.append(fonts.svg_text(font, run, cx, cy, color))
            cx += font.text_width(run)
            run = ""
    while i < len(text):
        c = text[i]
        if c == "\n":
            flush(); cx = start_x; cy += str_h; i += 1
        elif c == "\x02" and i + 1 < len(text):
            flush(); color = L.rgb(L.palette_order[ord(text[i + 1])]); i += 2
        elif c == "\x01" and i + 1 < len(text):
            flush(); i += 2
        else:
            run += c; i += 1
    flush()
    return out


def render_menu_svg(menu, L, samples, selected=-1):
    items = menu.items
    n = len(items)
    h = L.button_height(n)
    x0, w, bw = L.lcd_w - L.menu_w, L.menu_w, L.menu_border
    normal, small = fonts.load_font(L.font_name), fonts.load_font(L.sfont_name)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" shape-rendering="crispEdges">'
             % (L.lcd_w, L.lcd_h, L.lcd_w, L.lcd_h), _rect(0, 0, L.lcd_w, L.lcd_h, L.rgb("BG"))]
    y = L.menu_y_off
    for i, it in enumerate(items[:L.menu_max]):
        sel = (i == selected)
        rise, fall = L.rgb("RISE_EDGE"), L.rgb("FALLEN_EDGE")
        top_right, left_bottom = (fall, rise) if sel else (rise, fall)
        parts += [_rect(x0, y, w, bw, top_right), _rect(x0, y, bw, h, left_bottom),
                  _rect(x0 + w - bw, y, bw, h, top_right), _rect(x0, y + h - bw, w, bw, left_bottom),
                  _rect(x0 + bw, y + bw, w - 2 * bw, h - 2 * bw, L.rgb("MENU_ACTIVE" if sel else "MENU"))]
        text = label_text(it, row_sample(samples, it, i))
        spec = samples.get("icons", {}).get(plain_label(it.label))
        if spec:
            ix, iy = x0 + bw + L.menu_icon_off, y + (h - L.icon_h) // 2
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="1"/>'
                         % (ix, iy, L.icon_w - 1, L.icon_h - 1, L.rgb("MENU_TEXT")))
            if spec == "checked":
                parts.append(_rect(ix + 3, iy + 3, L.icon_w - 6, L.icon_h - 6, L.rgb("MENU_TEXT")))
            tx = x0 + bw + L.menu_icon_off + L.icon_size
        else:
            tx = x0 + bw + L.menu_text_off
        lines = text.count("\n") + 1
        if L.font_name != L.sfont_name and h < lines * L.font_h + 2:
            font, str_h = small, L.sfont_str_h
            ty = y + (h - lines * str_h - 1) // 2
        else:
            font, str_h = normal, L.font_str_h
            ty = y + (h - lines * str_h + (str_h - L.font_h)) // 2
        parts.append('<g data-font="%s">' % font.name)
        parts += _draw_text(L, font, text, tx, ty, str_h, L.rgb("MENU_TEXT"), tx)
        parts.append("</g>")
        y += h
    parts.append("</svg>")
    return "\n".join(parts)
