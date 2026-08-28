/*
 * SD-card guide viewer: paged CommonMark subset (docs/manual/07-sd-card.md "Guides").
 * Reference implementation and linter: tools/manual/guide.py - keep the rules identical.
 * Included from ui.c under __SD_GUIDES__; runs inside the browser's load callback, so it
 * owns spi_buffer for the duration and needs no static RAM.
 */
#pragma GCC push_options
#pragma GCC optimize ("Os")

#define GUIDE_CHUNK    256                     // SD read chunk
#define GUIDE_LINE     96                      // source line buffer
#define GUIDE_OUT      112                     // translated line (+ colour escapes)
#define GUIDE_ROWS     28                      // text rows below the header
#define GUIDE_MAXCOL   8
#define GUIDE_X        2
#define GUIDE_ROW_Y(r) (sFONT_STR_HEIGHT * ((r) + 1) + 1)
#define GUIDE_EMPH     LCD_TRACE_1_COLOR       // **emphasis**
#define GUIDE_HEAD     LCD_TRACE_2_COLOR       // headings, table header row

typedef struct { FIL *f; char *buf; UINT size, pos; DWORD chunk; } guide_rd_t;

static void guide_seek(guide_rd_t *r, DWORD ofs) { f_lseek(r->f, ofs); r->chunk = ofs; r->size = r->pos = 0; }
static DWORD guide_tell(guide_rd_t *r) { return r->chunk + r->pos; }

static int guide_getc(guide_rd_t *r) {
  if (r->pos >= r->size) {
    r->chunk += r->size;
    if (f_read(r->f, r->buf, GUIDE_CHUNK, &r->size) != FR_OK || r->size == 0) { r->size = 0; return -1; }
    r->pos = 0;
  }
  return (uint8_t)r->buf[r->pos++];
}

// One source line without CR/LF into line[]; returns length, or -1 at EOF with nothing read
static int guide_readline(guide_rd_t *r, char *line) {
  int n = 0, c = guide_getc(r);
  if (c < 0) return -1;
  while (c >= 0 && c != '\n') { if (c != '\r' && n < GUIDE_LINE - 1) line[n++] = c; c = guide_getc(r); }
  line[n] = 0;
  return n;
}

static bool guide_is_rule(const char *s) {
  if (s[0] != '-' || s[1] != '-' || s[2] != '-') return false;
  for (s += 3; *s; s++) if (*s != ' ') return false;
  return true;
}
static bool guide_is_fence(const char *s) { while (*s == ' ') s++; return s[0] == '`' && s[1] == '`' && s[2] == '`'; }

// Inline markup -> lcd_printf text with colour escapes; base = normal colour. Returns pixel width.
static int guide_inline(const char *s, char *out, uint8_t base) {
  int o = 0, w = 0; bool emph = false;
#define PUT(ch)  do { if (o < GUIDE_OUT - 3) { out[o++] = (ch); w += sFONT_GET_WIDTH((uint8_t)(ch)); } } while (0)
#define COLOR(c) do { if (o < GUIDE_OUT - 3) { out[o++] = R_FGCOLOR[0]; out[o++] = (c); } } while (0)
  while (*s) {
    uint8_t c = *s;
    if (c == '\\' && s[1]) { PUT(s[1]); s += 2; continue; }
    if (c == '`') { s++; continue; }
    if (c == '[') {                                          // [text](url) -> text
      const char *e = strchr(s, ']');
      if (e && e[1] == '(' && strchr(e, ')')) { for (s++; s < e; s++) PUT(*s); s = strchr(e, ')') + 1; continue; }
    }
    if (c == '*' || c == '_') {
      int len = (s[1] == c) ? 2 : 1;
      if (!emph) {
        const char *e = s + len;                             // closing marker on this line?
        while ((e = strchr(e, c)) != NULL && !(len == 1 || e[1] == c)) e++;
        if (e && e > s + len && s[len] != ' ' && e[-1] != ' ') { emph = true; COLOR(GUIDE_EMPH); s += len; continue; }
      } else if (o && out[o - 1] != ' ') { emph = false; COLOR(base); s += len; continue; }
      for (int i = 0; i < len; i++) PUT(c);
      s += len; continue;
    }
    if (c >= 0x80) {                                         // UTF-8: only Ohm, degree, micro are drawable
      uint8_t c2 = (uint8_t)s[1];
      if      (c == 0xCE && c2 == 0xA9) PUT(S_OHM[0]);
      else if (c == 0xC2 && c2 == 0xB0) PUT(S_DEGREE[0]);
      else if (c == 0xC2 && c2 == 0xB5) PUT(S_MICRO[0]);
      else if (c == 0xCE && c2 == 0xBC) PUT(S_MICRO[0]);
      else PUT('?');
      s++; while ((*s & 0xC0) == 0x80) s++;
      continue;
    }
    PUT(c); s++;
  }
  out[o] = 0;
  return w;
#undef PUT
#undef COLOR
}

// Split a table row into trimmed cells (in place); returns count (<= GUIDE_MAXCOL)
static int guide_cells(char *s, char *cell[]) {
  int n = 0; char *p = s + 1, *w = s + 1;                   // skip the leading '|'
  cell[n] = w;
  for (; *p; p++) {
    if (*p == '\\' && p[1] == '|') { *w++ = '|'; p++; }
    else if (*p == '|') { *w++ = 0; if (++n >= GUIDE_MAXCOL) break; cell[n] = w; }
    else *w++ = *p;
  }
  *w = 0;
  if (n < GUIDE_MAXCOL) n++;
  for (int i = 0; i < n; i++) {                              // trim
    while (*cell[i] == ' ') cell[i]++;
    char *e = cell[i] + strlen(cell[i]); while (e > cell[i] && e[-1] == ' ') *--e = 0;
  }
  if (n > 1 && cell[n - 1][0] == 0) n--;                     // trailing '|'
  return n;
}

static bool guide_is_sep(char *cell[], int n) {
  for (int i = 0; i < n; i++) {
    const char *c = cell[i];
    if (!*c) return false;
    for (; *c; c++) if (*c != '-' && *c != ':') return false;
  }
  return true;
}

// Draw a table whose first line starts at file offset `start`. Advances the reader past it and *row past its rows.
static void guide_table(guide_rd_t *r, DWORD start, char *line, char *out, int *row) {
  uint16_t width[GUIDE_MAXCOL] = {0}; uint8_t align[GUIDE_MAXCOL] = {0};   // 0 left, 1 right, 2 centre
  char *cell[GUIDE_MAXCOL]; int ncol = 0, rows = 0; bool sep = false;
  DWORD end;
  guide_seek(r, start);
  for (;;) {                                                  // pass 1: measure columns
    end = guide_tell(r);
    if (guide_readline(r, line) < 0 || line[0] != '|') break;
    int n = guide_cells(line, cell);
    if (rows == 1 && guide_is_sep(cell, n)) {
      sep = true;
      for (int i = 0; i < n; i++) { size_t l = strlen(cell[i]); align[i] = (cell[i][l - 1] == ':') ? (cell[i][0] == ':' ? 2 : 1) : 0; }
      continue;
    }
    for (int i = 0; i < n; i++) { int w = guide_inline(cell[i], out, LCD_FG_COLOR); if (w > width[i]) width[i] = w; }
    if (n > ncol) ncol = n;
    rows++;
  }
  guide_seek(r, start);
  int gutter = sFONT_GET_WIDTH(' '), x0[GUIDE_MAXCOL], x = GUIDE_X;
  for (int i = 0; i < ncol; i++) { x0[i] = x; x += width[i] + gutter; }
  int total = x - gutter - GUIDE_X, ri = 0;
  while (*row < GUIDE_ROWS && guide_tell(r) < end && guide_readline(r, line) >= 0) {  // pass 2: draw
    int n = guide_cells(line, cell);
    if (ri == 1 && sep) {                                     // separator row: a 1 px rule
      lcd_set_colors(LCD_FG_COLOR, LCD_FG_COLOR);
      lcd_fill(GUIDE_X, GUIDE_ROW_Y(*row) + sFONT_STR_HEIGHT / 2, total, 1);
      lcd_set_colors(LCD_FG_COLOR, LCD_BG_COLOR);
      (*row)++; ri++; continue;
    }
    uint8_t colour = (ri == 0) ? GUIDE_HEAD : LCD_FG_COLOR;
    lcd_set_colors(colour, LCD_BG_COLOR);
    for (int i = 0; i < n && i < ncol; i++) {
      int w = guide_inline(cell[i], out, colour);
      int cx = x0[i] + (align[i] == 1 ? width[i] - w : align[i] == 2 ? (width[i] - w) / 2 : 0);
      lcd_printf(cx, GUIDE_ROW_Y(*row), "%s", out);
    }
    (*row)++; ri++;
  }
  guide_seek(r, end);
  lcd_set_colors(LCD_FG_COLOR, LCD_BG_COLOR);
}

// Count pages (non-empty '---' sections); reports whether the first line is a '# ' title
static int guide_pages(guide_rd_t *r, char *line, bool *has_title) {
  guide_seek(r, 0);
  int pages = 0; bool content = false, first = true, fence = false;
  *has_title = false;
  while (guide_readline(r, line) >= 0) {
    if (first) { first = false; *has_title = line[0] == '#' && line[1] == ' '; if (*has_title) continue; }
    if (guide_is_fence(line)) { fence = !fence; content = true; continue; }
    if (!fence && guide_is_rule(line)) { if (content) pages++; content = false; continue; }
    content = true;
  }
  return pages + (content ? 1 : 0);
}

static void guide_draw_page(guide_rd_t *r, char *line, char *out, const char *title, int page, int pages) {
  lcd_set_font(FONT_SMALL);
  lcd_clear_screen();
  lcd_set_colors(LCD_MENU_TEXT_COLOR, LCD_MENU_COLOR);       // header bar
  lcd_fill(0, 0, LCD_WIDTH, sFONT_STR_HEIGHT);
  lcd_printf(GUIDE_X, 1, "%s", title);
  char pn[12]; int n = plot_printf(pn, sizeof(pn), "%d/%d", page, pages), pw = 0;
  for (int i = 0; i < n; i++) pw += sFONT_GET_WIDTH((uint8_t)pn[i]);
  lcd_printf(LCD_WIDTH - GUIDE_X - pw, 1, "%s", pn);
  lcd_set_colors(LCD_FG_COLOR, LCD_BG_COLOR);
  // seek to the first line of the wanted page
  guide_seek(r, 0);
  int p = 1; bool content = false, fence = false, first = true;
  DWORD pos = 0;
  for (;;) {
    pos = guide_tell(r);
    if (guide_readline(r, line) < 0) { pos = guide_tell(r); break; }
    if (first) { first = false; if (line[0] == '#' && line[1] == ' ') continue; }
    if (!fence && guide_is_rule(line)) { if (content) p++; content = false; continue; }
    if (guide_is_fence(line)) fence = !fence;
    if (p == page) break;                                    // this line starts the page
    content = true;
  }
  guide_seek(r, pos);
  int row = 0; fence = false;
  while (row < GUIDE_ROWS) {
    DWORD lpos = guide_tell(r);
    if (guide_readline(r, line) < 0) break;
    if (guide_is_fence(line)) { fence = !fence; continue; }
    if (fence) { lcd_printf(GUIDE_X, GUIDE_ROW_Y(row++), "%s", line); continue; }
    if (guide_is_rule(line)) break;
    if (line[0] == '|') { guide_table(r, lpos, line, out, &row); continue; }
    if (line[0] == 0) { row++; continue; }
    if (line[0] == '#') {
      const char *s = line; while (*s == '#') s++; while (*s == ' ') s++;
      lcd_set_colors(GUIDE_HEAD, LCD_BG_COLOR); guide_inline(s, out, GUIDE_HEAD);
      lcd_printf(GUIDE_X, GUIDE_ROW_Y(row++), "%s", out);
      lcd_set_colors(LCD_FG_COLOR, LCD_BG_COLOR); continue;
    }
    guide_inline(line, out, LCD_FG_COLOR);
    lcd_printf(GUIDE_X, GUIDE_ROW_Y(row++), "%s", out);
  }
  lcd_set_font(FONT_NORMAL);
}

static FILE_LOAD_CALLBACK(load_guide) {
  (void)format;
  char *buf = (char *)spi_buffer;                            // chunk | line | out | title, all inside spi_buffer
  char *line = buf + GUIDE_CHUNK, *out = line + GUIDE_LINE, *title = out + GUIDE_OUT;
  guide_rd_t rd = { f, buf, 0, 0, 0 };
  bool has_title;
  int pages = guide_pages(&rd, line, &has_title), page = 1;
  if (has_title) { guide_seek(&rd, 0); guide_readline(&rd, line); guide_inline(line + 2, title, LCD_MENU_TEXT_COLOR); }
  else plot_printf(title, GUIDE_OUT, "%s", fno->fname);
  if (pages < 1) pages = 1;
  for (;;) {                                                 // the tap that opened the file may still be down
    int s = touch_check();
    if (s == EVT_TOUCH_NONE || s == EVT_TOUCH_RELEASED) break;
  }
  btn_check();                                               // drop the click that opened the file
  for (;;) {
    guide_draw_page(&rd, line, out, title, page, pages);
    for (;;) {                                               // wait for an event that changes the page
      int key = -1;
      uint16_t status = btn_check();
      if (status & EVT_UP)   key = 1;
      if (status & EVT_DOWN) key = 0;
      if (status & EVT_BUTTON_SINGLE_CLICK) key = 2;
      status = touch_check();
      if (status == EVT_TOUCH_PRESSED || status == EVT_TOUCH_DOWN) {
        int tx, ty; touch_position(&tx, &ty);
        key = (ty < sFONT_STR_HEIGHT * 2) ? 2 : (tx < LCD_WIDTH / 2 ? 0 : 1);
        touch_wait_release();
      }
      if (key == 2) goto done;
      if (key == 1 && page < pages) { page++; break; }
      if (key == 0 && page > 1)     { page--; break; }
      delayMilliseconds(20);
    }
  }
done:
  lcd_clear_screen();
  return NULL;
}

#pragma GCC pop_options
