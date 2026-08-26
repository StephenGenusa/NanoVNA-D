/*
 * Coaxial cable matched-loss table for the SWR ANT trace format.
 *
 * Source: ARRL Antenna Book for Radio Communications, Vol. 3, Table 23.4,
 * "Cable Attenuation (dB per 100 feet)", tabulated directly at amateur band
 * frequencies. Original figures (dB/100 ft):
 *
 *   MHz      1.8   3.6   7.1  14.2  21.2  28.4  50.1
 *   LMR-400  0.16  0.23  0.32  0.46  0.56  0.65  0.87
 *   RG-213   0.25  0.37  0.55  0.75  1.00  1.20  1.60
 *   RG-8X    0.49  0.68  1.00  1.40  1.70  1.90  2.50
 *   RG-58    0.56  0.82  1.20  1.70  2.00  2.40  3.20
 *   RG-174   1.10  1.50  2.10  3.10  3.80  4.40  5.90   (RG-316 is equivalent)
 *
 * Stored here converted to 0.01 dB per 100 m (x 3.28084), so the metric
 * CABLE LENGTH entry applies directly. Between rows the loss is
 * interpolated on sqrt(f), the dominant (skin-effect) term at HF; beyond
 * the table it is extrapolated by the same law from the nearest row.
 * Figures are for new, dry, name-brand cable; old, wet or off-brand cable
 * can be markedly worse - measure it (MEASURE -> CABLE) when in doubt.
 *
 * Included from plot.c on the target; the host test defines
 * COAX_HOST_TEST and includes this file directly.
 */

#define COAX_FREQS 7
#define COAX_TYPES 5   // excluding index 0 = MANUAL

static const uint16_t coax_freq_10khz[COAX_FREQS] = {180, 360, 710, 1420, 2120, 2840, 5010};

static const char *const coax_name[COAX_TYPES + 1] = {
  "MANUAL", "LMR-400", "RG-213", "RG-8X", "RG-58", "RG-174/316"
};

// 0.01 dB per 100 m at each table frequency
static const uint16_t coax_loss_100m[COAX_TYPES][COAX_FREQS] = {
  { 52,  75, 105,  151,  184,  213,  285}, // LMR-400
  { 82, 121, 180,  246,  328,  394,  525}, // RG-213
  {161, 223, 328,  459,  558,  623,  820}, // RG-8X
  {184, 269, 394,  558,  656,  787, 1050}, // RG-58
  {361, 492, 689, 1017, 1247, 1444, 1936}, // RG-174/316
};

static const char *coax_type_name(uint8_t type) {
  return coax_name[type <= COAX_TYPES ? type : 0];
}

// One-way matched loss (dB) of len_m metres of cable `type` at f_hz.
// type 0 or len <= 0 returns 0.
static float coax_loss_db(uint8_t type, float f_hz, float len_m) {
  if (type == 0 || type > COAX_TYPES || len_m <= 0.0f || f_hz <= 0.0f) return 0.0f;
  const uint16_t *row = coax_loss_100m[type - 1];
  float f = f_hz * 1e-4f;                      // to 10 kHz units, same as the table
  float loss;
  if (f <= coax_freq_10khz[0]) {
    loss = row[0] * vna_sqrtf(f / coax_freq_10khz[0]);
  } else if (f >= coax_freq_10khz[COAX_FREQS - 1]) {
    loss = row[COAX_FREQS - 1] * vna_sqrtf(f / coax_freq_10khz[COAX_FREQS - 1]);
  } else {
    int i = 1;
    while (f > coax_freq_10khz[i]) i++;
    float s0 = vna_sqrtf((float)coax_freq_10khz[i - 1]), s1 = vna_sqrtf((float)coax_freq_10khz[i]);
    float k = (vna_sqrtf(f) - s0) / (s1 - s0);
    loss = row[i - 1] + (row[i] - row[i - 1]) * k;
  }
  return loss * 0.01f * len_m * 0.01f;         // 0.01 dB units, per 100 m
}
