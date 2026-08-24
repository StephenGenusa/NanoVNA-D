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
