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
