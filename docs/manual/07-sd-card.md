# The SD card

The NanoVNA-H and H4 take a micro-SD card (FAT32 formatted on a PC; the H4 also reads exFAT,
the H does not) and use it to
save and load measurements, calibrations and screenshots, and to run command scripts. Nothing
on the card is needed for normal operation; the firmware never writes to it on its own. The
nanovna.com guide predates SD support in this firmware family, so this chapter is from the
source alone.[^src]

## What can be saved and loaded

| Format | Extension | Save | Load | Contents |
|---|---|---|---|---|
| Touchstone, one port | `.s1p` | SD CARD → SAVE S1P | LOAD → LOAD S1P | Frequency and S11 (real, imaginary) per sweep point: `# Hz S RI R 50` |
| Touchstone, two port | `.s2p` | SD CARD → SAVE S2P | LOAD → LOAD S2P | Frequency, S11, S21 per point (S12 and S22 columns are written as zero — the NanoVNA has no reverse path) |
| Screenshot | `.bmp`, `.tif`, or `.png` (H4) | SD CARD → SCREENSHOT, or tap the `BW:… p` text | LOAD → LOAD SCREENSHOT | The screen as an image: BMP 16-bit uncompressed (307 KB on the H4), TIFF PackBits (about 55 KB), or PNG (H4 only; indexed, compressed; 24 KB for a busy sweep screen, a few KB for a plain one) |
| Calibration | `.cal` | SD CARD → SAVE CALIBRATION, or CALIBRATE → SAVE → SAVE TO SD CARD | LOAD → LOAD CAL, or RECALL → LOAD FROM SD CARD | The same data as a calibration slot: correction terms plus the whole instrument setup ([chapter 3](03-calibration.md)) |
| Command script | `.cmd` or `.nvs` | — (write it on a PC) | CONFIG → EXPERT → MORE → LOAD COMMAND SCRIPT | Console commands, one per line |
| Firmware image | `.bin` | CONFIG → EXPERT → MORE → DUMP FIRMWARE | — | A copy of the running firmware, for backup or cloning to another unit with dfu-util |

Saving pauses the sweep for the duration of the write and resumes it afterwards. Touchstone
files contain what is currently displayed — calibrated data if calibration is applied, raw
data otherwise — so calibrate first.[^snp]

## File names

**SD CARD → AUTO NAME** (on by default) names files from the real-time clock so you never
have to type: on the H4, `VNA_yymmdd_hhmmss.ext`; on the H, which is built without long file
names, an eight-hex-digit FAT timestamp such as `5A3C8B41.s1p`. Set the clock first
(CONFIG → DATE/TIME) or every file will be stamped with the default date.[^names]

With AUTO NAME off, each save opens a text keypad for the name (up to 8 characters on the
H, 18 on the H4); the extension is added for you.[^len]

## Loading and viewing

**SD CARD → LOAD** opens the file browser for the chosen type. It lists files in pages (20 per
page on the H, 30 on the H4) as buttons; tap one, or roll the wheel to it and push. The
bottom row has **‹** and **›** for the previous and next page, **X** to leave, and **DEL** —
press DEL (it turns red), then the file to delete; the browser returns to normal mode after
one deletion. Touching the left, middle or right third of the list area when the buttons are
not under your finger acts as previous / select / next.[^browser]

Folders appear as `/NAME`; opening one lists its contents, and the first entry `..` goes up
one level. Two levels of folders are supported on the H4 (for example `CAL/HF/`); folders
inside the second level are not shown. The **NEW** button in the browser's bottom bar creates
a folder in the folder being shown (a text keypad asks for the name; an empty name or the
keypad's cancel returns without creating anything); it is not offered at the deepest level.
Files are still saved to the card root. On the H folders are a build option
(`__SD_BROWSER_FOLDERS__`, one level).

**Loading a Touchstone file** puts its data on the traces and sets the sweep start, stop and
point count to the file's, with the sweep held so the stored data stays on screen. The traces
then show the file, not the live ports; the moment you change the stimulus, resume the sweep
or press a marker operation that changes the sweep, the instrument goes back to live
measurement with the file's range (upstream #101, fixed in this fork).[^view]

**Loading a screenshot** shows it full-screen; the wheel or a tap on the left/right of the
screen steps to the previous/next image on the card, and a push or a centre tap returns to
the sweep.[^cont]

**Screenshot formats.** SD CARD → IMAGE FORMAT chooses what SCREENSHOT writes: BMP or TIFF on
the H; BMP, TIFF or PNG on the H4, cycling in that order. The choice is saved with the
configuration, and a configuration saved by an older firmware with TIFF selected keeps saving
TIFF. PNG is an indexed 8-bit, compressed image that opens anywhere: the same busy sweep screen
measured 307,322 B as BMP, 55 KB as TIFF and 24,194 B as PNG. A save takes a few seconds
(two passes over the screen). On the H4, LOAD SCREENSHOT lists all three types together and opens each with the
right decoder. The on-device PNG viewer implements only what the device writes (fixed-Huffman
compression, a small window): PNGs made on a PC are usually rejected with "Unsupported PNG"
and the device carries on.[^png]

**Loading a calibration** is the same as recalling a slot: correction and setup are restored
together, and the status shows `C*` (a live calibration not bound to a slot) until you save it
to one.

## Command scripts

A script is a text file of console commands, one per line, ending each line with a carriage
return (`\r`, as a Windows editor writes; lines ending in bare `\n` are joined). It is run by
CONFIG → EXPERT → MORE → LOAD COMMAND SCRIPT, one command at a time through the same parser
as the USB console, so anything in [chapter 8](08-console.md) that is marked "usable in
scripts" can go in it — set a sweep, recall a calibration, set traces and markers, pause. A
script is a convenient way to switch the instrument between saved setups without a PC. The
`.nvs` extension is accepted as an alias for `.cmd`, which mail and antivirus filters tend to
block (upstream #97).[^cmd]

## From the console

`sd_list {pattern}` lists files (e.g. `sd_list *.s1p`), `sd_read {file}` prints a file to the
console, `sd_delete {file}` removes one. These run in the sweep thread and interrupt the
sweep briefly.

## Guides

**SD CARD → LOAD → GUIDE** opens the card's `GUIDES` folder and shows a `.md` (or `.txt`)
file as pages of text on the device: turn the wheel or tap the right/left half of the screen
to change page, push the wheel or tap the header to return to the file list.[^guide] The
repository's `GUIDES/` folder (also attached to releases as `NanoVNA-guides.zip`) is a ready
pack of 27 guides, grouped by prefix: `ant-` antenna work (tuning workflow, SWR diagnostics,
radials, trimming, loading coils, lengths, band edges), `pota-` / `sota-` field operating (rules,
deploy sequence, safety), `choke-` (K9YC recipe, measuring a choke with the S21 series-through
formats, ferrite mixes), `coax-`, `cal-`, `ref-` (SWR/return-loss, dB, reactance and formula
cards), `prop-` (arrival angles and skip) and `dev-` (status letters, trace formats, MEASURE
panels, console cheat-sheet, menu map). The tables are generated from the same code tables the
firmware uses; the field material is condensed from the *Portable HF Vertical Antennas*
reference and its sources (N6LF, K9YC, ARRL), cited at the foot of each guide.

![The `dev-status` guide on the H4 (rendered)](img/dev-status-H4-p01.png){width=70%}

![The `ant-radials` guide, page 2, on the H (rendered)](img/ant-radials-H-p02.png){width=47%}

Guides are plain markdown, so they read on a PC too. What the viewer understands: `# Title`
on the first line (shown in the header); `---` alone on a line starts a new page;
`## Heading`; `**bold**` or `*emphasis*` in the trace-1 colour; `` `code` `` and
`[links](url)` reduced to their text; tables as `| a | b |` rows with a `|---|--:|` second row
for alignment; Ω, ° and µ are drawn, other non-ASCII characters show as `?`. There is no
wrapping or scrolling: keep lines under 60 characters and pages under 27 rows; the device
clips what does not fit. `python3 tools/manual/guide.py check FILE` reports anything the
device would clip, and `guide.py render FILE --target H4` shows each page exactly as it will
appear. On the NanoVNA-H the viewer is a build option (`__SD_GUIDES__`, about 2.8 KB, which
does not fit the H's default image — another option has to be dropped to enable it).

---

[^png]: `vna_modules/vna_png.c` `png_encode()` / `png_decode()`; `ui.c` `save_png()`, `load_png()`, `load_screenshot()`, `menu_image_format_acb()`, `fixScreenshotFormat()` (precedence `VNA_MODE_PNG` > `VNA_MODE_TIFF`).
[^src]: `FatFs/ffconf_303.h` `FF_FS_EXFAT 1`, `ffconf_072.h` `FF_FS_EXFAT 0`. File formats: `ui.c` `file_opt[]` and the `save_*` / `load_*` functions it names; screenshot gesture: `ui.c` `touch_made_screenshot()`.
[^snp]: `ui.c` `save_snp()`: header `!File created by NanoVNA` / `# Hz S RI R 50`; S2P lines are `"%u % f % f % f % f 0 0 0 0"` — frequency, S11, S21, then literal zeros for S12 and S22; data taken from `measured[]`, which holds calibrated values when calibration is applied.
[^names]: `ui.c` `ui_save_file()`: with `FF_USE_LFN` the name is `VNA_%06x_%06x` from the RTC date and time registers (BCD, so the digits read as a date), otherwise `%08x` from `rtc_get_FAT()`.
[^len]: `ui.c` `TXTINPUT_LEN`: `FF_MAX_LFN − 4` = 18 with long file names (`FatFs/ffconf_303.h`), 8 without (`ffconf_072.h`).
[^browser]: `vna_modules/vna_browser.c`: `FILES_PER_PAGE` = 2×10 (H) / 3×10 (H4); buttons `FILE_BUTTON_LEFT/RIGHT/EXIT/DEL`; `BROWSER_DELETE` toggled by DEL, cleared after `f_unlink()`; touch thirds → previous / select / next.
[^view]: `ui.c` `load_snp()`: sets `_sweep_points`, start and stop, then `sweep_mode |= SWEEP_FILE_VIEW`; `main.c` clears the flag on stimulus change or resume.
[^cont]: `FILE_OPT_CONTINUE` on the image formats: "in browser mode use leveler left/right for see next/prev file" (`ui.c`); `vna_modules/vna_browser.c` `need_continue`.
[^cmd]: `ui.c` `load_cmd()`: reads the file in 256-byte blocks, accumulates up to 128 characters per line, executes a line at each `\r` via `VNAShell_executeCMDLine()`, skips other control characters (so `\n` is ignored, not a terminator).
[^guide]: `vna_modules/vna_guide.c` `load_guide()`; `ui.c` `file_opt[FMT_GUIDE_FILE]` (`md|txt`), `menu_sdcard_browse`; the browser opens in `GUIDES` for this type (`vna_browser.c` `ui_mode_browser()`). The format's reference implementation and linter is `tools/manual/guide.py`.
