/* Host harness for vna_modules/vna_guide.c: runs the real viewer code over a file with the
 * FatFs / LCD / input layers stubbed, printing every drawn page as text. Used by
 * tests/test_guides.py (HostViewerTests) to check the C against guide.py.
 *   gcc -std=c11 -I. -o guide_host tests/host/guide_host.c && ./guide_host FILE [keys]
 * keys: string of 'n' (wheel up = next), 'p' (down = previous), 'x' (click = exit); default "nnnnnnnnnnx".
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>

typedef unsigned UINT; typedef uint32_t DWORD; typedef char TCHAR;
typedef struct { const uint8_t *data; size_t len, pos; } FIL;
typedef struct { char fname[64]; } FILINFO;
typedef enum { FR_OK = 0, FR_ERR } FRESULT;
static FRESULT f_read(FIL *f, void *buf, UINT n, UINT *rd) {
  size_t left = f->len - f->pos; if (n > left) n = left;
  memcpy(buf, f->data + f->pos, n); f->pos += n; *rd = n; return FR_OK;
}
static FRESULT f_lseek(FIL *f, DWORD ofs) { f->pos = ofs > f->len ? f->len : ofs; return FR_OK; }

#define LCD_WIDTH 480
#define sFONT_STR_HEIGHT 11
#define sFONT_GET_WIDTH(ch) 7
enum { LCD_BG_COLOR = 0, LCD_FG_COLOR, LCD_GRID_COLOR, LCD_MENU_COLOR, LCD_MENU_TEXT_COLOR, LCD_MENU_ACTIVE_COLOR,
       LCD_TRACE_1_COLOR, LCD_TRACE_2_COLOR };
#define R_FGCOLOR "\x02"
#define S_OHM "\x1E"
#define S_DEGREE "\x1F"
#define S_MICRO "\x1D"
enum { FONT_SMALL = 0, FONT_NORMAL };
#define EVT_BUTTON_SINGLE_CLICK 0x01
#define EVT_UP 0x10
#define EVT_DOWN 0x20
#define EVT_TOUCH_NONE 0
#define EVT_TOUCH_DOWN 1
#define EVT_TOUCH_PRESSED 2
#define EVT_TOUCH_RELEASED 3
#define FILE_LOAD_CALLBACK(name) const char *name(FIL *f, FILINFO *fno, uint8_t format)
static uint16_t spi_buffer[2048];
#define fs_file ((FIL *)((uint8_t *)spi_buffer + sizeof spi_buffer - sizeof(FIL)))

static int cur_page = 0;
static void lcd_set_font(int t) { (void)t; }
static void lcd_set_colors(uint16_t fg, uint16_t bg) { (void)fg; (void)bg; }
static void lcd_clear_screen(void) { printf("=== page draw %d\n", ++cur_page); }
static void lcd_fill(int x, int y, int w, int h) { if (h == 1) printf("%3d: <rule x=%d w=%d>\n", y, x, w); }
static int lcd_printf(int x, int y, const char *fmt, ...) {
  char s[256]; va_list ap; va_start(ap, fmt); int n = vsnprintf(s, sizeof s, fmt, ap); va_end(ap);
  printf("%3d @%-3d |", y, x);
  for (char *p = s; *p; p++) {
    if ((uint8_t)*p == 2) { printf("{c%d}", (uint8_t)p[1]); p++; }
    else if ((uint8_t)*p == 0x1E) printf("Ω"); else if ((uint8_t)*p == 0x1F) printf("°"); else if ((uint8_t)*p == 0x1D) printf("µ");
    else putchar(*p);
  }
  putchar('\n'); return n;
}
static int plot_printf(char *str, int size, const char *fmt, ...) { va_list ap; va_start(ap, fmt); int n = vsnprintf(str, size, fmt, ap); va_end(ap); return n; }
static const char *keys = "nnnnnnnnnnx"; static int ki = 0;
static uint16_t btn_check(void) {
  char k = keys[ki] ? keys[ki++] : 'x';
  return k == 'n' ? EVT_UP : k == 'p' ? EVT_DOWN : EVT_BUTTON_SINGLE_CLICK;
}
static int touch_check(void) { return EVT_TOUCH_NONE; }
static void touch_position(int *x, int *y) { *x = *y = 0; }
static void touch_wait_release(void) {}
static void delayMilliseconds(uint32_t ms) { (void)ms; }

#include "vna_modules/vna_guide.c"

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  if (argc > 2) keys = argv[2];
  FILE *fp = fopen(argv[1], "rb"); if (!fp) return 2;
  static uint8_t data[65536]; size_t len = fread(data, 1, sizeof data, fp); fclose(fp);
  FIL f = { data, len, 0 }; FILINFO fno; snprintf(fno.fname, sizeof fno.fname, "%s", argv[1]);
  load_guide(&f, &fno, 0);
  return 0;
}
