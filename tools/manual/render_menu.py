"""Render one firmware menu as an SVG mockup, following ui.c menu_draw_buttons / ui_draw_button."""
import re
import fonts
from menus import plain_label

_FMT = re.compile(r"%[-+ 0jb]*\d*(?:\.\d+)?[a-zA-Z]")


def conversion_count(item):
    """Number of printf conversions in an item's raw label -- used to tell whether
    `label_text` will have to fall back to a "--" placeholder for it (finding I6)."""
    return len(_FMT.findall(item.label))


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


_ONE_DU = re.compile(r"^[^%]*%[-+ 0]*[du][^%]*$")
_DECIMAL = re.compile(r"^\d+$")


def label_positions(items):
    """0-based occurrence index of each item among the *other* items of the same table
    sharing the same (post-'%'-substitution-independent) plain label, and the total
    occurrence count per (table, label) -- used to align a table-scoped sample list
    (menu_samples.json) with the right row regardless of unrelated items interleaved
    before/after (e.g. an SD-card row ahead of the "Empty N" slots in menu_save), and to
    let row_sample fail loudly when a scoped list's length doesn't match (I4). Returns
    (positions, counts) where positions[id(item)] = occurrence index and
    counts[(table, label)] = total occurrences."""
    counts = {}
    for it in items:
        if it.kind != "adv":
            continue
        counts[(it.table, plain_label(it.label))] = counts.get((it.table, plain_label(it.label)), 0) + 1
    seen = {}
    positions = {}
    for it in items:
        if it.kind != "adv":
            continue
        key = (it.table, plain_label(it.label))
        positions[id(it)] = seen.get(key, 0)
        seen[key] = seen.get(key, 0) + 1
    return positions, counts


def _derive_from_data(item, key, total):
    """Last-resort sample: when a label has exactly one %d/%u conversion and item.data is
    itself the literal decimal value to show, use it directly. Restricted to the
    repeated-slot pattern this is actually meant for -- menu_trace's "TRACE %d" (0..3),
    menu_save/recall's "Empty %d" (0..N) -- by requiring at least two adv rows in the
    table to share this exact label (`total`, from label_positions): a one-off selector
    row that merely *displays* live global state via the same "%u"/"%d" shape (e.g.
    "IF BANDWIDTH\n %u" Hz, "SWEEP POINTS\n %u", "SERIAL SPEED\n %u", "IF OFFSET\n
    %d" Hz -- each the only row in its own table using that label, with data=0, a
    placeholder the callback ignores at runtime) must not be fabricated a "0" here; it is
    left to render "--" and be counted as a missing sample instead (I6). Not used at all
    when the shown value is merely a function of data (menu_power, menu_marker_sel):
    those need a table-scoped hand list in menu_samples.json instead (I3)."""
    if total is None or total < 2:
        return None
    if not _DECIMAL.match(item.data) or not _ONE_DU.match(key):
        return None
    return str(int(item.data))


def row_sample(samples, item, occ=0, total=None):
    """Table-scoped sample lists (samples[item.table][key]) take precedence over the
    global key and are consumed in occurrence order: the occ'th item of item.table using
    this label gets table_list[occ]. `total`, if given, is the number of adv items in
    item.table actually using this label on this target (see `label_positions`); a
    scoped list of any other length is a silent-misalignment risk (I4) and raises rather
    than rendering a wrong or truncated row. When no scoped or global sample is defined
    at all, falls back to deriving the value directly from item.data where that is valid
    (see `_derive_from_data`); otherwise returns `samples` unchanged so `label_text`
    renders its own "--" placeholder."""
    table_samples = samples.get(item.table)
    key = plain_label(item.label)
    if isinstance(table_samples, dict) and key in table_samples:
        row_list = table_samples[key]
        if total is not None and len(row_list) != total:
            raise RuntimeError(
                "%s: sample list for %r has %d entries but %d row(s) on this target use this label"
                % (item.table, key, len(row_list), total))
        out = dict(samples)
        out[key] = [row_list[occ]] if occ < len(row_list) else []
        return out
    if key not in samples:
        derived = _derive_from_data(item, key, total)
        if derived is not None:
            out = dict(samples)
            out[key] = [derived]
            return out
    return samples


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
    # Occurrence positions/counts must come from the *whole* table, not the
    # menu_max-truncated slice actually drawn -- a table-scoped sample list in
    # menu_samples.json is sized to the full table (gen_menus.py computes `total`
    # the same way), so truncating here first would make row_sample's I4 length
    # check compare against a smaller, wrong count and raise spuriously.
    positions, counts = label_positions(items)
    y = L.menu_y_off
    for i, it in enumerate(items[:L.menu_max]):
        sel = (i == selected)
        rise, fall = L.rgb("RISE_EDGE"), L.rgb("FALLEN_EDGE")
        top_right, left_bottom = (fall, rise) if sel else (rise, fall)
        parts += [_rect(x0, y, w, bw, top_right), _rect(x0, y, bw, h, left_bottom),
                  _rect(x0 + w - bw, y, bw, h, top_right), _rect(x0, y + h - bw, w, bw, left_bottom),
                  _rect(x0 + bw, y + bw, w - 2 * bw, h - 2 * bw, L.rgb("MENU_ACTIVE" if sel else "MENU"))]
        occ = positions.get(id(it), 0)
        total = counts.get((it.table, plain_label(it.label)))
        text = label_text(it, row_sample(samples, it, occ, total))
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
