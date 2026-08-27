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


def callback_links(text):
    lists = {}
    for name, body in re.findall(r"const menuitem_t \*(\w+)\[\]\s*=\s*\{(.*?)\};", text, re.S):
        lists[name] = re.findall(r"=\s*(menu_\w+)", body)
    links = {}
    for fname, body in _FUNC.findall(text):
        targets = []
        for arg in _PUSH.findall(body):
            for tok in re.findall(r"\bmenu_\w+", arg):
                if tok in lists:
                    targets += lists[tok]
                else:
                    targets.append(tok)
        if targets:
            links[fname] = sorted(set(targets), key=targets.index)
    return links


def build_tree(menus, links, root="menu_top"):
    order = []
    seen = set()

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
                for t in links[it.ref]:
                    walk(t, path + [label])
    walk(root, [])
    return order
