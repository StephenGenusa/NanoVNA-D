/*
 * Host-side validation for vna_modules/vna_swr_bw.c.
 * Build and run (no cross-toolchain needed):
 *   gcc -Wall -Wextra -Werror -o /tmp/test_swr_bw tests/test_swr_bw.c -lm && /tmp/test_swr_bw
 *
 * Synthetic antenna: series RLC, Z = R + j R Q (f/f0 - f0/f), measured
 * against z0 = 50.  Q must be recovered from the SWR curve for R != 50,
 * for both the 2:1 and 3:1 levels, from a marker anywhere on the slope,
 * and with sample noise present.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>

#define SWR_BW_HOST_TEST
#define vna_sqrtf sqrtf
#include "../vna_modules/vna_swr_bw.c"

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; \
  printf("FAIL: " __VA_ARGS__); printf("\n"); } } while (0)

#define N 401
static float g_swr[N], g_freq[N];
static float get_swr(uint16_t i)  { return g_swr[i]; }
static float get_freq(uint16_t i) { return g_freq[i]; }
static float g_r;
static float get_r(uint16_t i)    { (void)i; return g_r; }

static float swr_of(float r, float x, float z0) {
  float g = sqrtf(((r - z0) * (r - z0) + x * x) / ((r + z0) * (r + z0) + x * x));
  return g >= 0.99f ? 99.0f : (1.0f + g) / (1.0f - g);
}

static void make_sweep(float fa, float fb, float f0, float r, float q, float noise) {
  uint32_t seed = 12345;
  for (int i = 0; i < N; i++) {
    float f = fa + (fb - fa) * i / (N - 1);
    float x = r * q * (f / f0 - f0 / f);
    g_freq[i] = f;
    seed = seed * 1103515245u + 12345u;
    float nz = noise * (((seed >> 8) & 0xFFFF) / 65535.0f - 0.5f);
    g_swr[i] = swr_of(r, x, 50.0f) + nz;
  }
}

int main(void) {
  swr_bw_result_t res;
  const float F0 = 7.1235e6f, FA = 6.9e6f, FB = 7.4e6f;

  // 1. Matched dip: Q recovered, both levels bracketed
  make_sweep(FA, FB, F0, 50.0f, 39.0f, 0.0f);
  g_r = 50.0f; swr_bw_analyse(get_swr, get_freq, get_r, N, -1, 50.0f, &res);
  CHECK(fabsf(res.f0 - F0) < 500.0f, "matched f0 %.0f", res.f0);
  CHECK(res.swr0 < 1.01f, "matched swr0 %.3f", res.swr0);
  CHECK(res.f_lo[0] && res.f_hi[0] && res.f_lo[1] && res.f_hi[1], "matched edges present");
  CHECK(fabsf(res.q - 39.0f) < 0.5f, "matched Q %.2f", res.q);

  // 2. Mismatched dips: Q still exact when R is supplied
  const float rs[] = {35.2f, 70.0f, 25.0f, 100.0f};
  for (unsigned k = 0; k < sizeof(rs) / sizeof(rs[0]); k++) {
    make_sweep(FA, FB, F0, rs[k], 39.0f, 0.0f);
    g_r = rs[k]; swr_bw_analyse(get_swr, get_freq, get_r, N, -1, 50.0f, &res);
    CHECK(fabsf(res.q - 39.0f) < 0.5f, "R=%.1f Q %.2f", rs[k], res.q);
    // Q from the 3:1 level alone must agree with the 2:1 result
    if (res.f_lo[1] && res.f_hi[1]) {
      float q3 = swr_bw_q(res.f0, res.f_hi[1] - res.f_lo[1], 3.0f, rs[k], 50.0f);
      CHECK(fabsf(q3 - 39.0f) < 0.6f, "R=%.1f Q(3:1) %.2f", rs[k], q3);
    }
  }
  // R=100 -> min SWR 2.0: no 2:1 bandwidth, 3:1 still gives Q
  make_sweep(FA, FB, F0, 100.0f, 39.0f, 0.0f);
  g_r = 100.0f; swr_bw_analyse(get_swr, get_freq, get_r, N, -1, 50.0f, &res);
  CHECK(res.f_lo[0] == 0.0f && res.f_hi[0] == 0.0f, "R=100 has no 2:1 edges");
  CHECK(fabsf(res.q - 39.0f) < 0.5f, "R=100 Q from 3:1 %.2f", res.q);

  // 3. Marker-anchored: start on the slope, walk to the dip; clamp out-of-range start
  make_sweep(FA, FB, F0, 35.2f, 39.0f, 0.0f);
  g_r = 35.2f; swr_bw_analyse(get_swr, get_freq, get_r, N, 40, 50.0f, &res);
  CHECK(fabsf(res.f0 - F0) < 500.0f, "from left slope f0 %.0f", res.f0);
  g_r = 35.2f; swr_bw_analyse(get_swr, get_freq, get_r, N, N - 5, 50.0f, &res);
  CHECK(fabsf(res.f0 - F0) < 500.0f, "from right slope f0 %.0f", res.f0);
  g_r = 35.2f; swr_bw_analyse(get_swr, get_freq, get_r, N, 5000, 50.0f, &res);
  CHECK(fabsf(res.f0 - F0) < 500.0f, "out-of-range start clamps, f0 %.0f", res.f0);

  // 4. Two dips: marker picks the nearer, global picks the deeper
  for (int i = 0; i < N; i++) {
    float f = FA + (FB - FA) * i / (N - 1);
    float x1 = 35.0f * 39.0f * (f / 7.05e6f - 7.05e6f / f);   // deeper dip (R=35)
    float x2 = 80.0f * 39.0f * (f / 7.30e6f - 7.30e6f / f);   // shallower (R=80)
    float s1 = swr_of(35.0f, x1, 50.0f), s2 = swr_of(80.0f, x2, 50.0f);
    g_freq[i] = f; g_swr[i] = s1 < s2 ? s1 : s2;
  }
  g_r = 35.0f; swr_bw_analyse(get_swr, get_freq, get_r, N, -1, 50.0f, &res);
  CHECK(fabsf(res.f0 - 7.05e6f) < 2000.0f, "global picks deeper dip, f0 %.0f", res.f0);
  g_r = 80.0f; swr_bw_analyse(get_swr, get_freq, get_r, N, 380, 50.0f, &res);
  CHECK(fabsf(res.f0 - 7.30e6f) < 2000.0f, "marker picks nearer dip, f0 %.0f", res.f0);

  // 5. Edge off the end of the sweep: that side is 0, no Q from that level
  make_sweep(7.04e6f, 7.40e6f, F0, 50.0f, 39.0f, 0.0f);   // 3:1 low edge (7.018 MHz) is outside, 2:1 (7.059) inside
  g_r = 50.0f; swr_bw_analyse(get_swr, get_freq, get_r, N, -1, 50.0f, &res);
  CHECK(res.f_lo[1] == 0.0f, "3:1 low edge off sweep is 0 (got %.0f)", res.f_lo[1]);
  CHECK(res.f_hi[1] != 0.0f, "3:1 high edge present");
  CHECK(res.f_lo[0] != 0.0f && res.f_hi[0] != 0.0f, "2:1 edges still in sweep");

  // 6. Dip above 3:1: nothing bracketed, q = 0, no crash
  make_sweep(FA, FB, F0, 250.0f, 39.0f, 0.0f);
  g_r = 250.0f; swr_bw_analyse(get_swr, get_freq, get_r, N, -1, 50.0f, &res);
  CHECK(res.swr0 > 3.0f, "high dip swr0 %.2f", res.swr0);
  CHECK(res.q == 0.0f && !res.f_lo[0] && !res.f_hi[0] && !res.f_lo[1] && !res.f_hi[1], "high dip has no edges");

  // 7. Noise: +/-0.02 SWR ripple must not stop the walk or wreck Q
  make_sweep(FA, FB, F0, 35.2f, 39.0f, 0.04f);
  g_r = 35.2f; swr_bw_analyse(get_swr, get_freq, get_r, N, 60, 50.0f, &res);
  CHECK(fabsf(res.f0 - F0) < 1500.0f, "noisy f0 %.0f", res.f0);
  CHECK(fabsf(res.q - 39.0f) < 2.0f, "noisy Q %.2f", res.q);

  // 8. Degenerate sizes
  g_r = 50.0f; swr_bw_analyse(get_swr, get_freq, get_r, 2, -1, 50.0f, &res);
  CHECK(res.q == 0.0f && res.f0 == 0.0f, "n<3 yields empty result");

  if (failures) { printf("%d failure(s)\n", failures); return 1; }
  printf("all swr_bw checks passed\n");
  return 0;
}
