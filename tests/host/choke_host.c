/* Host driver for vna_modules/vna_choke.c */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#define WORKFLOW_HOST_TEST
#define vna_sqrtf sqrtf
#define vna_fabsf fabsf
#include "vna_modules/vna_choke.c"

static int fails = 0;
#define CHECK(c) do { if (!(c)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
#define NEAR(a, b, tol) (fabsf((a) - (b)) <= (tol))
#define PI_F 3.14159265f      /* M_PI is not declared under -std=c11 */

/* synthetic sweep for the array helpers */
#define N 11
static float R[N], X[N], F[N];
static float get_r(uint16_t i) { return R[i]; }
static float get_x(uint16_t i) { return X[i]; }
static float get_f(uint16_t i) { return F[i]; }

int main(void) {
  float r, x;
  /* series-through: S21 = 0.5 (real) through 50 ohm ports => Z = 2*50*(1/0.5 - 1) = 100 ohm */
  choke_zser(0.5f, 0.0f, 50.0f, &r, &x);
  CHECK(NEAR(r, 100.0f, 0.01f) && NEAR(x, 0.0f, 0.01f));
  /* S21 = 0 (open) => a huge impedance, not a division by zero */
  choke_zser(0.0f, 0.0f, 50.0f, &r, &x);
  CHECK(r > 1e8f);
  /* a 5 kohm resistor in series: S21 = 2*Z0/(2*Z0 + Z) = 100/5100 */
  choke_zser(100.0f / 5100.0f, 0.0f, 50.0f, &r, &x);
  CHECK(NEAR(r, 5000.0f, 1.0f));

  /* de-embed: jig = 2 pF at 14 MHz (X = -1/(2*pi*f*C) = -5684 ohm) in parallel with the DUT.
     measured = DUT || jig; subtracting the jig's admittance must return the DUT. */
  {
    float xf = -1.0f / (2.0f * PI_F * 14e6f * 2e-12f);                   /* -5684; the jig's series Z is (0, xf): a pure C has R = 0, not "open" */
    float gd = 1.0f / 5000.0f, bd = 0.0f;                                /* DUT: 5 kohm resistive */
    float bf = -1.0f / xf;                                               /* jig susceptance */
    float g = gd, b = bd + bf;                                           /* parallel: admittances add */
    float rm = g / (g * g + b * b), xm = -b / (g * g + b * b);           /* what the VNA sees */
    choke_deembed(rm, xm, 0.0f, xf, &r, &x);                            /* jig: pure C, rf = 0 */
    CHECK(NEAR(r, 5000.0f, 5.0f));
    CHECK(NEAR(x, 0.0f, 5.0f));
    /* R_S ceiling from that jig: 1/(4*pi*f*C) = 2842 ohm @ 14 MHz */
    CHECK(NEAR(choke_rs_ceiling(0.0f, xf), 2842.0f, 5.0f));
    /* the empty jig measured against itself cancels to "open": that must NOT become a verdict */
    choke_deembed(0.0f, xf, 0.0f, xf, &r, &x);
    CHECK(r >= CHOKE_OPEN);
    CHECK(choke_verdict(r, 5000.0f, 2842.0f) == CHOKE_JIG);
    /* a reading at or above the ceiling is jig-limited, whatever its value */
    CHECK(choke_verdict(3000.0f, 5000.0f, 2842.0f) == CHOKE_JIG);
    CHECK(choke_verdict(2000.0f, 5000.0f, 2842.0f) == CHOKE_GOOD);
    /* negative R (noise below the null) is clamped, not a POOR verdict on a phantom */
    CHECK(choke_verdict(-40.0f, 5000.0f, 2842.0f) == CHOKE_JIG);
  }
  /* no fixture => no ceiling */
  CHECK(choke_rs_ceiling(0.0f, 0.0f) > 1e8f);

  /* verdict tiers (spec T2), target 5 k, ceiling far above (a good jig) */
  CHECK(choke_verdict(400.0f, 5000.0f, CHOKE_OPEN) == CHOKE_POOR);
  CHECK(choke_verdict(500.0f, 5000.0f, CHOKE_OPEN) == CHOKE_WEAK);
  CHECK(choke_verdict(999.0f, 5000.0f, CHOKE_OPEN) == CHOKE_WEAK);
  CHECK(choke_verdict(1000.0f, 5000.0f, CHOKE_OPEN) == CHOKE_MARGINAL);
  CHECK(choke_verdict(2000.0f, 5000.0f, CHOKE_OPEN) == CHOKE_GOOD);
  CHECK(choke_verdict(4999.0f, 5000.0f, CHOKE_OPEN) == CHOKE_GOOD);
  CHECK(choke_verdict(5000.0f, 5000.0f, CHOKE_OPEN) == CHOKE_MEETS);
  CHECK(choke_verdict(9999.0f, 5000.0f, CHOKE_OPEN) == CHOKE_MEETS);
  CHECK(choke_verdict(10000.0f, 5000.0f, CHOKE_OPEN) == CHOKE_HIGHPWR);
  /* a lower typed target moves the two upper tiers, not the fixed low ones; the target itself
     is clamped to >= 2000 by the keypad so GOOD can never be empty */
  CHECK(choke_verdict(3000.0f, 3000.0f, CHOKE_OPEN) == CHOKE_MEETS);
  CHECK(choke_verdict(2500.0f, 3000.0f, CHOKE_OPEN) == CHOKE_GOOD);

  /* band rung labels: lambda = 300/f_MHz snapped to the standard rung */
  CHECK(choke_rung_m(3.75e6f) == 80);
  CHECK(choke_rung_m(7.1e6f) == 40);
  CHECK(choke_rung_m(14.2e6f) == 20);
  CHECK(choke_rung_m(18.1e6f) == 17);
  CHECK(choke_rung_m(21.2e6f) == 15);
  CHECK(choke_rung_m(24.9e6f) == 12);
  CHECK(choke_rung_m(28.5e6f) == 10);
  CHECK(choke_rung_m(1.9e6f) == 160);
  CHECK(choke_rung_m(5.35e6f) == 60);
  CHECK(choke_rung_m(10.1e6f) == 30);
  CHECK(choke_rung_m(50.5e6f) == 6);
  CHECK(choke_rung_m(145e6f) == 2);

  /* band minimum: points 1..11 MHz, R falls to 900 at 7 MHz */
  for (int i = 0; i < N; i++) { F[i] = 1e6f * (i + 1); R[i] = 3000.0f; X[i] = 100.0f * (i - 5); }
  R[6] = 900.0f;
  uint16_t idx = 99;
  CHECK(choke_band_min(get_r, get_f, N, 6.5e6f, 7.5e6f, &idx) && idx == 6);
  CHECK(choke_band_min(get_r, get_f, N, 3e6f, 5.5e6f, &idx) && R[idx] == 3000.0f && F[idx] >= 3e6f && F[idx] <= 5.5e6f);
  CHECK(!choke_band_min(get_r, get_f, N, 20e6f, 21e6f, &idx));        /* band outside the sweep */

  /* parallel resonance: |Z| peak where X changes sign (X: -500..+500 crosses at i=5) */
  R[5] = 6300.0f; R[6] = 3000.0f;
  float zmag = 0;
  CHECK(choke_zpeak(get_r, get_x, N, &idx, &zmag) && idx == 5 && NEAR(zmag, 6300.0f, 1.0f));
  /* no sign change => no parallel resonance reported even though R has a peak */
  for (int i = 0; i < N; i++) X[i] = -200.0f;
  CHECK(!choke_zpeak(get_r, get_x, N, &idx, &zmag));

  printf(fails ? "FAILED %d\n" : "OK\n", fails);
  return fails != 0;
}
