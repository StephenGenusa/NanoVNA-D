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
#define __USE_HAM_SUBBANDS__
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

  printf("table data: %zu bytes in %d regions\n", total_bytes, HAM_REGION_COUNT);
  if (failures) { printf("%d FAILURES\n", failures); return 1; }
  printf("all checks passed\n");
  return 0;
}
