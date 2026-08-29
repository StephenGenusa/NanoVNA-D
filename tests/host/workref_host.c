/* Host driver for vna_modules/vna_workref.c. gcc -std=c11 -I. -o workref_host tests/host/workref_host.c -lm */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#define vna_sqrtf sqrtf
#define WORKREF_HOST_TEST
#define SWEEP_POINTS_MAX 401
typedef uint32_t freq_t;
/* stand-ins for the instrument state the module compares against */
static freq_t frequency0 = 1000000, frequency1 = 30000000;
static uint16_t sweep_points = 401, cal_status = 0x1f;
static float electrical_delayS11 = 0, electrical_delayS21 = 0, s21_offset = 0;
static uint8_t smooth = 0, in_tdr = 0, file_view = 0;
/* the swept table, as set_frequencies() fills it; cmd_scan changes THIS without touching frequency0/1 */
static freq_t f_first = 1000000, f_last = 30000000;
static freq_t getFrequency(uint16_t i) { return i == 0 ? f_first : f_last; }
static uint8_t get_smooth_factor(void) { return smooth; }
static float measured[2][SWEEP_POINTS_MAX][2];
#define WREF_IN_TDR()    (in_tdr)
#define WREF_FILE_VIEW() (file_view)
#define WREF_RTC_STAMP() (0x123456u)
#include "vna_modules/vna_workref.c"

static int fails = 0;
#define CHECK(c) do { if (!(c)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
  (void)frequency0;   /* stand-in kept for parity with firmware globals; module never reads it */
  memset(&wref_hdr, 0x5a, sizeof wref_hdr);        /* garbage, as at cold boot */
  CHECK(wref_state() == WREF_NONE);                 /* random header must not validate */
  for (int i = 0; i < 401; i++) { measured[0][i][0] = i * 0.001f; measured[0][i][1] = -0.5f; }
  CHECK(wref_store());
  CHECK(wref_state() == WREF_OK);
  CHECK(wref_s11[5][0] == 5 * 0.001f && wref_s11[5][1] == -0.5f);   /* same expression both sides: 0.005f != 5*0.001f in float */
  CHECK(wref_stamp() == 0x123456u);
  sweep_points = 101;  CHECK(wref_state() == WREF_STALE_POINTS); sweep_points = 401;
  f_last = 7300000; CHECK(wref_state() == WREF_STALE_SPAN); f_last = 30000000;   /* `scan 7000000 7300000 401`: same points, new span */
  f_first = 7000000; CHECK(wref_state() == WREF_STALE_SPAN); f_first = 1000000;
  frequency1 = 29000000; CHECK(wref_state() == WREF_OK); frequency1 = 30000000;   /* stimulus vars alone are not what was swept */
  cal_status = 0x0f;   CHECK(wref_state() == WREF_STALE_CAL);   cal_status = 0x1f;
  electrical_delayS11 = 1e-9f; CHECK(wref_state() == WREF_STALE_PROC); electrical_delayS11 = 0;
  smooth = 2;          CHECK(wref_state() == WREF_STALE_PROC);  smooth = 0;
  CHECK(wref_state() == WREF_OK);
  in_tdr = 1;  CHECK(!wref_store()); in_tdr = 0;   /* refused, previous ref intact */
  CHECK(wref_state() == WREF_OK);
  file_view = 1; CHECK(!wref_store()); file_view = 0;
  /* REPEAT CHECK: max |dGamma| between the stored reference and the current sweep */
  wref_repeat_measure(); CHECK(wref_repeat_gamma == 0);                 /* identical data -> 0 */
  measured[0][200][0] += 0.03f; measured[0][200][1] += 0.04f;           /* one point, |dGamma| = 0.05 */
  wref_repeat_measure();
  CHECK(fabsf(wref_repeat_gamma - 0.05f) < 1e-4f);
  measured[0][200][0] -= 0.03f; measured[0][200][1] -= 0.04f;           /* restore before STORE REF re-copies it */
  CHECK(wref_store()); CHECK(wref_repeat_gamma == 0);                   /* STORE REF clears a stale repeat reading */
  measured[0][200][0] += 0.03f; measured[0][200][1] += 0.04f;
  wref_repeat_measure(); CHECK(wref_repeat_gamma != 0);
  measured[0][200][0] -= 0.03f; measured[0][200][1] -= 0.04f;
  wref_clear(); CHECK(wref_state() == WREF_NONE); CHECK(wref_repeat_gamma == 0);   /* CLEAR REF also clears it */
  CHECK(!strcmp(wref_state_str(WREF_STALE_POINTS), "points"));
  printf(fails ? "FAILED %d\n" : "OK\n", fails);
  return fails != 0;
}
