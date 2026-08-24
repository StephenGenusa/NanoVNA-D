# SD Browser Folder Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One-level folder navigation in the SD file browser — always on for F303/H4, compile-time opt-in (default off) for F072/H.

**Architecture:** The browser keeps no file list in RAM (it re-walks the directory per page draw / open), so folders are added by letting directory entries pass the walk filter at root, tracking one `browser_folder` static, and treating `..` as a virtual entry 0 inside a folder so `file_count`, paging, `browser_get_max`, and delete-index mapping stay untouched. FatFS is unchanged (`f_opendir`/`f_open` take explicit `"DIR/FILE"` paths at `FF_FS_RPATH 0`). A `browser_ret_t`/`BROWSER_DONE` macro pair keeps the guard-off build's `browser_open_file` signature literally `void`, so the default F072 binary compiles to identical code.

**Tech Stack:** C, ChibiOS firmware, FatFS (config untouched), include-fragment `vna_modules/vna_browser.c` (compiled into ui.c).

**Spec:** `docs/superpowers/specs/2026-08-24-sd-folders-design.md`

## Global Constraints

- Guard: `__SD_BROWSER_FOLDERS__` — defined always for `NANOVNA_F303`, commented-out opt-in for F072, inside the `__SD_FILE_BROWSER__` submodule block.
- F072 default build must compile to identical code: `arm-none-eabi-size build/H.elf` text=94,976 / data=440 exactly (bin 96,344 B; only the embedded `__TIME__` string may differ).
- F072 opt-in test build must link under the 98,304 B cap.
- Exactly one folder level; `..` returns to root; browser opens at root; delete mode ignores folders and `..`; saves stay root-only.
- Builds via `./1_build.sh F072` / `./1_build.sh F303`; commit ends with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`; push only when the user asks (established: push after each completed issue fix).

---

### Task 1: Guard, folder state, walk filter, navigation, build matrix

**Files:**
- Modify: `nanovna.h` (guard define after `__SD_FILE_BROWSER__` near line 102)
- Modify: `vna_modules/vna_browser.c` (statics near line 23; `sd_findnext` near line 90; `browser_open_file` near line 105; `browser_draw_page` near line 174; `browser_key_press` near line 224; `ui_mode_browser` near line 264)

**Interfaces:**
- Consumes: existing statics `file_count`, `current_page`, `selection`, `browser_mode`, `keypad_mode`; `sd_open_dir(DIR*, path, pattern)`; `file_opt[]`; `plot_printf`; FatFS `FILINFO.fattrib`/`AM_DIR`.
- Produces (all internal to the fragment): `browser_folder[]`, `BROWSER_IN_FOLDER`, `browser_path(name)`, `browser_goto_folder(name)`, `browser_ret_t browser_open_file(int)` (stays `void` with guard off via `BROWSER_DONE`).

- [ ] **Step 1: Add the guard in `nanovna.h`**

Find (near line 101):
```c
// Enable SD card file browser, and allow load files from it
#define __SD_FILE_BROWSER__
```
Insert directly after:
```c
#ifdef __SD_FILE_BROWSER__
// Add one-level folder navigation to the SD file browser (see issue #76)
#if defined(NANOVNA_F303)
#define __SD_BROWSER_FOLDERS__   // always enabled on H4
#else
//#define __SD_BROWSER_FOLDERS__ // H opt-in: costs ~0.7-1 KB of the H's last ~1.9 KB flash
#endif
#endif
```

- [ ] **Step 2: Add folder state and helpers in `vna_modules/vna_browser.c`**

Find (near line 23):
```c
static uint16_t browser_mode;

#define BROWSER_DELETE    1
```
Replace with:
```c
static uint16_t browser_mode;

#define BROWSER_DELETE    1

#ifdef __SD_BROWSER_FOLDERS__
// One-level folder navigation (see issue #76). "" = card root.
// Name buffer size matches FILINFO.fname for the target FatFS config (8.3 or LFN)
#define BROWSER_NAME_SIZE  sizeof(((FILINFO*)0)->fname)
static char browser_folder[BROWSER_NAME_SIZE];
#define BROWSER_IN_FOLDER  (browser_folder[0] != 0)
#define BROWSER_DIR        browser_folder
// Prefix name with current folder for f_open / f_unlink
static const char *browser_path(const char *name) {
  static char path[2 * BROWSER_NAME_SIZE + 1];
  if (!BROWSER_IN_FOLDER) return name;
  plot_printf(path, sizeof(path), "%s/%s", browser_folder, name);
  return path;
}
// Enter folder (name) or return to root (name == NULL), redraw first page
static void browser_goto_folder(const char *name) {
  if (name) plot_printf(browser_folder, sizeof(browser_folder), "%s", name);
  else browser_folder[0] = 0;
  file_count = 0;
  current_page = 1;
  selection = -1;
  browser_draw_page(current_page);
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
```
(`browser_goto_folder` calls `browser_draw_page` which is defined later in the file — add a forward declaration right above the `#ifdef __SD_BROWSER_FOLDERS__` block: `static void browser_draw_page(int page);`)

- [ ] **Step 3: Let directories pass the walk at root**

Find (near line 90):
```c
static FRESULT sd_findnext(DIR* dp, FILINFO* fno) {
  while (f_readdir(dp, fno) == FR_OK && fno->fname[0]) {
    if (fno->fattrib & AM_DIR) continue;
    if (compare_ext(fno->fname, dp->pat)) return FR_OK;
```
Replace with:
```c
static FRESULT sd_findnext(DIR* dp, FILINFO* fno) {
  while (f_readdir(dp, fno) == FR_OK && fno->fname[0]) {
    if (fno->fattrib & AM_DIR) {
#ifdef __SD_BROWSER_FOLDERS__
      if (!BROWSER_IN_FOLDER) return FR_OK; // list folders at root (one level only)
#endif
      continue;
    }
    if (compare_ext(fno->fname, dp->pat)) return FR_OK;
```

- [ ] **Step 4: Navigation in `browser_open_file`**

Find (near line 105):
```c
static void browser_open_file(int sel) {
  FILINFO fno;
  DIR dj;
  int cnt;
  if ((uint16_t)sel >= file_count) return;
  if (f_mount(fs_volume, "", 1) != FR_OK) return;
repeat:
  cnt = sel;
  if (sd_open_dir(&dj, "", file_opt[keypad_mode].ext) != FR_OK) return;  // open dir
  while (sd_findnext(&dj, &fno) == FR_OK && cnt != 0) cnt--;             // skip cnt files
  f_closedir(&dj);
  if (cnt != 0) return;

  // Delete file if in delete mode
  if (browser_mode & BROWSER_DELETE) {f_unlink(fno.fname); return;}

  // Load file, get load function
  file_load_cb_t load = file_opt[keypad_mode].load;
  if (load == NULL) return;
  //
  lcd_set_colors(LCD_FG_COLOR, LCD_BG_COLOR);

  if (f_open(fs_file, fno.fname, FA_READ) != FR_OK) return;
```
Replace with:
```c
static browser_ret_t browser_open_file(int sel) {
  FILINFO fno;
  DIR dj;
  int cnt;
  if ((uint16_t)sel >= file_count) BROWSER_DONE(true);
  if (f_mount(fs_volume, "", 1) != FR_OK) BROWSER_DONE(true);
#ifdef __SD_BROWSER_FOLDERS__
  if (BROWSER_IN_FOLDER) {
    if (sel == 0) { // virtual '..' entry: return to root (ignored in delete mode)
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
```
Then, in the remainder of the same function, replace every remaining bare `return;` with `BROWSER_DONE(true);` and check the function's final exit also ends with `BROWSER_DONE(true);` — read the rest of the function (through about line 165) and convert each one; the `goto repeat` stays as is. (With the guard off, `BROWSER_DONE(true)` expands to plain `return;` and `browser_ret_t` to `void`, so the F072 default build is unchanged.)

Additionally, in the same function's continue-mode input loop, the next/prev wrap bound must exclude the virtual `..` (inside a folder, `sel` here is walk-space but `file_count` counts `..`). Find (near line 159):
```c
    int old_sel = sel;
         if (key == 0) {if (--sel < 0) sel = file_count - 1;}
    else if (key == 1) {if (++sel > file_count - 1) sel = 0;}
```
Replace with:
```c
    int old_sel = sel;
    int last_sel = file_count - 1;
#ifdef __SD_BROWSER_FOLDERS__
    if (BROWSER_IN_FOLDER) last_sel--; // sel is walk-space here, file_count includes virtual '..'
#endif
         if (key == 0) {if (--sel < 0) sel = last_sel;}
    else if (key == 1) {if (++sel > last_sel) sel = 0;}
```
(Accepted behavior quirk, documented: if image next/prev navigation at root lands on a folder entry, the browser shows that folder's listing — coherent, and only occurs when folders exist among images.)

- [ ] **Step 5: Folder display in `browser_draw_page`**

Find (near line 178):
```c
  if (f_mount(fs_volume, "", 1) != FR_OK ||
      sd_open_dir(&dj, "", file_opt[keypad_mode].ext) != FR_OK) {
```
Replace with:
```c
  if (f_mount(fs_volume, "", 1) != FR_OK ||
      sd_open_dir(&dj, BROWSER_DIR, file_opt[keypad_mode].ext) != FR_OK) {
```
Find (near line 185):
```c
  int cnt = 0;
  uint16_t start_file = (page - 1) * FILES_PER_PAGE;
  lcd_set_background(LCD_MENU_COLOR);
  //lcd_clear_screen();
  while (sd_findnext(&dj, &fno) == FR_OK) {
```
Replace with:
```c
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
```
Find (near line 198, inside the walk loop):
```c
      browser_draw_button(cnt - start_file + FILE_BUTTON_FILE, fno.fname);
```
Replace with:
```c
#ifdef __SD_BROWSER_FOLDERS__
      if (fno.fattrib & AM_DIR) { // mark folders with leading '/'
        char label[BROWSER_NAME_SIZE + 2];
        plot_printf(label, sizeof(label), "/%s", fno.fname);
        browser_draw_button(cnt - start_file + FILE_BUTTON_FILE, label);
      } else
#endif
      browser_draw_button(cnt - start_file + FILE_BUTTON_FILE, fno.fname);
```

- [ ] **Step 6: Keep the browser open on folder navigation**

Find (near line 242, in `browser_key_press`):
```c
    case FILE_BUTTON_FILE:  // Open or delete file
    default:
      browser_open_file(key - FILE_BUTTON_FILE + (current_page - 1) * FILES_PER_PAGE);
```
Replace with:
```c
    case FILE_BUTTON_FILE:  // Open or delete file
    default:
#ifdef __SD_BROWSER_FOLDERS__
      // false: folder navigation happened, browser stays open (page redrawn already)
      if (!browser_open_file(key - FILE_BUTTON_FILE + (current_page - 1) * FILES_PER_PAGE))
        return;
#else
      browser_open_file(key - FILE_BUTTON_FILE + (current_page - 1) * FILES_PER_PAGE);
#endif
```

- [ ] **Step 7: Open at root in `ui_mode_browser`**

Find (near line 270):
```c
  keypad_mode = mode;
  current_page = 1;
```
Replace with:
```c
  keypad_mode = mode;
#ifdef __SD_BROWSER_FOLDERS__
  browser_folder[0] = 0; // always open at card root
#endif
  current_page = 1;
```

- [ ] **Step 8: F072 default build — must be unchanged**

Run: `./1_build.sh F072`
Expected: text=94,976 data=440 in the size line, `build/H.bin` = 96,344 bytes — exactly the pre-change numbers (the guard is off, and the `browser_ret_t`/`BROWSER_DONE` macros keep the source compiling to the same `void` function). Any size delta means guard leakage — stop and find it.

- [ ] **Step 9: F303 build (folders always on)**

Run: `./1_build.sh F303`
Expected: clean build (only the pre-existing plot.c sign-compare warning), size grows from 94,092 B by roughly 0.5–1 KB. Record the delta.

- [ ] **Step 10: F072 opt-in test build, then revert the toggle**

Temporarily uncomment the F072 define in `nanovna.h` (`//#define __SD_BROWSER_FOLDERS__` → `#define __SD_BROWSER_FOLDERS__`), run `./1_build.sh F072`, and verify it links under the 98,304 B cap (expect ~97.0–97.4 KB). Then restore the comment and rebuild F072 once more to confirm the default numbers from Step 8 return.

- [ ] **Step 11: Commit**

```bash
git add nanovna.h vna_modules/vna_browser.c
git commit -m "Add one-level folder navigation to SD file browser

Folders list at root with a leading '/', entering shows a virtual '..'
plus matching files; delete mode ignores folders. Always enabled on
F303/H4; compile-time opt-in on F072/H (flash headroom). FatFS config
unchanged (explicit paths, no f_chdir).

Fixes DiSlord/NanoVNA-D#76

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: On-device checklist (needs the user / hardware — does not block completion)

**Files:** none (verification only)

- [ ] **Step 1: Flash and exercise** (when an H4 or opted-in H is available)

`./2_prog.sh F303` in DFU mode. On a card, create `CALS/` with several `.cal` files and leave some in root. Verify: RECALL→SD browser lists `/CALS` and root `.cal` files; entering shows `..` first plus only `.cal` files; loading one applies it; `..` returns to root; paging works with more than one page of entries; delete mode deletes a file, ignores `/CALS` and `..`; screenshots still save to root. Report results (or that this awaits hardware).
