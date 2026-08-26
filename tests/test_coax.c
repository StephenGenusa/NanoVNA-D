/*
 * Host-side validation for vna_modules/vna_coax.c.
 * Build and run (no cross-toolchain needed):
 *   gcc -Wall -Wextra -Werror -o /tmp/test_coax tests/test_coax.c -lm && /tmp/test_coax
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define COAX_HOST_TEST
#define vna_sqrtf sqrtf
#include "../vna_modules/vna_coax.c"

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; \
  printf("FAIL: " __VA_ARGS__); printf("\n"); } } while (0)

// ARRL Vol 3 Table 23.4, dB per 100 ft, verbatim
static const float mhz[COAX_FREQS] = {1.8f, 3.6f, 7.1f, 14.2f, 21.2f, 28.4f, 50.1f};
static const float arrl[COAX_TYPES][COAX_FREQS] = {
  {0.16f, 0.23f, 0.32f, 0.46f, 0.56f, 0.65f, 0.87f},
  {0.25f, 0.37f, 0.55f, 0.75f, 1.00f, 1.20f, 1.60f},
  {0.49f, 0.68f, 1.00f, 1.40f, 1.70f, 1.90f, 2.50f},
  {0.56f, 0.82f, 1.20f, 1.70f, 2.00f, 2.40f, 3.20f},
  {1.10f, 1.50f, 2.10f, 3.10f, 3.80f, 4.40f, 5.90f},
};
#define FT_PER_M 3.280840f

int main(void) {
  // 1. Stored table reproduces the ARRL figures: 100 ft of each cable at each row
  for (int t = 0; t < COAX_TYPES; t++)
    for (int i = 0; i < COAX_FREQS; i++) {
      float got = coax_loss_db((uint8_t)(t + 1), mhz[i] * 1e6f, 100.0f / FT_PER_M);
      CHECK(fabsf(got - arrl[t][i]) < 0.006f, "%s @ %.1f MHz: %.3f vs ARRL %.2f", coax_name[t + 1], mhz[i], got, arrl[t][i]);
    }

  // 2. Worked case from the reference document: 50 ft RG-58 on 20 m = 0.85 dB
  float rg58_50ft_20m = coax_loss_db(4, 14.2e6f, 50.0f / FT_PER_M);
  CHECK(fabsf(rg58_50ft_20m - 0.85f) < 0.01f, "50 ft RG-58 @ 14.2 MHz = %.3f (expect 0.85)", rg58_50ft_20m);
  // 100 ft RG-58 on 10 m = 2.40 dB
  float rg58_100ft_10m = coax_loss_db(4, 28.4e6f, 100.0f / FT_PER_M);
  CHECK(fabsf(rg58_100ft_10m - 2.40f) < 0.01f, "100 ft RG-58 @ 28.4 MHz = %.3f (expect 2.40)", rg58_100ft_10m);

  // 3. Linear in length
  CHECK(fabsf(coax_loss_db(4, 7.1e6f, 20.0f) - 2.0f * coax_loss_db(4, 7.1e6f, 10.0f)) < 1e-4f, "loss linear in length");

  // 4. Interpolation between rows: monotone, between neighbours, sqrt(f)-shaped
  for (int t = 1; t <= COAX_TYPES; t++) {
    float prev = 0.0f;
    for (float f = 1.0e6f; f <= 60.0e6f; f += 0.25e6f) {
      float v = coax_loss_db((uint8_t)t, f, 100.0f);
      CHECK(v > prev, "%s monotone at %.2f MHz", coax_name[t], f * 1e-6f);
      prev = v;
    }
  }
  float mid = coax_loss_db(4, 10.0e6f, 100.0f / FT_PER_M);       // between 7.1 and 14.2 rows
  CHECK(mid > 1.20f && mid < 1.70f, "RG-58 @ 10 MHz between rows: %.3f", mid);
  // sqrt(f) law: at the geometric-mean-of-sqrt point the value is the mean of the rows
  float sm = (sqrtf(7.1f) + sqrtf(14.2f)) * 0.5f;
  float fm = sm * sm * 1e6f;
  float vm = coax_loss_db(4, fm, 100.0f / FT_PER_M);
  CHECK(fabsf(vm - 1.45f) < 0.01f, "sqrt(f) interpolation midpoint %.3f (expect 1.45)", vm);

  // 5. Extrapolation by sqrt(f) beyond the table
  float lo = coax_loss_db(4, 0.45e6f, 100.0f / FT_PER_M);         // 1.8 MHz / 4 -> half the loss
  CHECK(fabsf(lo - 0.28f) < 0.01f, "extrapolate below table: %.3f (expect 0.28)", lo);
  float hi = coax_loss_db(4, 200.4e6f, 100.0f / FT_PER_M);        // 50.1 MHz x 4 -> double
  CHECK(fabsf(hi - 6.40f) < 0.02f, "extrapolate above table: %.3f (expect 6.40)", hi);

  // 6. MANUAL / invalid / zero-length return 0
  CHECK(coax_loss_db(0, 7.1e6f, 10.0f) == 0.0f, "type 0 returns 0");
  CHECK(coax_loss_db(COAX_TYPES + 1, 7.1e6f, 10.0f) == 0.0f, "out-of-range type returns 0");
  CHECK(coax_loss_db(4, 7.1e6f, 0.0f) == 0.0f, "zero length returns 0");
  CHECK(strcmp(coax_type_name(0), "MANUAL") == 0, "type 0 name");
  CHECK(strcmp(coax_type_name(COAX_TYPES + 7), "MANUAL") == 0, "out-of-range name clamps to MANUAL");

  if (failures) { printf("%d failure(s)\n", failures); return 1; }
  printf("all coax checks passed\n");
  return 0;
}
