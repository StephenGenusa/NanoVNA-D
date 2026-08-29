/* Host driver for vna_modules/vna_workflow_math.c */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#define WORKFLOW_HOST_TEST
#include "vna_modules/vna_workflow_math.c"

static int fails = 0;
#define CHECK(c) do { if (!(c)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
  /* the v1 spec's sign error: f0 7.310 above target 7.100 => element SHORT => ADD */
  float d = tune_delta_len_m(TUNE_ANT_DIPOLE, 7.31e6f, 7.10e6f);
  CHECK(d > 0);                                   /* ADD */
  CHECK(fabsf(d - 0.581f) < 0.02f);               /* 20.1 m * 0.02873 = 0.58 m total */
  CHECK(tune_per_leg(TUNE_ANT_DIPOLE));           /* 29 cm per leg */
  CHECK(tune_delta_len_m(TUNE_ANT_DIPOLE, 7.00e6f, 7.10e6f) < 0);   /* REMOVE */
  CHECK(tune_delta_len_m(TUNE_ANT_UNKNOWN, 7.31e6f, 7.10e6f) == 0);
  CHECK(fabsf(tune_assumed_len_m(TUNE_ANT_DIPOLE, 7.1e6f) - 20.09f) < 0.05f);
  CHECK(fabsf(tune_assumed_len_m(TUNE_ANT_VERTICAL, 7.1e6f) - 10.05f) < 0.05f);
  /* E2 sanity table: full-size kHz/cm on 80/40/20/10 m */
  CHECK(fabsf(tune_fullsize_hz_per_m(3.6e6f)  / 1e5f - 1.8f)  < 0.1f);
  CHECK(fabsf(tune_fullsize_hz_per_m(7.1e6f)  / 1e5f - 7.1f)  < 0.2f);
  CHECK(fabsf(tune_fullsize_hz_per_m(14.2e6f) / 1e5f - 28.0f) < 0.6f);
  CHECK(fabsf(tune_fullsize_hz_per_m(28.4e6f) / 1e5f - 113.f) < 3.f);
  /* measured sensitivity: added 4 cm, f0 fell 27.6 kHz => -6.9 kHz/cm = -6.9e5 Hz/m */
  CHECK(fabsf(tune_sensitivity_hz_per_m(7.310e6f, 7.2824e6f, 0.04f) + 6.9e5f) < 1e4f);
  CHECK(tune_sensitivity_hz_per_m(7.31e6f, 7.28e6f, 0.0f) == 0);
  /* the field-critical sign, pinned directly (final-review.md Minor 1): wire added lowered f0,
   * so k < 0; df = f_swrmin - target = +182400 Hz (f0 still above target) => need > 0 => ADD */
  {
    float k = -690000.0f, df = 182400.0f;
    float need = tune_need_m(df, k);
    CHECK(need > 0);                              /* ADD */
    CHECK(fabsf(need - 0.2643f) < 0.001f);
  }
  {
    /* mirror case: f0 fell below target (df < 0) with the same k => need < 0 => REMOVE */
    float need = tune_need_m(-182400.0f, -690000.0f);
    CHECK(need < 0);
  }
  printf(fails ? "FAILED %d\n" : "OK\n", fails);
  return fails != 0;
}
