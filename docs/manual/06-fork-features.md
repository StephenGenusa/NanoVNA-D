# Features added in this fork

This firmware is DiSlord's NanoVNA-D with additions made in the StephenGenusa fork. This
chapter describes each addition as a feature of the device; appendix A lists which sections of
the manual are fork-only, for readers on stock firmware. Upstream issue numbers refer to
[DiSlord/NanoVNA-D](https://github.com/DiSlord/NanoVNA-D/issues).

## Amateur band indicators

**DISPLAY → SCALE → HAM BANDS** selects a region: OFF, IARU R1, IARU R2, IARU R3, USA, CANADA,
UK, GERMANY, JAPAN, AUSTRALIA. With a region set, every amateur band inside the current sweep
is marked by a 2-pixel bar along the bottom edge of the plot, in the link colour, on rectangular
formats (not Smith or polar). The bar's ends are the band edges for that region, so sweeping
6.9–7.4 MHz with USA selected shows a bar from 7.000 to 7.300 MHz.

On the **H4 only**, the bar is additionally coloured by IARU sub-band: **orange** for CW,
**blue** for narrow-band digital, **green** for phone, following the regional band plans (a
country region uses its IARU region's plan, clipped to the country's own band edges).
Segments are indicative — national band plans differ in detail and change; check your own
regulations.

The setting is saved with the configuration (CONFIG → SAVE CONFIG).[^ham]

## SWR at the antenna: `SWR ANT` and `CABLE LOSS`

A lossy feedline makes any antenna look better than it is: the reflected wave is attenuated
on the way out and again on the way back, so the SWR at the radio end is always lower than
the SWR at the antenna. Through 50 ft of RG‑58 on 20 m (0.85 dB one way) a true 3:1 reads
2.4:1; through 100 ft on 10 m (2.4 dB) a 10:1 reads 2.8:1.

**DISPLAY → FORMAT → SWR ANT → SWR ANT** is an S11 trace format that undoes this (the SWR ANT
submenu groups the format with its feedline settings). It multiplies the
measured reflection coefficient by 10^(L/10), where L is the one-way loss of the cable in dB,
and displays the resulting SWR:[^swrant]

- Enter L under **DISPLAY → FORMAT → SWR ANT → CABLE LOSS** (dB, one way, at the band you are on — from
  the cable's data sheet, from MEASURE → CABLE with the far end open, or from CABLE TYPE
  below). Until a loss is entered the trace is not drawn and its marker line reads
  `set CABLE LOSS`, so an uncorrected number is never mistaken for a corrected one.
- The value is not saved: it is specific to one cable on one band, and a stale value would be
  worse than none. Enter it again after a power cycle.
- Where the corrected reflection would exceed 1 (which happens when L is over-estimated), the
  trace shows the same "infinite" value as SWR does for a total reflection.

Accuracy is set by how well L is known. An error of ±0.2 dB moves a true 2:1 by about ±0.07
and a true 3:1 by about ±0.2; above 5:1 the correction magnifies any error and the reading is
only indicative. Use a common-mode choke at the feedpoint: without one the outside of the coax
shield is part of the antenna, and what the VNA sees — corrected or not — is the SWR of antenna
plus shield.

Console: `trace N swrant`. Running SWR and SWR ANT as two traces shows the feedline's effect
directly.

## Coax presets: `CABLE TYPE` and `CABLE LENGTH` (H4 only)

**DISPLAY → FORMAT → SWR ANT → CABLE TYPE** cycles MANUAL → LMR‑400 → RG‑213 → RG‑8X → RG‑58 →
RG‑174/316. With a type selected and **CABLE LENGTH** entered in metres, the firmware computes
the one-way loss for every sweep point from the ARRL Antenna Book's attenuation table
(dB/100 ft at 1.8, 3.6, 7.1, 14.2, 21.2, 28.4 and 50.1 MHz, stored converted to dB/100 m,
interpolated on √f) and feeds it to SWR ANT — so a wide sweep is corrected correctly at each
frequency and a band change needs no re-entry. The CABLE LOSS button shows the computed value
at the sweep centre; typing a loss there returns to MANUAL.[^coax]

The table is for new, dry, name-brand cable. Old, wet or off-brand coax can be markedly
worse; when in doubt measure it (MEASURE → CABLE, antenna disconnected) and enter the result
under CABLE LOSS.

## SWR bandwidth and Q: `MEASURE → SWR BW (S11)` (H4; opt-in on the H)

A short, efficient antenna has a narrow, sharp SWR dip; resistive loss damps the resonance and
makes the dip broad and easy to hit. A flat, wide SWR curve is therefore not a triumph — it is
often a symptom. This panel puts numbers on the dip:

```
S11 SWR BW
f0: 7.123456MHz (SWR 1.42)
2:1  7.057 - 7.191MHz  Bw 133kHz
3:1  7.005 - 7.244MHz  Bw 239kHz
Q: 39.0
```

It walks from the active marker to the nearest SWR minimum (or takes the deepest dip in the
sweep when no marker is active), reports f₀ and the minimum SWR, the frequencies where the
curve crosses 2:1 and 3:1 on each side with the bandwidth between them (an edge outside the
sweep is flagged — widen the sweep), and the bandwidth quality factor Q. Q follows Yaghjian &
Best's relation between fractional VSWR bandwidth and Q, generalised to use the resistance
measured at the dip instead of assuming a 50 Ω match, so it is exact for a series-RLC-like dip
at any minimum SWR; when the dip is RLC-like the 2:1 and 3:1 levels give the same Q, which is
a useful check on the measurement.[^swrbw] f₀ is taken as the geometric mean of the bracketing
crossings, which sit on the steep sides of the dip and are far less sensitive to noise than its
flat bottom.

On the H the feature is a build option (`__S11_SWR_BW_MEASURE__`); it would leave about 100
bytes of flash, so it is off by default.

## ZERO marker search

**MARKER → SEARCH** cycles MAXIMUM → MINIMUM → **ZERO**. ZERO places the marker on the point
whose trace value is closest to zero — on a REACTANCE trace, that is the resonance; the
SEARCH ‹LEFT / SEARCH ›RIGHT buttons then step to the next sign change in that direction. The
search mode is saved with the configuration. (Upstream #107.)

## Output mute on pause

**STIMULUS → MUTE OUTPUT ON PAUSE** (off by default): when the sweep is paused, the current
scan is allowed to finish and then the signal generator's outputs are disabled, so a paused
NanoVNA radiates nothing. Resuming re-enables them. Useful when the instrument sits connected
to an antenna between measurements. (Upstream #50.)

## Raw S21 phase

The THRU input reaches the codec with its differential pair inverted relative to the
reflection input, which cannot be undone by the codec's routing registers; stock firmware
therefore reports raw (uncalibrated) S21 phase 180° off — a through cable reads ≈180° instead
of ≈0°. This fork negates the raw S21 sample so the phase is physically true. Calibrated results
are unaffected either way (the sign cancels in the transmission error term), so the only
visible change is with calibration off, or in raw data taken over USB.

**Re-do your THRU calibration after flashing**: thru data saved by older firmware carries the
old sign and would show calibrated S21 phase 180° off. Verified on two NanoVNA‑H4 units
(stock ≈180°, this firmware ≈0°); the NanoVNA‑H has not been checked. (Upstream #81.)

## SD card: folders and `.nvs` scripts

The file browser shows folders as `/NAME`; open one to see its files and use `..` to go up a
level. Two levels are supported on the H4 (`CAL/HF/…`), and the browser's NEW button creates a
folder in place. On the H folders are a build option
(`__SD_BROWSER_FOLDERS__`, one level) because of flash. (Upstream #76.)

Command scripts are accepted with the `.nvs` extension as well as `.cmd` — mail systems and
antivirus filters commonly block `.cmd` attachments. (Upstream #97.)

## Console: `*IDN?`

`*IDN?` (or `*idn?`) replies `NanoVNA,<board>,<serial>,<version>` in the SCPI style that
VISA, pyvisa and LabVIEW expect, so the device can be identified without a custom driver.
The serial is the same 12-character encoding the USB descriptor and the About screen use.
(Upstream #98.)

## Smaller changes

- **Touch double-tap filter**: a second tap within 100 ms of releasing the first is ignored,
  which stops one intended tap registering twice on the button underneath. (Upstream #109.)
- **Stored-file viewing**: changing the stimulus while an `.s1p`/`.s2p` loaded from the SD card
  is on screen resumes the live sweep instead of leaving the axes and markers out of step.
  (Upstream #101.)
- **Sweep hang after ~12 hours**: fixed a 32-bit system-timer wrap that could stop the sweep
  after about 12 hours of continuous running. (Upstream #110.)
- **Clock-generator variants**: builds for boards with an MS5351 or SWC5351 in place of the
  Si5351 (`make CLOCK_GEN=MS5351`); the About screen names the chip. (Upstream #54.)
- **About screen** (CONFIG → VERSION): shows the clock-generator chip on the TCXO line and the
  encoded serial next to the raw one; the version string carries the `-sg` suffix.

---

[^ham]: `vna_modules/vna_hambands.c` (band tables, region names, IARU segment tables under `__USE_HAM_SUBBANDS__`); drawn by `cell_draw_ham_bands()` in `plot.c`; setting `config._ham_region`.
[^swrant]: `plot.c` `swr_ant()`: `x = |Γ| · exp(L · ln10/10)`; blank when `cable_loss_db == 0` (`trace_is_blank()`); `ui.c` `input_cable_loss()`. The relation is the standard transmission-line result; cross-checked against Maxwell, *Reflections III*, appendix 6 (a 3:1 load through 0.5 dB reads 2.61:1 — the formula gives 2.608:1).
[^coax]: `vna_modules/vna_coax.c`: ARRL Antenna Book Vol. 3, Table 23.4, quoted verbatim in the file header; host test `tests/test_coax.c` reproduces every table value and the worked cases 50 ft RG‑58 @ 14.2 MHz = 0.85 dB and 100 ft @ 28.4 MHz = 2.40 dB.
[^swrbw]: `vna_modules/vna_swr_bw.c`; A. D. Yaghjian and S. R. Best, "Impedance, Bandwidth, and Q of Antennas," *IEEE Trans. Antennas Propag.* 53(4), 2005; A. D. Yaghjian, arXiv:2501.03146 (2025), eq. 7, 12, 21. Host test `tests/test_swr_bw.c` recovers Q = 39.0 from synthetic dips with R = 25…100 Ω.
