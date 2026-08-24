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
