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

#define WREF_HAS_S21   (1<<0)
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
  uint32_t stamp;
} wref_hdr_t;

typedef enum { WREF_NONE = 0, WREF_STALE_POINTS, WREF_STALE_SPAN, WREF_STALE_CAL,
               WREF_STALE_PROC, WREF_OK } wref_state_t;

static wref_hdr_t wref_hdr WREF_SECTION_HDR;
static float wref_s11[SWEEP_POINTS_MAX][2] WREF_SECTION_DATA;

#define WREF_MAGIC ((uint32_t)0x57524546u ^ (uint32_t)(uintptr_t)&wref_hdr)   /* 'WREF' */

static void wref_clear(void) { wref_hdr.magic = 0; }

static bool wref_store(void) {
  if (WREF_IN_TDR() || WREF_FILE_VIEW()) return false;
  memcpy(wref_s11, measured[0], sizeof(float) * 2 * sweep_points);
  wref_hdr.start      = getFrequency(0);                  /* the swept table, not frequency0/1 */
  wref_hdr.stop       = getFrequency(sweep_points - 1);
  wref_hdr.points     = sweep_points;
  wref_hdr.wcal_status = cal_status;
  wref_hdr.edelay[0]  = electrical_delayS11;
  wref_hdr.edelay[1]  = electrical_delayS21;
  wref_hdr.ws21_offset = s21_offset;
  wref_hdr.smooth     = get_smooth_factor();
  wref_hdr.flags      = 0;
  wref_hdr.stamp      = WREF_RTC_STAMP();
  wref_hdr.magic      = WREF_MAGIC;
  return true;
}

static wref_state_t wref_state(void) {
  if (wref_hdr.magic != WREF_MAGIC) return WREF_NONE;
  if (wref_hdr.points != sweep_points) return WREF_STALE_POINTS;
  if (wref_hdr.start != getFrequency(0) || wref_hdr.stop != getFrequency(sweep_points - 1)) return WREF_STALE_SPAN;
  if (wref_hdr.wcal_status != cal_status) return WREF_STALE_CAL;
  if (wref_hdr.edelay[0] != electrical_delayS11 || wref_hdr.edelay[1] != electrical_delayS21 ||
      wref_hdr.ws21_offset != s21_offset || wref_hdr.smooth != get_smooth_factor()) return WREF_STALE_PROC;
  return WREF_OK;
}

static uint32_t wref_stamp(void) { return wref_hdr.magic == WREF_MAGIC ? wref_hdr.stamp : 0; }

static const char *wref_state_str(wref_state_t s) {
  static const char * const names[] = { "none", "points", "span", "cal", "proc", "ok" };
  return names[s];
}
