// Pure arithmetic for the workflow panels; host-tested in tests/host/tune_host.c.
// Sources: ARRL Antenna Book dipole/vertical length rules (468/f, 234/f ft);
// first-order resonant-element scaling dL/L = -df/f; full-size df/dL = f/L.
// TUNE_ANT_* enum lives in nanovna.h (ui.c cycles it); the host driver defines it before including this file.
#ifdef WORKFLOW_HOST_TEST
enum { TUNE_ANT_UNKNOWN = 0, TUNE_ANT_DIPOLE, TUNE_ANT_VERTICAL, TUNE_ANT_EFHW, TUNE_ANT_COUNT };
#endif
#define FT_TO_M 0.3048f

static float tune_assumed_len_m(uint8_t type, float f_hz) {
  float f_mhz = f_hz * 1e-6f;
  if (f_mhz <= 0) return 0;
  switch (type) {
    case TUNE_ANT_DIPOLE:
    case TUNE_ANT_EFHW:     return 468.0f / f_mhz * FT_TO_M;
    case TUNE_ANT_VERTICAL: return 234.0f / f_mhz * FT_TO_M;
    default:                return 0;
  }
}
static bool tune_per_leg(uint8_t type) { return type == TUNE_ANT_DIPOLE; }

// f0 above target -> element too short -> positive (ADD)
static float tune_delta_len_m(uint8_t type, float f0_hz, float target_hz) {
  float L = tune_assumed_len_m(type, target_hz);
  if (L == 0 || f0_hz <= 0) return 0;
  return L * (f0_hz - target_hz) / f0_hz;
}
// signed Hz per metre of length added
static float tune_sensitivity_hz_per_m(float f0_before, float f0_after, float change_m) {
  if (change_m == 0) return 0;
  return (f0_after - f0_before) / change_m;
}
// |df/dL| for a full-size quarter-wave section: L = 71.32/f_MHz m -> f/L = f_MHz^2 * 1.402e4 Hz/m
static float tune_fullsize_hz_per_m(float f_hz) {
  float f_mhz = f_hz * 1e-6f;
  return f_mhz * f_mhz * 1.402e4f;
}
// metres to add (signed) given df = f(SWRmin) - target and a measured sensitivity k (Hz/m,
// signed, k < 0 for "wire added lowers f0"); caller guards k != 0.
static float tune_need_m(float df, float k) { return -df / k; }

// Is the target inside the calibrated range? cal0/cal1 are 0 when there is no calibration.
static bool tune_target_in_cal(uint32_t target, uint32_t cal0, uint32_t cal1) {
  return cal1 > cal0 && target >= cal0 && target <= cal1;
}

// Sweep to bracket a tuning target: 20% below and 10% above it (wire is cut long, so the
// first dip sits below the target). Clipped to the calibrated range when the target is
// inside it. Returns true when the current sweep [cur0, cur1] should be replaced: it does
// not bracket the target, or it is wider than the proposal (the 3.5-30 MHz default). A
// sweep the user already narrowed onto the target is left alone.
static bool tune_span_for_target(uint32_t target, uint32_t cal0, uint32_t cal1,
                                 uint32_t cur0, uint32_t cur1, uint32_t *start, uint32_t *stop) {
  if (target == 0) return false;
  uint32_t s = (uint32_t)(target * 0.80f), e = (uint32_t)(target * 1.10f);
  if (tune_target_in_cal(target, cal0, cal1)) {
    if (s < cal0) s = cal0;
    if (e > cal1) e = cal1;
  }
  *start = s; *stop = e;
  return target < cur0 || target > cur1 || (cur1 - cur0) > (e - s);
}
