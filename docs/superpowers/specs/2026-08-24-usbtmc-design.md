# USBTMC/USB488 Support (build-time opt-in) — Design Spec

**Date:** 2026-08-24
**Status:** Proposed (awaiting review — largest feature specced in this line of work)
**Origin:** Issue DiSlord/NanoVNA-D#98 — request for "GPIB-like" visibility in
NI-VISA software. Physical GPIB is impossible (no IEEE-488 hardware); the
VISA-native equivalent is the USBTMC device class with the USB488 subclass,
which enumerates automatically as a `USB0::<vid>::<pid>::<serial>::INSTR`
resource in NI-MAX / pyvisa, driverless. The `*IDN?` shell command (shipped,
commit 69a3b8f) already covers VISA-over-serial; this spec covers full
instrument-class enumeration.

## Problem

VISA-based tools (LabVIEW, MATLAB Instrument Toolbox, pyvisa) only see the
NanoVNA as a raw COM port (`ASRLn::INSTR`) with no standard protocol. Generic
instrument software expects a USBTMC `INSTR` resource speaking 488.2. Today
only purpose-built apps (Solver64, NanoVNA-App, -Saver) can talk to it.

## Decisions

### Opt-in build flag, default OFF
```c
// Add USBTMC/USB488 instrument class (VISA support), composite with CDC serial.
// Default disabled: adds ~5 KB flash. Not available on F072 (flash full).
//#define __USE_USBTMC__
```
in `nanovna.h` next to the other commented-out options (`__USE_FREQ_TABLE__`
pattern). Uncommenting it turns the feature on. Guard block adds:
```c
#if defined(__USE_USBTMC__) && !defined(NANOVNA_F303)
#error "__USE_USBTMC__ requires the F303 target (F072 flash budget exceeded)"
#endif
```
Default builds of both targets are **byte-identical to today**. The H4 can
opt in (~49 KB flash free); the H cannot (2.7 KB free vs ~5 KB needed) and
fails loudly rather than silently overflowing.

### Composite device: CDC + USBTMC, both live
The existing CDC-ACM interface pair stays untouched so NanoVNA-App/-Saver/
Solver64 keep working with a TMC-enabled build. Descriptor changes in
`usbcfg.c` (all under the guard):
- Device class becomes composite/IAD (`0xEF/0x02/0x01`), `bcdDevice` bumped
  (0x0200) so Windows re-reads cached descriptors under the same VID/PID
  (0x0483:0x5740). Residual risk: a machine with a stale driver cache may
  need a one-time "uninstall device" in Device Manager — documented, not
  engineered around.
- Interfaces 0–1: existing CDC (comm + data) wrapped in an IAD.
- Interface 2: USBTMC (`bInterfaceClass 0xFE`, `bInterfaceSubClass 0x03`
  = USBTMC, `bInterfaceProtocol 0x01` = USB488).
- Endpoints: **EP3 bulk-OUT + bulk-IN (64 B)** for TMC messages, **EP4
  interrupt-IN** for USB488 `READ_STATUS_BYTE` responses. (CDC keeps EP1
  bulk + EP2 interrupt; STM32F303 USB has 8 endpoints — fits.)
- `usbcfg.usbcfg.requests_hook` becomes a dispatcher: TMC class requests
  (by `wIndex` = interface 2) → new TMC handler; everything else →
  existing `sduRequestsHook`.

### Protocol scope (what "USBTMC support" means here)
Mandatory USBTMC control requests implemented: `INITIATE_ABORT_BULK_OUT/IN`,
`CHECK_ABORT_BULK_OUT/IN_STATUS`, `INITIATE_CLEAR`, `CHECK_CLEAR_STATUS`,
`GET_CAPABILITIES`. USB488: `READ_STATUS_BYTE` (via EP4 per spec).
Capabilities report: no TRIGGER, no REN_CONTROL/local-lockout, not
talk-only/listen-only — the minimal legal USB488 instrument. Bulk protocol:
`DEV_DEP_MSG_OUT` (host→device command), `REQUEST_DEV_DEP_MSG_IN` +
`DEV_DEP_MSG_IN` (device→host response) with correct bTag handling,
transfer-size honoring, and EOM flags. `VENDOR_SPECIFIC_*` rejected.

### Command layer: tunnel the shell, add 488.2 common commands
No SCPI command tree is invented. A TMC `DEV_DEP_MSG_OUT` payload is one
**existing shell command line** — the same 63-command protocol every NanoVNA
tool already speaks (`sweep`, `data`, `frequencies`, `marker`, ...), so VISA
users get the full documented capability surface on day one, and
`viWrite("sweep 1000000 30000000 101")` / `viRead` works exactly like the
serial console.

The 488.2 mandatory common commands are intercepted in the TMC layer before
shell dispatch (they are not valid shell syntax): `*IDN?` (delegates to the
existing `cmd_idn`), `*RST` (delegates to existing `reset` semantics minus
reboot: load defaults via `load 0`-equivalent — exact mapping decided at
implementation), `*CLS`, `*ESR?`, `*ESE`/`*ESE?`, `*SRE`/`*SRE?`, `*STB?`,
`*OPC`/`*OPC?`, `*WAI`, `*TST?` (returns 0). Status model: minimal 488.2
Standard Event / Status Byte registers backing `*ESR?`/`*STB?`/
`READ_STATUS_BYTE` — command-error and query-error bits, MAV bit when a
response is pending. No SRQ generation (capability declared absent).

### Data path and RAM
New include-fragment **`vna_modules/vna_usbtmc.c`**, included from
`usbcfg.c` under the guard (no Makefile changes, matching every other
module). It implements a **TMC response stream**: shell output is captured
by pointing `shell_stream` at a small TMC-backed `BaseSequentialStream`
whose writes fill EP-sized chunks and release them as `DEV_DEP_MSG_IN`
transfers sized to the host's request — i.e. responses are **streamed, not
buffered whole**, so a 401-point `data` dump (~20 KB of text) works without
a 20 KB buffer. RAM cost: EP buffers (3 × 64 B) + TMC state (~100 B) +
one 512 B staging buffer — under 1 KB, static, F303 only. Command lines
arriving via `DEV_DEP_MSG_OUT` reuse the existing shell line buffer path
(same entry as `VNAShell_executeLine`), serialized with the console: a TMC
transaction owns the shell while executing (console input is not
interleaved mid-command — same mutual exclusion the SD script loader uses).

### What does NOT change
- Default builds: byte-identical firmware for both targets.
- `config_t`, UI, menus: untouched — this is build-time only, no runtime
  toggle (a VNA_MODE bit could be added later if anyone wants to disable
  TMC without reflashing).
- The CDC shell, serial console (`VNA_MODE_CONNECTION`), and all existing
  host software behavior.

### Validation
- Host-side: none possible for USB protocol; logic that is host-testable
  (488.2 status register model, common-command parser) goes in the fragment
  under a `USBTMC_HOST_TEST` guard with a `tests/test_usbtmc.c` runner
  (same pattern as `tests/test_hambands.c`).
- Acceptance: `tests/visa_acceptance.py` (pyvisa, run manually against a
  flashed H4): resource discovery (`USB0::0x0483::0x5740::...::INSTR`
  present), `*IDN?` query, `*STB?`/`*OPC?`, a `sweep`+`data 0` tunnel
  round-trip with >16 KB read, abort/clear recovery, and CDC-still-works
  (serial `version` query on the same enumeration).
- Build matrix: default F072 + F303 (byte-identical to pre-feature),
  TMC-enabled F303 (builds, size recorded), TMC-enabled F072 (#error).

## Out of scope
- A real SCPI command tree (`:SENSe:FREQuency:STARt` etc.) — the shell
  tunnel is the contract; a SCPI façade can layer on later without
  protocol changes.
- SRQ/service-request generation, TRIGGER, REN/local-lockout (capabilities
  declared absent — legal per USBTMC/USB488).
- USBTMC on F072, Ethernet/LXI, and any runtime enable/disable UI.
- NI driver-cache remediation beyond the documented Device Manager note.

## Risks
- **Windows driver-cache confusion** on machines that saw the CDC-only
  device: mitigated by bcdDevice bump; documented fallback (uninstall
  device once). Worst case is cosmetic (COM port renumbering).
- **ChibiOS has no TMC class driver** — the state machine is written from
  scratch against the USBTMC 1.0 / USB488 specs (TinyUSB's implementation
  used as reference). This is the bulk of the effort and the main schedule
  risk.
- **Host quirk matrix** (NI-VISA vs pyvisa-py vs Keysight IO Libraries):
  mitigated by declaring the minimal capability set (fewer optional paths
  to get wrong) and the pyvisa acceptance script; NI-VISA on Windows is
  the reference target.
- **Shell contention** (console + TMC both active): serialized via the
  existing mutex pattern; a stuck TMC host cannot wedge the console
  because aborts/clear reset the TMC state machine without touching the
  shell thread.

## Effort estimate
~5 KB flash, <1 KB RAM (F303 only). Implementation is dominated by the TMC
bulk state machine and Windows/NI-VISA validation; expect the plan to break
into: (1) host-testable 488.2 status/common-command module, (2) composite
descriptors + enumeration (lsusb/NI-MAX visible, no data path), (3) bulk
OUT command path, (4) streamed IN response path, (5) aborts/clear/status,
(6) acceptance script + docs. Each stage leaves default builds untouched.
