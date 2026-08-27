"""Parse the firmware's menu tables (menuitem_t arrays in preprocessed ui.c) into a tree."""
import re
from dataclasses import dataclass

_STR = r'"(?:[^"\\]|\\.)*"'
# gcc -E fully macro-expands NULL to ((void *)0); accept either spelling.
_NULL_LIT = r"\(\(void \*\)0\)"
_NULL = r"(?:NULL|%s)" % _NULL_LIT
_NULL_FORMS = ("NULL", "((void *)0)")
# one table (menu_sweep_points) casts its ref: "(const void *)menu_keyboard_acb" / "(const void *)menu_back".
# Strip an optional leading cast, guarded so it never eats the null form's own outer parenthesis.
_CAST = r"(?:(?!%s)\([^)]*\)\s*)?" % _NULL_LIT
_TABLE = re.compile(r"(static\s+)?const menuitem_t (menu_\w+)\[\]\s*=\s*\{(.*?)\};", re.S)
_ITEM = re.compile(r"\{\s*(MT_\w+)\s*,\s*([^,]+?)\s*,\s*((?:%s\s*)+|%s)\s*,\s*%s(\w+|%s)\s*\}" % (_STR, _NULL, _CAST, _NULL), re.S)
_ESC = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "'": "'", "0": "\0"}


@dataclass
class Item:
    kind: str
    data: str
    label: str
    ref: str
    table: str


@dataclass
class Menu:
    name: str
    items: list
    static: bool


def decode_c_string(lit):
    out = []
    for piece in re.findall(_STR, lit):
        s = piece[1:-1]
        i = 0
        while i < len(s):
            c = s[i]
            if c != "\\":
                out.append(c); i += 1; continue
            i += 1
            c = s[i]
            if c == "x":
                m = re.match(r"[0-9a-fA-F]{1,2}", s[i + 1:])
                out.append(chr(int(m.group(0), 16))); i += 1 + len(m.group(0))
            elif c in "01234567":
                m = re.match(r"[0-7]{1,3}", s[i:])
                out.append(chr(int(m.group(0), 8))); i += len(m.group(0))
            else:
                out.append(_ESC[c]); i += 1
    return "".join(out)


def plain_label(label):
    return re.sub(r"[\x01\x02].", "", label)


_KIND = {"MT_SUBMENU": "submenu", "MT_CALLBACK": "callback", "MT_ADV_CALLBACK": "adv", "MT_NEXT": "next"}


def parse_menus(text):
    menus = {}
    for static, name, body in _TABLE.findall(text):
        items = []
        consumed = 0
        for m in _ITEM.finditer(body):
            consumed += 1
            kind, data, label, ref = m.groups()
            if kind not in _KIND:
                raise RuntimeError("%s: unknown item type %s" % (name, kind))
            items.append(Item(_KIND[kind], data.strip(), decode_c_string(label) if label not in _NULL_FORMS else "",
                              None if ref in _NULL_FORMS else ref, name))
        braces = body.count("{")
        if consumed != braces:
            raise RuntimeError("%s: parsed %d items but found %d '{' — unrecognised item shape" % (name, consumed, braces))
        if not items or items[-1].kind != "next":
            raise RuntimeError("%s: table does not end with an MT_NEXT sentinel" % name)
        menus[name] = Menu(name, items, bool(static))
    # expand MT_NEXT continuations (e.g. menu_back appended to the end of most tables).
    # Resolve continuations against a snapshot of each table's original items: menus are
    # rewritten in place below, and a referenced table (e.g. menu_back, which is itself the
    # first table in source order) may already have had its own trailing MT_NEXT sentinel
    # stripped by the time a later table follows into it.
    original_items = {name: menu.items for name, menu in menus.items()}
    for menu in menus.values():
        expanded = []
        seen = set()
        cur = original_items[menu.name]
        while True:
            body, tail = cur[:-1], cur[-1]
            expanded += body
            if tail.ref is None:
                break
            if tail.ref in seen or tail.ref not in menus:
                raise RuntimeError("%s: bad MT_NEXT continuation %r" % (menu.name, tail.ref))
            seen.add(tail.ref)
            cur = original_items[tail.ref]
        menu.items = expanded
    return menus


_FUNC = re.compile(r"void\s+(\w+)\s*\(\s*uint16_t\s+data(?:\s*,\s*button_t\s*\*\s*b)?\s*\)\s*\{(.*?)\n\}", re.S)
_PUSH = re.compile(r"menu_(?:push|set)_submenu\(\s*([^)]*)\)")


class LinkMap(dict):
    """dict[callback name -> list of tables it pushes], plus (in `.list_expanded`) the
    subset of callback names whose push target came from expanding a `menu_*_list[]`
    array (dynamic, state-dependent dispatch: `menu_push_submenu(menu_measure_list[x])`)
    rather than naming a table directly. build_tree uses `.list_expanded` to tell a
    genuinely one-to-one push apart from a dispatch table, per finding I2."""

    def __init__(self):
        super().__init__()
        self.list_expanded = set()


def callback_links(text):
    lists = {}
    for name, body in re.findall(r"const menuitem_t \*(\w+)\[\]\s*=\s*\{(.*?)\};", text, re.S):
        lists[name] = re.findall(r"=\s*(menu_\w+)", body)
    links = LinkMap()
    for fname, body in _FUNC.findall(text):
        targets = []
        via_list = False
        for arg in _PUSH.findall(body):
            for tok in re.findall(r"\bmenu_\w+", arg):
                if tok in lists:
                    targets += lists[tok]
                    via_list = True
                else:
                    targets.append(tok)
        if targets:
            links[fname] = sorted(set(targets), key=targets.index)
            if via_list:
                links.list_expanded.add(fname)
    return links


_BARE_FMT = re.compile(r"^%[-+ #0-9.]*[a-zA-Z]$")


def _mode_name(menu):
    """A pushed table's own breadcrumb segment, used instead of the pushing item's label
    when that label can't be trusted to identify which table is meant (see
    `variant_tables`): the plain first line of the table's first MT_ADV_CALLBACK item
    whose label is real static text -- not "OFF", not empty, and not a bare printf
    conversion with no static text of its own (some tables, e.g. the smith-format
    selectors, give every row the literal label "%s" and rewrite it at runtime; that
    string is meaningless as a heading and would collide across tables). Falls back to
    the table name with its "menu_" prefix stripped."""
    for it in menu.items:
        if it.kind != "adv":
            continue
        first = plain_label(it.label).split("\n")[0].strip()
        if first and first != "OFF" and not _BARE_FMT.match(first):
            return first
    return menu.name[len("menu_"):] if menu.name.startswith("menu_") else menu.name


def _ref_share_counts(menus):
    """The largest number of items in any single table that share the same ref. A ref
    used this way more than once *within one table* (e.g. every FORMAT row shares
    menu_format_acb; every measure-mode row shares menu_measure_acb) makes that
    particular item's own label an arbitrary pick among siblings, not a real
    identification of which pushed table is meant."""
    counts = {}
    for menu in menus.values():
        local = {}
        for it in menu.items:
            if it.kind in ("callback", "adv") and it.ref:
                local[it.ref] = local.get(it.ref, 0) + 1
        for ref, c in local.items():
            counts[ref] = max(counts.get(ref, 0), c)
    return counts


def variant_tables(menus, links):
    """Tables reached only via an ambiguous push: a callback whose regex-detected targets
    span more than one table -- a real "which one?" case, whether from a literal
    A-or-B push (menu_format_acb: SMITH pushes menu_marker_s11smith or _s21smith
    depending on channel) or a `menu_*_list[]` dispatch across many state-dependent
    tables (menu_measure_acb/_cb: any of the measure-mode tables, chosen at runtime).
    For these `build_tree` brings in `_mode_name` for the breadcrumb (see there for
    how it is combined with the pushing item's own label), and callers should mark the
    heading (e.g. append " (variant)") to say so.

    A callback resolving to exactly one target -- e.g. every calibration step in
    menu_calop sharing one callback that only ever pushes menu_save -- is not
    ambiguous: this parser cannot see the runtime guard that makes only one of those
    items actually push, but since there is only one possible destination anyway, the
    item's own label identifies it fine."""
    variant = set()
    for targets in links.values():
        if len(targets) > 1:
            variant.update(targets)
    return variant


def build_tree(menus, links, root="menu_top"):
    variant = variant_tables(menus, links)
    share = _ref_share_counts(menus)
    order = []
    seen = set()
    # A shared/dispatch ref (e.g. menu_measure_acb) is typically reused by every item of
    # every table in its own target family (each of the small per-mode tables repeats the
    # same OFF/mode items with the same callback as the big picker table). Expanding it
    # again from inside a sibling that ref already placed would re-derive fresh (deeper)
    # paths for the remaining siblings depth-first, cascading one extra breadcrumb segment
    # per sibling. A ref is expanded once, from wherever it is first reached; every later
    # occurrence (from a sibling it already placed) is a no-op.
    expanded_refs = set()

    def walk(name, path):
        if name in seen:
            return
        seen.add(name)
        order.append((name, path))
        for it in menus[name].items:
            label = plain_label(it.label).split("\n")[0].strip()
            if it.kind == "submenu" and it.ref:
                walk(it.ref, path + [label])
            elif it.kind in ("callback", "adv") and it.ref in links:
                if it.ref in expanded_refs:
                    continue
                expanded_refs.add(it.ref)
                for t in links[it.ref]:
                    if t not in variant:
                        seg = [label]
                    elif share.get(it.ref, 1) > 1:
                        # the item's own label is an arbitrary pick among siblings that
                        # share this ref (e.g. "LOGMAG") -- drop it, use the target
                        # table's own mode name instead.
                        seg = [_mode_name(menus[t])]
                    else:
                        # exactly one item pushes via this ref (so its label -- e.g.
                        # "MEASURE" -- genuinely names what was clicked), but the push
                        # is a multi-way dispatch, so name the specific mode reached too.
                        seg = [label, _mode_name(menus[t])]
                    walk(t, path + seg)
    walk(root, [])
    return order
