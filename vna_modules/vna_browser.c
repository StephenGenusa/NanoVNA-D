/*
 * Copyright (c) 2019-2023, Dmitry (DiSlord) dislordlive@gmail.com
 * All rights reserved.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * The software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Radio; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */
static uint16_t file_count;
static uint16_t page_count;
static uint16_t current_page;
static uint16_t browser_mode;

#define BROWSER_DELETE    1

static void browser_draw_page(int page);

#ifdef __SD_BROWSER_FOLDERS__
// Folder navigation up to BROWSER_DEPTH_MAX levels deep (see issue #76). Depth 0 = card root.
// The browser never holds a listing: it re-walks one directory per draw, so depth only costs
// the folder names and the joined path below. Name size matches FILINFO.fname (8.3 or LFN).
#ifndef BROWSER_DEPTH_MAX
#define BROWSER_DEPTH_MAX  2
#endif
#define BROWSER_NAME_SIZE  sizeof(((FILINFO*)0)->fname)
static char    browser_dir[BROWSER_DEPTH_MAX][BROWSER_NAME_SIZE];      // folder name at each level
static uint8_t browser_depth;                                          // 0..BROWSER_DEPTH_MAX
static char    browser_dirpath[BROWSER_DEPTH_MAX * BROWSER_NAME_SIZE]; // "a/b" for f_opendir
#define BROWSER_IN_FOLDER  (browser_depth != 0)
#define BROWSER_DIR        browser_dirpath
// Rebuild the joined directory path from the level names
static void browser_join_path(void) {
  int n = 0;
  browser_dirpath[0] = 0;
  for (int i = 0; i < browser_depth; i++)
    n += plot_printf(browser_dirpath + n, sizeof(browser_dirpath) - n, i ? "/%s" : "%s", browser_dir[i]);
}
// Prefix name with the current directory for f_open / f_unlink
static const char *browser_path(const char *name) {
  static char path[(BROWSER_DEPTH_MAX + 1) * BROWSER_NAME_SIZE + 1];
  if (!BROWSER_IN_FOLDER) return name;
  plot_printf(path, sizeof(path), "%s/%s", browser_dirpath, name);
  return path;
}
// Enter folder (name) or go up one level (name == NULL), redraw first page
static void browser_goto_folder(const char *name) {
  if (name) { if (browser_depth < BROWSER_DEPTH_MAX) plot_printf(browser_dir[browser_depth++], BROWSER_NAME_SIZE, "%s", name); }
  else if (browser_depth) browser_depth--;
  browser_join_path();
  file_count = 0;
  current_page = 1;
  selection = -1;
  browser_draw_page(current_page);
}
// Open the browser at a given first-level folder ("" or NULL = root)
static void browser_set_folder(const char *name) {
  browser_depth = 0;
  if (name && name[0]) { plot_printf(browser_dir[0], BROWSER_NAME_SIZE, "%s", name); browser_depth = 1; }
  browser_join_path();
}
// NEW folder: the browser hands off to the text keypad (KM_FOLDER_NAME) and comes back to the same
// folder afterwards, on DONE (mkdir), CANCEL, or an empty name.
static uint8_t browser_format;        // file format the browser was opened with (keypad_mode is reused by the keypad)
static bool    browser_reopen;        // set while the keypad is up; ui_mode_browser() then keeps the folder
UI_KEYBOARD_CALLBACK(input_foldername) {
  (void)data;
  if (b) return;
  if (kp_buf[0] == 0) return;                                          // empty name = cancel
  FRESULT res = f_mkdir(browser_path(kp_buf));
  if (res != FR_OK) ui_message_box("NEW FOLDER", res == FR_EXIST ? "Already exists" : "Fail", 2000);
}
void ui_mode_browser(int mode);
static void browser_reopen_after_keypad(void) {
  ui_mode = UI_NORMAL;                                                 // let ui_mode_browser() run
  ui_mode_browser(browser_format);
}
// browser_open_file returns true if browser must close after processing
typedef bool browser_ret_t;
#define BROWSER_DONE(close) return close
#else
#define BROWSER_DIR ""
#define browser_path(name) (name)
typedef void browser_ret_t;
#define BROWSER_DONE(close) return
#endif

// Buttons in browser
enum {FILE_BUTTON_LEFT = 0, FILE_BUTTON_RIGHT, FILE_BUTTON_EXIT, FILE_BUTTON_DEL,
#ifdef __SD_BROWSER_FOLDERS__
      FILE_BUTTON_NEW,
#endif
      FILE_BUTTON_FILE};

#define SMALL_BUTTON_SIZE    FONT_STR_WIDTH(6)
// Button position on screen
typedef struct  {
  uint16_t x;
  uint16_t y;
  uint16_t w;
  uint8_t  h;
  uint8_t  ofs;
} browser_btn_t;
static const browser_btn_t browser_btn[] = {
#ifdef __SD_BROWSER_FOLDERS__
  [FILE_BUTTON_LEFT] = {         0  + 2*SMALL_BUTTON_SIZE, LCD_HEIGHT - FILE_BOTTOM_HEIGHT, LCD_WIDTH/2 - 3*SMALL_BUTTON_SIZE, FILE_BOTTOM_HEIGHT, (LCD_WIDTH/2 - 3*SMALL_BUTTON_SIZE - FONT_WIDTH)/2}, // < previous
  [FILE_BUTTON_NEW]  = {         0  +   SMALL_BUTTON_SIZE, LCD_HEIGHT - FILE_BOTTOM_HEIGHT,                 SMALL_BUTTON_SIZE, FILE_BOTTOM_HEIGHT, (              SMALL_BUTTON_SIZE - 3*FONT_WIDTH)/2}, // NEW folder
#else
  [FILE_BUTTON_LEFT] = {         0  + SMALL_BUTTON_SIZE, LCD_HEIGHT - FILE_BOTTOM_HEIGHT, LCD_WIDTH/2 - 2*SMALL_BUTTON_SIZE, FILE_BOTTOM_HEIGHT, (LCD_WIDTH/2 - 2*SMALL_BUTTON_SIZE - FONT_WIDTH)/2}, // < previous
#endif
  [FILE_BUTTON_RIGHT]= {LCD_WIDTH/2 + SMALL_BUTTON_SIZE, LCD_HEIGHT - FILE_BOTTOM_HEIGHT, LCD_WIDTH/2 - 2*SMALL_BUTTON_SIZE, FILE_BOTTOM_HEIGHT, (LCD_WIDTH/2 - 2*SMALL_BUTTON_SIZE - FONT_WIDTH)/2}, // > next
  [FILE_BUTTON_EXIT] = {LCD_WIDTH   - SMALL_BUTTON_SIZE, LCD_HEIGHT - FILE_BOTTOM_HEIGHT,                 SMALL_BUTTON_SIZE, FILE_BOTTOM_HEIGHT, (                SMALL_BUTTON_SIZE - FONT_WIDTH)/2}, // X exit
  [FILE_BUTTON_DEL]  = {         0  +                 0, LCD_HEIGHT - FILE_BOTTOM_HEIGHT,                 SMALL_BUTTON_SIZE, FILE_BOTTOM_HEIGHT, (              SMALL_BUTTON_SIZE - 3*FONT_WIDTH)/2}, // DEL
  // File button, only size and start position, must be idx = FILE_BUTTON_FILE
  [FILE_BUTTON_FILE] = {                              0,                               0,           LCD_WIDTH/FILES_COLUMNS, FILE_BUTTON_HEIGHT,                                   FONT_WIDTH/2 + 3},
};

static void browser_get_button_pos(int idx, browser_btn_t *b) {
  int n = idx >= FILE_BUTTON_FILE ? FILE_BUTTON_FILE : idx;
#if 0
  memcpy(b, &browser_btn[n], sizeof(browser_btn_t));
#else
  b->x = browser_btn[n].x;
  b->y = browser_btn[n].y;
  b->w = browser_btn[n].w;
  b->h = browser_btn[n].h;
  b->ofs = browser_btn[n].ofs;
#endif
  if (idx > FILE_BUTTON_FILE) { // for file buttons use multiplier from start offset
    idx-= FILE_BUTTON_FILE;
    b->x+= b->w * (idx / FILES_ROWS);
    b->y+= b->h * (idx % FILES_ROWS);
  }
}

static void browser_draw_button(int idx, const char *txt) {
  if (idx < 0) return;
  button_t b;
  browser_btn_t btn;
  browser_get_button_pos(idx, &btn);
  // Mark DEL button in file delete mode
  b.bg = (idx == FILE_BUTTON_DEL && (browser_mode & BROWSER_DELETE)) ? LCD_LOW_BAT_COLOR : LCD_MENU_COLOR;
  b.fg = LCD_MENU_TEXT_COLOR;
  b.border = (idx == selection) ? BROWSER_BUTTON_BORDER|BUTTON_BORDER_FALLING : BROWSER_BUTTON_BORDER|BUTTON_BORDER_RISE;
  if (txt == NULL) b.border|= BUTTON_BORDER_NO_FILL;
  ui_draw_button(btn.x, btn.y, btn.w, btn.h, &b);
  if (txt) lcd_printf(btn.x + btn.ofs, btn.y + (btn.h - FONT_STR_HEIGHT) / 2, txt);
}

static char ext_lower(char c) {return (c >= 'A' && c <= 'Z') ? c - 'A' + 'a' : c;}
static bool compare_ext(const char *name, const char *ext) {
  int i = 0, j = 0;
  while (name[i]) if (name[i++] == '.') j = i;    // Get last '.' position + 1
  if (j == 0) return false;
  // ext is a '|' separated list of allowed extensions (e.g. "cmd|nvs"), compare case insensitive
  for (i = j;; ext++) {
    char c = (*ext == '|') ? 0 : *ext;            // '|' terminates one list entry
    if (ext_lower(name[i]) != ext_lower(c)) {     // mismatch: skip to next list entry
      while (*ext && *ext != '|') ext++;
      if (*ext == 0) return false;                // list exhausted
      i = j;                                      // for's ext++ moves past the '|'
    } else {
      if (c == 0) return true;                    // full entry matched
      i++;
    }
  }
}

static FRESULT sd_findnext(DIR* dp, FILINFO* fno) {
  while (f_readdir(dp, fno) == FR_OK && fno->fname[0]) {
    if (fno->fattrib & AM_DIR) {
#ifdef __SD_BROWSER_FOLDERS__
      if (browser_depth < BROWSER_DEPTH_MAX) return FR_OK; // list folders while another level can be entered
#endif
      continue;
    }
    if (compare_ext(fno->fname, dp->pat)) return FR_OK;
//#if FF_USE_LFN && FF_USE_FIND == 2
//    if (compare_ext(fno->altname, dp->pat)) return FR_OK;
//#endif
  }
  return FR_NO_FILE;
}

static FRESULT sd_open_dir(DIR* dp, const TCHAR* path, const TCHAR* pattern) {
  dp->pat = pattern;
  return f_opendir(dp, path);
}

static browser_ret_t browser_open_file(int sel) {
  FILINFO fno;
  DIR dj;
  int cnt;
  if ((uint16_t)sel >= file_count) BROWSER_DONE(true);
  if (f_mount(fs_volume, "", 1) != FR_OK) BROWSER_DONE(true);
#ifdef __SD_BROWSER_FOLDERS__
  if (BROWSER_IN_FOLDER) {
    if (sel == 0) { // virtual '..' entry: up one level (ignored in delete mode)
      if (!(browser_mode & BROWSER_DELETE)) browser_goto_folder(NULL);
      return false;
    }
    sel--;          // walk entries skip the virtual '..'
  }
#endif
repeat:
  cnt = sel;
  if (sd_open_dir(&dj, BROWSER_DIR, file_opt[keypad_mode].ext) != FR_OK) BROWSER_DONE(true); // open dir
  while (sd_findnext(&dj, &fno) == FR_OK && cnt != 0) cnt--;             // skip cnt files
  f_closedir(&dj);
  if (cnt != 0) BROWSER_DONE(true);
#ifdef __SD_BROWSER_FOLDERS__
  if (fno.fattrib & AM_DIR) { // folder selected: enter it (ignored in delete mode)
    if (!(browser_mode & BROWSER_DELETE)) browser_goto_folder(fno.fname);
    return false;
  }
#endif

  // Delete file if in delete mode
  if (browser_mode & BROWSER_DELETE) {f_unlink(browser_path(fno.fname)); BROWSER_DONE(true);}

  // Load file, get load function
  file_load_cb_t load = file_opt[keypad_mode].load;
  if (load == NULL) BROWSER_DONE(true);
  //
  lcd_set_colors(LCD_FG_COLOR, LCD_BG_COLOR);

  if (f_open(fs_file, browser_path(fno.fname), FA_READ) != FR_OK) BROWSER_DONE(true);
  //  START_PROFILE;
  const char *error = load(fs_file, &fno, keypad_mode);
  f_close(fs_file);
  //  STOP_PROFILE;
  // Check, need continue load next or previous file
  bool need_continue = file_opt[keypad_mode].opt & FILE_OPT_CONTINUE;
  if (error) {
    lcd_clear_screen();
    ui_message_box(error, fno.fname, need_continue ? 100 : 2000);
  }
  if (!need_continue) BROWSER_DONE(true);

  // Process input
  while (1) {
    uint16_t status = btn_check();
    int key = -1;
    if (status & EVT_DOWN) key = 0;
    if (status & EVT_UP  ) key = 1;
    if (status & EVT_BUTTON_SINGLE_CLICK) key = 2;

    status = touch_check();
    if (status == EVT_TOUCH_PRESSED || status == EVT_TOUCH_DOWN) {
      int touch_x, touch_y;
      touch_position(&touch_x, &touch_y);
           if (touch_x < LCD_WIDTH *1/3) key = 0;
      else if (touch_x < LCD_WIDTH *2/3) key = 2;
      else                               key = 1;
      touch_wait_release();
    }
    //chThdSleepMilliseconds(100); // Device hang after ~2min in this place, not switch thread back
    delayMilliseconds(100);
    int old_sel = sel;
    int last_sel = file_count - 1;
#ifdef __SD_BROWSER_FOLDERS__
    if (BROWSER_IN_FOLDER) last_sel--; // sel is walk-space here, file_count includes virtual '..'
#endif
         if (key == 0) {if (--sel < 0) sel = last_sel;}
    else if (key == 1) {if (++sel > last_sel) sel = 0;}
    else if (key == 2) break;
    if (old_sel != sel) goto repeat;
  }
  BROWSER_DONE(true);
}

static void browser_draw_buttons(void) {
  browser_draw_button(FILE_BUTTON_DEL, "DEL");
#ifdef __SD_BROWSER_FOLDERS__
  browser_draw_button(FILE_BUTTON_NEW, browser_depth < BROWSER_DEPTH_MAX ? "NEW" : "");
#endif
  browser_draw_button(FILE_BUTTON_LEFT,  "<");
  browser_draw_button(FILE_BUTTON_RIGHT, ">");
  browser_draw_button(FILE_BUTTON_EXIT,  "X");
}

static void browser_draw_page(int page) {
  FILINFO fno;
  DIR dj;
  // Mount SD card and open directory
  if (f_mount(fs_volume, "", 1) != FR_OK ||
      sd_open_dir(&dj, BROWSER_DIR, file_opt[keypad_mode].ext) != FR_OK) {
    ui_message_box("ERROR", "NO CARD", 2000);
    ui_mode_normal();
    return;
  }
  // Draw Browser UI
  int cnt = 0;
  uint16_t start_file = (page - 1) * FILES_PER_PAGE;
  lcd_set_background(LCD_MENU_COLOR);
  //lcd_clear_screen();
#ifdef __SD_BROWSER_FOLDERS__
  if (BROWSER_IN_FOLDER) { // virtual '..' entry occupies first slot
    if (cnt >= start_file && cnt < (start_file + FILES_PER_PAGE))
      browser_draw_button(cnt - start_file + FILE_BUTTON_FILE, "..");
    cnt++;
  }
#endif
  while (sd_findnext(&dj, &fno) == FR_OK) {
    if (cnt >= start_file && cnt < (start_file + FILES_PER_PAGE)) {
      //uint16_t sec = ((fno.ftime<<1)  & 0x3F);
      //uint16_t min = ((fno.ftime>>5)  & 0x3F);
      //uint16_t h   = ((fno.ftime>>11) & 0x1F);
      //uint16_t d   = ((fno.fdate>>0)  & 0x1F);
      //uint16_t m   = ((fno.fdate>>5)  & 0x0F);
      //uint16_t year= ((fno.fdate>>9)  & 0x3F) + 1980;
      //lcd_printf(x, y, "%2d %s %u - %u/%02u/%02u %02u:%02u:%02u", cnt, fno.fname, fno.fsize, year, m, d, h, min, sec);
#ifdef __SD_BROWSER_FOLDERS__
      if (fno.fattrib & AM_DIR) { // mark folders with leading '/'
        char label[BROWSER_NAME_SIZE + 2];
        plot_printf(label, sizeof(label), "/%s", fno.fname);
        browser_draw_button(cnt - start_file + FILE_BUTTON_FILE, label);
      } else
#endif
      browser_draw_button(cnt - start_file + FILE_BUTTON_FILE, fno.fname);
    }
    cnt++;
    if (file_count && (start_file + FILES_PER_PAGE == cnt)) break;
  }
  f_closedir(&dj);
  // Calculate page and file count on first run
  if (file_count == 0) {
    file_count = cnt;
    page_count = cnt == 0 ? 1 : (file_count + FILES_PER_PAGE - 1) / FILES_PER_PAGE;
  }
  // Erase not used button
  cnt-= start_file;
  while(cnt < FILES_PER_PAGE) {
    browser_btn_t btn;
    browser_get_button_pos(cnt + FILE_BUTTON_FILE, &btn);
    lcd_fill(btn.x, btn.y, btn.w, btn.h);
    cnt++;
  }
  lcd_fill(0, LCD_HEIGHT - FILE_BOTTOM_HEIGHT, LCD_WIDTH, FILE_BOTTOM_HEIGHT);

  browser_draw_buttons();
  lcd_printf((LCD_WIDTH - FONT_STR_WIDTH(6)) / 2, LCD_HEIGHT - (FILE_BOTTOM_HEIGHT + FONT_STR_HEIGHT) / 2, "- %u | %u -", page, page_count);
  return;
}

static void browser_key_press(int key) {
  int page;
  switch (key) {
    case FILE_BUTTON_LEFT:
    case FILE_BUTTON_RIGHT: // Switch page on left / right change
      page = current_page;
      if (key == FILE_BUTTON_LEFT  && --current_page < 1) current_page = page_count;
      if (key == FILE_BUTTON_RIGHT && ++current_page > page_count) current_page = 1;
      if (page != current_page)
        browser_draw_page(current_page);
    break;
    case FILE_BUTTON_EXIT:  //Exit
      ui_mode_normal();
    break;
    case FILE_BUTTON_DEL:   // Toggle delete mode
      browser_mode^= BROWSER_DELETE;
      browser_draw_buttons();
    break;
#ifdef __SD_BROWSER_FOLDERS__
    case FILE_BUTTON_NEW:   // Create a folder here (text keypad), then return to this folder
      if (browser_depth >= BROWSER_DEPTH_MAX) break;
      browser_format = keypad_mode;
      browser_reopen = true;
      ui_mode_keypad(KM_FOLDER_NAME);
    break;
#endif
    case FILE_BUTTON_FILE:  // Open or delete file
    default:
#ifdef __SD_BROWSER_FOLDERS__
      // false: folder navigation happened, browser stays open (page redrawn already)
      if (!browser_open_file(key - FILE_BUTTON_FILE + (current_page - 1) * FILES_PER_PAGE))
        return;
#else
      browser_open_file(key - FILE_BUTTON_FILE + (current_page - 1) * FILES_PER_PAGE);
#endif
      if (browser_mode & BROWSER_DELETE) {
        file_count = 0;                      // Reeset file count (recalculate on draw page)
        selection = -1;                      // Reset delection
        browser_mode&=~BROWSER_DELETE;       // Exit file delete mode
        browser_draw_page(current_page);
        return;
      }
      if (file_opt[keypad_mode].opt & FILE_OPT_KEEP) { // viewer closed: back to the file list
        selection = -1;
        browser_draw_page(current_page);
        return;
      }
      ui_mode_normal(); // Exit
    break;
  }
}

static int browser_get_max(void) {
  // get max buttons depend from page and file count
  int max = current_page == page_count ? (file_count % FILES_PER_PAGE) : FILES_PER_PAGE;
  if (file_count > 0 && max == 0) max = FILES_PER_PAGE;
  return max + FILE_BUTTON_FILE - 1;
}

void ui_mode_browser(int mode) {
  if (ui_mode == UI_BROWSER)
    return;
  set_area_size(0, 0);
  ui_mode = UI_BROWSER;
  keypad_mode = mode;
#ifdef __SD_BROWSER_FOLDERS__
  if (browser_reopen) browser_reopen = false;                          // back from the NEW folder keypad: keep the folder
  else
#ifdef __SD_GUIDES__
  browser_set_folder(mode == FMT_GUIDE_FILE ? "GUIDES" : NULL);
#else
  browser_set_folder(NULL); // always open at card root
#endif
#endif
  current_page = 1;
  file_count = 0;
  selection = -1;
  browser_mode = 0;
  browser_draw_page(current_page);
}

// Process UI input for browser
static void ui_browser_touch(int touch_x, int touch_y) {
  browser_btn_t btn;
  int old = selection;
  int max = browser_get_max();
  for (int idx = 0; idx <= max; idx++) {
    browser_get_button_pos(idx, &btn);
    if (touch_x < btn.x || touch_x >= btn.x + btn.w ||
        touch_y < btn.y || touch_y >= btn.y + btn.h) continue;
    // Found button under touch
    browser_draw_button(selection = idx, NULL);  // draw new selection
    browser_draw_button(old, NULL);              // clear old
    touch_wait_release();
    selection = -1;
    browser_draw_button(idx, NULL);              // clear selection
    browser_key_press(idx);
    return;
  }
}

static void ui_browser_lever(uint16_t status) {
  if (status == EVT_BUTTON_SINGLE_CLICK) {
    if (selection >= 0) browser_key_press(selection); // Process click
    return;
  }
  int max = browser_get_max();
  do {
    int old = selection;
    if((status & EVT_DOWN) && --selection < 0) selection = max;
    if((status & EVT_UP)   && ++selection > max) selection = 0;
    if (old != selection) {
      browser_draw_button(old, NULL);       // clear old selection
      browser_draw_button(selection, NULL); // draw new selection
    }
    chThdSleepMilliseconds(100);
  } while ((status = btn_wait_release()) != 0);
}
