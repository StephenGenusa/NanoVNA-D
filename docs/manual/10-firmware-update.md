# Updating the firmware

The NanoVNA's STM32 has a USB bootloader in ROM ("DFU mode"). Put the device into DFU mode,
connect it by USB, and a PC tool writes a new firmware image into flash. The nanovna.com guide
describes this with ST's Windows *DfuSe* tool;[^guide] this chapter uses `dfu-util`, which runs on
Linux, macOS and Windows, and the scripts in this repository that wrap it. The procedure was
run on a new NanoVNA‑H4 on 2026‑08‑26 (backup, flash, verify, recalibrate).

**The H and the H4 take different images.** `NanoVNA-H_*.bin` is for the NanoVNA‑H
(STM32F072, 2.8″ screen); `NanoVNA-H4_*.bin` for the NanoVNA‑H4 (STM32F303, 4″). The bootloader
will not stop you flashing the wrong one; it simply won't run. If that happens, enter DFU mode
with the button (below) and flash the right image.

## 1. Enter DFU mode

Three ways; all end with a **blank screen** and the device enumerating on USB as
`0483:df11` (STMicroelectronics DFU):

- **From the menu:** CONFIG → EXPERT → DFU → **RESET AND ENTER DFU**.[^menu]
- **From the console:** `reset dfu`.
- **With the button, when the firmware won't start:** hold the jog wheel pressed while
  switching the power on (H4; the guide describes this as "engineering mode"). On older
  NanoVNA‑H boards without that behaviour, short the `BOOT0` pad to `VDD` on the PCB while
  powering on, as the guide shows.

Check with `lsusb` (or `dfu-util -l`): you should see `0483:df11`.

## 2. Back up what is there

Before writing anything, read the whole flash out — it contains the current firmware *and*
the configuration and calibration slots in the upper pages, so the backup can restore the
device exactly as it was:

    ./0_backup_firmware.sh F303      # NanoVNA-H4;  ./0_backup_firmware.sh (no argument) = NanoVNA-H

The script runs `dfu-util` in upload mode and writes a timestamped `.bin` into
`firmware_backups/`. Check the file is the full flash size (256 KB for the H4, 128 KB for
the H) before continuing. To restore it later:
`dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D <backup.bin>`. The bootloader refuses to
read flash out if read-out protection is set; stock firmware does not set it.[^backup]

## 3. Flash the new image

Either build it (`./1_build.sh` for the H4, `./1_build.sh F072` for the H — see the README's
build section) or download it from the release page, checking `SHA256SUMS`. Then:

    ./2_prog.sh            # flashes build/H4.bin
    ./2_prog.sh F072       # flashes build/H.bin

which runs `dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D <image>`; `:leave` makes the
device reboot into the new firmware when the write completes. To flash a downloaded release
image directly, run that `dfu-util` line with the release file.[^prog]

If `dfu-util` reports "no DFU capable USB device", the device is not in DFU mode (repeat
step 1), or on Linux the USB device needs a udev rule / root to be accessible.

## 4. Verify

Power-cycle if the device did not restart on its own. **CONFIG → VERSION** shows the version
string (this firmware: `1.2.54-sg` and later, with the build date) and the board and chip
lines; `version` on the console prints the same string.

## 5. Recalibrate

A firmware update does not touch the calibration slots, but two things mean you should
calibrate again:

- this firmware's raw S21 sign differs from stock DiSlord builds, so a THRU calibration made
  by older firmware gives S21 phase 180° off until THRU is re-done ([chapter 6](06-fork-features.md));
- a calibration is only as good as the day it was made, and a flash is a natural moment to
  refresh it.

CALIBRATE → RESET, then the full procedure in [chapter 3](03-calibration.md), and save to
slot 0.

## Going back

Flash the backup from step 2 the same way (`dfu-util … -D <backup.bin>`); it restores the
previous firmware and the slots. Stock DiSlord releases are at
[github.com/DiSlord/NanoVNA-D/releases](https://github.com/DiSlord/NanoVNA-D/releases).

---

[^guide]: "Upgrade NanoVNA use DFU", nanovna.com (mirrored): DfuSe from ST, the BOOT0/VDD jumper or the CONFIG → DFU menu for the H, hold-the-switch-at-power-on for the H4, and the "different firmware for 2.8″ and 4″" warning — all restated here.
[^menu]: `ui.c` `menu_dfu[]`: "RESET AND ENTER DFU" → `menu_dfu_cb`; console `reset dfu` in `main.c` `cmd_reset`.
[^backup]: `0_backup_firmware.sh` (repository root): `dfu-util -a 0 -s 0x08000000:<size> -U <file>`; flash sizes 128 KB (F072) / 256 KB (F303).
[^prog]: `2_prog.sh`: `dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D build/H4.bin` (default F303 since 1.2.54‑sg).
