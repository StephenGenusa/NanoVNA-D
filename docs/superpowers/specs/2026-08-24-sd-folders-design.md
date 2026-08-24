# SD Card Folder Browsing (one level) — Design Spec

**Date:** 2026-08-24
**Status:** Approved (scope set by user: build option on F072, always on for F303)
**Origin:** Issue DiSlord/NanoVNA-D#76 — organize calibrations/files in folders.
DiSlord deferred it as a "huge increase [in] code size"; measurement says
otherwise for this browser architecture (see Cost).

## Problem

The SD file browser shows only the card root. Users with several test
fixtures and calibration sets for different frequency ranges want to group
files in folders (one level is enough, per the request). Saving into
folders is NOT requested — loading/organizing is.

## Key insight (from research 2026-08-24)

The browser keeps **no file list in RAM**: every page draw and file open
re-walks the directory via `f_readdir`, filtering by extension, paging with
three `uint16_t` counters. Folders therefore add no list memory and no
restructuring — just directory entries flowing through the same walk.
FatFS needs **no configuration change**: `f_opendir`/`f_open` accept
explicit `"DIR/FILE"` paths with the current `FF_FS_RPATH 0` (the measured
`f_chdir` alternative costs +148 B and is unnecessary).

## Decisions

### Availability: guard `__SD_BROWSER_FOLDERS__`
In `nanovna.h`, inside the existing `__SD_FILE_BROWSER__` submodule block:
```c
// Add one-level folder navigation to the SD file browser (see issue #76)
#if defined(NANOVNA_F303)
#define __SD_BROWSER_FOLDERS__   // always enabled on H4
#else
//#define __SD_BROWSER_FOLDERS__ // H opt-in: costs ~0.7-1 KB of the H's last ~1.9 KB flash
#endif
```
- **F303/H4: always on.**
- **F072/H: compile-time opt-in, default OFF** — default H binaries stay
  byte-identical; uncommenting one line enables it for users who want it.

### Scope: exactly one level
- At **root**: directory entries pass the browser filter and are listed
  among the files (FAT order, not grouped — accepted; matches the flat
  listing's existing unsorted behavior), labeled with a leading `/`
  (e.g. `/CALS`). Selecting one enters it.
- **Inside a folder**: a synthetic `..` entry occupies the first button;
  only extension-matching *files* are listed (sub-subdirectories are
  skipped — one level, per the issue). Selecting `..` returns to root.
- The browser always opens at root (`ui_mode_browser` resets the folder) —
  predictable, no stale-path state.

### Mechanics
- State: `static char browser_folder[...]` — empty string = root; sized to
  the target's FatFS name buffer (8.3 → 13 bytes on F072 where
  `FF_USE_LFN 0`; `FF_LFN_BUF+1` on F303). Plus one stack path-join buffer
  in `browser_open_file` (`"folder/name"`).
- `sd_findnext()`: at root, directory entries (`AM_DIR`) pass the filter;
  inside a folder they are skipped (current behavior). Hidden/system
  entries keep being skipped.
- `browser_draw_page()` / `browser_open_file()`: `sd_open_dir(&dj,
  browser_folder, ...)` instead of `""`; open joins the folder into the
  path. The `..` entry shifts file indexing by one inside a folder.
- `browser_key_press()`: selecting a directory (or `..`) sets/clears
  `browser_folder`, resets `file_count`/`current_page`/`selection`, and
  redraws — same reset pattern `ui_mode_browser` uses today.
- **Delete mode**: `DEL` acts on files only; selecting a folder or `..` in
  delete mode does nothing (`f_unlink` on a non-empty dir would fail
  anyway — this makes it explicit). Folder create/delete is out of scope.
- **Saving is unchanged**: all saves (screenshots, s1p/cal/bin, keyboard
  names) still land in the card root. "Save into current folder" is a
  possible follow-up, ~150–250 B more, not part of this spec.
- All folder code sits under `#ifdef __SD_BROWSER_FOLDERS__`; with the
  guard off the compiled browser is unchanged.

### Cost (measured/calibrated, from the research pass)
- FatFS: **0 B** (no config change).
- Browser: **~0.6–1 KB flash** (~50–70 lines in this code style; calibrated
  against the 44-line ham-band renderer ≈ 550 B measured).
- RAM: ~16 B (F072, 8.3 names) / ~260 B (F303, LFN buffer) static.
- Budget: F303 trivial (~49 KB free). F072 fits (~1.9 KB free) but the
  default stays OFF there precisely because it would consume ~35–50% of
  the H's remaining lifetime feature budget.

## Validation
- Build matrix: F072 default (must be **byte-identical** to pre-feature),
  F072 with guard enabled (builds, size recorded, must stay under the
  98,304 B cap), F303 (builds, size recorded).
- On-device checklist (H4 or opted-in H): create `CALS/` on the card with
  `.cal` files plus some in root; browser lists `/CALS` and root files;
  entering shows `..` + only `.cal` files; loading one works; `..`
  returns; paging works with >1 page of entries inside and outside a
  folder; delete mode deletes a file but ignores folders; screenshots
  still save to root.

## Out of scope
- Nested folders (beyond one level), folder create/rename/delete from the
  device, saving into folders, sorted/grouped listings, remembering the
  last-visited folder across browser sessions.

## Risks
- **F072 headroom** if a user enables the option late in the H's life —
  mitigated: opt-in with the cost stated at the define.
- **Path length**: folder + 8.3 name fits every buffer on F072; on F303
  LFN the join buffer is sized `2*FF_LFN_BUF+2` on stack — verify stack
  margin (browser runs in the sweep thread's UI path, same stack that
  already carries `FF_LFN_BUF` locals in `ui_save_file`).
- **Off-by-one in `..` indexing** (page counts, `browser_get_max`,
  delete-index mapping) — the risk area for implementation; the plan must
  walk every consumer of `file_count`.
