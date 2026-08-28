NanoVNA - Very tiny handheld Vector Network Analyzer
==========================================================
[release]: https://github.com/DiSlord/NanoVNA-D/releases

<div align="center">
<img src="/doc/nanovna.jpg" width="480px">
</div>

# About

**NanoVNA-H** and **NanoVNA-H4** are very tiny handheld Vector Network Analyzers (VNA).
They are standalone portable devices withLCD and battery.
This project aims to provide improved firmware for this useful instrument for enthusiast.

This repository contains the source code of the improved NanoVNA-H and NanoVNA-H4 firmware.

The documentation describes the build and flash process on a MacOS or a Linux (Debian or Ubuntu) system, other Linux (or even BSD) systems may behave similar.

# About this fork

This is [StephenGenusa/NanoVNA-D](https://github.com/StephenGenusa/NanoVNA-D), a fork of
[DiSlord/NanoVNA-D](https://github.com/DiSlord/NanoVNA-D) carrying fixes and features for
open upstream issues. I am new to the NanoVNA and this is my experimental fork.

* **Ham band indicators** with a region setting (DISPLAY→SCALE→HAM BANDS): band edges drawn
  on the frequency axis for IARU R1/R2/R3, USA, Canada, UK, Germany, Japan, or Australia
  (upstream [#103](https://github.com/DiSlord/NanoVNA-D/pull/103)/[#104](https://github.com/DiSlord/NanoVNA-D/issues/104)).
  On the H4 the bar is additionally colored by sub-band: CW (orange), narrow digital (blue),
  phone (green), per the IARU regional band plans.
* **SD folder browsing** (one level): folders show as `/NAME` in the file browser, `..` returns
  to root ([#76](https://github.com/DiSlord/NanoVNA-D/issues/76)). Always on for the H4; opt-in
  for the H (`__SD_BROWSER_FOLDERS__` in `nanovna.h`, flash headroom).
* **`.nvs` accepted for command scripts** alongside `.cmd`, which mail/AV filters block
  ([#97](https://github.com/DiSlord/NanoVNA-D/issues/97)).
* **`*IDN?` console command** (SCPI-style identify) for VISA/pyvisa/LabVIEW use
  ([#98](https://github.com/DiSlord/NanoVNA-D/issues/98)).
* **ZERO marker search** alongside MAXIMUM/MINIMUM — finds the trace value closest to zero,
  e.g. reactance zero crossings ([#107](https://github.com/DiSlord/NanoVNA-D/issues/107)).
* **Raw S21 phase corrected** (hardware THRU polarity inversion undone in firmware,
  [#81](https://github.com/DiSlord/NanoVNA-D/issues/81)).
  **Note: re-do your THRU calibration after flashing** — thru data saved by older firmware
  carries the old sign and would show S21 phase off by 180°. Verified on two NanoVNA‑H4 units
  (raw S21 phase reads ≈180° on stock firmware, ≈0° with this fix; calibrated results are
  identical). The NanoVNA‑H has not been checked.
* **Optional output mute on pause** (STIMULUS→MUTE OUTPUT ON PAUSE, default off): finishes the
  current scan, then disables the Si5351 outputs while paused
  ([#50](https://github.com/DiSlord/NanoVNA-D/issues/50)).
* **Touch double-tap filter** — accidental rapid re-taps ignored (100 ms window,
  [#109](https://github.com/DiSlord/NanoVNA-D/issues/109)).
* **Consistent stored-file viewing**: changing the stimulus while displaying an `.s1p`/`.s2p`
  loaded from SD resumes live sweep instead of desyncing axes and markers
  ([#101](https://github.com/DiSlord/NanoVNA-D/issues/101)).
* **Fix sweep hang after ~12 h uptime** (32-bit system-time wrap,
  [#110](https://github.com/DiSlord/NanoVNA-D/issues/110)).
* **`CLOCK_GEN` build option** for boards with an MS5351/SWC5351 clock chip (see Build below,
  [#54](https://github.com/DiSlord/NanoVNA-D/issues/54)).
* **SWR ANT trace format** (DISPLAY→FORMAT→SWR ANT) — the SWR at the far end of the feedline,
  de-embedded from the measured S11 using the one-way cable loss you enter in
  DISPLAY→FORMAT→CABLE LOSS (dB, matched loss at the band in use; from the cable's data sheet or
  a MEASURE→CABLE run). Feedline loss attenuates the reflected wave twice, so a lossy coax always
  reads a better SWR than the antenna has: |Γ_ant| = |Γ_meas|·10^(L/10). Run SWR and SWR ANT as two
  traces to see the difference. The trace is blank and the marker reads `set CABLE LOSS` until a
  loss is entered; the value is not saved across power cycles because it is cable- and band-specific.
  Accuracy is set by how well you know L: ±0.2 dB moves a true 2:1 by ±0.07, a 3:1 by ±0.2, and
  a 10:1 by several units — the reading is reliable below about 5:1. Use a common-mode choke at the
  feedpoint; without one the coax shield is part of the antenna being measured. Console:
  `trace 0 swrant`.
* **Coax presets for SWR ANT** (H4 only): DISPLAY→FORMAT→CABLE TYPE cycles MANUAL / LMR‑400 /
  RG‑213 / RG‑8X / RG‑58 / RG‑174‑316; with a type selected and CABLE LENGTH (metres) entered, the
  loss is computed per sweep point from ARRL Antenna Book Vol. 3 Table 23.4 (interpolated on √f),
  so it follows band changes without re-entry; the CABLE LOSS button shows the value at sweep
  centre, and typing a loss there returns to MANUAL. The table is for new, dry, name-brand cable —
  old, wet or off-brand coax can be markedly worse; measure it (MEASURE→CABLE, antenna disconnected)
  when in doubt. Host test: `gcc -Wall -Wextra -Werror -o /tmp/test_coax tests/test_coax.c -lm && /tmp/test_coax`.
* **SWR BW measure** (MEASURE→SWR BW (S11)) — bandwidth and Q of an SWR dip. Walks from the
  active marker to the nearest minimum (deepest dip in the sweep if no marker is active), reports
  f₀ and minimum SWR, the 2:1 and 3:1 edge frequencies and bandwidths (an edge outside the sweep
  is flagged, so widen the sweep), and the bandwidth quality factor Q. A narrow, deep dip is a
  high-Q, low-loss antenna; a broad, shallow one means something in the system is dissipating —
  loss makes an antenna easier to match, so a good SWR curve is not by itself a good antenna.
  Q follows Yaghjian & Best (fractional VSWR-s bandwidth = 2√β/Q, β = (s−1)²/4s), generalized
  to use the measured R at the dip rather than assuming a 50 Ω match, which makes it exact for
  a series-RLC dip at any minimum SWR; 2:1 and 3:1 give the same Q when the dip is RLC-like.
  Always on for the H4; opt-in for the H (`__S11_SWR_BW_MEASURE__` in `nanovna.h`, ~1.4 KB,
  which consumes essentially all of the H's remaining flash).
  Host test: `gcc -Wall -Wextra -Werror -o /tmp/test_swr_bw tests/test_swr_bw.c -lm && /tmp/test_swr_bw`.

Design/plan documents for the larger features live in `docs/superpowers/`, and host-side table
tests in `tests/` (`gcc -Wall -Wextra -Werror -o /tmp/test_hambands tests/test_hambands.c && /tmp/test_hambands`).

## User manual

**Read it here:** [PDF](https://github.com/StephenGenusa/NanoVNA-D/releases/download/v1.2.54-sg/NanoVNA-manual-1.2.54-sg.pdf) ·
[single-file HTML](https://github.com/StephenGenusa/NanoVNA-D/releases/download/v1.2.54-sg/NanoVNA-manual-1.2.54-sg.html)
(both attached to the [v1.2.54-sg release](https://github.com/StephenGenusa/NanoVNA-D/releases/tag/v1.2.54-sg)).

A manual written from the firmware source lives in [`docs/manual/`](docs/manual/00-front.md):
every menu, trace format, console command and status letter is taken from the code that
implements it and footnoted to it, with the original NanoVNA guide's procedures checked
against the code and reworded. Start at [`00-front.md`](docs/manual/00-front.md). Chapters:
[orientation](docs/manual/01-orientation.md) (screen, status letters, wheel, touch),
[trace formats](docs/manual/02-trace-formats.md), [calibration](docs/manual/03-calibration.md),
[markers](docs/manual/04-markers.md), [MEASURE panels](docs/manual/05-measure.md),
[fork features](docs/manual/06-fork-features.md), [SD card](docs/manual/07-sd-card.md),
[console commands](docs/manual/08-console.md), [menu map](docs/manual/09-menu-map.md) with a
mockup of every menu on both devices, and [firmware update](docs/manual/10-firmware-update.md).
[`GUIDES/`](GUIDES/) is a pack of 27 reference pages for the SD card — antenna tuning and
radials, POTA/SOTA field rules and safety, choke recipe and measurement, coax loss, SWR and
formula cards, the device's own formats and commands — that the H4 shows on screen via
SD CARD → LOAD → GUIDE. They are plain markdown you can extend (manual chapter 7).
Sweep screens in the chapters are rendered from modelled circuits by
[`tools/manual/screen.py`](tools/manual/screen.py), which reproduces the firmware's drawing code
pixel for pixel and is regression-tested against real H4 screenshots.

The menu map, console reference and trace-format table are generated by the scripts in
`tools/manual/` (`make -C docs/manual all`) and checked against the source by
`python3 -m unittest tests.test_manual_gen`, so they cannot drift from the firmware.
`make -C docs/manual dist` builds the PDF and HTML (pandoc + XeLaTeX).

References for the antenna-measurement features:

* A. D. Yaghjian and S. R. Best, "Impedance, Bandwidth, and Q of Antennas," *IEEE Trans.
  Antennas Propag.*, vol. 53, no. 4, pp. 1298–1324, Apr. 2005.
* A. D. Yaghjian, "Fundamentals of Antenna Bandwidth and Quality Factor," arXiv:2501.03146
  (2025), eq. 7, 12, 21 — open-access restatement of the above.
* M. W. Maxwell, W2DU, *Reflections III: Transmission Lines and Antennas*, Appendix 6 — the
  SWR-through-line-loss relation used by SWR ANT (3:1 through 0.5 dB reads 2.61:1).
* ARRL Antenna Book, Vol. 1, "Q of Antennas" — the 2:1 SWR bandwidth convention.
* ARRL Antenna Book, Vol. 3, Table 23.4, "Cable Attenuation (dB per 100 feet)" — the coax preset
  figures (stored converted to dB per 100 m).

## Prebuilt Firmware

`binaries/` holds the current release builds with SHA-256 checksums:

    binaries/NanoVNA-H_1.2.54-sg.bin    NanoVNA-H  (STM32F072)
    binaries/NanoVNA-H4_1.2.54-sg.bin   NanoVNA-H4 (STM32F303)

`.hex` versions are alongside for tools that want them. Flash the `.bin` with dfu-util at
`0x08000000` (see Flash Firmware below, or `./2_prog.sh`). Releases on GitHub carry the same
files as assets. **Re-do calibration after flashing** (see the S21 note above).

## Prepare ARM Cross Tools

**UPDATE**: Recent gcc version works to build NanoVNA, no need to use old version.

### MacOSX

Install cross tools and firmware updating tool.

    brew tap px4/px4
    brew install gcc-arm-none-eabi-80
    brew install dfu-util

### Linux (ubuntu)

Download arm cross tools from [here](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads).

    wget https://developer.arm.com/-/media/Files/downloads/gnu-rm/8-2018q4/gcc-arm-none-eabi-8-2018-q4-major-linux.tar.bz2
    sudo tar xfj gcc-arm-none-eabi-8-2018-q4-major-linux.tar.bz2 -C /usr/local
    PATH=/usr/local/gcc-arm-none-eabi-8-2018-q4-major/bin:$PATH
    sudo apt install -y dfu-util

### Debian

    sudo apt install gcc-arm-none-eabi
    sudo apt install -y dfu-util

## Fetch Source Code

Do this once to initialize your local clone from GitHub (ChibiOS and FatFS are vendored
in-tree — no submodules to fetch):

    git clone https://github.com/StephenGenusa/NanoVNA-D.git
    cd NanoVNA-D

## Update Source Code

To get updates from the GitHub repository, go to your `NanoVNA-D` directory and type:

    git pull

## Build the NanoVNA-H Firmware

Go to your `NanoVNA-D` directory and type:

    export TARGET=F072
    make clean
    make

## Build the NanoVNA-H4 Firmware

Go to your `NanoVNA-D` directory and type:

    export TARGET=F303
    make clean
    make

For boards populated with an MS5351 or SWC5351 clock generator (e.g. HW version 4.3_MS),
bake in the matching default (also switchable at runtime via CONFIG→MODE):

    make TARGET=F303 CLOCK_GEN=MS5351

## Helper Scripts

Three scripts in the repository root wrap the common workflow (each takes `F072` or `F303`
as argument):

    ./0_backup_firmware.sh   # back up the device's current firmware over DFU (default F072)
    ./1_build.sh             # clean build -> build/H4.bin or build/H.bin      (default F303)
    ./2_prog.sh              # flash the built firmware via dfu-util           (default F303)

`1_build.sh` adds the ARM toolchain to `PATH` itself if it finds one under `/usr/local` or `/opt`.

## Flash Firmware

When the build of your firmware is finished, you can flash it onto your NanoVNA device.
First, let the device enter DFU mode by one of following methods.

* Open the device and jumper `BOOT0` pin to `Vdd` pin when powering the device.
* Select menu Config->DFU (needs recent firmware).
* Press the jog switch on your -H4 when powering the device.

Then, flash the firmware using `dfu-util` via USB.

#### For NanoVNA-H:

Go to your `NanoVNA-D` directory and type:

    dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D build/H.bin

#### For NanoVNA-H4:

Go to your `NanoVNA-D` directory and type:

    dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D build/H4.bin

#### Or simply type directly after building the firmware (for both variants).

Go to your `NanoVNA-D` directory and type:

    make flash

#### Ignore the apparent error message during flashing

The low-level tool `dfu-util` displays a lot of information that is very useful especially for developers, but can confuse the user.
In particular, please ignore the message about corrupt firmware, this is the normal behaviour of the unit before clearing the status.
It is important to note that after clearing the status, there is no longer an error condition present.

```
...
Determining device status...
DFU state(10) = dfuERROR, status(10) = Device's firmware is corrupt. It cannot return to run-time (non-DFU) operations
Clearing status
Determining device status...
DFU state(2) = dfuIDLE, status(0) = No error condition is present
...
```

## Companion Tools

There are several numbers of great companion PC tools from third-party.
* `tools/vna/` — fork-authored PC scripts that drive the device over the USB console, e.g.
  `resonance_log.py` (log f0 and R at X = 0 across ground-system changes, with the dB gain of
  each step); see `tools/vna/README.md`.

* [NanoVNA-App software](https://github.com/OneOfEleven/NanoVNA-H/blob/master/Release/NanoVNA-App.rar) by OneOfEleven
* [NanoVNASharp Windows software](https://drive.google.com/drive/folders/1IZEtx2YdqchaTO8Aa9QbhQ8g_Pr5iNhr) by hugen79
* [NanoVNA WebSerial/WebUSB](https://github.com/cho45/NanoVNA-WebUSB-Client) by cho45
* [Android NanoVNA app](https://play.google.com/store/apps/details?id=net.lowreal.nanovnawebapp) by cho45
* [NanoVNASaver](https://github.com/NanoVNA-Saver/nanovna-saver) by mihtjel and the members of NanoVNA-Saver
* [TAPR VNAR4](https://groups.io/g/nanovna-users/files/NanoVNA%20PC%20Software/TAPR%20VNA) supports NanoVNA by erikkaashoek
* [The NanoVNA toolbox](https://github.com/Ho-Ro/nanovna-tools) by Ho-Ro
* see [python](/python/README.md) directory to use NanoVNA with Python and Jupyter Notebook.

## Documentation

* [This firmware's user manual](docs/manual/00-front.md) — written from the source; see *User manual* above.
* [NanoVNA User Guide(ja)](https://cho45.github.io/NanoVNA-manual/) by cho45. [(en:google translate)](https://translate.google.com/translate?sl=ja&tl=en&u=https%3A%2F%2Fcho45.github.io%2FNanoVNA-manual%2F)
* [NanoVNA user group](https://groups.io/g/nanovna-users/topics) on groups.io.

## Reference

* [Schematics](/doc/nanovna-sch.pdf)
* [PCB Photo](/doc/nanovna-pcb-photo.jpg)
* [Block Diagram](/doc/nanovna-blockdiagram.png)
* Kit available from https://ttrf.tk/kit/nanovna

## Note

Hardware design material is disclosed to prevent bad quality clone. Please let me know if you would have your own unit.

## Credit
* [@DiSlord](https://github.com/DiSlord/)

## Based on code from:
* [@edy555](https://github.com/edy555)

### Contributors
* [@OneOfEleven](https://github.com/OneOfEleven)
* [@hugen79](https://github.com/hugen79)
* [@cho45](https://github.com/cho45)

