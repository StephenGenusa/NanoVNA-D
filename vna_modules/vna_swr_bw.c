/*
 * SWR bandwidth / Q analysis of an S11 sweep.
 *
 * Pure algorithm over a sampled SWR curve: locate the dip (nearest the
 * given start index, or the global minimum), find the first 2:1 and 3:1
 * crossings on each side, and compute the bandwidth quality factor.
 *
 * Q follows Yaghjian & Best, "Impedance, Bandwidth and Q of Antennas",
 * IEEE Trans. AP 53(4), 2005 (eq. 7/12 there; exact for an RLC model per
 * eq. 21 of Yaghjian, arXiv:2501.03146): for an antenna tuned and matched
 * at f0, the fractional VSWR-s bandwidth is 2*sqrt(beta)/Q with
 * beta = (s-1)^2/(4s).  A VNA measures against a fixed z0 that generally
 * differs from R at the dip, so the matched form is generalized: with
 * g = (s-1)/(s+1) the reactance at the band edge satisfies
 *   |Xs|^2 = (g^2 (R+z0)^2 - (R-z0)^2) / (1 - g^2)
 * and, for a series-RLC dip (X ~ R*Q*BW/f0 across the band),
 *   Q = f0 * |Xs| / (R * BW).
 * This reduces to the Yaghjian/Best expression when R = z0, and recovers
 * Q exactly for any R in the RLC model (see tests/test_swr_bw.c).
 *
 * Included from measure.c on the target; the host test defines
 * SWR_BW_HOST_TEST and includes this file directly.
 */

#define SWR_BW_LEVELS 2
static const float swr_bw_level[SWR_BW_LEVELS] = {2.0f, 3.0f};

typedef struct {
  uint16_t idx;                 // sample index of the dip
  float    f0;                  // interpolated dip frequency (Hz)
  float    swr0;                // interpolated minimum SWR
  float    f_lo[SWR_BW_LEVELS]; // low-side crossing frequency per level, 0 if not in sweep
  float    f_hi[SWR_BW_LEVELS]; // high-side crossing frequency per level, 0 if not in sweep
  float    q;                   // bandwidth Q, 0 if not computable
} swr_bw_result_t;

typedef float (*swr_bw_get_t)(uint16_t idx);

// Walk from idx to the nearest local minimum of get(). Each step moves to
// the lowest sample within SWR_BW_LOOKAHEAD positions and only if it is
// strictly lower than the current one, so sample noise on the shallow part
// of the slope does not stop the descent and the walk always terminates.
#define SWR_BW_LOOKAHEAD 6
static uint16_t swr_bw_find_dip(swr_bw_get_t get, uint16_t n, uint16_t idx) {
  if (n < 2) return 0;
  if (idx > n - 1) idx = n - 1;
  for (;;) {
    float v = get(idx);
    uint16_t best = idx;
    for (int d = -SWR_BW_LOOKAHEAD; d <= SWR_BW_LOOKAHEAD; d++) {
      if (d == 0) continue;
      int j = (int)idx + d;
      if (j < 0 || j >= (int)n) continue;
      float vj = get((uint16_t)j);
      if (vj < v) { v = vj; best = (uint16_t)j; }
    }
    if (best == idx) return idx;
    idx = best;
  }
}

static uint16_t swr_bw_global_min(swr_bw_get_t get, uint16_t n) {
  uint16_t best = 0;
  float vbest = get(0);
  for (uint16_t i = 1; i < n; i++) { float v = get(i); if (v < vbest) { vbest = v; best = i; } }
  return best;
}

// Linear-interpolated frequency where get() first rises through level,
// walking from idx in direction dir (+1 / -1). 0 if the sweep ends first.
static float swr_bw_cross(swr_bw_get_t get, swr_bw_get_t freq, uint16_t n, uint16_t idx, int dir, float level) {
  float v0 = get(idx);
  if (v0 >= level) return 0.0f;
  for (;;) {
    if (dir < 0 ? idx == 0 : idx >= n - 1) return 0.0f;
    uint16_t next = idx + dir;
    float v1 = get(next);
    if (v1 >= level) {
      float k = (v1 == v0) ? 0.0f : (level - v0) / (v1 - v0);
      return freq(idx) + (freq(next) - freq(idx)) * k;
    }
    idx = next; v0 = v1;
  }
}

// Q from bandwidth at SWR level s, dip resistance r, reference z0.
static float swr_bw_q(float f0, float bw, float s, float r, float z0) {
  if (bw <= 0.0f || r <= 0.0f) return 0.0f;
  float g = (s - 1.0f) / (s + 1.0f), g2 = g * g;
  float x2 = (g2 * (r + z0) * (r + z0) - (r - z0) * (r - z0)) / (1.0f - g2);
  if (x2 <= 0.0f) return 0.0f;   // dip SWR at or above s: no bandwidth at this level
  return f0 * vna_sqrtf(x2) / (r * bw);
}

// Analyse the sweep. start: sample index to walk from, or -1 for the global
// minimum. r_at(idx) returns the resistance at a sample (from the impedance
// data); z0 is the reference impedance.
static void swr_bw_analyse(swr_bw_get_t get, swr_bw_get_t freq, swr_bw_get_t r_at, uint16_t n, int start, float z0, swr_bw_result_t *res) {
  memset(res, 0, sizeof(*res));
  if (n < 3) return;
  uint16_t x = (start < 0) ? swr_bw_global_min(get, n) : swr_bw_find_dip(get, n, (uint16_t)start);
  float r0 = r_at(x);
  res->idx  = x;
  res->f0   = freq(x);
  res->swr0 = get(x);
  for (int i = 0; i < SWR_BW_LEVELS; i++) {
    res->f_lo[i] = swr_bw_cross(get, freq, n, x, -1, swr_bw_level[i]);
    res->f_hi[i] = swr_bw_cross(get, freq, n, x, +1, swr_bw_level[i]);
  }
  // The crossings lie on the steep sides of the dip and are far less
  // sensitive to noise than the flat bottom, so when a level is bracketed
  // take f0 as the geometric mean of its edges (exact for X ~ f/f0 - f0/f)
  // and Q from that level; the tightest bracketed level wins. With no
  // bracketed level f0/swr0 stay at the dip sample.
  for (int i = 0; i < SWR_BW_LEVELS; i++) {
    if (res->f_lo[i] && res->f_hi[i]) {
      res->f0 = vna_sqrtf(res->f_lo[i] * res->f_hi[i]);
      res->q  = swr_bw_q(res->f0, res->f_hi[i] - res->f_lo[i], swr_bw_level[i], r0, z0);
      break;
    }
  }
}
