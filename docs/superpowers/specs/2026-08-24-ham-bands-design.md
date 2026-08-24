# Ham Band Indicators with Region Setting — Design Spec

**Date:** 2026-08-24
**Status:** Approved
**Origin:** Port of orphaned PR #103 ("Add amateur radio band indicators plotting",
commit `4e252d19674294c2d707b7e824ca8c35c7ab955f`, wiped from upstream by a
pull[bot] force-push before merge; feature request #104 remains open upstream).

## Problem

Users want a visual indicator of amateur radio band edges on the frequency
axis of the sweep display. PR #103 implemented this but (a) never actually
landed upstream, (b) hardcoded a single IARU Region 1 table, and (c) carried
several defects (a `VNA_MODE` bit inserted mid-enum that shifts persisted
config bits, a `GET_PALTETTE_COLOR` typo since fixed upstream, a duplicate
prototype, a shadowed variable, a stale comment).

Band edges differ by ITU/IARU region and by country, so the port adds a
**region setting** instead of a hardcoded table.

## Decisions

### Region granularity (user-selected)
IARU regions **plus key countries** — 9 tables:

1. IARU Region 1 (Europe/Africa/Middle East/N. Asia)
2. IARU Region 2 (Americas)
3. IARU Region 3 (Asia-Pacific)
4. USA (FCC Part 97)
5. Canada (ISED)
6. UK (Ofcom)
7. Germany (BNetzA)
8. Japan (MIC)
9. Australia (ACMA)

Each table is a sorted array of `{uint32_t start_hz; uint32_t end_hz}` covering
allocations from 135.7 kHz through 1.3 GHz (23 cm), clipped to the device's
`FREQUENCY_MAX` (2.7 GHz). Estimated ~150 entries total ≈ 1.2–1.3 KB of
const flash data.

### Persistence
- New setting `_ham_region`: `0` = OFF (default), `1..9` = table index.
- Stored in `config_t` by renaming one byte of the existing
  `uint8_t _reserved[3]` tail (before `checksum`). Existing configs have this
  byte zeroed, so **old saved configs load as OFF with no `CONFIG_MAGIC` bump**
  and no format break in either direction.
- NOT a `VNA_MODE` bit — avoids PR #103's persisted-bitfield shift defect and
  a mode value >1 bit is needed anyway.

### Data/API module
New file `vna_modules/vna_hambands.c` (include-fragment pattern used by the
other `vna_modules`), guarded by `__USE_HAM_BAND_INDICATOR__` (enabled for
both targets in `nanovna.h`).

API:
```c
const char *ham_region_name(uint8_t region);            // short name for menu
const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count); // NULL if OFF
```

### Rendering
In `plot.c` `draw_cell()`, after grid rendering, matching the PR #103
approach but rewritten against the current renderer:
- Draw a **2 px horizontal bar in `LCD_LINK_COLOR`** along the bottom edge of
  the rectangular grid, spanning each band's on-screen extent.
- Frequency domain only (skipped in TDR/time domain, and when span is zero).
- Bands narrower than one pixel at the current span draw a minimum 1 px mark.
- Frequency→x mapping uses the same conversion as the existing grid/marker
  code; per-cell clipping via the standard cell coordinate offsets.
- Redraw via `request_to_redraw(REDRAW_AREA)` on region change.

### UI
`Scale` menu gains a **"HAM BANDS\n<current region name>"** entry opening a
submenu with the group-check pattern (`menu_bandwidth`-style, `MT_ADV_CALLBACK`):
OFF + 9 regions = 10 items + back = 11 ≤ `MENU_BUTTON_MAX` (16).

### Flash budget
F072 currently at 93,364 of 98,304 B → ~4.9 KB headroom. Feature estimate:
~1.3 KB data + ~0.5 KB code ≈ 1.8 KB — fits. **Fallback if the F072 build
overflows:** restrict `__USE_HAM_BAND_INDICATOR__` to F303 only.

### Validation
Host-side test (plain `gcc`, no cross-toolchain) compiled against the table
source asserting for every region: entries sorted ascending, `start < end`,
no overlaps, all within `[135700, FREQUENCY_MAX]`. Run manually / from a
small script; not wired into the firmware build.

## Out of scope (explicitly deferred)

- **Sub-band segments** (CW/digital/phone). Costed at ~+2–2.5 KB best case
  (packed 100 Hz-unit boundary encoding) up to +6–10 KB naive — against
  ~4.9 KB F072 headroom — and US segment edges vary by license class, making
  the data ill-defined without another setting. User decision 2026-08-24:
  keep out of scope; plain band edges only.
- Custom user-defined bands.
- On-screen band labels.
- Region auto-detect.

## Risks

- F072 flash overflow → mitigated by measured estimate + F303-only fallback.
- Config layout mistake → mitigated: only a rename of an existing zeroed
  reserved byte; struct size and offsets unchanged (assert via host test or
  `_Static_assert` on `sizeof(config_t)`).
- Band table correctness → mitigated by host-side validation test; tables
  cite their source (IARU band plans, FCC 97.301, etc.) in comments.
