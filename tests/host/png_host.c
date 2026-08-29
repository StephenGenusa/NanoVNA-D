/* Host driver for vna_modules/vna_png.c: writes synthetic screens as PNG (+ .idx index dumps),
 * decodes them back with the fragment's own inflater, or checks that a file is rejected.
 *   gcc -std=c11 -I. -o png_host tests/host/png_host.c
 *   ./png_host OUTDIR encode | decode NAME | reject NAME
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define PNG_HOST_TEST
#define PNG_565_TO_RGB(v)      (((((v) >> 11) & 31) * 255 / 31) << 16 | ((((v) >> 5) & 63) * 255 / 63) << 8 | (((v) & 31) * 255 / 31))
#define PNG_RGB_TO_565(r,g,b)  ((((r) * 31 / 255) << 11) | (((g) * 63 / 255) << 5) | ((b) * 31 / 255))
#include "vna_modules/vna_png.c"

#define W 480
#define H 320
static uint8_t screen[H][W];
static uint8_t decoded[H][W];
static uint16_t palette[256];
static uint8_t work[PNG_WORK_BYTES > PNG_DWORK_BYTES ? PNG_WORK_BYTES : PNG_DWORK_BYTES];
static uint8_t rowbuf[W];

static unsigned io_write(void *ctx, const void *d, unsigned n) { return fwrite(d, 1, n, (FILE *)ctx); }
static unsigned io_read(void *ctx, void *d, unsigned n) { return fread(d, 1, n, (FILE *)ctx); }
static int get_row(void *ctx, unsigned y, uint8_t *row) { (void)ctx; memcpy(row, screen[y], W); return 1; }
static int put_row(void *ctx, unsigned y, const uint8_t *row) { (void)ctx; memcpy(decoded[y], row, W); return 1; }

static void fill(const char *name, unsigned ncolors) {
  unsigned seed = 12345;
  for (unsigned i = 0; i < 256; i++) palette[i] = (uint16_t)((i * 2654435761u) >> 16);
  for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
    unsigned v;
    if (!strcmp(name, "flat")) v = 0;
    else if (!strcmp(name, "palette")) v = (x / 40 + y / 40) % 32;
    else if (!strcmp(name, "gradient")) v = (x * 100 / W) % ncolors;
    else if (!strcmp(name, "noise")) { seed = seed * 1103515245u + 12345u; v = (seed >> 16) % ncolors; }
    else v = (x + y) % ncolors;
    screen[y][x] = v;
  }
}

static int encode_one(const char *dir, const char *name, unsigned ncolors) {
  char path[512]; fill(name, ncolors);
  snprintf(path, sizeof path, "%s/%s.idx", dir, name); FILE *f = fopen(path, "wb"); fwrite(screen, 1, sizeof screen, f); fclose(f);
  snprintf(path, sizeof path, "%s/%s.png", dir, name); f = fopen(path, "wb");
  png_io_t io = { io_write, io_read, get_row, put_row, f, W, H, palette, ncolors, work, rowbuf };
  int ok = png_encode(&io); long size = ftell(f); fclose(f);
  printf("%-8s %s %ld bytes\n", name, ok ? "encoded" : "FAILED", size); return ok;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *dir = argv[1];
  if (!strcmp(argv[2], "encode")) {
    int ok = encode_one(dir, "flat", 1) & encode_one(dir, "palette", 32) & encode_one(dir, "gradient", 100)
           & encode_one(dir, "c256", 256) & encode_one(dir, "c300", 256) & encode_one(dir, "noise", 256);
    return ok ? 0 : 1;
  }
  if ((!strcmp(argv[2], "decode") || !strcmp(argv[2], "reject")) && argc > 3) {
    char path[512]; snprintf(path, sizeof path, "%s/%s.png", dir, argv[3]);
    FILE *f = fopen(path, "rb"); if (!f) return 2;
    png_io_t io = { io_write, io_read, get_row, put_row, f, W, H, palette, 0, work, rowbuf };
    const char *err = png_decode(&io); fclose(f);
    if (!strcmp(argv[2], "reject")) { printf("%s\n", err ? err : "accepted"); return err ? 0 : 1; }
    if (err) { printf("decode error: %s\n", err); return 1; }
    snprintf(path, sizeof path, "%s/%s.idx", dir, argv[3]); f = fopen(path, "rb"); if (fread(screen, 1, sizeof screen, f) != sizeof screen) return 2; fclose(f);
    int same = !memcmp(screen, decoded, sizeof screen); printf("%s\n", same ? "match" : "MISMATCH"); return same ? 0 : 1;
  }
  return 2;
}
