# Ham Sub-Band Segments (F303-only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the F303/H4 only, color the existing ham band indicator bar by sub-band type (CW / narrow digital / phone) using the three IARU regional band plans, leaving the F072/H binary unchanged.

**Architecture:** Segment tables for the 3 IARU plans live in `vna_modules/vna_hambands.c` under a new `__USE_HAM_SUBBANDS__` guard (defined only for `NANOVNA_F303` in `nanovna.h`). Each of the 9 region settings maps to a parent plan (USA/Canada→R2, UK/Germany→R1, Japan/Australia→R3). Rendering stays inside `cell_draw_ham_bands()` in `plot.c`: the gold edge bar is drawn first as today, then segments overlay it clipped to each band's on-screen extent, in fixed compile-time `RGB565()` colors (deliberately NOT config palette entries — old saved configs hold zeros in spare palette slots and would render black). No UI changes; segments follow the existing HAM BANDS region setting.

**Tech Stack:** C (GCC ARM 8-2018-q4-major cross target, host `gcc` for the table test), include-fragment pattern, no build-system changes.

**Spec:** `docs/superpowers/specs/2026-08-24-ham-subbands-design.md`

## Global Constraints

- New guard `__USE_HAM_SUBBANDS__` defined **only** when `defined(NANOVNA_F303) && defined(__USE_HAM_BAND_INDICATOR__)`.
- The F072 build must be unaffected: after all tasks, `./1_build.sh F072` must produce a binary of exactly **95,416 bytes** (current master size) with zero new warnings.
- Segment types: `HAM_SEG_CW` / `HAM_SEG_DIGI` / `HAM_SEG_PHONE` only. Segments HF-only: all within [135700, 29700000] Hz.
- Segment colors are compile-time constants: CW `RGB565(255, 96, 0)`, DIGI `RGB565(0,160,255)`, PHONE `RGB565(0,200,0)`. No new `config_t` fields, no palette entries, no `CONFIG_MAGIC` change.
- Region numbering (1..9) from the parent feature is frozen; the plan-mapping table indexes it.
- Both targets must build via `./1_build.sh F072` / `./1_build.sh F303`; host test via `gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`.
- Every task ends with a commit; messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Do not push unless the user asks (origin = user's fork, push works via SSH).

---

### Task 1: Segment tables, region→plan mapping, API, host test

**Files:**
- Modify: `vna_modules/vna_hambands.c` (append after `ham_bands_get()`)
- Test: `tests/test_hambands.c`

**Interfaces:**
- Consumes: existing `ham_band_t`, `HAM_REGION_COUNT` (9), `ham_bands_get(uint8_t, uint16_t*)`, `ham_regions[]`, and the `HAM_BANDS_HOST_TEST` host-compile convention.
- Produces (used by Task 2):
  - `enum {HAM_SEG_CW = 0, HAM_SEG_DIGI, HAM_SEG_PHONE};`
  - `typedef struct { freq_t start; freq_t end; uint8_t type; } ham_segment_t;`
  - `const ham_segment_t *ham_segments_get(uint8_t region, uint16_t *count);` — maps region 1..9 to its parent IARU plan's segment table; `NULL` for 0/out-of-range.

- [ ] **Step 1: Append the segment section to `vna_modules/vna_hambands.c`**

Add at the end of the file. Values compiled from the IARU Region 1 HF band plan (2020 rev.), IARU Region 2 band plan (2016 rev.), and IARU Region 3 band plan; beacon slices folded into DIGI per the spec. Step 4 cross-checks them.

```c
#ifdef __USE_HAM_SUBBANDS__
/*
 * HF sub-band segments (CW / narrow digital / phone) for the three IARU
 * regional band plans. Country regions map to their parent plan (see
 * ham_region_plan[]); the renderer clips segments to the region's own
 * band edges, so plan segments wider than a country's band never show.
 * Beacon slices are folded into HAM_SEG_DIGI. HF only (<= 29.7 MHz);
 * VHF+ bands render edge-only.
 */
#ifdef HAM_BANDS_HOST_TEST
enum {HAM_SEG_CW = 0, HAM_SEG_DIGI, HAM_SEG_PHONE};
typedef struct {
  freq_t  start;
  freq_t  end;
  uint8_t type;
} ham_segment_t;
#endif

// IARU Region 1 HF band plan segments
static const ham_segment_t ham_segments_r1[] = {
  {135700,   137400,   HAM_SEG_CW},    // 2200m CW
  {137400,   137800,   HAM_SEG_DIGI},  // 2200m narrow digi
  {472000,   475000,   HAM_SEG_CW},    // 630m CW
  {475000,   479000,   HAM_SEG_DIGI},  // 630m CW/digi
  {1810000,  1838000,  HAM_SEG_CW},    // 160m CW
  {1838000,  1843000,  HAM_SEG_DIGI},  // 160m narrow digi
  {1843000,  2000000,  HAM_SEG_PHONE}, // 160m all modes
  {3500000,  3570000,  HAM_SEG_CW},    // 80m CW
  {3570000,  3600000,  HAM_SEG_DIGI},  // 80m narrow digi
  {3600000,  3800000,  HAM_SEG_PHONE}, // 80m all modes
  {5351500,  5354000,  HAM_SEG_CW},    // 60m CW/narrow
  {5354000,  5366000,  HAM_SEG_PHONE}, // 60m all modes (USB)
  {5366000,  5366500,  HAM_SEG_DIGI},  // 60m weak signal narrow
  {7000000,  7040000,  HAM_SEG_CW},    // 40m CW
  {7040000,  7050000,  HAM_SEG_DIGI},  // 40m narrow digi
  {7050000,  7200000,  HAM_SEG_PHONE}, // 40m all modes
  {10100000, 10130000, HAM_SEG_CW},    // 30m CW
  {10130000, 10150000, HAM_SEG_DIGI},  // 30m narrow digi (no phone on 30m)
  {14000000, 14070000, HAM_SEG_CW},    // 20m CW
  {14070000, 14101000, HAM_SEG_DIGI},  // 20m digi (incl beacons 14099-14101)
  {14101000, 14350000, HAM_SEG_PHONE}, // 20m all modes
  {18068000, 18095000, HAM_SEG_CW},    // 17m CW
  {18095000, 18111000, HAM_SEG_DIGI},  // 17m digi (incl beacons)
  {18111000, 18168000, HAM_SEG_PHONE}, // 17m all modes
  {21000000, 21070000, HAM_SEG_CW},    // 15m CW
  {21070000, 21151000, HAM_SEG_DIGI},  // 15m digi (incl beacons 21149-21151)
  {21151000, 21450000, HAM_SEG_PHONE}, // 15m all modes
  {24890000, 24915000, HAM_SEG_CW},    // 12m CW
  {24915000, 24931000, HAM_SEG_DIGI},  // 12m digi (incl beacons)
  {24931000, 24990000, HAM_SEG_PHONE}, // 12m all modes
  {28000000, 28070000, HAM_SEG_CW},    // 10m CW
  {28070000, 28225000, HAM_SEG_DIGI},  // 10m digi (incl beacons 28190-28225)
  {28225000, 29700000, HAM_SEG_PHONE}, // 10m all modes
};

// IARU Region 2 HF band plan segments
static const ham_segment_t ham_segments_r2[] = {
  {135700,   137400,   HAM_SEG_CW},    // 2200m CW
  {137400,   137800,   HAM_SEG_DIGI},  // 2200m narrow digi
  {472000,   475000,   HAM_SEG_CW},    // 630m CW
  {475000,   479000,   HAM_SEG_DIGI},  // 630m CW/digi
  {1800000,  1810000,  HAM_SEG_DIGI},  // 160m digimodes
  {1810000,  1840000,  HAM_SEG_CW},    // 160m CW
  {1840000,  2000000,  HAM_SEG_PHONE}, // 160m all modes
  {3500000,  3570000,  HAM_SEG_CW},    // 80m CW
  {3570000,  3600000,  HAM_SEG_DIGI},  // 80m narrow digi
  {3600000,  4000000,  HAM_SEG_PHONE}, // 75/80m all modes
  {5330500,  5406400,  HAM_SEG_PHONE}, // 60m channelized USB (envelope)
  {7000000,  7040000,  HAM_SEG_CW},    // 40m CW
  {7040000,  7043000,  HAM_SEG_DIGI},  // 40m narrow digi
  {7043000,  7300000,  HAM_SEG_PHONE}, // 40m all modes
  {10100000, 10130000, HAM_SEG_CW},    // 30m CW
  {10130000, 10150000, HAM_SEG_DIGI},  // 30m narrow digi (no phone on 30m)
  {14000000, 14070000, HAM_SEG_CW},    // 20m CW
  {14070000, 14101000, HAM_SEG_DIGI},  // 20m digi (incl beacons)
  {14101000, 14350000, HAM_SEG_PHONE}, // 20m all modes
  {18068000, 18095000, HAM_SEG_CW},    // 17m CW
  {18095000, 18111000, HAM_SEG_DIGI},  // 17m digi (incl beacons)
  {18111000, 18168000, HAM_SEG_PHONE}, // 17m all modes
  {21000000, 21070000, HAM_SEG_CW},    // 15m CW
  {21070000, 21151000, HAM_SEG_DIGI},  // 15m digi (incl beacons)
  {21151000, 21450000, HAM_SEG_PHONE}, // 15m all modes
  {24890000, 24915000, HAM_SEG_CW},    // 12m CW
  {24915000, 24931000, HAM_SEG_DIGI},  // 12m digi (incl beacons)
  {24931000, 24990000, HAM_SEG_PHONE}, // 12m all modes
  {28000000, 28070000, HAM_SEG_CW},    // 10m CW
  {28070000, 28300000, HAM_SEG_DIGI},  // 10m digi (incl beacons 28190-28300)
  {28300000, 29700000, HAM_SEG_PHONE}, // 10m all modes
};

// IARU Region 3 HF band plan segments
static const ham_segment_t ham_segments_r3[] = {
  {135700,   137400,   HAM_SEG_CW},    // 2200m CW
  {137400,   137800,   HAM_SEG_DIGI},  // 2200m narrow digi
  {472000,   475000,   HAM_SEG_CW},    // 630m CW
  {475000,   479000,   HAM_SEG_DIGI},  // 630m CW/digi
  {1800000,  1838000,  HAM_SEG_CW},    // 160m CW
  {1838000,  1843000,  HAM_SEG_DIGI},  // 160m narrow digi
  {1843000,  2000000,  HAM_SEG_PHONE}, // 160m all modes
  {3500000,  3570000,  HAM_SEG_CW},    // 80m CW
  {3570000,  3600000,  HAM_SEG_DIGI},  // 80m narrow digi
  {3600000,  3900000,  HAM_SEG_PHONE}, // 80m all modes
  {5351500,  5354000,  HAM_SEG_CW},    // 60m CW/narrow
  {5354000,  5366000,  HAM_SEG_PHONE}, // 60m all modes (USB)
  {5366000,  5366500,  HAM_SEG_DIGI},  // 60m weak signal narrow
  {7000000,  7025000,  HAM_SEG_CW},    // 40m CW
  {7025000,  7035000,  HAM_SEG_DIGI},  // 40m narrow digi
  {7035000,  7200000,  HAM_SEG_PHONE}, // 40m all modes
  {10100000, 10130000, HAM_SEG_CW},    // 30m CW
  {10130000, 10150000, HAM_SEG_DIGI},  // 30m narrow digi (no phone on 30m)
  {14000000, 14070000, HAM_SEG_CW},    // 20m CW
  {14070000, 14101000, HAM_SEG_DIGI},  // 20m digi (incl beacons)
  {14101000, 14350000, HAM_SEG_PHONE}, // 20m all modes
  {18068000, 18095000, HAM_SEG_CW},    // 17m CW
  {18095000, 18111000, HAM_SEG_DIGI},  // 17m digi (incl beacons)
  {18111000, 18168000, HAM_SEG_PHONE}, // 17m all modes
  {21000000, 21070000, HAM_SEG_CW},    // 15m CW
  {21070000, 21151000, HAM_SEG_DIGI},  // 15m digi (incl beacons)
  {21151000, 21450000, HAM_SEG_PHONE}, // 15m all modes
  {24890000, 24915000, HAM_SEG_CW},    // 12m CW
  {24915000, 24931000, HAM_SEG_DIGI},  // 12m digi (incl beacons)
  {24931000, 24990000, HAM_SEG_PHONE}, // 12m all modes
  {28000000, 28070000, HAM_SEG_CW},    // 10m CW
  {28070000, 28300000, HAM_SEG_DIGI},  // 10m digi (incl beacons)
  {28300000, 29700000, HAM_SEG_PHONE}, // 10m all modes
};

// Region (1..9) -> parent IARU plan (1..3). Index is region-1.
// 1=IARU R1 2=IARU R2 3=IARU R3 4=USA 5=Canada 6=UK 7=Germany 8=Japan 9=Australia
static const uint8_t ham_region_plan[HAM_REGION_COUNT] = {1, 2, 3, 2, 2, 1, 1, 3, 3};

typedef struct {
  const ham_segment_t *segments;
  uint16_t count;
} ham_seg_table_t;

#define HAM_SEG_TABLE(tbl) {tbl, sizeof(tbl)/sizeof(tbl[0])}
static const ham_seg_table_t ham_seg_tables[3] = {
  HAM_SEG_TABLE(ham_segments_r1),
  HAM_SEG_TABLE(ham_segments_r2),
  HAM_SEG_TABLE(ham_segments_r3),
};

const ham_segment_t *ham_segments_get(uint8_t region, uint16_t *count) {
  if (region == 0 || region > HAM_REGION_COUNT) return NULL;
  const ham_seg_table_t *t = &ham_seg_tables[ham_region_plan[region - 1] - 1];
  *count = t->count;
  return t->segments;
}
#endif // __USE_HAM_SUBBANDS__
```

- [ ] **Step 2: Extend `tests/test_hambands.c`**

Two edits. First, make the host build compile the segment section — find:
```c
#define HAM_BANDS_HOST_TEST
#include "../vna_modules/vna_hambands.c"
```
Replace with:
```c
#define HAM_BANDS_HOST_TEST
#define __USE_HAM_SUBBANDS__
#include "../vna_modules/vna_hambands.c"
```

Second, add segment checks in `main()` — find:
```c
  printf("table data: %zu bytes in %d regions\n", total_bytes, HAM_REGION_COUNT);
```
Insert directly before:
```c
  // --- Sub-band segment checks (__USE_HAM_SUBBANDS__) ---
  uint16_t seg_count;
  CHECK(ham_segments_get(0, &seg_count) == NULL, "segments region 0 must return NULL");
  CHECK(ham_segments_get(HAM_REGION_COUNT + 1, &seg_count) == NULL,
        "segments region %d must return NULL", HAM_REGION_COUNT + 1);
  // Country regions share their parent IARU plan's table
  uint16_t c1, c2;
  CHECK(ham_segments_get(4, &c1) == ham_segments_get(2, &c2), "USA must map to R2 plan");
  CHECK(ham_segments_get(5, &c1) == ham_segments_get(2, &c2), "Canada must map to R2 plan");
  CHECK(ham_segments_get(6, &c1) == ham_segments_get(1, &c2), "UK must map to R1 plan");
  CHECK(ham_segments_get(7, &c1) == ham_segments_get(1, &c2), "Germany must map to R1 plan");
  CHECK(ham_segments_get(8, &c1) == ham_segments_get(3, &c2), "Japan must map to R3 plan");
  CHECK(ham_segments_get(9, &c1) == ham_segments_get(3, &c2), "Australia must map to R3 plan");

  size_t seg_bytes = 0;
  for (uint8_t plan = 1; plan <= 3; plan++) {         // plans == regions 1..3
    const ham_segment_t *segs = ham_segments_get(plan, &seg_count);
    uint16_t band_count;
    const ham_band_t *bands = ham_bands_get(plan, &band_count);
    CHECK(segs != NULL && seg_count > 0, "plan %u: empty segment table", plan);
    if (segs == NULL) continue;
    seg_bytes += seg_count * sizeof(ham_segment_t);
    for (uint16_t i = 0; i < seg_count; i++) {
      CHECK(segs[i].start < segs[i].end,
            "plan %u seg %u: start %u >= end %u", plan, i, segs[i].start, segs[i].end);
      CHECK(segs[i].type <= HAM_SEG_PHONE,
            "plan %u seg %u: bad type %u", plan, i, segs[i].type);
      CHECK(segs[i].start >= 135700 && segs[i].end <= 29700000,
            "plan %u seg %u: outside HF range (%u-%u)", plan, i, segs[i].start, segs[i].end);
      if (i > 0)
        CHECK(segs[i].start >= segs[i - 1].end,
              "plan %u seg %u: not sorted/non-overlapping (%u < %u)",
              plan, i, segs[i].start, segs[i - 1].end);
      // Every segment must lie inside one band of the plan's edge table
      int inside = 0;
      for (uint16_t bnd = 0; bnd < band_count; bnd++)
        if (segs[i].start >= bands[bnd].start && segs[i].end <= bands[bnd].end) { inside = 1; break; }
      CHECK(inside, "plan %u seg %u (%u-%u): not inside any band of the plan's edge table",
            plan, i, segs[i].start, segs[i].end);
    }
  }
  printf("segment data: %zu bytes in 3 plans\n", seg_bytes);
```
(Note: adjacent segments share boundary frequencies — CW ends where DIGI starts — so the sort check for segments uses `>=` where the band-edge check uses `>`.)

- [ ] **Step 3: Run the test**

Run: `gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`
Expected: exit 0, `all checks passed`, segment data ≈ 1,150–1,200 bytes (97 entries × 12 B). The "inside any band" check will catch mismatches between segment values and the edge tables (e.g., a segment reaching past a band edge) — fix the segment entry, not the edge table.

- [ ] **Step 4: Cross-check segment values against the IARU band plans**

Spot-check via web search (IARU R1 HF band plan, IARU R2 band plan, IARU R3 band plan): the R1 phone starts (1843/3600/7050/14101/18111/21151/24931/28225 kHz), R2's 160m digi slice at 1800–1810 and 10m phone start at 28300, and R3's 40m phone start at 7035. If offline: the structural test in Step 3 plus the WARC-band symmetry (identical 30/17/15/12m segments in all three plans) is the fallback; note it in the commit message. Fix any entry that disagrees.

- [ ] **Step 5: Commit**

```bash
git add vna_modules/vna_hambands.c tests/test_hambands.c
git commit -m "Add IARU R1/R2/R3 HF sub-band segment tables with region-to-plan mapping

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: F303 guard, firmware types, and segment rendering

**Files:**
- Modify: `nanovna.h` (guard define after `__USE_HAM_BAND_INDICATOR__` near line 60; types/prototype inside the existing `#ifdef __USE_HAM_BAND_INDICATOR__` block near line 1405)
- Modify: `plot.c` (segment colors above `cell_draw_ham_bands` near line 1373; overlay loop inside it)

**Interfaces:**
- Consumes: `ham_segments_get(uint8_t, uint16_t*)`, `HAM_SEG_CW`/`HAM_SEG_DIGI`/`HAM_SEG_PHONE`, `ham_segment_t` (Task 1); existing `cell_draw_ham_bands()` locals `bands`, `count`, `fstart`, `fstop`, `fspan`, `bs`, `be`, `y_top`, `y_bottom`, `w`, `x0`; `RGB565()` and `pixel_t` from `nanovna.h`.
- Produces: working segment coloring on F303 builds; F072 binary unchanged.

- [ ] **Step 1: Add the guard in `nanovna.h`**

Find (near line 59):
```c
// Add amateur radio band indicator on rectangular grid bottom (region setting in config._ham_region)
#define __USE_HAM_BAND_INDICATOR__
```
Insert directly after:
```c
// Add CW/digi/phone sub-band coloring to the band indicator (F303 only: F072 flash is full)
#if defined(NANOVNA_F303) && defined(__USE_HAM_BAND_INDICATOR__)
#define __USE_HAM_SUBBANDS__
#endif
```

- [ ] **Step 2: Add firmware-visible types and prototype in `nanovna.h`**

Find (near line 1405):
```c
#define HAM_REGION_COUNT 9
const char *ham_region_name(uint8_t region);
const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count);
#endif
```
Replace with:
```c
#define HAM_REGION_COUNT 9
const char *ham_region_name(uint8_t region);
const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count);
#ifdef __USE_HAM_SUBBANDS__
enum {HAM_SEG_CW = 0, HAM_SEG_DIGI, HAM_SEG_PHONE};
typedef struct {
  freq_t  start;
  freq_t  end;
  uint8_t type;
} ham_segment_t;
const ham_segment_t *ham_segments_get(uint8_t region, uint16_t *count);
#endif
#endif
```

- [ ] **Step 3: Add segment colors in `plot.c`**

Find (near line 1370):
```c
#ifdef __USE_HAM_BAND_INDICATOR__
//**************************************************************************************
//           Amateur radio band indicator (2px bar on rectangular grid bottom)
//**************************************************************************************
```
Insert directly after:
```c
#ifdef __USE_HAM_SUBBANDS__
// Fixed compile-time colors (NOT config palette: old saved configs hold zeros
// in spare palette slots and would render the segments black)
static const pixel_t ham_seg_colors[] = {
  [HAM_SEG_CW]    = RGB565(255, 96,   0),  // orange
  [HAM_SEG_DIGI]  = RGB565(  0, 160, 255), // light blue
  [HAM_SEG_PHONE] = RGB565(  0, 200,   0), // green
};
#endif
```

- [ ] **Step 4: Overlay segments in `cell_draw_ham_bands`**

Two edits in `plot.c`. First, fetch the segment table once — find:
```c
  freq_t fspan = fstop - fstart;
  pixel_t color = GET_PALETTE_COLOR(LCD_LINK_COLOR);
```
Replace with:
```c
  freq_t fspan = fstop - fstart;
  pixel_t color = GET_PALETTE_COLOR(LCD_LINK_COLOR);
#ifdef __USE_HAM_SUBBANDS__
  uint16_t seg_count;
  const ham_segment_t *segs = ham_segments_get(config._ham_region, &seg_count);
#endif
```
Second, overlay after the base bar — find:
```c
    for (int y = y_top; y <= y_bottom; y++)
      for (int x = xs; x <= xe; x++)                     // xs==xe still draws 1px minimum
        cell_buffer[y * CELLWIDTH + x] = color;
  }
}
```
Replace with:
```c
    for (int y = y_top; y <= y_bottom; y++)
      for (int x = xs; x <= xe; x++)                     // xs==xe still draws 1px minimum
        cell_buffer[y * CELLWIDTH + x] = color;
#ifdef __USE_HAM_SUBBANDS__
    // Overlay CW/digi/phone segments, clipped to [bs, be] (band ∩ sweep, so
    // plan segments never paint outside this region's own band edges)
    for (uint16_t s = 0; s < seg_count; s++) {
      freq_t ss = segs[s].start, se = segs[s].end;
      if (se < bs) continue;
      if (ss > be) break;                                // sorted: rest is past this band
      if (ss < bs) ss = bs;
      if (se > be) se = be;
      int sxs = (int)(((uint64_t)(ss - fstart) * WIDTH) / fspan) + CELLOFFSETX - x0;
      int sxe = (int)(((uint64_t)(se - fstart) * WIDTH) / fspan) + CELLOFFSETX - x0;
      if (sxs < 0) sxs = 0;
      if (sxe > w - 1) sxe = w - 1;
      if (sxs > sxe) continue;
      for (int y = y_top; y <= y_bottom; y++)
        for (int x = sxs; x <= sxe; x++)
          cell_buffer[y * CELLWIDTH + x] = ham_seg_colors[segs[s].type];
    }
#endif
  }
}
```
(`segs` is non-NULL whenever `bands` is non-NULL — both key on the same `config._ham_region` — and the early `return` on `bands == NULL` runs before `segs` is used. `bs`/`be` are the band range already clipped to the sweep, so segment clipping to `[bs, be]` implements the spec's "segment ∩ band ∩ sweep" rule.)

- [ ] **Step 5: Build F303 and record size**

Run: `./1_build.sh F303`
Expected: clean build (only the pre-existing plot.c sign-compare warning). `build/H4.bin` grows ~1.5–2 KB over 91,632 B — anywhere under ~94 KB is fine (the F303 link region has ~50 KB free).

- [ ] **Step 6: Build F072 and verify it is unchanged**

Run: `./1_build.sh F072`
Expected: **exactly 95,416 bytes** for `build/H.bin` and no new warnings — `__USE_HAM_SUBBANDS__` must not be defined for F072, so no segment code or data can appear. If the size differs, the guard leaked (check Step 1's `#if defined(NANOVNA_F303)` condition); stop and fix before committing.

- [ ] **Step 7: Re-run the host test**

Run: `gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`
Expected: PASS (regression: firmware header changes must not break the host build, which takes its types from the `HAM_BANDS_HOST_TEST` guard, not `nanovna.h`).

- [ ] **Step 8: Commit**

```bash
git add nanovna.h plot.c
git commit -m "Render CW/digi/phone sub-band coloring on H4 (F303) band indicator

Segments follow the 3 IARU regional plans; country regions map to their
parent plan clipped to national band edges. F072 build unchanged
(__USE_HAM_SUBBANDS__ is F303-only).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 9: On-device check (needs the user / H4 hardware)**

If an H4 is available: `./2_prog.sh F303` in DFU mode, select SCALE→HAM BANDS→IARU R1, sweep 3–8 MHz: the 80 m bar should show orange (3.50–3.57), light blue (3.57–3.60), green (3.60–3.80), and 60 m a thin mark near 5.35 MHz. On a NanoVNA-H, the same region must show the plain gold bar exactly as before. Report result or that this awaits hardware — does not block completion.
