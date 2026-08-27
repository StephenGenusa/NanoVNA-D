# PNG screenshots on the NanoVNA-H4 — design

Status: Approved 2026-08-27 (design agreed in conversation; this file records it).

## Purpose

Replace TIFF as the H4's compact screenshot format with PNG — indexed 8-bit, compressed —
that opens anywhere and is smaller than the current TIFF PackBits output. Keep the on-device
screenshot viewer working for the new format. Keep the TIFF code in the tree, off by default
on the H4. The H is unchanged (BMP + TIFF; no flash for PNG).

Measured baseline: TIFF support costs 700 B (H) / 668 B (H4); BMP save+load ≈ 400 B.
H4 flash headroom ≈ 160 KB; H4 main SRAM is essentially full (bss 40,720 B), so PNG must not
add static RAM.

## Build flags and format selection

- `__SD_CARD_DUMP_PNG__` — defined only under `#if defined(NANOVNA_F303)`.
- `__SD_CARD_DUMP_TIFF__` — stays defined for F072; for F303 it becomes a commented-out opt-in.
- `#error` if both `__SD_CARD_DUMP_PNG__` and `__SD_CARD_DUMP_TIFF__` are defined: the format
  selector is one persisted bit (`VNA_MODE_TIFF`), and a build has BMP plus exactly one of
  PNG/TIFF.
- The `VNA_MODE_TIFF` bit is reused unchanged in `config_t`. With PNG built in, its menu label
  is `BMP\0PNG` and `fixScreenshotFormat()` maps `FMT_BMP_FILE` → `FMT_PNG_FILE` when the bit
  is set. Existing H4 users with the bit set therefore get PNG on first save after flashing —
  intended, documented in the README.
- `FMT_PNG_FILE` is added to the save/load format enum right after `FMT_BMP_FILE`, under its
  own guard, mirroring how `FMT_TIF_FILE` is placed, with a matching `KM_PNG_NAME` keypad entry
  in the same position (the two enums must stay in lockstep — see the existing
  `// Must be equal to Save/Load format enum` comment in `ui.c`). `file_opt[FMT_PNG_FILE] =
  FILE_OPTIONS("png", save_png, load_png, FILE_OPT_REDRAW | FILE_OPT_CONTINUE)`. The browser's
  LOAD SCREENSHOT entry already routes through `fixScreenshotFormat`, so it lists `.png` files
  when PNG is the active format (and `.bmp` otherwise), matching today's BMP/TIFF behaviour.

## Encoder (`save_png`)

Output: PNG signature; `IHDR` (width = `LCD_WIDTH`, height = `LCD_HEIGHT`, bit depth 8,
colour type 3 indexed, compression 0, filter 0, interlace 0); `PLTE`; one or more `IDAT`;
`IEND`. Every chunk carries its CRC-32.

Pixels: rows are read back from the LCD as RGB565 exactly as `save_bmp` does (row buffer in
`spi_buffer`). Each pixel is mapped to a palette index by exact match against a dynamic palette
seeded from `config._lcd_palette` (up to `MAX_PALETTE` = 32 entries) and grown on a miss, up to
256 entries; a 257th distinct colour maps to the nearest existing entry (never fails the save).
The palette is written as `PLTE` after the pixel data has been scanned — so the encoder makes
two passes over the screen: pass 1 builds the palette (no output), pass 2 encodes. Two LCD
reads are acceptable (a save already takes on the order of a second); it avoids buffering a
PLTE we cannot finalise before the first IDAT.

Scanline format: filter byte 0 followed by `LCD_WIDTH` index bytes.

Compression: a zlib stream (header `0x78 0x01`, Adler-32 trailer) of deflate blocks using
**fixed Huffman codes** only, with LZ77 matching:
- input window = the last `W` bytes of scanline data, `W` a power of two chosen from the RAM
  budget below (target 1024 — two H4 rows — minimum 512);
- 3-byte hash into a head table of `H` entries (target 512), no chains — one candidate per
  hash, verified by comparison;
- match length 3..258, distance 1..W; literals otherwise;
- one block per IDAT chunk, or the whole image in one block with IDAT split at buffer
  boundaries (the bit stream is continuous across IDAT chunks — the plan picks whichever is
  simpler; both are valid PNG).

CRC-32: bit-serial implementation, no table (≈40 B code; ~0.1 s for a 150 KB stream at
72 MHz). Adler-32 maintained over the uncompressed scanline data.

IDAT chunking: an output buffer of `O` bytes (target 1024) in `spi_buffer`; when full, the
chunk is written as length, `IDAT`, data, CRC. The final chunk flushes the remainder.

## Decoder (`load_png`)

Accepts only what the encoder writes plus the obvious neighbours: signature; `IHDR` with
colour type 3, bit depth 8, no interlace, width/height equal to the LCD; `PLTE` (1..256
entries, converted to RGB565 on load); any number of `IDAT` chunks concatenated; `IEND`.
Other chunks are skipped by length. CRCs are not verified on load (the file came from us or
the user's PC; corruption shows as garbage, as with BMP today).

Inflate: zlib header check; stored blocks and fixed-Huffman blocks only; a dynamic-Huffman
block (BTYPE 2) or a back-reference distance greater than `W` returns an "unsupported PNG"
result and the browser shows its existing bad-file message. Output ring of `W` bytes plus one
assembled scanline; each completed scanline is translated through the palette to RGB565 and
sent to the LCD with the same bulk path `load_bmp` uses. Consequence, documented: PNGs from
other tools generally do not open on the device (they use dynamic Huffman and 32 KB windows).

## RAM budget

No new static allocation. All working memory lives in `spi_buffer` (4096 B) during a
save/load. FatFS keeps `FATFS` (572 B) and `FIL` (592 B) at the tail of `spi_buffer` while a
file is open (`fs_volume`/`fs_file` in `nanovna.h`), leaving **2,932 B** usable.

Encoder layout (target): LCD row buffer as indices 480 B (the RGB565 row is read into the
same region and converted in place, reading 16-bit values from the end backwards so the
1-byte indices never overrun unread pixels) + window 1024 B + hash heads 512 × 2 B = 1024 B +
output buffer 384 B = 2,912 B. If `W`/`H`/`O` must shrink, the order is: output buffer to
256 B, then hash heads to 256 entries, then window to 512 B. Decoder layout: window 1024 B +
scanline 480 B + input buffer 512 B + palette 256 × 2 B = 2,504 B.

The plan verifies the split with `_Static_assert`s against `SPI_BUFFER_SIZE*2 - sizeof(FATFS)
- sizeof(FIL)` so a future FatFS configuration change fails the build rather than corrupting
the file system objects.

## Files

- `vna_modules/vna_png.c` — encoder and decoder as an include fragment; pure functions over an
  I/O callback pair (`write(const void*, size)` / `read(void*, size)`) and a `rowsource`
  callback, so the host test can drive them without FatFS or an LCD. Guarded `PNG_HOST_TEST`
  provides the typedefs.
- `ui.c` — `save_png`/`load_png` wrappers (LCD read/write + FatFS I/O), `FMT_PNG_FILE`,
  `KM_PNG_NAME`, `file_opt` entry, `fixScreenshotFormat`, `vna_mode_data` label `BMP\0PNG`.
- `nanovna.h` — flags, `#error` guard, enum placement.
- `README.md` — feature paragraph and caveats (H4 only; viewer opens device-written PNGs;
  TIFF opt-in on H4; users with the TIFF bit set now get PNG; file sizes).

## Testing

- `tests/test_png.c` (host, gcc): encodes synthetic screens through the fragment — flat colour,
  the real default palette, a gradient forcing palette growth, exactly 256 colours, 300
  colours (nearest-match path), and a worst-case noise screen (no matches; output must stay a
  valid stream and under 1.5× raw size) — writing each PNG to a temp file; then decodes each
  with the fragment's own inflate and asserts pixel-exact round trip.
- `tests/check_png.py` (Python 3, stdlib): opens each file, verifies chunk CRCs, inflates the
  IDAT stream with `zlib`, checks IHDR/PLTE and that the decoded indices equal the source. A
  Python-generated PNG (dynamic Huffman) must be rejected cleanly by the C decoder.
- Mutation checks before trusting the tests: corrupt a CRC byte → checker fails; raise the
  encoder's match distance above `W` → C decoder rejects.
- Target: both builds; H4 delta expected 3–4 KB, H unchanged. Hardware: save a screenshot on
  the H4, open it from the browser, open the same file on a PC, compare file size with a TIFF
  of the same screen (opt-in build).

## Out of scope

True-colour or 16-bit PNG, scanline filters other than 0, interlacing, dynamic Huffman in
either direction, PNG on the H, changes to the USB `capture` (RLE8) protocol, zlib/CRC tables
in flash.
