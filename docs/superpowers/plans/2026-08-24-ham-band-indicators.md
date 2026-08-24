# Ham Band Indicators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw a 2-pixel amateur-radio band indicator bar along the bottom of the rectangular grid, with a user-selectable region (OFF + 9 region/country band tables) persisted in `config_t`.

**Architecture:** Band tables and their lookup API live in a new include-fragment `vna_modules/vna_hambands.c` (included from `plot.c`, the same pattern as `vna_modules/vna_render.c`). Rendering is a new `cell_draw_ham_bands()` called from `draw_cell()` in `plot.c`. The region setting is one byte carved from `config_t`'s existing `_reserved[3]` tail (old saved configs have it zeroed → loads as OFF, no `CONFIG_MAGIC` bump). UI is a Scale-menu submenu using the existing group-check pattern. A host-side `gcc` test validates the tables.

**Tech Stack:** C (GCC ARM 8-2018-q4-major cross target, host `gcc` for the table test), ChibiOS firmware, no new build-system entries (include-fragment pattern).

**Spec:** `docs/superpowers/specs/2026-08-24-ham-bands-design.md`

## Global Constraints

- Feature guard macro: `__USE_HAM_BAND_INDICATOR__`, enabled for **both** targets.
- `config_t` size and all existing member offsets must not change (only `uint8_t _reserved[3]` → `uint8_t _ham_region; uint8_t _reserved[2];`). No `CONFIG_MAGIC` change.
- Do **not** add a `VNA_MODE_*` enum value (PR #103's defect: inserting mid-enum shifts persisted `config._vna_mode` bits).
- Both targets must build cleanly: `./1_build.sh F072` and `./1_build.sh F303` (run `make clean` between targets — the scripts do this). Toolchain is already on PATH at `/usr/local/gcc-arm-none-eabi-8-2018-q4-major/bin`.
- F072 flash budget: baseline is 93,364 B of 98,304 B. If the final F072 build exceeds the 98,304 B link region (link error), fall back to F303-only: define `__USE_HAM_BAND_INDICATOR__` under `#if defined(NANOVNA_F303)` — but report this to the user first; do not silently restrict.
- Every task ends with a commit. Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Do not push; the `origin` remote is upstream (DiSlord's repo) and is not writable.

---

### Task 1: Band tables module + host validation test

**Files:**
- Create: `vna_modules/vna_hambands.c`
- Test: `tests/test_hambands.c`

**Interfaces:**
- Consumes: nothing (self-contained fragment; the includer provides `freq_t` — the host test typedefs it).
- Produces (used by Tasks 3–4):
  - `#define HAM_REGION_COUNT 9`
  - `const char *ham_region_name(uint8_t region);` — `"OFF"` for 0 or out-of-range, else the region's short name.
  - `const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count);` — `NULL` for 0 or out-of-range, else a pointer to a sorted, non-overlapping array of `ham_band_t {freq_t start; freq_t end;}` and its length in `*count`.
  - Region numbering (persisted values, keep stable): 1=IARU R1, 2=IARU R2, 3=IARU R3, 4=USA, 5=Canada, 6=UK, 7=Germany, 8=Japan, 9=Australia.

- [ ] **Step 1: Create `vna_modules/vna_hambands.c`**

Exact content (the band values below were compiled from the IARU R1/R2/R3 band plans, FCC Part 97.301, Ofcom UK amateur licence schedule, BNetzA AFuV, Japan MIC/JARL band plan, and the ACMA amateur LCD; the test in Step 2 checks structure, and Step 3 is a source cross-check):

```c
/*
 * Amateur radio band edge tables with region setting.
 *
 * Include-fragment (like other vna_modules): #include'd from plot.c in the
 * firmware build, or from tests/test_hambands.c on the host.
 * The includer provides freq_t (uint32_t Hz); firmware gets ham_band_t and
 * the API prototypes from nanovna.h, the host test defines HAM_BANDS_HOST_TEST
 * to get the typedef here instead.
 *
 * Region numbering is persisted in config._ham_region — never renumber:
 *   0=OFF 1=IARU R1 2=IARU R2 3=IARU R3 4=USA 5=Canada 6=UK 7=Germany
 *   8=Japan 9=Australia
 *
 * Tables list national/regional band EDGES only (no sub-band segments, see
 * docs/superpowers/specs/2026-08-24-ham-bands-design.md). Entries are sorted
 * ascending and non-overlapping; the 60 m entries for R2/USA/Canada and UK
 * are channelized/bandlet allocations shown as their envelope.
 */
#ifdef HAM_BANDS_HOST_TEST
typedef struct {
  freq_t start;
  freq_t end;
} ham_band_t;
#define HAM_REGION_COUNT 9
#endif

// IARU Region 1 (Europe, Africa, Middle East, northern Asia) band plan
static const ham_band_t ham_bands_iaru_r1[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1810000,    2000000},    // 160m
  {3500000,    3800000},    // 80m
  {5351500,    5366500},    // 60m (WRC-15)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   52000000},   // 6m
  {70000000,   70500000},   // 4m (not all R1 countries)
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

// IARU Region 2 (Americas) band plan
static const ham_band_t ham_bands_iaru_r2[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    4000000},    // 80m
  {5330500,    5406400},    // 60m (channelized, envelope)
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {222000000,  225000000},  // 1.25m
  {420000000,  450000000},  // 70cm
  {902000000,  928000000},  // 33cm
  {1240000000, 1300000000}, // 23cm
};

// IARU Region 3 (Asia-Pacific) band plan
static const ham_band_t ham_bands_iaru_r3[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    3900000},    // 80m
  {5351500,    5366500},    // 60m (WRC-15)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

// USA, FCC Part 97.301 (all license classes combined)
static const ham_band_t ham_bands_usa[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    4000000},    // 80m
  {5330500,    5406400},    // 60m (5 channels, envelope)
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {222000000,  225000000},  // 1.25m
  {420000000,  450000000},  // 70cm
  {902000000,  928000000},  // 33cm
  {1240000000, 1300000000}, // 23cm
};

// Canada, ISED RBR-4
static const ham_band_t ham_bands_canada[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    4000000},    // 80m
  {5330500,    5406400},    // 60m (5 channels, envelope)
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {222000000,  225000000},  // 1.25m
  {430000000,  450000000},  // 70cm
  {902000000,  928000000},  // 33cm
  {1240000000, 1300000000}, // 23cm
};

// UK, Ofcom amateur licence (Full)
static const ham_band_t ham_bands_uk[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1810000,    2000000},    // 160m
  {3500000,    3800000},    // 80m
  {5258500,    5406500},    // 60m (11 bandlets, envelope)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   52000000},   // 6m
  {70000000,   70500000},   // 4m
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1325000000}, // 23cm (UK extends to 1325 MHz)
};

// Germany, BNetzA AFuV (class A)
static const ham_band_t ham_bands_germany[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1810000,    2000000},    // 160m
  {3500000,    3800000},    // 80m
  {5351500,    5366500},    // 60m (WRC-15)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   52000000},   // 6m
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

// Japan, MIC/JARL band plan (split 160m/80m allocations)
static const ham_band_t ham_bands_japan[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    1810000},    // 160m lower
  {1825000,    1875000},    // 160m upper
  {3500000,    3580000},    // 80m segment 1
  {3662000,    3687000},    // 80m segment 2
  {3702000,    3716000},    // 80m segment 3
  {3745000,    3770000},    // 80m segment 4
  {3791000,    3805000},    // 80m segment 5
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1260000000, 1300000000}, // 23cm (Japan: 1260-1300 MHz)
};

// Australia, ACMA amateur LCD (Advanced)
static const ham_band_t ham_bands_australia[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    1875000},    // 160m
  {3500000,    3700000},    // 80m lower
  {3776000,    3800000},    // 80m upper
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {430000000,  450000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

typedef struct {
  const char *name;
  const ham_band_t *bands;
  uint16_t count;
} ham_region_t;

#define HAM_BANDS_TABLE(name, tbl) {name, tbl, sizeof(tbl)/sizeof(tbl[0])}
static const ham_region_t ham_regions[HAM_REGION_COUNT] = {
  HAM_BANDS_TABLE("IARU R1",   ham_bands_iaru_r1),
  HAM_BANDS_TABLE("IARU R2",   ham_bands_iaru_r2),
  HAM_BANDS_TABLE("IARU R3",   ham_bands_iaru_r3),
  HAM_BANDS_TABLE("USA",       ham_bands_usa),
  HAM_BANDS_TABLE("CANADA",    ham_bands_canada),
  HAM_BANDS_TABLE("UK",        ham_bands_uk),
  HAM_BANDS_TABLE("GERMANY",   ham_bands_germany),
  HAM_BANDS_TABLE("JAPAN",     ham_bands_japan),
  HAM_BANDS_TABLE("AUSTRALIA", ham_bands_australia),
};

const char *ham_region_name(uint8_t region) {
  if (region == 0 || region > HAM_REGION_COUNT) return "OFF";
  return ham_regions[region - 1].name;
}

const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count) {
  if (region == 0 || region > HAM_REGION_COUNT) return NULL;
  *count = ham_regions[region - 1].count;
  return ham_regions[region - 1].bands;
}
```

- [ ] **Step 2: Create the failing/host test `tests/test_hambands.c`**

```c
/*
 * Host-side validation for vna_modules/vna_hambands.c band tables.
 * Build and run (no cross-toolchain needed):
 *   gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t freq_t;
#define FREQUENCY_MAX 2700000000U
#define HAM_BANDS_HOST_TEST
#include "../vna_modules/vna_hambands.c"

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; \
  printf("FAIL: " __VA_ARGS__); printf("\n"); } } while (0)

int main(void) {
  uint16_t count;

  // Region 0 and out-of-range are OFF
  CHECK(ham_bands_get(0, &count) == NULL, "region 0 must return NULL");
  CHECK(ham_bands_get(HAM_REGION_COUNT + 1, &count) == NULL,
        "region %d must return NULL", HAM_REGION_COUNT + 1);
  CHECK(strcmp(ham_region_name(0), "OFF") == 0, "region 0 name must be OFF");
  CHECK(strcmp(ham_region_name(HAM_REGION_COUNT + 1), "OFF") == 0,
        "out-of-range region name must be OFF");

  size_t total_bytes = 0;
  for (uint8_t r = 1; r <= HAM_REGION_COUNT; r++) {
    const char *name = ham_region_name(r);
    const ham_band_t *bands = ham_bands_get(r, &count);
    CHECK(name != NULL && name[0] != '\0', "region %u: empty name", r);
    CHECK(strlen(name) <= 10, "region %u (%s): name too long for menu button", r, name);
    CHECK(bands != NULL, "region %u (%s): NULL table", r, name);
    CHECK(count > 0, "region %u (%s): empty table", r, name);
    if (bands == NULL) continue;
    total_bytes += count * sizeof(ham_band_t);
    for (uint16_t i = 0; i < count; i++) {
      CHECK(bands[i].start < bands[i].end,
            "region %u (%s) entry %u: start %u >= end %u",
            r, name, i, bands[i].start, bands[i].end);
      CHECK(bands[i].start >= 135700,
            "region %u (%s) entry %u: start %u below 2200m band",
            r, name, i, bands[i].start);
      CHECK(bands[i].end <= FREQUENCY_MAX,
            "region %u (%s) entry %u: end %u above FREQUENCY_MAX",
            r, name, i, bands[i].end);
      if (i > 0)
        CHECK(bands[i].start > bands[i - 1].end,
              "region %u (%s) entry %u: not sorted/non-overlapping (%u <= %u)",
              r, name, i, bands[i].start, bands[i - 1].end);
    }
  }
  printf("table data: %zu bytes in %d regions\n", total_bytes, HAM_REGION_COUNT);
  if (failures) { printf("%d FAILURES\n", failures); return 1; }
  printf("all checks passed\n");
  return 0;
}
```

- [ ] **Step 3: Run the test**

Run: `gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`
Expected: exit 0, `all checks passed`, and a printed table-size total in the 1200–1300 byte range. If any CHECK fails, fix the offending table entry (the tables above are already sorted; a failure means a typo introduced while transcribing).

- [ ] **Step 4: Cross-check table values against sources**

Spot-check each region's entries against its cited source (IARU R1/R2/R3 band plans, FCC 97.301, Ofcom licence schedule, BNetzA AFuV, JARL band plan, ACMA LCD) using web search if available; if offline, verify at least internal consistency (WARC bands 30/17/12 m identical everywhere; 2m is 144–146 in R1 and 144–148 in R2) and note in the commit message that values follow the spec's cited sources. Fix any entry that disagrees with its source.

- [ ] **Step 5: Commit**

```bash
git add vna_modules/vna_hambands.c tests/test_hambands.c
git commit -m "Add ham band region tables module with host validation test

Refs DiSlord/NanoVNA-D#103, DiSlord/NanoVNA-D#104

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Wire the module into the firmware (config field, defines, prototypes)

**Files:**
- Modify: `nanovna.h` (feature define near line 58; `config_t` near line 1011; API prototypes near line 1395)
- Modify: `main.c` (config default initializer near line 866)
- Modify: `plot.c` (include the fragment near line 26)

**Interfaces:**
- Consumes: `vna_modules/vna_hambands.c` from Task 1.
- Produces (used by Tasks 3–4): `config._ham_region` (uint8_t, 0=OFF..9), `__USE_HAM_BAND_INDICATOR__`, and firmware-visible `ham_band_t`, `HAM_REGION_COUNT`, `ham_region_name()`, `ham_bands_get()` via `nanovna.h`.

- [ ] **Step 1: Add the feature define in `nanovna.h`**

Find (near line 57):
```c
// Add show y grid line values option
#define __USE_GRID_VALUES__
```
Insert directly after:
```c
// Add amateur radio band indicator on rectangular grid bottom (region setting in config._ham_region)
#define __USE_HAM_BAND_INDICATOR__
```

- [ ] **Step 2: Rename one reserved config byte in `nanovna.h`**

Find (near line 1010, in `config_t`):
```c
  uint8_t  _band_mode;
  uint8_t  _reserved[3];
  uint32_t checksum;
```
Replace with:
```c
  uint8_t  _band_mode;
  uint8_t  _ham_region;  // 0 = OFF, 1..HAM_REGION_COUNT (was _reserved byte, zero in old configs)
  uint8_t  _reserved[2];
  uint32_t checksum;
```
(Size and offsets unchanged: one named byte replaces the first reserved byte. Old saved configs load with `_ham_region == 0` → OFF.)

- [ ] **Step 3: Add the API declarations in `nanovna.h`**

Find (near line 1395):
```c
int config_save(void);
int config_recall(void);
```
Insert directly before:
```c
#ifdef __USE_HAM_BAND_INDICATOR__
typedef struct {
  freq_t start;
  freq_t end;
} ham_band_t;
#define HAM_REGION_COUNT 9
const char *ham_region_name(uint8_t region);
const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count);
#endif
```

- [ ] **Step 4: Add the explicit default in `main.c`**

Find (near line 881, in `config_t config = {`):
```c
  ._band_mode = 0,
};
```
Replace with:
```c
  ._band_mode = 0,
  ._ham_region = 0, // ham band indicator OFF
};
```

- [ ] **Step 5: Include the fragment in `plot.c`**

Find (near line 26):
```c
#include "chprintf.h"
#include "nanovna.h"
```
Insert directly after:
```c
#ifdef __USE_HAM_BAND_INDICATOR__
#include "vna_modules/vna_hambands.c"
#endif
```

- [ ] **Step 6: Build both targets**

Run: `./1_build.sh F072` then `./1_build.sh F303`
Expected: both link cleanly. The linker may warn about nothing; unused-function warnings must not appear (the API functions are non-static, so they are kept even before Tasks 3–4 use them). Record the F072 `build/H.bin` size — expect roughly baseline + ~1.4 KB (table data now linked).

- [ ] **Step 7: Re-run the host test (regression)**

Run: `gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`
Expected: PASS (the `HAM_BANDS_HOST_TEST` guard keeps the fragment host-compilable).

- [ ] **Step 8: Commit**

```bash
git add nanovna.h main.c plot.c
git commit -m "Wire ham band tables into firmware: config._ham_region, defines, prototypes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Render the band bar in draw_cell

**Files:**
- Modify: `plot.c` (new `cell_draw_ham_bands()` before `draw_cell` near line 1368; call site inside `draw_cell` after the grid block near line 1454)

**Interfaces:**
- Consumes: `config._ham_region`, `ham_bands_get()` (Task 2); existing plot.c statics: `cell_buffer`, `CELLWIDTH`, `WIDTH`, `HEIGHT`, `CELLOFFSETX`, `GET_PALETTE_COLOR`, `LCD_LINK_COLOR`, `props_mode`, `DOMAIN_MODE`, `DOMAIN_FREQ`, `get_sweep_frequency()`, `ST_START`/`ST_STOP`.
- Produces: `static void cell_draw_ham_bands(int x0, int y0, int w, int h)` — plot.c-internal, drawn only when a rectangular-grid trace is enabled.

- [ ] **Step 1: Add the drawing function in `plot.c`**

Insert directly before `static void draw_cell(int x0, int y0) {` (line 1368):

```c
#ifdef __USE_HAM_BAND_INDICATOR__
//**************************************************************************************
//           Amateur radio band indicator (2px bar on rectangular grid bottom)
//**************************************************************************************
static void cell_draw_ham_bands(int x0, int y0, int w, int h) {
  uint16_t count;
  const ham_band_t *bands = ham_bands_get(config._ham_region, &count);
  if (bands == NULL) return;                             // OFF or invalid region
  if ((props_mode & DOMAIN_MODE) != DOMAIN_FREQ) return; // frequency domain only
  // Bar occupies the two bottom grid rows y = HEIGHT-1 and HEIGHT
  int y_top = HEIGHT - 1 - y0, y_bottom = HEIGHT - y0;
  if (y_bottom < 0 || y_top >= h) return;                // cell doesn't contain the bar
  if (y_top < 0) y_top = 0;
  if (y_bottom > h - 1) y_bottom = h - 1;
  freq_t fstart = get_sweep_frequency(ST_START);
  freq_t fstop  = get_sweep_frequency(ST_STOP);
  if (fstart >= fstop) return;                           // zero span / CW
  freq_t fspan = fstop - fstart;
  pixel_t color = GET_PALETTE_COLOR(LCD_LINK_COLOR);
  for (uint16_t i = 0; i < count; i++) {
    freq_t bs = bands[i].start, be = bands[i].end;
    if (be < fstart) continue;
    if (bs > fstop) break;                               // table sorted: rest is off-screen
    if (bs < fstart) bs = fstart;
    if (be > fstop)  be = fstop;
    // Same freq->x mapping as the grid: 0..WIDTH over fstart..fstop, +CELLOFFSETX
    int xs = (int)(((uint64_t)(bs - fstart) * WIDTH) / fspan) + CELLOFFSETX - x0;
    int xe = (int)(((uint64_t)(be - fstart) * WIDTH) / fspan) + CELLOFFSETX - x0;
    if (xs < 0) xs = 0;
    if (xe > w - 1) xe = w - 1;
    if (xs > xe) continue;                               // band outside this cell
    for (int y = y_top; y <= y_bottom; y++)
      for (int x = xs; x <= xe; x++)                     // xs==xe still draws 1px minimum
        cell_buffer[y * CELLWIDTH + x] = color;
  }
}
#endif
```

- [ ] **Step 2: Call it from `draw_cell`**

Find (near line 1450, end of the grid-drawing block):
```c
  // Polar greed
  else if (trace_type & (1 << TRC_POLAR))
    cell_polar_grid(x0, y0, w, h, c);
#endif
```
Insert directly after (before the `// Draw traces` loop, so traces and markers render on top of the bar):
```c
#ifdef __USE_HAM_BAND_INDICATOR__
  // Amateur radio band indicator on rectangular grid bottom
  if (trace_type & RECTANGULAR_GRID_MASK)
    cell_draw_ham_bands(x0, y0, w, h);
#endif
```

- [ ] **Step 3: Build both targets**

Run: `./1_build.sh F072` then `./1_build.sh F303`
Expected: clean build, no new warnings (the only pre-existing warning is the upstream sign-compare in `cell_blit_bitmap`, plot.c:277). Note: until Task 4 there is no UI to enable the feature; rendering is verifiable via the shell `config` mechanism only after flashing, so on-device visual check is deferred to Task 4 Step 6.

- [ ] **Step 4: Commit**

```bash
git add plot.c
git commit -m "Draw ham band indicator bar on rectangular grid bottom

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Scale-menu region submenu + final size verification

**Files:**
- Modify: `ui.c` (callbacks after `menu_vna_mode_acb` near line 1093; submenu array + Scale-menu entry near line 2161)

**Interfaces:**
- Consumes: `config._ham_region`, `ham_region_name()`, `HAM_REGION_COUNT`; ui.c patterns: `UI_FUNCTION_ADV_CALLBACK`, `menu_push_submenu`, `BUTTON_ICON_GROUP`/`BUTTON_ICON_GROUP_CHECKED`, `request_to_redraw`, `REDRAW_BACKUP`/`REDRAW_AREA`, `MT_ADV_CALLBACK`, `MT_NEXT`, `menu_back`, `R_LINK_COLOR`.
- Produces: `menu_ham_bands[]` submenu reachable from DISPLAY→SCALE, showing the active region with a group-check icon; selecting an entry sets `config._ham_region` and redraws the plot area.

- [ ] **Step 1: Add the menu callbacks in `ui.c`**

Find (near line 1093, the closing brace of `menu_vna_mode_acb`):
```c
  apply_VNA_mode(data, VNA_MODE_TOGGLE);
}
```
Insert directly after:
```c
#ifdef __USE_HAM_BAND_INDICATOR__
const menuitem_t menu_ham_bands[];
static UI_FUNCTION_ADV_CALLBACK(menu_ham_bands_sel_acb) {
  (void)data;
  if (b) {
    b->p1.text = ham_region_name(config._ham_region);
    return;
  }
  menu_push_submenu(menu_ham_bands);
}

static UI_FUNCTION_ADV_CALLBACK(menu_ham_bands_acb) {
  if (b) {
    b->icon = config._ham_region == data ? BUTTON_ICON_GROUP_CHECKED : BUTTON_ICON_GROUP;
    b->p1.text = ham_region_name(data);
    return;
  }
  config._ham_region = data;
  request_to_redraw(REDRAW_BACKUP | REDRAW_AREA);
}
#endif
```

- [ ] **Step 2: Add the submenu array and Scale-menu entry**

Find (near line 2170, in `menu_scale[]`):
```c
#ifdef __USE_GRID_VALUES__
  { MT_ADV_CALLBACK, VNA_MODE_SHOW_GRID, "SHOW GRID\nVALUES", menu_vna_mode_acb },
  { MT_ADV_CALLBACK, VNA_MODE_DOT_GRID , "DOT GRID",          menu_vna_mode_acb },
#endif
  { MT_NEXT, 0, NULL, menu_back } // next-> menu_back
};
```
Replace with:
```c
#ifdef __USE_GRID_VALUES__
  { MT_ADV_CALLBACK, VNA_MODE_SHOW_GRID, "SHOW GRID\nVALUES", menu_vna_mode_acb },
  { MT_ADV_CALLBACK, VNA_MODE_DOT_GRID , "DOT GRID",          menu_vna_mode_acb },
#endif
#ifdef __USE_HAM_BAND_INDICATOR__
  { MT_ADV_CALLBACK, 0, "HAM BANDS\n " R_LINK_COLOR "%s", menu_ham_bands_sel_acb },
#endif
  { MT_NEXT, 0, NULL, menu_back } // next-> menu_back
};

#ifdef __USE_HAM_BAND_INDICATOR__
const menuitem_t menu_ham_bands[] = {
  { MT_ADV_CALLBACK, 0, "%s", menu_ham_bands_acb }, // OFF
  { MT_ADV_CALLBACK, 1, "%s", menu_ham_bands_acb }, // IARU R1
  { MT_ADV_CALLBACK, 2, "%s", menu_ham_bands_acb }, // IARU R2
  { MT_ADV_CALLBACK, 3, "%s", menu_ham_bands_acb }, // IARU R3
  { MT_ADV_CALLBACK, 4, "%s", menu_ham_bands_acb }, // USA
  { MT_ADV_CALLBACK, 5, "%s", menu_ham_bands_acb }, // CANADA
  { MT_ADV_CALLBACK, 6, "%s", menu_ham_bands_acb }, // UK
  { MT_ADV_CALLBACK, 7, "%s", menu_ham_bands_acb }, // GERMANY
  { MT_ADV_CALLBACK, 8, "%s", menu_ham_bands_acb }, // JAPAN
  { MT_ADV_CALLBACK, 9, "%s", menu_ham_bands_acb }, // AUSTRALIA
  { MT_NEXT, 0, NULL, menu_back } // next-> menu_back
};
#endif
```
(11 items including back ≤ `MENU_BUTTON_MAX` 16. `menu_scale` grows to 12 items including back — still ≤ 16. The `"%s"` label consumes `b->p1.text`, same as `menu_transform`'s `"WINDOW\n " R_LINK_COLOR "%s"` entry.)

- [ ] **Step 3: Build both targets and record final sizes**

Run: `./1_build.sh F072` then `./1_build.sh F303`
Expected: clean builds. Compare F072 `arm-none-eabi-size build/H.elf` (or the `make` size output) flash usage against the 93,364 B baseline; total must stay ≤ 98,304 B. Expected growth ≈ 1.8–2.2 KB. If it does NOT fit, stop and report per Global Constraints (F303-only fallback needs user sign-off).

- [ ] **Step 4: Re-run the host table test**

Run: `gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ui.c
git commit -m "Add HAM BANDS region submenu to Scale menu

Region setting (OFF + IARU R1/R2/R3, USA, Canada, UK, Germany, Japan,
Australia) persists in config._ham_region via SAVE CONFIG; old saved
configs load as OFF. Completes port of DiSlord/NanoVNA-D#103 with
region support (feature request DiSlord/NanoVNA-D#104).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: On-device check (needs the user / hardware)**

If a device is connected and the user wants it: `./2_prog.sh F072` (device in DFU mode), then DISPLAY→SCALE→HAM BANDS→pick a region, sweep 1–30 MHz, confirm gold (`LCD_LINK_COLOR`) 2 px marks at the HF band edges; CONFIG→SAVE to persist. Report to the user either the result or that this step awaits hardware — it does not block plan completion.
