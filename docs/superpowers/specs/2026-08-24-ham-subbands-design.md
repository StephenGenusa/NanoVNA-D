# Ham Sub-Band Segments (F303/H4 only) — Design Spec

**Date:** 2026-08-24
**Status:** Approved
**Builds on:** `docs/superpowers/specs/2026-08-24-ham-bands-design.md` (shipped:
plain band-edge indicator with 9-region setting, both targets).

## Problem

The band indicator shows only band edges. Users tuning antennas care where
the CW, digital, and phone segments fall inside a band (e.g., an 80 m
antenna resonant at 3.55 MHz vs. 3.75 MHz serves different operators).
Segment data costs ~1.5–2 KB of flash — affordable only on the F303/H4
(~50 KB free); the F072/H has ~2.9 KB left and its 16 KB RAM is fully
committed, which also rules out the SD-card-offload alternative (tables
loaded from SD need persistent RAM; `const` flash tables need none).

## Decisions

### Target scope
New guard `__USE_HAM_SUBBANDS__`, defined **only** under
`#if defined(NANOVNA_F303)` in `nanovna.h` (next to `__LCD_BRIGHTNESS__`,
the existing F303-only pattern). It additionally requires
`__USE_HAM_BAND_INDICATOR__`. The F072 binary is byte-for-byte unaffected;
the H keeps the plain edge bar.

### Segment data model: 3 IARU plans, not 9 country tables
Segment tables exist **only for the three IARU regional band plans**. Each
of the 9 selectable regions maps to a parent plan, and segments are drawn
**clipped to the intersection of the segment and the region's own band
edges** (from the existing edge tables):

| Region setting | Segment plan |
|---|---|
| 1 IARU R1, 6 UK, 7 Germany | IARU Region 1 |
| 2 IARU R2, 4 USA, 5 Canada | IARU Region 2 |
| 3 IARU R3, 8 Japan, 9 Australia | IARU Region 3 |

Rationale: this sidesteps the per-country license-class problem entirely
(US phone edges differ by class; the IARU plan is a class-neutral
band-plan guide, which is what a display indicator is), and cuts authoring
from ~9 tables to 3. Clipping to the country's edge table keeps it honest
(e.g., R1 segments above 3.8 MHz never show for UK/Germany because their
80 m edge table ends at 3.8 MHz).

### Segment types and scope
Three types, following the IARU bandwidth-class structure:

- `HAM_SEG_CW` — CW / ≤200 Hz segments
- `HAM_SEG_DIGI` — narrow-band digimode segments (≤500 Hz; beacon slices
  fold into this)
- `HAM_SEG_PHONE` — all-modes / phone segments

**HF only (135.7 kHz – 29.7 MHz).** Bands above 29.7 MHz (6 m and up)
render edge-only even on the H4: VHF+ plans are dominated by repeater/
satellite/beacon channelization that a 2 px bar cannot meaningfully show,
and antenna sub-band tuning is an HF concern. Estimated data: 3 plans ×
~10 HF bands × ~3 segments ≈ 90–110 entries.

Storage: plain structs (no packing — the H4 doesn't need it):
```c
typedef struct {
  freq_t  start;
  freq_t  end;
  uint8_t type;   // HAM_SEG_CW / HAM_SEG_DIGI / HAM_SEG_PHONE
} ham_segment_t;   // 12 B aligned
```
≈ 1.3 KB data + ~0.4 KB render/lookup code, F303 only.

API (in `vna_modules/vna_hambands.c`, prototype in `nanovna.h` under the
new guard):
```c
const ham_segment_t *ham_segments_get(uint8_t region, uint16_t *count);
// Maps region -> parent IARU plan; NULL for region 0/invalid.
```

### Rendering
`cell_draw_ham_bands()` in `plot.c` keeps its current structure. Per
visible band it first draws the full-width bar in `LCD_LINK_COLOR` (as
today — this remains the "edge/unclassified" color), then, under
`__USE_HAM_SUBBANDS__`, overlays each segment that intersects
`[band ∩ sweep]` in its type color. Same 2 px bar, same minimum 1 px
rule per segment. VHF+ bands and gaps with no segment data are left in
`LCD_LINK_COLOR` — so the display degrades gracefully wherever segment
data doesn't exist.

### Colors: compile-time constants, not palette entries
`config._lcd_palette` has 5 unused slots (27 enum entries of
`MAX_PALETTE` 32), but **old saved configs hold zeros there** — new
palette indices would render black-on-black after `config_recall` without
a `CONFIG_MAGIC` bump. Segment colors are not worth resetting everyone's
config or adding fallback logic, so they are fixed `RGB565()` compile-time
constants (the macro resolves correctly for both 8-bit and 16-bit LCD
modes):

```c
#define HAM_SEG_CW_COLOR    RGB565(255, 96,  0)   // orange
#define HAM_SEG_DIGI_COLOR  RGB565(  0,160,255)   // light blue
#define HAM_SEG_PHONE_COLOR RGB565(  0,200,  0)   // green
```
(Edges/unclassified stay on the user-configurable `LCD_LINK_COLOR`.)

### UI
**No new UI.** Segment coloring is automatic on the H4 whenever the
existing HAM BANDS region setting is not OFF. The existing submenu,
`config._ham_region` persistence, and config compatibility are untouched.
A show/hide-segments toggle is possible later (one `_vna_mode`-independent
config bit or reuse of a reserved byte) if anyone asks.

### Validation
Extend `tests/test_hambands.c` (host gcc, same command): compile with
`__USE_HAM_SUBBANDS__`-equivalent defines and assert for each of the 3
segment plans: entries sorted, non-overlapping, `start < end`, type is
one of the 3 values, range within [135700, 29700000], and **every segment
lies inside a band of the corresponding IARU edge table** (catches typos
against the already-validated edge data). Segment values are authored
from the current IARU R1/R2/R3 HF band plans, cited in comments, at
implementation time.

## Out of scope

- Sub-bands on the F072/H (flash and RAM budget; edge bar unchanged there).
- SD-card-resident band data (saves ~nothing: only 1.2 KB of the feature
  is data, loader code eats the savings, and loaded tables would need RAM
  neither target has). Revisit only as a *custom user bands* feature.
- VHF/UHF segmentation, license-class variants, beacon/satellite as
  distinct types, per-type user colors, on-screen labels.

## Risks

- **Two targets now render differently** — mitigated: difference is purely
  additive coloring inside one function under one guard; edge behavior is
  identical code.
- **Band-plan drift** (IARU plans get revised) — mitigated: single source
  file, cited sources, host test guards structure; values are a display
  guide, not a legal reference.
- **Color legibility on custom palettes** — fixed colors were chosen
  against the default black background; a user with a white background
  theme keeps legibility since all three constants are mid-brightness.
