#!/bin/bash
# Detect which NanoVNA is attached in DFU mode, from the flash layout the STM32
# bootloader reports through dfu-util. Sourced by 0_backup_firmware.sh and 2_prog.sh.
#
#   STM32F072xB (NanoVNA-H)  : "@Internal Flash  /0x08000000/064*0002Kg"  (64 x 2 KB = 128 KB)
#   STM32F303xC (NanoVNA-H4) : "@Internal Flash  /0x08000000/128*0002Kg"  (128 x 2 KB = 256 KB)
#
# detect_target prints F072 or F303 on stdout and returns 0; on any doubt (no DFU device,
# more than one, or an unfamiliar layout) it explains on stderr and returns 1 so the caller
# can ask for an explicit target instead of guessing.

detect_target() {
  local dfu="${DFU_UTIL:-$(command -v dfu-util || true)}"
  [ -x "$dfu" ] || { echo "dfu-util not found; install with: sudo apt install dfu-util" >&2; return 1; }

  local layouts
  layouts=$("$dfu" -l 2>/dev/null | grep -o '@Internal Flash */0x08000000/[0-9]*\*[0-9]*K[a-z]' | sort -u || true)

  local n
  n=$(printf '%s\n' "$layouts" | grep -c . || true)
  if [ "$n" -eq 0 ]; then
    echo "No NanoVNA in DFU mode found (USB 0483:df11). Put it in DFU mode first" >&2
    echo "(CONFIG -> DFU on the device, or hold the jog switch while powering on)." >&2
    return 1
  fi
  if [ "$n" -gt 1 ]; then
    echo "More than one DFU device attached; pass the target explicitly (F072 or F303)." >&2
    return 1
  fi

  case "$layouts" in
    *"/064*0002K"*) echo F072 ;;
    *"/128*0002K"*) echo F303 ;;
    *)
      echo "Unfamiliar flash layout '$layouts'; pass the target explicitly (F072 or F303)." >&2
      return 1 ;;
  esac
}

# Human-readable name for a target
target_name() {
  case "$1" in
    F072) echo "STM32F072 (NanoVNA-H, 128 KB flash)" ;;
    F303) echo "STM32F303 (NanoVNA-H4, 256 KB flash)" ;;
    *)    echo "$1" ;;
  esac
}
