# Manual generators

Scripts that produce the generated parts of `docs/manual/` from the firmware source.
Python 3 standard library only. Run from the repository root.

    python3 tools/manual/gen_menus.py          # menu map chapter + one SVG per menu, both targets
    python3 -m unittest tests.test_manual_gen  # parser/renderer checks

Requirements: `arm-none-eabi-gcc` (the firmware toolchain; the scripts look in
`/usr/local/gcc-arm-none-eabi-*/bin` if it is not on PATH) and GNU make — the
preprocessor is used to resolve per-target `#ifdef`s exactly as the firmware build does.

Descriptions for menu items live in `menu_desc.json` keyed `"<table>/<label>"`, where
`<label>` is the item's plain first line with firmware glyph bytes (the nanovna.h `S_*`
macros, e.g. BACK/MORE arrows, Ω, °) translated to real characters and any `%` format
left in place (e.g. `"menu_formatS11/CABLE LOSS"`, `"menu_device/›DFU"`); items without
one render as `[describe]`. Sample values for labels that show a live value (`%`
formats) live in `menu_samples.json`: a flat `"label with %": [...]` key applies
wherever that exact label occurs; a table-scoped key (the table name, e.g.
`"menu_ham_bands"`) holds `{label: [...]}` overrides consumed one value per row, in
item order, for just that table -- and, where the value differs by target (e.g.
`menu_sweep_points`, from `POINTS_SET` in nanovna.h), `{label: {"H": [...], "H4":
[...]}}`.

Some ADV-callback buttons rewrite their whole label at runtime from other state (e.g.
POWER's "AUTO" vs the wattage buttons) rather than filling in the table's own `%`
format; the mockups substitute the table's static label and sample values in these
cases, so they can differ structurally from the real device's screen, and the numbers
shown throughout are illustrative samples, not live readings.
