# Appendix A — What is fork-only

This manual describes the StephenGenusa fork of DiSlord's NanoVNA-D firmware. Readers on
stock DiSlord firmware (1.2.x) will not find the following on their device; everything else in
the manual applies to both.

| Where in the manual | Fork-only item | On stock firmware |
|---|---|---|
| Ch. 1, status column | — (identical) | — |
| Ch. 2, trace formats | `SWR ANT` (console `swrant`) | absent |
| Ch. 4, Searching | `ZERO` search mode | only MAXIMUM / MINIMUM |
| Ch. 5, MEASURE | `SWR BW (S11)` panel | absent |
| Ch. 6 | the whole chapter: ham band indicators and H4 sub-bands (DISPLAY → SCALE → HAM BANDS), SWR ANT + CABLE LOSS, coax presets (CABLE TYPE / CABLE LENGTH under FORMAT, H4), SWR BW, ZERO search, MUTE OUTPUT ON PAUSE, raw S21 phase sign, SD folders, `.nvs` scripts, `*IDN?`, touch double-tap filter, stored-file viewing fix, 12-hour hang fix, `CLOCK_GEN` builds, About-screen additions, `-sg` version suffix | absent |
| Ch. 7 | one-level folder browsing (`/NAME`, `..`) and `.nvs` scripts | flat file list; `.cmd` only |
| Ch. 8 | `*IDN?` / `*idn?`; `trace N swrant` | absent |
| Ch. 9, menu map | DISPLAY → SCALE → HAM BANDS; DISPLAY → FORMAT → SWR ANT, CABLE LOSS, CABLE TYPE (H4), CABLE LENGTH (H4); STIMULUS → MUTE OUTPUT ON PAUSE; MEASURE → SWR BW (S11) (H4) | absent |
| Ch. 10 | the repository's `0_backup_firmware.sh`, `1_build.sh`, `2_prog.sh` | use `dfu-util` or DfuSe directly |
| Ch. 3, THRU note | the "re-do THRU after flashing" warning applies when moving between stock and fork firmware in either direction | — |

Stock-firmware behaviour that differs and is noted in the text: raw (uncalibrated) S21 phase
reads ≈180° off on stock builds (chapter 6); calibrated results are the same on both.

Everything in the generated chapters (8, 9, and the trace-format table) is produced from this
fork's source at the version on the title page; items that exist only on one device are
marked "H4 only" / "H only" there.
