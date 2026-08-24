#!/bin/bash
# Back up the firmware currently on a NanoVNA by reading its entire flash
# over DFU (dfu-util "upload", device -> host).
#
# The dump includes the firmware AND the config/calibration slots stored in
# the upper flash pages, so it can be restored later with:
#   dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D <backup.bin>
#
# Usage:
#   ./0_backup_firmware.sh            # NanoVNA-H  (F072, 128 KB flash, default)
#   ./0_backup_firmware.sh F303       # NanoVNA-H4 (F303, 256 KB flash)
#   ./0_backup_firmware.sh F072 my.bin   # optional explicit output filename
#   TARGET=F303 ./0_backup_firmware.sh
#
# Put the device in DFU mode first (jumper BOOT0 to Vdd at power-on, or
# CONFIG -> DFU from the device menu). It enumerates as USB 0483:df11.
#
# NOTE: If the device's flash read-out protection (RDP) is enabled the
# bootloader refuses uploads and dfu-util will fail; stock NanoVNA firmware
# does not set RDP, so this normally works.
set -euo pipefail
cd "$(dirname "$0")"

TARGET="${1:-${TARGET:-F072}}"
case "$TARGET" in
  F072) FLASH_SIZE=0x20000; MODEL=H  ;;   # STM32F072xB: 128 KB
  F303) FLASH_SIZE=0x40000; MODEL=H4 ;;   # STM32F303xC: 256 KB
  *) echo "Unknown TARGET '$TARGET' (expected F072 or F303)" >&2; exit 1 ;;
esac

BACKUP_DIR=firmware_backups
OUT="${2:-$BACKUP_DIR/NanoVNA-${MODEL}_$(date +%Y%m%d_%H%M%S).bin}"

DFU_UTIL="${DFU_UTIL:-$(command -v dfu-util || true)}"
[ -x "$DFU_UTIL" ] || { echo "dfu-util not found; install with: sudo apt install dfu-util" >&2; exit 1; }
[ -e "$OUT" ] && { echo "$OUT already exists; refusing to overwrite" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"

echo "==> Reading $FLASH_SIZE bytes of flash from NanoVNA-$MODEL into $OUT"
"$DFU_UTIL" -d 0483:df11 -a 0 -s "0x08000000:$FLASH_SIZE" -U "$OUT"

SIZE=$(stat -c %s "$OUT")
echo
echo "==> Backup complete: $OUT ($SIZE bytes)"
[ "$SIZE" -eq $((FLASH_SIZE)) ] || echo "WARNING: expected $((FLASH_SIZE)) bytes, got $SIZE" >&2
