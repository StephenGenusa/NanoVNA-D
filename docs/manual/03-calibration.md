# Calibration

A VNA measures the signal that comes back from a port and the signal that gets through to
the other port. Between the measuring circuits and your device sit connectors, cables and the
instrument's own imperfections, all of which add their own reflections and losses. Calibration
measures known standards through that same path and computes the correction that removes it,
so that what is displayed is the device under test alone. This chapter explains what the
NanoVNA measures for each standard, what it computes, when the correction stops being valid,
and how to save and recall it. The mathematics is DiSlord's implementation in `main.c`; the
procedure is the same one the original NanoVNA guide describes.[^guide]

## When to calibrate

Calibrate **after connecting the cables and adapters you will measure through**, at the
**frequency range and point count you will use**. A calibration is a set of corrections, one
per sweep point, taken at specific frequencies; it is exactly right only at those frequencies.
You need a new calibration when you:

- change the cable, adapter or fixture between the port and the device (the correction
  includes them);
- change the sweep so far that interpolation (below) is no longer good enough — when the new
  range extends outside the calibrated one, or is a small slice of it;
- change the output power (STIMULUS → POWER); the correction is kept but the status letters
  turn dim to warn you, and the RANGE button restores the power the calibration was made at;
- flash new firmware (this fork changes the sign of raw S21 — see the THRU note below).

Let the instrument warm up first; the reading on a bare port drifts while it does, and a
calibration taken during that drift carries the drift with it.

## The standards

The calibration kit has three one-port standards and one two-port connection:

| Standard | What it is | What the firmware assumes |
|---|---|---|
| OPEN | Nothing connected, or the kit's open (a connector with no centre contact) | Total reflection in phase: Γ = +1. The firmware's model is an *ideal* open; the fringing-capacitance model in the source is compiled out.[^open] |
| SHORT | The kit's short (centre pin joined to the body) | Total reflection inverted: Γ = −1 |
| LOAD | A 50 Ω termination | No reflection: Γ = 0. The quality of this part sets the floor of every reflection measurement — a poor load makes a poor calibration. |
| THRU | A cable (or the two cables joined by a barrel) from CH0 to CH1 | Loss-free, delay-free connection: S21 = 1 |
| ISOLN | Loads on both ports (or a load on CH0 and CH1 left open) | No signal leaks from CH0 to CH1: S21 = 0 |

Standards are measured at the **reference plane** — the point where you connect them. If you
calibrate at the end of a cable, the cable is inside the correction and measurements are
referred to its far end; if you calibrate at the port and then add a cable, the cable's delay
and loss appear in the results. Electrical delay (DISPLAY → SCALE → E‑DELAY) can shift the
reference plane after the fact for phase, but not remove a cable's loss.

## The procedure

**CALIBRATE → RESET**, then **CALIBRATE → CALIBRATE** and, for each standard, connect it, wait
until the trace is steady, and press its button:

1. **OPEN** on CH0.
2. **SHORT** on CH0.
3. **LOAD** on CH0.
4. **ISOLN** — a load on CH0 and a load on CH1 (with one load: load on CH0, CH1 open).
   Optional; skip it if you only measure S11.
5. **THRU** — connect CH0 to CH1 with the cable you will use. Optional; skip it if you only
   measure S11.
6. **DONE** — computes the correction, switches it on, and opens the SAVE menu; pick a slot
   (0–6) or SAVE TO SD CARD. **DONE IN RAM** does the same without offering to save: the
   calibration is live (the status shows `C*`) until the next power cycle or recall.

Each button takes **one sweep** of that standard, at an IF bandwidth of at least 100 Hz — the
firmware narrows the bandwidth for the calibration sweep if a wider (faster) one is set, and
restores it afterwards. There is no averaging, which is why the "wait until steady" matters.[^collect]

The status column at the left of the screen shows which standards have been taken (`O`, `S`,
`t`) and, after DONE, which terms were computed (`D`, `R`, `S`, `T`, `X`); `C0`…`C6` means the
correction is applied from that slot. Chapter 1 lists every letter.

**Partial calibrations are allowed.** DONE computes whatever it can from the standards taken:

| Taken | What you get |
|---|---|
| LOAD only | Directivity correction (Ed): removes the port's own reflection — the biggest error term. |
| OPEN + SHORT (+ LOAD) | Full one-port correction: directivity, source match (Es) and reflection tracking (Er). This is the normal S11 calibration. |
| OPEN or SHORT alone | Reflection tracking only, with source match assumed zero. Coarse; use both. |
| + THRU | Transmission tracking (Et) for S21. |
| + ISOLN | Isolation (Ex), subtracted from S21 before tracking. Worth taking when you measure high attenuation, where leakage between the ports is comparable to the signal; for ordinary through measurements it changes little. |

Taking a standard again replaces the previous measurement of it and, for OPEN/SHORT, clears
the computed Es/Er until you press DONE again; the correction is switched off while a
calibration is in progress.

## What the firmware computes

For reflection (S11) the NanoVNA uses the standard three-term one-port error model:[^apply]

    S11_actual = (S11_measured − Ed) / (Er + Es · (S11_measured − Ed))

- **Ed** (directivity) is the LOAD measurement itself: what the port reflects with a perfect
  termination attached.
- **Es** (source match) and **Er** (reflection tracking) come from OPEN and SHORT: with Ed
  removed, the two known reflections (+1 and −1) give two equations for the two unknowns.[^eser]

For transmission (S21):[^et]

    S21_actual = (S21_measured − Ex) · Et,   Et = 1 / (S21_thru − Ex)

- **Ex** (isolation) is the ISOLN measurement (zero if not taken).
- **Et** (transmission tracking) makes the THRU measurement read exactly 1.

**ENHANCED RESPONSE** (CALIBRATE menu) additionally multiplies S21 by (1 − Es · S11_actual),
compensating the source mismatch's effect on the through path using the device's own
corrected S11. It helps with poorly matched two-port devices and is harmless otherwise.[^enh]

A THRU calibration made by firmware before this fork carries the opposite sign in its stored
THRU data (see [chapter 6](06-fork-features.md), *Raw S21 phase*); with it, calibrated S21
phase reads 180° off. Re-do THRU after flashing.

## Interpolation: `c` instead of `C`

The correction is stored per sweep point at the calibrated start, stop and point count. If
you change any of them, the firmware does not discard the calibration; it **interpolates**:
for each new frequency it takes the two nearest calibrated frequencies and blends their terms
linearly, and outside the calibrated range it uses the nearest end point unchanged. The status
letter changes from `C` to lower-case `c` in the interpolation colour, and the CALIBRATE →
RANGE button shows the calibrated range (`CAL: 101p`, start, stop); pressing it puts the sweep
back to exactly that range and power.[^interp]

Interpolation is good when the new sweep lies inside the calibrated one and is not much
narrower than it (the error terms vary smoothly with frequency). It is poor when the new sweep
is a small slice of a wide calibration — a 101-point calibration over 50 kHz–900 MHz has one
point every 9 MHz, so a 7.0–7.3 MHz sweep would be corrected from two points that bracket the
whole band — and it is a guess outside the calibrated range. For band work, calibrate over the
band.

## Save, recall, and what a slot holds

**CALIBRATE → SAVE** stores the calibration in one of seven flash slots (0–6) together with
the complete instrument setup: sweep range and points, traces and formats, markers, electrical
delay, S21 offset, power. **RECALL** restores all of it. Slot 0 is loaded automatically at
power-up, so keep your everyday calibration there.[^slot0] The button labels show the slot's
range once it holds a calibration and `Empty` otherwise.

**SAVE TO SD CARD / LOAD FROM SD CARD** write and read the same data as a `.cal` file, for
keeping more than seven calibrations or for moving one between devices of the same model.

**APPLY** switches the correction off and on without discarding it (useful for seeing raw
data); **RESET** clears the current calibration (the slots are untouched). The console
equivalents are `cal on|off|reset`, `save N`, `recall N` ([chapter 8](08-console.md)).

## The LOAD R setting

Upstream firmware can be built with impedance renormalisation, which lets the LOAD standard's
resistance be set to something other than 50 Ω. That option is not compiled into this firmware;
the LOAD is taken as exactly 50 Ω.[^loadr]

## Checking a calibration

After DONE, with the LOAD still connected, an S11 LOGMAG trace should sit far down the
scale across the range — how far depends on the load's quality `[verify on hardware:
typical figure for the supplied kit]`. Swap to the OPEN: LOGMAG near 0 dB,
Smith marker at the right-hand end of the horizontal axis; SHORT: near 0 dB, marker at the
left-hand end. If the open and short do not land on the axis ends, a cable or adapter was
changed between calibrating and checking, or a standard was measured while the trace was
still settling.

---

[^guide]: Procedure after the NanoVNA user guide (cho45, as translated on nanovna.com), reworded; every statement about behaviour here was checked against `main.c`.
[^open]: `main.c` `eterm_calc_es()`: the capacitive open model (`c = 50e-15`) is under `#if 0`; `s11ao = 1 + j0` is used.
[^collect]: `main.c` `cal_collect()`: `if (bw < BANDWIDTH_100) config._bandwidth = BANDWIDTH_100;` then one `sweep(false, mask)`; the averaging loop has `count = 1`.
[^apply]: `main.c` `apply_CH0_error_term()`.
[^eser]: `main.c` `cal_done()`: both OPEN and SHORT → `eterm_calc_es()` + `eterm_calc_er(-1)`; OPEN only → Es = 0, `eterm_calc_er(1)`; SHORT only → Es = 0, `eterm_calc_er(-1)`; LOAD missing → Ed = 0; ISOLN missing → Ex = 0.
[^et]: `main.c` `eterm_calc_et()` and `apply_CH1_error_term()`.
[^enh]: `main.c` `apply_CH1_error_term()` under `CALSTAT_ENHANCED_RESPONSE`: `S21a *= 1 − Es · S11a`.
[^interp]: `main.c` `needInterpolate()`, `cal_interpolate()` (linear between the two bracketing calibrated points; clamped to the end points outside the range); `ui.c` `menu_cal_range_acb()`: `reset_sweep_frequency(); set_power(cal_power);` when interpolated.
[^slot0]: `main.c` startup: `caldata_recall(0)` / `load_properties(0)`.
[^loadr]: `nanovna.h`: `cal_load_r` is `current_props._cal_load_r` only under `__VNA_Z_RENORMALIZATION__`, otherwise `50.0f`; the option is commented out in this build.
