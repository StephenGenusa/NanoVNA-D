/*
 * PNG screenshot codec: indexed 8-bit PNG, fixed-Huffman deflate with a small LZ77 window,
 * and a bounded inflater for the on-device viewer. Pure include fragment driven through the
 * callbacks in png_io_t; no globals, no static RAM (the caller lends the workspace and the
 * row buffer). Included from ui.c under __SD_CARD_DUMP_PNG__; tests/host/png_host.c defines
 * PNG_HOST_TEST and includes it directly. See docs/manual/07-sd-card.md "Screenshots".
 *
 * Memory (bytes): encoder work = PNG_WINDOW ring + PNG_HASH*2 heads + PNG_OUT output buffer;
 * decoder work = PNG_WINDOW ring + PNG_IN input buffer. The row buffer (width bytes) is the
 * caller's. Matches never reach back more than PNG_WINDOW, so the decoder ring suffices.
 */
#ifdef PNG_HOST_TEST
#include <stdint.h>
#include <string.h>
#endif

typedef struct {
  unsigned (*write)(void *ctx, const void *data, unsigned len);   // return bytes written
  unsigned (*read)(void *ctx, void *data, unsigned len);          // return bytes read
  int (*get_row)(void *ctx, unsigned y, uint8_t *row);            // encoder: fill row[width] with palette indices
  int (*put_row)(void *ctx, unsigned y, const uint8_t *row);      // decoder: consume a decoded row
  void *ctx;
  unsigned width, height;
  uint16_t *palette;        // RGB565 in LCD order (config._lcd_palette format), 256 entries available
  unsigned  ncolors;        // encoder: entries in use (get_row may grow it); decoder: PLTE size
  uint8_t  *work;           // PNG_WORK_BYTES (encode) / PNG_DWORK_BYTES (decode)
  uint8_t  *row;            // width bytes
} png_io_t;

#define PNG_WINDOW      512                       // LZ77 window / inflate ring, power of two, >= row + 1 for row matches
#define PNG_HASH        256                       // hash heads, power of two
#define PNG_OUT         256                       // IDAT payload buffer
#define PNG_IN          256                       // decoder input buffer
#define PNG_WORK_BYTES  (PNG_WINDOW + PNG_HASH * 2 + PNG_OUT)
#define PNG_DWORK_BYTES (PNG_WINDOW + PNG_IN)

// ---------------------------------------------------------------- checksums (no tables)
static uint32_t png_crc32(uint32_t crc, const uint8_t *p, unsigned n) {
  crc = ~crc;
  while (n--) {
    crc ^= *p++;
    for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1)));
  }
  return ~crc;
}

static uint32_t png_adler32(uint32_t adler, const uint8_t *p, unsigned n) {
  uint32_t a = adler & 0xFFFF, b = adler >> 16;
  while (n--) { a += *p++; if (a >= 65521) a -= 65521; b += a; if (b >= 65521) b -= 65521; }
  return (b << 16) | a;
}

// ---------------------------------------------------------------- chunk writer
typedef struct { png_io_t *io; uint32_t crc; int ok; } png_chunk_t;

static void png_be32(uint8_t *p, uint32_t v) { p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v; }

static void png_chunk_begin(png_chunk_t *c, png_io_t *io, const char *tag, uint32_t len) {
  uint8_t h[8]; png_be32(h, len); memcpy(h + 4, tag, 4);
  c->io = io; c->ok &= io->write(io->ctx, h, 8) == 8;
  c->crc = png_crc32(0, h + 4, 4);
}
static void png_chunk_write(png_chunk_t *c, const uint8_t *p, unsigned n) {
  c->crc = png_crc32(c->crc, p, n); c->ok &= c->io->write(c->io->ctx, p, n) == n;
}
static void png_chunk_end(png_chunk_t *c) {
  uint8_t t[4]; png_be32(t, c->crc); c->ok &= c->io->write(c->io->ctx, t, 4) == 4;
}

// ---------------------------------------------------------------- deflate tables (RFC 1951)
static const uint16_t png_len_base[29]  = {3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258};
static const uint8_t  png_len_extra[29] = {0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
static const uint16_t png_dist_base[30] = {1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577};
static const uint8_t  png_dist_extra[30]= {0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};

// ---------------------------------------------------------------- encoder
typedef struct {
  png_io_t *io;
  uint8_t *out; unsigned outn;          // IDAT payload buffer
  uint32_t bits; unsigned nbits;        // LSB-first bit accumulator
  uint32_t adler;
  uint8_t *ring; uint16_t *head; uint32_t pos;   // LZ77: ring of emitted bytes, hash heads, absolute position
  int ok;
} png_enc_t;

static void png_flush_idat(png_enc_t *e) {
  if (!e->outn) return;
  png_chunk_t c = { e->io, 0, e->ok };
  png_chunk_begin(&c, e->io, "IDAT", e->outn); png_chunk_write(&c, e->out, e->outn); png_chunk_end(&c);
  e->ok = c.ok; e->outn = 0;
}
static void png_put_byte(png_enc_t *e, uint8_t b) {
  e->out[e->outn++] = b;
  if (e->outn == PNG_OUT) png_flush_idat(e);
}
static void png_put_bits(png_enc_t *e, uint32_t v, unsigned n) {      // n <= 16
  e->bits |= v << e->nbits; e->nbits += n;
  while (e->nbits >= 8) { png_put_byte(e, e->bits & 0xFF); e->bits >>= 8; e->nbits -= 8; }
}
static void png_align_byte(png_enc_t *e) { if (e->nbits) { png_put_byte(e, e->bits & 0xFF); e->bits = 0; e->nbits = 0; } }
static void png_put_rev(png_enc_t *e, uint32_t code, unsigned n) {    // Huffman codes go MSB first
  uint32_t r = 0; for (unsigned i = 0; i < n; i++) { r = (r << 1) | (code & 1); code >>= 1; }
  png_put_bits(e, r, n);
}
static void png_put_literal(png_enc_t *e, unsigned v) {                // fixed code: 0-143 -> 8 bits from 0x30, 144-255 -> 9 bits from 0x190
  if (v < 144) png_put_rev(e, 0x30 + v, 8); else png_put_rev(e, 0x190 + v - 144, 9);
}
static void png_put_symbol(png_enc_t *e, unsigned sym) {               // 256-279 -> 7 bits, 280-287 -> 8 bits from 0xC0
  if (sym < 280) png_put_rev(e, sym - 256, 7); else png_put_rev(e, 0xC0 + sym - 280, 8);
}
static void png_put_match(png_enc_t *e, unsigned len, unsigned dist) {
  unsigned i = 0; while (i < 28 && png_len_base[i + 1] <= len) i++;
  png_put_symbol(e, 257 + i); if (png_len_extra[i]) png_put_bits(e, len - png_len_base[i], png_len_extra[i]);
  unsigned d = 0; while (d < 29 && png_dist_base[d + 1] <= dist) d++;
  png_put_rev(e, d, 5);            if (png_dist_extra[d]) png_put_bits(e, dist - png_dist_base[d], png_dist_extra[d]);
}

#define PNG_RING(e, p) ((e)->ring[(p) & (PNG_WINDOW - 1)])

// Byte at absolute position p: emitted bytes live in the ring; the lookahead (>= base) in src
static inline uint8_t png_byte_at(png_enc_t *e, uint32_t p, uint32_t base, const uint8_t *src) {
  return p >= base ? src[p - base] : PNG_RING(e, p);
}

// Compress one buffer of scanline data; matches may reach back into earlier buffers via the ring
static void png_lz_feed(png_enc_t *e, const uint8_t *src, unsigned n) {
  uint32_t base = e->pos, stop = e->pos + n;
  while (e->pos < stop) {
    unsigned best = 0, bestd = 0;
    unsigned avail = stop - e->pos;
    if (avail >= 3) {
      const uint8_t *s = src + (e->pos - base);
      unsigned h = ((s[0] << 6) ^ (s[1] << 3) ^ s[2] ^ (s[0] * 31)) & (PNG_HASH - 1);
      uint32_t cand = e->head[h] | (e->pos & ~0xFFFFu);
      if (cand >= e->pos) cand -= 0x10000;                              // head holds the low 16 bits of a position
      uint32_t dist = e->pos - cand;
      if (cand < e->pos && dist <= PNG_WINDOW && e->head[h] != 0xFFFF) {
        unsigned len = 0, max = avail > 258 ? 258 : avail;
        while (len < max && png_byte_at(e, cand + len, base, src) == s[len]) len++;
        if (len >= 3) { best = len; bestd = dist; }
      }
      e->head[h] = e->pos & 0xFFFF;
    }
    unsigned step = best ? best : 1;
    if (best) png_put_match(e, best, bestd); else png_put_literal(e, src[e->pos - base]);
    for (unsigned k = 0; k < step; k++) {                                // consumed bytes enter the ring
      PNG_RING(e, e->pos) = src[e->pos - base];
      if (k && stop - e->pos >= 3) {                                      // keep heads fresh inside a match
        const uint8_t *s = src + (e->pos - base);
        e->head[((s[0] << 6) ^ (s[1] << 3) ^ s[2] ^ (s[0] * 31)) & (PNG_HASH - 1)] = e->pos & 0xFFFF;
      }
      e->pos++;
    }
  }
}

static int png_encode(png_io_t *io) {
  static const uint8_t sig[8] = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n'};
  png_enc_t e = { io, io->work + PNG_WINDOW + PNG_HASH * 2, 0, 0, 0, 1,
                  io->work, (uint16_t *)(io->work + PNG_WINDOW), 0, 1 };
  // pass 1: build the palette (get_row grows io->palette / io->ncolors as a side effect)
  for (unsigned y = 0; y < io->height; y++) if (!io->get_row(io->ctx, y, io->row)) return 0;
  e.ok &= io->write(io->ctx, sig, 8) == 8;
  uint8_t ihdr[13]; png_be32(ihdr, io->width); png_be32(ihdr + 4, io->height);
  ihdr[8] = 8; ihdr[9] = 3; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  png_chunk_t c = { io, 0, 1 };
  png_chunk_begin(&c, io, "IHDR", 13); png_chunk_write(&c, ihdr, 13); png_chunk_end(&c);
  png_chunk_begin(&c, io, "PLTE", io->ncolors * 3);
  for (unsigned i = 0; i < io->ncolors; i++) {
    uint32_t rgb = PNG_565_TO_RGB(io->palette[i]);
    uint8_t p[3] = { rgb >> 16, rgb >> 8, rgb }; png_chunk_write(&c, p, 3);
  }
  png_chunk_end(&c); e.ok &= c.ok;
  // pass 2: one fixed-Huffman deflate block for the whole image, IDAT chunks of PNG_OUT bytes
  memset(e.head, 0xFF, PNG_HASH * 2);
  png_put_byte(&e, 0x78); png_put_byte(&e, 0x01);
  png_put_bits(&e, 1, 1); png_put_bits(&e, 1, 2);                      // BFINAL=1, BTYPE=01
  for (unsigned y = 0; y < io->height; y++) {
    if (!io->get_row(io->ctx, y, io->row)) return 0;
    uint8_t filt = 0;
    e.adler = png_adler32(e.adler, &filt, 1); e.adler = png_adler32(e.adler, io->row, io->width);
    png_lz_feed(&e, &filt, 1);
    png_lz_feed(&e, io->row, io->width);
  }
  png_put_symbol(&e, 256);                                             // end of block
  png_align_byte(&e);
  uint8_t ad[4]; png_be32(ad, e.adler); for (int i = 0; i < 4; i++) png_put_byte(&e, ad[i]);
  png_flush_idat(&e);
  png_chunk_begin(&c, io, "IEND", 0); png_chunk_end(&c); e.ok &= c.ok;
  return e.ok;
}

// ---------------------------------------------------------------- decoder
typedef struct {
  png_io_t *io;
  uint8_t *in; unsigned inn, inp;       // input buffer over the IDAT payload stream
  uint32_t chunk_left;                   // payload bytes left in the current IDAT chunk
  int have_chunk;                        // inside an IDAT chunk (its CRC still to be skipped)
  uint32_t bits; unsigned nbits;
  uint8_t *ring; uint32_t pos;           // output ring and absolute output position
  unsigned rowp, y;
  int err;                               // 1 I/O or format, 2 filter, 3 unsupported
} png_dec_t;

static int png_skip(png_io_t *io, uint32_t n) {
  uint8_t s[16];
  while (n) { unsigned k = n > 16 ? 16 : n; if (io->read(io->ctx, s, k) != k) return 0; n -= k; }
  return 1;
}
static int png_next_idat(png_dec_t *d) {           // move to the next IDAT payload; 0 at IEND / error
  uint8_t h[8];
  for (;;) {
    if (d->have_chunk) { d->have_chunk = 0; if (!png_skip(d->io, 4)) return 0; }   // CRC of the chunk just consumed
    if (d->io->read(d->io->ctx, h, 8) != 8) return 0;
    uint32_t len = ((uint32_t)h[0] << 24) | (h[1] << 16) | (h[2] << 8) | h[3];
    if (!memcmp(h + 4, "IDAT", 4)) { d->chunk_left = len; d->have_chunk = 1; return 1; }
    if (!memcmp(h + 4, "IEND", 4)) return 0;
    if (!png_skip(d->io, len + 4)) return 0;
  }
}
static int png_in_byte(png_dec_t *d) {
  if (d->inp >= d->inn) {
    while (d->chunk_left == 0) if (!png_next_idat(d)) { d->err = 1; return 0; }
    unsigned n = d->chunk_left > PNG_IN ? PNG_IN : d->chunk_left;
    if (d->io->read(d->io->ctx, d->in, n) != n) { d->err = 1; return 0; }
    d->inn = n; d->inp = 0; d->chunk_left -= n;
  }
  return d->in[d->inp++];
}
static uint32_t png_get_bits(png_dec_t *d, unsigned n) {
  while (d->nbits < n) { d->bits |= (uint32_t)png_in_byte(d) << d->nbits; d->nbits += 8; }
  uint32_t v = d->bits & ((1u << n) - 1); d->bits >>= n; d->nbits -= n; return v;
}
static unsigned png_get_rev(png_dec_t *d, unsigned n) {               // Huffman code, MSB first
  unsigned v = 0; for (unsigned i = 0; i < n; i++) v = (v << 1) | png_get_bits(d, 1); return v;
}
static void png_out_byte(png_dec_t *d, uint8_t b) {
  d->ring[d->pos & (PNG_WINDOW - 1)] = b; d->pos++;
  if (d->rowp == 0) { if (b != 0) d->err = 2; d->rowp = 1; return; }    // scanline filter byte must be 0
  d->io->row[d->rowp++ - 1] = b;
  if (d->rowp == d->io->width + 1) {
    if (d->y >= d->io->height || !d->io->put_row(d->io->ctx, d->y, d->io->row)) d->err = 1;
    d->y++; d->rowp = 0;
  }
}
static unsigned png_fixed_litlen(png_dec_t *d) {                       // one fixed-Huffman literal/length symbol
  unsigned c = png_get_rev(d, 7);
  if (c <= 23) return 256 + c;
  c = (c << 1) | png_get_bits(d, 1);                                    // 8 bits
  if (c >= 48 && c <= 191) return c - 48;
  if (c >= 192 && c <= 199) return 280 + c - 192;
  c = (c << 1) | png_get_bits(d, 1);                                    // 9 bits (400-511)
  return 144 + c - 400;
}

static const char *png_decode(png_io_t *io) {
  uint8_t h[33];
  if (io->read(io->ctx, h, 33) != 33 || memcmp(h, "\x89PNG\r\n\x1a\n", 8) || memcmp(h + 12, "IHDR", 4)) return "Format err";
  uint32_t w = ((uint32_t)h[16] << 24) | (h[17] << 16) | (h[18] << 8) | h[19], ht = ((uint32_t)h[20] << 24) | (h[21] << 16) | (h[22] << 8) | h[23];
  if (w != io->width || ht != io->height || h[24] != 8 || h[25] != 3 || h[28] != 0) return "Unsupported PNG";
  png_dec_t d = { io, io->work + PNG_WINDOW, 0, 0, 0, 0, 0, 0, io->work, 0, 0, 0, 0 };
  for (;;) {                                                           // PLTE must precede IDAT
    if (io->read(io->ctx, h, 8) != 8) return "Format err";
    uint32_t len = ((uint32_t)h[0] << 24) | (h[1] << 16) | (h[2] << 8) | h[3];
    if (!memcmp(h + 4, "PLTE", 4)) {
      if (len % 3 || len > 768 || len == 0) return "Format err";
      io->ncolors = len / 3;
      for (unsigned i = 0; i < io->ncolors; i++) {
        uint8_t p[3]; if (io->read(io->ctx, p, 3) != 3) return "Format err";
        io->palette[i] = PNG_RGB_TO_565(p[0], p[1], p[2]);
      }
      if (!png_skip(io, 4)) return "Format err";
      break;
    }
    if (!memcmp(h + 4, "IDAT", 4) || !memcmp(h + 4, "IEND", 4)) return "Format err";
    if (!png_skip(io, len + 4)) return "Format err";
  }
  if (!png_next_idat(&d)) return "Format err";
  if (png_in_byte(&d) != 0x78) return "Unsupported PNG";
  png_in_byte(&d);                                                     // zlib FLG
  int final = 0;
  while (!final && !d.err) {
    final = png_get_bits(&d, 1); unsigned type = png_get_bits(&d, 2);
    if (type == 0) {                                                   // stored block
      d.bits = 0; d.nbits = 0;
      unsigned len = png_in_byte(&d); len |= png_in_byte(&d) << 8; png_in_byte(&d); png_in_byte(&d);
      while (len-- && !d.err) png_out_byte(&d, png_in_byte(&d));
    } else if (type == 1) {                                            // fixed Huffman
      for (;;) {
        unsigned sym = png_fixed_litlen(&d);
        if (d.err) break;
        if (sym < 256) { png_out_byte(&d, sym); continue; }
        if (sym == 256) break;
        unsigned li = sym - 257; if (li > 28) { d.err = 3; break; }
        unsigned len = png_len_base[li] + png_get_bits(&d, png_len_extra[li]);
        unsigned di = png_get_rev(&d, 5); if (di > 29) { d.err = 3; break; }
        unsigned dist = png_dist_base[di] + png_get_bits(&d, png_dist_extra[di]);
        if (dist > PNG_WINDOW || dist > d.pos) { d.err = 3; break; }
        while (len--) png_out_byte(&d, d.ring[(d.pos - dist) & (PNG_WINDOW - 1)]);
      }
    } else d.err = 3;                                                  // dynamic Huffman: not supported
  }
  if (d.err == 3) return "Unsupported PNG";
  if (d.err || d.y != io->height) return "Format err";
  return NULL;
}
