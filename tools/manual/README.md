# Manual generators

Scripts that produce the generated parts of `docs/manual/` from the firmware source.
Python 3 standard library only. Run from the repository root.

    python3 tools/manual/gen_menus.py          # menu map chapter + one SVG per menu, both targets
    python3 -m unittest tests.test_manual_gen  # parser/renderer checks

Requirements: `arm-none-eabi-gcc` (the firmware toolchain; the scripts look in
`/usr/local/gcc-arm-none-eabi-*/bin` if it is not on PATH) and GNU make — the
preprocessor is used to resolve per-target `#ifdef`s exactly as the firmware build does.

Descriptions for menu items live in `menu_desc.json` keyed `"<table>/<label>"`; items
without one render as `[describe]`. Sample values for labels that show a live value
(`%` formats) live in `menu_samples.json`.
