/*
 * Workflow reference sweep, stored in the F303's 8 KB CCM SRAM (ram4).
 *
 * CCM is reachable by the CPU only. NEVER pass a pointer into wref_hdr or wref_s11 to
 * f_read, f_write, disk_*, spi_DMATxBuffer, spi_DMARxBuffer, lcd_bulk* or lcd_read_memory:
 * the SD and LCD paths hand caller pointers to DMA (lcd.c SD_RxDataBlock/SD_TxDataBlock) and
 * FatFs bypasses its sector cache for aligned multi-sector transfers. Stage through
 * spi_buffer like save_snp does.
 *
 * ChibiOS zeroes the .ram4_clear input section at EVERY boot (crt1.c:207-211) and leaves plain
 * .ram4 NOINIT (random at power-on, old contents across a warm reset). The header lives in
 * .ram4_clear, so magic == 0 after any reset and a stale reference can never appear; the S11
 * payload in .ram4 survives a reset but is unreachable without a valid header. The address
 * XOR in WREF_MAGIC is belt-and-braces only (&wref_hdr is 0x10000000 in every build).
 *
 * Staleness is decided by VALUE against the swept table (getFrequency(0) / getFrequency(n-1)),
 * never against frequency0/frequency1 and never by hooking a setter: the `scan` console
 * command (main.c cmd_scan) writes sweep_points and calls set_frequencies() directly, so a
 * same-points, different-span scan leaves frequency0/1 untouched.
 */
#ifndef WORKREF_HOST_TEST
#define WREF_SECTION_HDR  __attribute__((section(".ram4_clear")))
#define WREF_SECTION_DATA __attribute__((section(".ram4")))
#define WREF_IN_TDR()     ((props_mode & DOMAIN_MODE) == DOMAIN_TIME)
#define WREF_FILE_VIEW()  (sweep_mode & SWEEP_FILE_VIEW)
#ifdef __USE_RTC__
#define WREF_RTC_STAMP()  rtc_get_tr_bin()
#else
#define WREF_RTC_STAMP()  0u
#endif
#else
#define WREF_SECTION_HDR
#define WREF_SECTION_DATA
#endif

/* Header flag bits. WREF_HAS_S21 marks the S11 block as holding the CHOKE panel's de-embedded
 * series Z (R, X per point) instead of Gamma: firmware gets it from nanovna.h, which shares it
 * with ui.c; the host driver includes this module without nanovna.h. */
#ifndef WREF_HAS_S21
#define WREF_HAS_S21   (1<<0)
#endif
#define WREF_FROM_FILE (1<<1)

typedef struct {
  uint32_t magic;
  freq_t   start, stop;
  uint16_t points;
  uint16_t wcal_status;   /* not "cal_status": that identifier is a #define (current_props._cal_status)
                             in nanovna.h and would macro-expand inside this member's own name */
  float    edelay[2];
  float    ws21_offset;   /* ditto: "s21_offset" is #defined to current_props._s21_offset */
  uint8_t  smooth;
  uint8_t  flags;
  uint16_t lastsaveid;    /* the cal slot id (nanovna.h's lastsaveid) at STORE REF time: two slots
                             calibrated over the same span carry bit-identical wcal_status, so this
                             is the only thing that catches RECALL <n> switching calibrations */
  uint32_t stamp;
} wref_hdr_t;

#ifdef WORKREF_HOST_TEST
/* Firmware builds get this from nanovna.h (__VNA_WORKFLOW_MODULE__), shared with ui.c;
 * the host driver includes this module directly, without nanovna.h. */
typedef enum { WREF_NONE = 0, WREF_STALE_POINTS, WREF_STALE_SPAN, WREF_STALE_CAL,
               WREF_STALE_PROC, WREF_OK } wref_state_t;
#endif

static wref_hdr_t wref_hdr WREF_SECTION_HDR;
static float wref_s11[SWEEP_POINTS_MAX][2] WREF_SECTION_DATA;
#ifdef __VNA_WORKFLOW_CHOKE__
// Fixture null (spec §2.2): the OPEN test jig's S21, subtracted in admittance by the CHOKE panel.
static wref_hdr_t wfix_hdr WREF_SECTION_HDR;
static float wfix_s21[SWEEP_POINTS_MAX][2] WREF_SECTION_DATA;
#define WFIX_MAGIC ((uint32_t)0x57464958u ^ (uint32_t)(uintptr_t)&wfix_hdr)   /* 'WFIX' */
#endif

/* max |dGamma| between the reference and the last REPEAT CHECK sweep, 0 = not measured. Plain
 * .bss (not WREF_SECTION_*): it is a scratch reading, not part of the persisted reference. */
float wref_repeat_gamma;

#define WREF_MAGIC ((uint32_t)0x57524546u ^ (uint32_t)(uintptr_t)&wref_hdr)   /* 'WREF' */

// Fill everything but magic from the current instrument state (shared by both blocks).
static void wref_hdr_fill(wref_hdr_t *h) {
  h->start = getFrequency(0); h->stop = getFrequency(sweep_points - 1);
  h->points = sweep_points; h->wcal_status = cal_status;
  h->edelay[0] = electrical_delayS11; h->edelay[1] = electrical_delayS21;
  h->ws21_offset = s21_offset; h->smooth = get_smooth_factor();
  h->flags = 0; h->lastsaveid = lastsaveid; h->stamp = WREF_RTC_STAMP();
}

static wref_state_t wref_hdr_state(const wref_hdr_t *h, uint32_t magic) {
  if (h->magic != magic) return WREF_NONE;
  if (h->points != sweep_points) return WREF_STALE_POINTS;
  if (h->start != getFrequency(0) || h->stop != getFrequency(sweep_points - 1)) return WREF_STALE_SPAN;
  if (h->wcal_status != cal_status || h->lastsaveid != lastsaveid) return WREF_STALE_CAL;
  if (h->edelay[0] != electrical_delayS11 || h->edelay[1] != electrical_delayS21 ||
      h->ws21_offset != s21_offset || h->smooth != get_smooth_factor()) return WREF_STALE_PROC;
  return WREF_OK;
}

void wref_clear(void) { wref_hdr.magic = 0; wref_repeat_gamma = 0; }

bool wref_store(void) {
  if (WREF_IN_TDR() || WREF_FILE_VIEW()) return false;
  memcpy(wref_s11, measured[0], sizeof(float) * 2 * sweep_points);
  wref_hdr_fill(&wref_hdr);
  wref_hdr.magic      = WREF_MAGIC;
  wref_repeat_gamma   = 0;                       // a new reference retires the old repeat reading
  return true;
}

/* true iff wref_store() would succeed right now: ui.c pre-checks this for the immediate
 * "Not in TDR / file view" message box, without duplicating the WREF_IN_TDR()/WREF_FILE_VIEW()
 * macros (private to this file) in ui.c. */
bool wref_can_store(void) { return !WREF_IN_TDR() && !WREF_FILE_VIEW(); }

static bool wref_store_pending;

/* menu_wref_store_acb() defers the actual capture instead of calling wref_store() here:
 * ui_process() (main.c) runs BEFORE measurementDataSmooth() / transform_domain(), while
 * prepare_tune() / prepare_s11_resonance() run from draw_all() AFTER both, so a store made
 * directly from the button press would mix raw and smoothed/transformed data with what the
 * panel later compares it against (final-review.md I1). wref_store_consume(), called from
 * measure_prepare() (plot.c) which runs on the same thread after both, does the real work. */
static uint8_t wref_store_kind;   /* header flags for the pending store: 0 = plain S11 */
void wref_store_request(void) { wref_store_pending = true; wref_store_kind = 0; }
#ifdef __VNA_WORKFLOW_CHOKE__
/* CHOKE STORE REF: the same deferral, but the block is filled with de-embedded series Z */
void wref_store_request_kind(uint8_t flags) { wref_store_pending = true; wref_store_kind = flags; }
static bool wref_store_z(void);
#endif

/* Consumes a pending STORE REF request, if any. Returns true iff a store actually happened
 * (requested AND wref_store() succeeded), so the caller can reset tune_change_m only then. */
bool wref_store_consume(void) {
  if (!wref_store_pending) return false;
  wref_store_pending = false;
#ifdef __VNA_WORKFLOW_CHOKE__
  if (wref_store_kind & WREF_HAS_S21) return wref_store_z();
#endif
  return wref_store();
}

wref_state_t wref_state(void) { return wref_hdr_state(&wref_hdr, WREF_MAGIC); }

uint32_t wref_stamp(void) { return wref_hdr.magic == WREF_MAGIC ? wref_hdr.stamp : 0; }

#ifdef __VNA_WORKFLOW_CHOKE__
bool wfix_store(void) {
  if (WREF_IN_TDR() || WREF_FILE_VIEW()) return false;
  memcpy(wfix_s21, measured[1], sizeof(float) * 2 * sweep_points);
  wref_hdr_fill(&wfix_hdr);
  wfix_hdr.magic = WFIX_MAGIC;
  return true;
}
void         wfix_clear(void) { wfix_hdr.magic = 0; }

/* Same deferral as STORE REF (wref_store_request above): the FIXTURE button runs from
 * ui_process(), BEFORE measurementDataSmooth(), while prepare_choke() reads measured[1] after
 * it - so capture the fixture from measure_prepare() (plot.c) instead of from the button. */
static bool wfix_store_pending;
void wfix_store_request(void) { wfix_store_pending = true; }
bool wfix_store_consume(void) {
  if (!wfix_store_pending) return false;
  wfix_store_pending = false;
  return wfix_store();
}
wref_state_t wfix_state(void) { return wref_hdr_state(&wfix_hdr, WFIX_MAGIC); }
uint32_t     wfix_stamp(void) { return wfix_hdr.magic == WFIX_MAGIC ? wfix_hdr.stamp : 0; }
static inline const float *wfix_s21_at(uint16_t i) { return wfix_s21[i]; }   /* read by the CHOKE panel (measure.c) */

/* CHOKE STORE REF stores the DE-EMBEDDED SERIES Z (R, X per point), not Gamma, in the S11
 * block - one 3.2 KB block, two possible contents, told apart by WREF_HAS_S21. The Z itself is
 * computed by measure.c (choke_z_at(): measured[1] and the fixture, neither of which this
 * module knows), so the fill is a callback measure.c installs from prepare_choke(). */
void (*wref_fill_z_cb)(void);

static bool wref_store_z(void) {
  if (WREF_IN_TDR() || WREF_FILE_VIEW()) return false;
  if (wfix_state() != WREF_OK || !wref_fill_z_cb) return false;   // no correction -> no Z to store
  wref_fill_z_cb();
  wref_hdr_fill(&wref_hdr);
  wref_hdr.flags      = WREF_HAS_S21;
  wref_hdr.magic      = WREF_MAGIC;
  wref_repeat_gamma   = 0;
  return true;
}

/* The stored series R at sweep index i (valid only while wref_state_z() != WREF_NONE);
 * a choke_get_t for choke_band_min() in measure.c. */
static float wref_z_r(uint16_t i) { return wref_s11[i][0]; }

/* Z data is meaningless once the fixture it was de-embedded with is gone or stale, so it reads
 * NONE until a matching fixture is stored again - the block is never erased for that reason.
 * The header's own staleness (points / span / cal / proc) still applies on top. */
wref_state_t wref_state_z(void) {
  wref_state_t s = wref_state();
  if (s == WREF_NONE || !(wref_hdr.flags & WREF_HAS_S21)) return WREF_NONE;
  return wfix_state() == WREF_OK ? s : WREF_NONE;
}

/* The TUNE / RESONANCE panels read Gamma: a Z block must be invisible to them. */
wref_state_t wref_state_s11(void) {
  wref_state_t s = wref_state();
  return (s != WREF_NONE && (wref_hdr.flags & WREF_HAS_S21)) ? WREF_NONE : s;
}
#endif

// REPEATABILITY / REPEAT CHECK: max |dGamma| between the stored reference and the current
// sweep (measured[0], already a fresh sweep by the time the menu button runs).
void wref_repeat_measure(void) {
  wref_repeat_gamma = 0;
  if (WREF_IN_TDR() || wref_state_s11() != WREF_OK) return;   // never Gamma arithmetic on a Z block
  for (uint16_t i = 0; i < sweep_points; i++) {
    float dr = measured[0][i][0] - wref_s11[i][0], di = measured[0][i][1] - wref_s11[i][1];
    float g = dr * dr + di * di;
    if (g > wref_repeat_gamma) wref_repeat_gamma = g;
  }
  wref_repeat_gamma = vna_sqrtf(wref_repeat_gamma);
}

static const char *wref_state_str(wref_state_t s) {
  static const char * const names[] = { "none", "points", "span", "cal", "proc", "ok" };
  return names[s];
}
