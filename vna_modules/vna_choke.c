/*
 * CHOKE (S21) workflow arithmetic. Pure functions: no firmware globals, so the same file is
 * compiled by tests/host/choke_host.c. Included from measure.c under __VNA_WORKFLOW_CHOKE__.
 *
 * Series-through fixture: the DUT is in series between port 1 and port 2, so
 *   Z_ser = 2 * Z0 * (1 / S21 - 1)                                  (spec T2)
 * The empty jig's stray capacitance shunts the DUT; its S21 is stored by STORE FIXTURE and
 * removed in admittance: Y_dut = Y_meas - Y_fix.
 *
 * Two different R_S limits come out of that jig, and this file computes both:
 *  - choke_rs_ceiling() is the UN-NULLED one, R = 1 / (2 |B_fix|) = 1 / (4 pi f C): what the
 *    jig can resolve with no fixture stored, and the number the panel prints as "jig ceiling".
 *  - choke_rs_ceiling_deembed() is the limit that actually applies to a de-embedded reading.
 *    After the null, B_fix is subtracted rather than endured, and the conductance G (which IS
 *    R_S) is read directly, not as a difference of two large numbers. What still leaks into G
 *    is the null's repeatability rotating B_fix into it, so the limit is the raw ceiling
 *    divided by that fractional error - roughly 20x higher. Only this one gates the verdict.
 */
#ifdef WORKFLOW_HOST_TEST
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#endif

typedef float (*choke_get_t)(uint16_t idx);
enum { CHOKE_POOR = 0, CHOKE_WEAK, CHOKE_MARGINAL, CHOKE_GOOD, CHOKE_MEETS, CHOKE_HIGHPWR, CHOKE_JIG, CHOKE_VERDICT_COUNT };
#define CHOKE_OPEN 1e9f   /* "infinite" impedance sentinel (S21 = 0, or a de-embed that cancelled) */

static void choke_zser(float s21_re, float s21_im, float z0, float *r, float *x) {
  float d = s21_re * s21_re + s21_im * s21_im;
  if (d < 1e-12f) { *r = CHOKE_OPEN; *x = 0; return; }
  float ir = s21_re / d, ii = -s21_im / d;               /* 1/S21 */
  *r = 2.0f * z0 * (ir - 1.0f);
  *x = 2.0f * z0 * ii;
}

static void choke_z2y(float r, float x, float *g, float *b) {
  float d = r * r + x * x;
  if (d < 1e-12f) { *g = 1e12f; *b = 0; return; }
  *g = r / d; *b = -x / d;
}

static void choke_deembed(float rm, float xm, float rf, float xf, float *r, float *x) {
  float gm, bm, gf, bf;
  choke_z2y(rm, xm, &gm, &bm);
  choke_z2y(rf, xf, &gf, &bf);
  float g = gm - gf, b = bm - bf, d = g * g + b * b;
  if (d < 1e-24f) { *r = CHOKE_OPEN; *x = 0; return; }
  *r = g / d; *x = -b / d;
}

static float choke_rs_ceiling(float rf, float xf) {
  float gf, bf;
  choke_z2y(rf, xf, &gf, &bf);
  bf = vna_fabsf(bf);
  return bf < 1e-12f ? CHOKE_OPEN : 1.0f / (2.0f * bf);
}

/* The resolvable R_S once the fixture has been de-embedded: the raw ceiling divided by the
 * fractional repeatability of the null (5 %, this panel's design estimate for a re-inserted
 * clip-lead jig - the spec has no measured figure for a nulled fixture). Judging a de-embedded
 * reading against the raw ceiling would throw away correct multi-kilohm readings above ~7 MHz,
 * which is exactly what STORE FIXTURE exists to make measurable. */
#define CHOKE_NULL_REPEAT 0.05f
static float choke_rs_ceiling_deembed(float rf, float xf) {
  float c = choke_rs_ceiling(rf, xf);
  return c >= CHOKE_OPEN ? CHOKE_OPEN : c / CHOKE_NULL_REPEAT;
}

// Verdict on R_S alone (spec T2): the three low tiers are fixed (K9YC/N6LF), the two upper
// ones scale with the typed target (5 k by default: MEETS 5-10 k, HIGH PWR above 10 k).
// A reading at or above the ceiling handed in - choke_rs_ceiling_deembed(), the NULLED limit -
// or a negative one, which is noise around the null, is the JIG, not the choke (spec E10):
// no tier, CHOKE_JIG instead.
static uint8_t choke_verdict(float rs, float target, float ceiling) {
  if (rs < 0.0f || rs >= ceiling) return CHOKE_JIG;
  if (rs < 500.0f)  return CHOKE_POOR;
  if (rs < 1000.0f) return CHOKE_WEAK;
  if (rs < 2000.0f) return CHOKE_MARGINAL;
  if (rs < target)  return CHOKE_GOOD;
  if (rs < 2.0f * target) return CHOKE_MEETS;
  return CHOKE_HIGHPWR;
}

// Band label from frequency: lambda = 300/f_MHz snapped to the nearest standard rung (in the
// log domain, so 18.1 MHz -> 17 m, not 16). Derived, not a second band table (spec T2).
static uint8_t choke_rung_m(float f_hz) {
  static const uint8_t rungs[] = { 160, 80, 60, 40, 30, 20, 17, 15, 12, 10, 6, 4, 2 };
  float lambda = 300e6f / f_hz, best = 1e9f;
  uint8_t out = rungs[0];
  for (unsigned i = 0; i < sizeof(rungs) / sizeof(rungs[0]); i++) {
    float ratio = lambda > rungs[i] ? lambda / rungs[i] : rungs[i] / lambda;
    if (ratio < best) { best = ratio; out = rungs[i]; }
  }
  return out;
}

// Index of the minimum R over the points whose frequency lies in [f_lo, f_hi]; false if none.
static bool choke_band_min(choke_get_t get_r, choke_get_t get_f, uint16_t n, float f_lo, float f_hi, uint16_t *idx) {
  bool found = false;
  float best = 0;
  for (uint16_t i = 0; i < n; i++) {
    float f = get_f(i);
    if (f < f_lo || f > f_hi) continue;
    float r = get_r(i);
    if (!found || r < best) { best = r; *idx = i; found = true; }
  }
  return found;
}

// Parallel (anti-)resonance: the largest |Z| at a point where X crosses from INDUCTIVE to
// CAPACITIVE against a neighbour (spec E6/E7 - that direction is the |Z| peak; the other one,
// capacitive to inductive, is a series resonance and a |Z| minimum). false when the sweep
// contains no inductive-to-capacitive crossing.
static bool choke_zpeak(choke_get_t get_r, choke_get_t get_x, uint16_t n, uint16_t *idx, float *zmag) {
  bool found = false;
  for (uint16_t i = 1; i + 1 < n; i++) {
    float x0 = get_x(i - 1), x1 = get_x(i + 1);
    if (!(x0 > 0 && x1 < 0)) continue;
    float r = get_r(i), x = get_x(i), z = vna_sqrtf(r * r + x * x);
    if (!found || z > *zmag) { *zmag = z; *idx = i; found = true; }
  }
  return found;
}
