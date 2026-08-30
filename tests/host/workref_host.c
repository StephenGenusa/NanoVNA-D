/* Host driver for vna_modules/vna_workref.c. gcc -std=c11 -I. -o workref_host tests/host/workref_host.c -lm */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#define vna_sqrtf sqrtf
#define WORKREF_HOST_TEST
#define __VNA_WORKFLOW_CHOKE__
#define SWEEP_POINTS_MAX 401
typedef uint32_t freq_t;
/* stand-ins for the instrument state the module compares against */
static freq_t frequency0 = 1000000, frequency1 = 30000000;
static uint16_t sweep_points = 401, cal_status = 0x1f;
static uint16_t lastsaveid = 0;   /* nanovna.h's lastsaveid: the cal slot RECALLed/SAVEd last */
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

/* stands in for measure.c's choke_wref_fill_z(): the CHOKE panel's de-embedded series Z */
static void stub_fill_z(void) {
  for (uint16_t i = 0; i < sweep_points; i++) { wref_s11[i][0] = 3900.0f; wref_s11[i][1] = 0.0f; }
}

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
  lastsaveid = 1;      CHECK(wref_state() == WREF_STALE_CAL);   lastsaveid = 0;
  /* ^ I4: RECALL 1 -> RECALL 2 with identical wcal_status (two slots both fully calibrated
   * over the same span) must still go stale; lastsaveid is the only thing that catches it. */
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
  /* I2: REPEAT CHECK must refuse in TDR, same as STORE REF, even with a real mismatch pending -
   * measured[0] would be domain-transformed data there, not a comparable S11 sweep. */
  in_tdr = 1; wref_repeat_measure(); CHECK(wref_repeat_gamma == 0); in_tdr = 0;
  measured[0][200][0] -= 0.03f; measured[0][200][1] -= 0.04f;
  wref_clear(); CHECK(wref_state() == WREF_NONE); CHECK(wref_repeat_gamma == 0);   /* CLEAR REF also clears it */
  CHECK(!strcmp(wref_state_str(WREF_STALE_POINTS), "points"));

  /* I1: deferred STORE REF. menu_wref_store_acb only sets a pending flag; the real memcpy /
   * header write happens in wref_store_consume(), called later from measure_prepare() (after
   * smoothing / transform_domain in the firmware) - so the button press itself never touches
   * measured[] processing state. */
  CHECK(wref_store()); CHECK(wref_state() == WREF_OK);              /* fresh reference to defer over */
  CHECK(!wref_store_pending);
  measured[0][7][0] = 0.25f; measured[0][7][1] = -0.75f;
  wref_store_request();
  CHECK(wref_store_pending);                    /* request recorded ... */
  CHECK(wref_s11[7][0] != 0.25f);               /* ... but nothing copied yet ... */
  CHECK(wref_state() == WREF_OK);               /* ... and the old reference is still valid */
  CHECK(wref_store_consume());                  /* consumer runs: not in TDR/file view -> stores */
  CHECK(!wref_store_pending);                   /* flag cleared */
  CHECK(wref_s11[7][0] == 0.25f && wref_s11[7][1] == -0.75f);
  CHECK(!wref_store_consume());                 /* nothing pending now -> no-op */
  /* a request made while refused (TDR) stays pending but wref_store() still refuses on consume */
  in_tdr = 1; wref_store_request(); CHECK(wref_store_pending);
  CHECK(!wref_store_consume()); CHECK(!wref_store_pending); in_tdr = 0;

  /* fixture block: independent of the S11 reference, same staleness rules */
  {
    for (uint16_t i = 0; i < sweep_points; i++) { measured[1][i][0] = 0.5f; measured[1][i][1] = -0.1f; }
    CHECK(wfix_state() == WREF_NONE);
    CHECK(wfix_store());
    CHECK(wfix_state() == WREF_OK);
    CHECK(wfix_s21_at(3)[0] == 0.5f && wfix_s21_at(3)[1] == -0.1f);
    CHECK(wref_state() == WREF_OK);          /* the S11 reference stored earlier is untouched */
    wref_clear();
    CHECK(wfix_state() == WREF_OK);          /* clearing one block leaves the other */
    sweep_points = 101;
    CHECK(wfix_state() == WREF_STALE_POINTS);
    sweep_points = 401;                       /* the driver's default (workref_host.c:13) */
    in_tdr = 1; CHECK(!wfix_store()); in_tdr = 0;
    wfix_clear();
    CHECK(wfix_state() == WREF_NONE);
  }
  /* Z reference (CHOKE STORE REF): the de-embedded series Z lives in the S11 block, flagged
   * WREF_HAS_S21, and is filled by measure.c through wref_fill_z_cb from wref_store_consume() -
   * choke_z_at() reads measured[1] and the fixture, neither of which this module knows about. */
  {
    for (int i = 0; i < 401; i++) { measured[0][i][0] = i * 0.001f; measured[0][i][1] = -0.5f; }
    for (uint16_t i = 0; i < sweep_points; i++) { measured[1][i][0] = 0.5f; measured[1][i][1] = -0.1f; }
    CHECK(wref_store());                        /* a plain S11 reference ... */
    CHECK(wref_state_s11() == WREF_OK);         /* ... reads OK as S11 ... */
    CHECK(wref_state_z() == WREF_NONE);         /* ... and never as Z */
    wref_fill_z_cb = stub_fill_z;
    CHECK(wfix_state() == WREF_NONE);
    wref_store_request_kind(WREF_HAS_S21);
    CHECK(!wref_store_consume());               /* no fixture -> a Z store is refused ... */
    CHECK(wref_state_s11() == WREF_OK);         /* ... and the plain reference is intact */
    CHECK(wref_s11[5][0] == 5 * 0.001f);
    CHECK(wfix_store());
    wref_store_request_kind(WREF_HAS_S21);
    CHECK(wref_store_consume());
    CHECK(wref_state_z() == WREF_OK);
    CHECK(wref_state_s11() == WREF_NONE);       /* Z data must never be read as S11 */
    CHECK(wref_z_r(5) == 3900.0f);
    /* REPEAT CHECK is Gamma arithmetic: it must not run against a Z block (3900 - 0.005 would
     * otherwise report a max |dGamma| of ~3900) */
    wref_repeat_measure(); CHECK(wref_repeat_gamma == 0);
    wfix_clear();
    CHECK(wref_state_z() == WREF_NONE);         /* no fixture -> the correction is gone, so is the ref */
    CHECK(wref_state_s11() == WREF_NONE);
    CHECK(wfix_store());
    CHECK(wref_state_z() == WREF_OK);           /* the block was NOT erased, it reads again */
    CHECK(wref_z_r(5) == 3900.0f);
    /* a stale Z reference only shows its reason once a matching fixture is back */
    f_last = 20000000;
    CHECK(wref_state_z() == WREF_NONE);         /* stale fixture hides it entirely */
    CHECK(wfix_store());                        /* re-null the jig on the new span ... */
    CHECK(wref_state_z() == WREF_STALE_SPAN);   /* ... now the Z block reports why it is stale */
    f_last = 30000000; CHECK(wfix_store());
    CHECK(wref_state_z() == WREF_OK);
    /* a plain STORE REF over a Z block goes back to S11 data */
    wref_store_request(); CHECK(wref_store_consume());
    CHECK(wref_state_s11() == WREF_OK);
    CHECK(wref_state_z() == WREF_NONE);
    CHECK(wref_s11[5][0] == 5 * 0.001f);
    wref_clear(); wfix_clear();
  }
  printf(fails ? "FAILED %d\n" : "OK\n", fails);
  return fails != 0;
}
