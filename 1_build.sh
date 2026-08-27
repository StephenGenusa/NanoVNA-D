#!/bin/bash
# Clean the build area and do a complete build of the NanoVNA firmware.
#
# Usage:
#   ./1_build.sh            # builds NanoVNA-H  (TARGET=F072, default) -> build/H.bin
#   ./1_build.sh F303       # builds NanoVNA-H4 (TARGET=F303)          -> build/H4.bin
#   TARGET=F303 ./1_build.sh
set -euo pipefail
cd "$(dirname "$0")"

# Find the ARM toolchain if it is not already on PATH
if ! command -v arm-none-eabi-gcc >/dev/null 2>&1; then
  for d in /usr/local/gcc-arm-none-eabi-*/bin /opt/gcc-arm-none-eabi-*/bin; do
    if [ -x "$d/arm-none-eabi-gcc" ]; then PATH="$d:$PATH"; export PATH; break; fi
  done
fi
command -v arm-none-eabi-gcc >/dev/null 2>&1 || { echo "arm-none-eabi-gcc not found; install the ARM toolchain (see README)" >&2; exit 1; }

TARGET="${1:-${TARGET:-F072}}"
case "$TARGET" in
  F072) BIN=build/H.bin ;;
  F303) BIN=build/H4.bin ;;
  *) echo "Unknown TARGET '$TARGET' (expected F072 or F303)" >&2; exit 1 ;;
esac

echo "==> Cleaning build area"
make TARGET="$TARGET" clean
rm -rf build .dep

echo "==> Building TARGET=$TARGET"
make -j"$(nproc)" TARGET="$TARGET"

echo
echo "==> Build complete: $BIN ($(stat -c %s "$BIN") bytes)"
