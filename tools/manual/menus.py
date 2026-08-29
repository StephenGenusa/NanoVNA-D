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
    for name, body in re.findall(r"const menuitem_t \*(?:const\s+)?(\w+)\[\]\s*=\s*\{(.*?)\};", text, re.S):
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


def _build(menus, links, root="menu_top"):
    """Shared traversal for build_tree and variant_tables: walk from `root`, assigning
    each reachable table exactly one breadcrumb path, and record which tables actually
    received a mode-name-based segment (as opposed to the plain pushing item's label)
    when *they* were assigned. That -- and only that -- is what "variant" means: a table
    that some other, ultimately-unused ref would also have called ambiguous is not
    marked, because assign() is idempotent and only the ref that gets there first
    decides the path (see the comment below on assigning a whole link as a batch). This
    keeps the "(variant)" signal consistent with the breadcrumb build_tree actually
    produced, rather than a second, independently-computed guess that can disagree with
    it (e.g. menu_measure is one of menu_measure_cb's dispatch targets *and* one of
    menu_measure_acb's -- only the first ref to reach it should get a say).

    Within an ambiguous link (more than one target), a ref used by only one item in its
    own declaring table (menu_measure_cb: the single "MEASURE" item in menu_top) names
    one target directly and unambiguously -- the one the C array itself puts first, e.g.
    `menu_measure_list[MEASURE_NONE] = menu_measure`, so `links[ref][0]`. That target is
    the one actually reached by clicking the button in its default state, so it keeps
    the plain item-label path and is not variant; only the *other* targets, which the
    same single click cannot be labelled for, get a mode-name segment appended after the
    item's own label and are variant. A ref shared by several items in its own table
    (menu_format_acb, menu_measure_acb) has no such single "direct" item to exempt, so
    every target it can reach gets a mode-name-only segment (its own item label would be
    an arbitrary pick among the siblings sharing that ref, e.g. "LOGMAG") and is
    variant."""
    share = _ref_share_counts(menus)
    order = []
    paths = {}
    variant = set()
    # A shared/dispatch ref (e.g. menu_measure_acb) is typically reused by every item of
    # every table in its own target family (each of the small per-mode tables repeats the
    # same OFF/mode items with the same callback as the big picker table). A ref is
    # expanded once, from wherever it is first reached; every later occurrence (from a
    # sibling it already placed) is a no-op.
    expanded_refs = set()

    def assign(name, path, is_variant=False):
        """Give `name` its breadcrumb path if it doesn't have one yet. Returns True the
        one time this call is the one that assigns it (the caller should then descend
        into it); False if some earlier call already assigned it (do not re-path,
        re-mark variant, or re-descend)."""
        if name in paths:
            return False
        paths[name] = path
        order.append((name, path))
        if is_variant:
            variant.add(name)
        return True

    def walk(name):
        path = paths[name]
        for it in menus[name].items:
            label = plain_label(it.label).split("\n")[0].strip()
            if it.kind == "submenu" and it.ref:
                if assign(it.ref, path + [label]):
                    walk(it.ref)
            elif it.kind in ("callback", "adv") and it.ref in links:
                if it.ref in expanded_refs:
                    continue
                expanded_refs.add(it.ref)
                targets = links[it.ref]
                ambiguous = len(targets) > 1
                shared_in_table = share.get(it.ref, 1) > 1
                # Assign every target of this link its path (and variant status) *before*
                # descending into any of them -- see the docstring above for why: several
                # of these targets can themselves reuse the very same ref for their own
                # items, and descending into one before its siblings were assigned let
                # that inner, coincidentally-earlier walk invent its own (deeper) paths
                # for the rest, cascading one extra breadcrumb segment per sibling.
                newly = []
                for i, t in enumerate(targets):
                    if not ambiguous:
                        seg, is_var = [label], False
                    elif shared_in_table:
                        seg, is_var = [_mode_name(menus[t])], True
                    elif i == 0:
                        seg, is_var = [label], False
                    else:
                        seg, is_var = [label, _mode_name(menus[t])], True
                    if assign(t, path + seg, is_var):
                        newly.append(t)
                for t in newly:
                    walk(t)

    assign(root, [])
    walk(root)
    return order, variant


def build_tree(menus, links, root="menu_top"):
    order, _ = _build(menus, links, root)
    return order


def variant_tables(menus, links, root="menu_top"):
    _, variant = _build(menus, links, root)
    return variant
