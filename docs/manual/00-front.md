# NanoVNA‑H / NanoVNA‑H4 User Manual

**Firmware: NanoVNA‑D 1.2.57‑sg** (StephenGenusa fork of DiSlord's NanoVNA‑D)

## What this is

A manual for the NanoVNA‑H and NanoVNA‑H4 vector network analyzers as they behave with this
firmware. It was written from the firmware's source code — every menu, format, command and
status letter is taken from the tables and functions that implement it, and each chapter's
footnotes name them — with the procedures from the original NanoVNA user guide
(cho45, nanovna.com translation) checked against the code and reworded. Menu mockups are drawn
from the firmware's own layout rules and fonts and are labelled simulated. Sweep screens
labelled *rendered* are drawn by a renderer that follows the firmware's own drawing code
pixel for pixel (grid, traces, markers, readouts, status column) from a modelled circuit — a
dipole, a load, a filter; it is checked against real screenshots (`tests/test_screen_render.py`).
Screens labelled *captured* are screenshots of a real NanoVNA-H4. Anything not established from
the code is marked `[verify on hardware]`.

The firmware is DiSlord's NanoVNA‑D with additions made in this fork by a new NanoVNA user;
DiSlord did the heavy lifting. Chapter 6 describes the additions and appendix A lists which
sections are fork-only, so a reader on stock DiSlord firmware knows what they will not see.

## Chapters

1. [Orientation](01-orientation.md) — the screen, the status letters, the jog wheel, touch, keypads
2. Sweep and traces — stimulus and the [trace formats](02-trace-formats.md)
3. [Calibration](03-calibration.md)
4. [Markers](04-markers.md)
5. [MEASURE panels](05-measure.md)
6. [Features added in this fork](06-fork-features.md)
7. [The SD card](07-sd-card.md)
8. [Console commands](08-console.md) (generated)
9. [Menu map](09-menu-map.md) (generated, with a mockup of every menu)
10. [Updating the firmware](10-firmware-update.md)

## Safety and care

- **It transmits.** The sweep source (STIMULUS → POWER selects 2–8 mA of clock-generator
  drive; chapter 1's `P` status letter) radiates from whatever antenna is connected while
  the sweep runs. It is a low-level signal, but be aware of it near receivers; this fork can
  mute the source while paused (chapter 6).
- **It is a small-signal instrument.** Never connect the ports to a live transmitter or to an
  antenna during a nearby transmission, and discharge long antennas and cables before
  connecting them. Static from a coiled coax on a dry day is enough to damage the input.
- **Battery.** The internal cell is lithium; charge over USB, keep the unit out of a hot car,
  and watch the icon (chapter 1). A low-battery colour means charge before it shuts off
  mid-measurement.
- **SMA connectors** are rated for a finite number of matings and for finger-tight torque with
  the supplied wrench; use SMA "savers" (short adapters) on the ports if you connect and
  disconnect often, and calibrate at the saver's face.
- **Firmware updates** cannot brick the device — the USB bootloader is in ROM — but they can
  leave it unresponsive until the correct image is flashed (chapter 10).

## Conventions

Menu paths are written **DISPLAY → FORMAT → SWR**. Console commands are in `monospace`.
"CH0" is the port that both reflection (S11) and the source use; "CH1" is the receive port
for transmission (S21). Both devices are described together; where they differ the text says
"H" or "H4". Chapter footnotes cite `file.c` `function()` in the firmware source.
