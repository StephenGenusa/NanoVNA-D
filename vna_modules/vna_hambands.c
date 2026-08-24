/*
 * Amateur radio band edge tables with region setting.
 *
 * Include-fragment (like other vna_modules): #include'd from plot.c in the
 * firmware build, or from tests/test_hambands.c on the host.
 * The includer provides freq_t (uint32_t Hz); firmware gets ham_band_t and
 * the API prototypes from nanovna.h, the host test defines HAM_BANDS_HOST_TEST
 * to get the typedef here instead.
 *
 * Region numbering is persisted in config._ham_region — never renumber:
 *   0=OFF 1=IARU R1 2=IARU R2 3=IARU R3 4=USA 5=Canada 6=UK 7=Germany
 *   8=Japan 9=Australia
 *
 * Tables list national/regional band EDGES only (no sub-band segments, see
 * docs/superpowers/specs/2026-08-24-ham-bands-design.md). Entries are sorted
 * ascending and non-overlapping; the 60 m entries for R2/USA/Canada and UK
 * are channelized/bandlet allocations shown as their envelope.
 */
#ifdef HAM_BANDS_HOST_TEST
typedef struct {
  freq_t start;
  freq_t end;
} ham_band_t;
#define HAM_REGION_COUNT 9
#endif

// IARU Region 1 (Europe, Africa, Middle East, northern Asia) band plan
static const ham_band_t ham_bands_iaru_r1[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1810000,    2000000},    // 160m
  {3500000,    3800000},    // 80m
  {5351500,    5366500},    // 60m (WRC-15)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   52000000},   // 6m
  {70000000,   70500000},   // 4m (not all R1 countries)
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

// IARU Region 2 (Americas) band plan
static const ham_band_t ham_bands_iaru_r2[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    4000000},    // 80m
  {5330500,    5406400},    // 60m (channelized, envelope)
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {222000000,  225000000},  // 1.25m
  {420000000,  450000000},  // 70cm
  {902000000,  928000000},  // 33cm
  {1240000000, 1300000000}, // 23cm
};

// IARU Region 3 (Asia-Pacific) band plan
static const ham_band_t ham_bands_iaru_r3[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    3900000},    // 80m
  {5351500,    5366500},    // 60m (WRC-15)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

// USA, FCC Part 97.301 (all license classes combined)
static const ham_band_t ham_bands_usa[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    4000000},    // 80m
  {5330500,    5406400},    // 60m (5 channels, envelope)
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {222000000,  225000000},  // 1.25m
  {420000000,  450000000},  // 70cm
  {902000000,  928000000},  // 33cm
  {1240000000, 1300000000}, // 23cm
};

// Canada, ISED RBR-4
static const ham_band_t ham_bands_canada[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    2000000},    // 160m
  {3500000,    4000000},    // 80m
  {5330500,    5406400},    // 60m (5 channels, envelope)
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {222000000,  225000000},  // 1.25m
  {430000000,  450000000},  // 70cm
  {902000000,  928000000},  // 33cm
  {1240000000, 1300000000}, // 23cm
};

// UK, Ofcom amateur licence (Full)
static const ham_band_t ham_bands_uk[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1810000,    2000000},    // 160m
  {3500000,    3800000},    // 80m
  {5258500,    5406500},    // 60m (11 bandlets, envelope)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   52000000},   // 6m
  {70000000,   70500000},   // 4m
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1325000000}, // 23cm (UK extends to 1325 MHz)
};

// Germany, BNetzA AFuV (class A)
static const ham_band_t ham_bands_germany[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1810000,    2000000},    // 160m
  {3500000,    3800000},    // 80m
  {5351500,    5366500},    // 60m (WRC-15)
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   52000000},   // 6m
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

// Japan, MIC/JARL band plan (split 160m/80m allocations)
static const ham_band_t ham_bands_japan[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    1810000},    // 160m lower
  {1825000,    1875000},    // 160m upper
  {3500000,    3580000},    // 80m segment 1
  {3662000,    3687000},    // 80m segment 2
  {3702000,    3716000},    // 80m segment 3
  {3745000,    3770000},    // 80m segment 4
  {3791000,    3805000},    // 80m segment 5
  {7000000,    7200000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  146000000},  // 2m
  {430000000,  440000000},  // 70cm
  {1260000000, 1300000000}, // 23cm (Japan: 1260-1300 MHz)
};

// Australia, ACMA amateur LCD (Advanced)
static const ham_band_t ham_bands_australia[] = {
  {135700,     137800},     // 2200m
  {472000,     479000},     // 630m
  {1800000,    1875000},    // 160m
  {3500000,    3700000},    // 80m lower
  {3776000,    3800000},    // 80m upper
  {7000000,    7300000},    // 40m
  {10100000,   10150000},   // 30m
  {14000000,   14350000},   // 20m
  {18068000,   18168000},   // 17m
  {21000000,   21450000},   // 15m
  {24890000,   24990000},   // 12m
  {28000000,   29700000},   // 10m
  {50000000,   54000000},   // 6m
  {144000000,  148000000},  // 2m
  {430000000,  450000000},  // 70cm
  {1240000000, 1300000000}, // 23cm
};

typedef struct {
  const char *name;
  const ham_band_t *bands;
  uint16_t count;
} ham_region_t;

#define HAM_BANDS_TABLE(name, tbl) {name, tbl, sizeof(tbl)/sizeof(tbl[0])}
static const ham_region_t ham_regions[HAM_REGION_COUNT] = {
  HAM_BANDS_TABLE("IARU R1",   ham_bands_iaru_r1),
  HAM_BANDS_TABLE("IARU R2",   ham_bands_iaru_r2),
  HAM_BANDS_TABLE("IARU R3",   ham_bands_iaru_r3),
  HAM_BANDS_TABLE("USA",       ham_bands_usa),
  HAM_BANDS_TABLE("CANADA",    ham_bands_canada),
  HAM_BANDS_TABLE("UK",        ham_bands_uk),
  HAM_BANDS_TABLE("GERMANY",   ham_bands_germany),
  HAM_BANDS_TABLE("JAPAN",     ham_bands_japan),
  HAM_BANDS_TABLE("AUSTRALIA", ham_bands_australia),
};

const char *ham_region_name(uint8_t region) {
  if (region == 0 || region > HAM_REGION_COUNT) return "OFF";
  return ham_regions[region - 1].name;
}

const ham_band_t *ham_bands_get(uint8_t region, uint16_t *count) {
  if (region == 0 || region > HAM_REGION_COUNT) return NULL;
  *count = ham_regions[region - 1].count;
  return ham_regions[region - 1].bands;
}

#ifdef __USE_HAM_SUBBANDS__
/*
 * HF sub-band segments (CW / narrow digital / phone) for the three IARU
 * regional band plans. Country regions map to their parent plan (see
 * ham_region_plan[]); the renderer clips segments to the region's own
 * band edges, so plan segments wider than a country's band never show.
 * Beacon slices are folded into HAM_SEG_DIGI. HF only (<= 29.7 MHz);
 * VHF+ bands render edge-only.
 */
#ifdef HAM_BANDS_HOST_TEST
enum {HAM_SEG_CW = 0, HAM_SEG_DIGI, HAM_SEG_PHONE};
typedef struct {
  freq_t  start;
  freq_t  end;
  uint8_t type;
} ham_segment_t;
#endif

// IARU Region 1 HF band plan segments
static const ham_segment_t ham_segments_r1[] = {
  {135700,   137400,   HAM_SEG_CW},    // 2200m CW
  {137400,   137800,   HAM_SEG_DIGI},  // 2200m narrow digi
  {472000,   475000,   HAM_SEG_CW},    // 630m CW
  {475000,   479000,   HAM_SEG_DIGI},  // 630m CW/digi
  {1810000,  1838000,  HAM_SEG_CW},    // 160m CW
  {1838000,  1843000,  HAM_SEG_DIGI},  // 160m narrow digi
  {1843000,  2000000,  HAM_SEG_PHONE}, // 160m all modes
  {3500000,  3570000,  HAM_SEG_CW},    // 80m CW
  {3570000,  3600000,  HAM_SEG_DIGI},  // 80m narrow digi
  {3600000,  3800000,  HAM_SEG_PHONE}, // 80m all modes
  {5351500,  5354000,  HAM_SEG_CW},    // 60m CW/narrow
  {5354000,  5366000,  HAM_SEG_PHONE}, // 60m all modes (USB)
  {5366000,  5366500,  HAM_SEG_DIGI},  // 60m weak signal narrow
  {7000000,  7040000,  HAM_SEG_CW},    // 40m CW
  {7040000,  7050000,  HAM_SEG_DIGI},  // 40m narrow digi
  {7050000,  7200000,  HAM_SEG_PHONE}, // 40m all modes
  {10100000, 10130000, HAM_SEG_CW},    // 30m CW
  {10130000, 10150000, HAM_SEG_DIGI},  // 30m narrow digi (no phone on 30m)
  {14000000, 14070000, HAM_SEG_CW},    // 20m CW
  {14070000, 14101000, HAM_SEG_DIGI},  // 20m digi (incl beacons 14099-14101)
  {14101000, 14350000, HAM_SEG_PHONE}, // 20m all modes
  {18068000, 18095000, HAM_SEG_CW},    // 17m CW
  {18095000, 18111000, HAM_SEG_DIGI},  // 17m digi (incl beacons)
  {18111000, 18168000, HAM_SEG_PHONE}, // 17m all modes
  {21000000, 21070000, HAM_SEG_CW},    // 15m CW
  {21070000, 21151000, HAM_SEG_DIGI},  // 15m digi (incl beacons 21149-21151)
  {21151000, 21450000, HAM_SEG_PHONE}, // 15m all modes
  {24890000, 24915000, HAM_SEG_CW},    // 12m CW
  {24915000, 24931000, HAM_SEG_DIGI},  // 12m digi (incl beacons)
  {24931000, 24990000, HAM_SEG_PHONE}, // 12m all modes
  {28000000, 28070000, HAM_SEG_CW},    // 10m CW
  {28070000, 28225000, HAM_SEG_DIGI},  // 10m digi (incl beacons 28190-28225)
  {28225000, 29700000, HAM_SEG_PHONE}, // 10m all modes
};

// IARU Region 2 HF band plan segments
static const ham_segment_t ham_segments_r2[] = {
  {135700,   137400,   HAM_SEG_CW},    // 2200m CW
  {137400,   137800,   HAM_SEG_DIGI},  // 2200m narrow digi
  {472000,   475000,   HAM_SEG_CW},    // 630m CW
  {475000,   479000,   HAM_SEG_DIGI},  // 630m CW/digi
  {1800000,  1810000,  HAM_SEG_DIGI},  // 160m digimodes
  {1810000,  1840000,  HAM_SEG_CW},    // 160m CW
  {1840000,  2000000,  HAM_SEG_PHONE}, // 160m all modes
  {3500000,  3570000,  HAM_SEG_CW},    // 80m CW
  {3570000,  3600000,  HAM_SEG_DIGI},  // 80m narrow digi
  {3600000,  4000000,  HAM_SEG_PHONE}, // 75/80m all modes
  {5330500,  5406400,  HAM_SEG_PHONE}, // 60m channelized USB (envelope)
  {7000000,  7040000,  HAM_SEG_CW},    // 40m CW
  {7040000,  7043000,  HAM_SEG_DIGI},  // 40m narrow digi
  {7043000,  7300000,  HAM_SEG_PHONE}, // 40m all modes
  {10100000, 10130000, HAM_SEG_CW},    // 30m CW
  {10130000, 10150000, HAM_SEG_DIGI},  // 30m narrow digi (no phone on 30m)
  {14000000, 14070000, HAM_SEG_CW},    // 20m CW
  {14070000, 14101000, HAM_SEG_DIGI},  // 20m digi (incl beacons)
  {14101000, 14350000, HAM_SEG_PHONE}, // 20m all modes
  {18068000, 18095000, HAM_SEG_CW},    // 17m CW
  {18095000, 18111000, HAM_SEG_DIGI},  // 17m digi (incl beacons)
  {18111000, 18168000, HAM_SEG_PHONE}, // 17m all modes
  {21000000, 21070000, HAM_SEG_CW},    // 15m CW
  {21070000, 21151000, HAM_SEG_DIGI},  // 15m digi (incl beacons)
  {21151000, 21450000, HAM_SEG_PHONE}, // 15m all modes
  {24890000, 24915000, HAM_SEG_CW},    // 12m CW
  {24915000, 24931000, HAM_SEG_DIGI},  // 12m digi (incl beacons)
  {24931000, 24990000, HAM_SEG_PHONE}, // 12m all modes
  {28000000, 28070000, HAM_SEG_CW},    // 10m CW
  {28070000, 28300000, HAM_SEG_DIGI},  // 10m digi (incl beacons 28190-28300)
  {28300000, 29700000, HAM_SEG_PHONE}, // 10m all modes
};

// IARU Region 3 HF band plan segments
static const ham_segment_t ham_segments_r3[] = {
  {135700,   137400,   HAM_SEG_CW},    // 2200m CW
  {137400,   137800,   HAM_SEG_DIGI},  // 2200m narrow digi
  {472000,   475000,   HAM_SEG_CW},    // 630m CW
  {475000,   479000,   HAM_SEG_DIGI},  // 630m CW/digi
  {1800000,  1838000,  HAM_SEG_CW},    // 160m CW
  {1838000,  1843000,  HAM_SEG_DIGI},  // 160m narrow digi
  {1843000,  2000000,  HAM_SEG_PHONE}, // 160m all modes
  {3500000,  3570000,  HAM_SEG_CW},    // 80m CW
  {3570000,  3600000,  HAM_SEG_DIGI},  // 80m narrow digi
  {3600000,  3900000,  HAM_SEG_PHONE}, // 80m all modes
  {5351500,  5354000,  HAM_SEG_CW},    // 60m CW/narrow
  {5354000,  5366000,  HAM_SEG_PHONE}, // 60m all modes (USB)
  {5366000,  5366500,  HAM_SEG_DIGI},  // 60m weak signal narrow
  {7000000,  7025000,  HAM_SEG_CW},    // 40m CW
  {7025000,  7035000,  HAM_SEG_DIGI},  // 40m narrow digi
  {7035000,  7200000,  HAM_SEG_PHONE}, // 40m all modes
  {10100000, 10130000, HAM_SEG_CW},    // 30m CW
  {10130000, 10150000, HAM_SEG_DIGI},  // 30m narrow digi (no phone on 30m)
  {14000000, 14070000, HAM_SEG_CW},    // 20m CW
  {14070000, 14101000, HAM_SEG_DIGI},  // 20m digi (incl beacons)
  {14101000, 14350000, HAM_SEG_PHONE}, // 20m all modes
  {18068000, 18095000, HAM_SEG_CW},    // 17m CW
  {18095000, 18111000, HAM_SEG_DIGI},  // 17m digi (incl beacons)
  {18111000, 18168000, HAM_SEG_PHONE}, // 17m all modes
  {21000000, 21070000, HAM_SEG_CW},    // 15m CW
  {21070000, 21151000, HAM_SEG_DIGI},  // 15m digi (incl beacons)
  {21151000, 21450000, HAM_SEG_PHONE}, // 15m all modes
  {24890000, 24915000, HAM_SEG_CW},    // 12m CW
  {24915000, 24931000, HAM_SEG_DIGI},  // 12m digi (incl beacons)
  {24931000, 24990000, HAM_SEG_PHONE}, // 12m all modes
  {28000000, 28070000, HAM_SEG_CW},    // 10m CW
  {28070000, 28300000, HAM_SEG_DIGI},  // 10m digi (incl beacons)
  {28300000, 29700000, HAM_SEG_PHONE}, // 10m all modes
};

// Region (1..9) -> parent IARU plan (1..3). Index is region-1.
// 1=IARU R1 2=IARU R2 3=IARU R3 4=USA 5=Canada 6=UK 7=Germany 8=Japan 9=Australia
static const uint8_t ham_region_plan[HAM_REGION_COUNT] = {1, 2, 3, 2, 2, 1, 1, 3, 3};

typedef struct {
  const ham_segment_t *segments;
  uint16_t count;
} ham_seg_table_t;

#define HAM_SEG_TABLE(tbl) {tbl, sizeof(tbl)/sizeof(tbl[0])}
static const ham_seg_table_t ham_seg_tables[3] = {
  HAM_SEG_TABLE(ham_segments_r1),
  HAM_SEG_TABLE(ham_segments_r2),
  HAM_SEG_TABLE(ham_segments_r3),
};

const ham_segment_t *ham_segments_get(uint8_t region, uint16_t *count) {
  if (region == 0 || region > HAM_REGION_COUNT) return NULL;
  const ham_seg_table_t *t = &ham_seg_tables[ham_region_plan[region - 1] - 1];
  *count = t->count;
  return t->segments;
}
#endif // __USE_HAM_SUBBANDS__
