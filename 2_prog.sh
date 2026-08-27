#!/bin/bash
# Flash the built firmware to a NanoVNA in DFU mode using dfu-util.
# (Based on the original prog.sh, updated for the current build outputs.)
#
# Usage:
#   ./2_prog.sh             # flashes build/H4.bin (NanoVNA-H4, TARGET=F303, default)
#   ./2_prog.sh F072        # flashes build/H.bin  (NanoVNA-H,  TARGET=F072)
#   TARGET=F072 ./2_prog.sh
#
# Put the device in DFU mode first (jumper BOOT0 to Vdd at power-on, or
# CONFIG -> DFU from the device menu). It enumerates as USB 0483:df11.
set -euo pipefail
cd "$(dirname "$0")"

TARGET="${1:-${TARGET:-F303}}"
case "$TARGET" in
  F072) BIN=build/H.bin ;;
  F303) BIN=build/H4.bin ;;
  *) echo "Unknown TARGET '$TARGET' (expected F072 or F303)" >&2; exit 1 ;;
esac

DFU_UTIL="${DFU_UTIL:-$(command -v dfu-util || true)}"
[ -x "$DFU_UTIL" ] || { echo "dfu-util not found; install with: sudo apt install dfu-util" >&2; exit 1; }
[ -f "$BIN" ]      || { echo "$BIN not found; run ./1_build.sh $TARGET first" >&2; exit 1; }

echo "==> Flashing $BIN with $DFU_UTIL"
"$DFU_UTIL" -d 0483:df11 -a 0 -s 0x08000000:leave -D "$BIN"
