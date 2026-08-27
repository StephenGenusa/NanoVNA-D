# Sweep and traces

The NanoVNA steps its source through a set of frequencies — the **sweep** — measuring the
reflection at CH0 (S11) and the transmission from CH0 to CH1 (S21) at each point, then draws
up to four **traces**, each showing one of those two quantities in one of 31 **formats**. This
chapter covers setting the sweep and the traces; the formats are tabulated in the next.
Procedures are after the original guide, checked against `ui.c` and `main.c`.[^guide]

## Setting the sweep

**STIMULUS** on the top-level menu:

| Button | What it sets |
|---|---|
| START / STOP | The sweep's end points. Entering either switches the frequency line to START/STOP display. |
| CENTER / SPAN | The same sweep expressed as centre and width; entering either switches the display to CENTER/SPAN. |
| CW FREQ | A single frequency: the source sits there and every point is measured at it — for tuning or for driving a device at one frequency. |
| FREQ STEP | The spacing between sweep points. Entering a value keeps START and moves STOP so that the points fall on that spacing (span = step × (points − 1)). |
| JOG STEP | The step the wheel uses in the frequency lever modes ([chapter 1](01-orientation.md)): AUTO uses decade-rounded steps, or enter a fixed step. |
| SWEEP POINTS | 51, 101, 201, 301 or 401 points on the H4; 51 or 101 on the H (`POINTS_SET`, `SWEEP_POINTS_MAX`). More points = finer resolution and a proportionally longer sweep. |
| MUTE OUTPUT ON PAUSE | Fork addition, [chapter 6](06-fork-features.md). |

The frequency keypad takes `G`, `M`, `k` or `×1` (hertz) to accept a value. The range is
600 Hz to 2.7 GHz (`FREQUENCY_MIN`/`MAX`); above the harmonic threshold (CONFIG → EXPERT →
THRESHOLD, default 300 MHz) the source's 3rd and 5th harmonics are used, with less signal and
more noise.[^range] The wheel also adjusts START/STOP or CENTER/SPAN directly in the frequency
lever modes, and markers can set them (MARKER → OPERATIONS, [chapter 4](04-markers.md)).

**PAUSE SWEEP** (top level; the button reads RESUME while paused) freezes the display and the
source at the last point. Console: `sweep`, `freq`, `pause`, `resume`.

**Sweep speed** is set by the IF bandwidth, DISPLAY → IF BANDWIDTH: 4000, 2000, 1000, 333,
100 or 30 Hz. A narrower bandwidth averages longer at each point — lower noise floor,
slower sweep; 30 Hz is the choice for measuring deep notches or high attenuation, 4000 Hz for
watching a tuning adjustment in real time.[^bw] The frequency line shows the current value
(`BW:1000Hz 101p`).

## Traces

Four traces (0–3). **DISPLAY → TRACE → TRACE n** toggles a trace on or off and makes it the
**active trace** — the one that FORMAT, CHANNEL, SCALE and the touch scale gestures act on
(marked `▸` in the top-left readout). Tapping a trace's readout line also makes it active.
Each trace has its own channel and format:

- **DISPLAY → CHANNEL** cycles the active trace between S11 (REFL) and S21 (THRU).
- **DISPLAY → FORMAT S11 (REFL)** / **FORMAT S21 (THRU)** choose the format; the S11 menu lists
  reflection formats (SWR, R, X, |Z|, Smith, …), the S21 menu the through-measurement ones
  (Rser, Xser, shunt/series |Z|, …). Formats common to both (LOGMAG, PHASE, DELAY, LINEAR,
  REAL, IMAG, SMITH, POLAR) appear in both. Pressing SMITH again on a Smith trace opens the
  marker readout formats ([chapter 4](04-markers.md)).

By default trace 0 is S11 LOGMAG, trace 1 S21 LOGMAG, trace 2 S11 SMITH, trace 3 S21
PHASE.[^defaults] Traces are drawn in their own colours (trace 0 yellow, 1 cyan, 2 green, 3
magenta; the `color` console command changes the palette).

## Scale and reference

**DISPLAY → SCALE**, for the active trace:

| Button | Effect |
|---|---|
| TRACE | Select which trace the following buttons act on |
| AUTO SCALE | Chooses a scale and reference position that fit the current data on the grid with a margin |
| TOP / BOTTOM | Enter the value at the top or bottom grid line; scale and reference follow |
| SCALE | Value per grid division |
| REF POSITION | Which grid line (0 = bottom … 8 = top) carries the reference value; for SWR the bottom line is always 1.0 |
| E-DELAY | Electrical delay in seconds for the active channel — shifts the reference plane along a cable so phase reads flat; MARKER → OPERATIONS → E-DELAY sets it from a marker |
| S21 OFFSET | A dB offset added to S21, e.g. +30 dB to display a device measured through a 30 dB attenuator at its true gain |
| SHOW GRID VALUES | Prints the value of each grid line at the right edge |
| DOT GRID | Draws the grid dotted instead of solid |
| HAM BANDS | Fork addition, [chapter 6](06-fork-features.md) |

Tapping near the left or right edge of the plot also changes scale and reference by quarters
of the screen height ([chapter 1](01-orientation.md)). SCALE, TOP/BOTTOM and REF POSITION are
in the trace's own units (dB, Ω, …, or SWR units for SWR).[^scale]

## Smoothing

**DISPLAY → DATA SMOOTH** applies a smoothing pass over the sweep data before display, with
factors ×1, ×2, ×4, ×5, ×6 (stronger with the factor); the status column shows `sN`. It
quiets a noisy trace at the cost of rounding sharp features; prefer a narrower IF bandwidth
when the feature itself matters.[^smooth]

## Time domain

**DISPLAY → TRANSFORM** turns the sweep into an impulse or step response along a cable
(time-domain reflectometry): TRANSFORM on/off, **LOW PASS IMPULSE**, **LOW PASS STEP** (needs a
sweep starting near 0 Hz — the low-pass modes reflect the spectrum about DC), **BANDPASS**
(any sweep), a **WINDOW** of MINIMUM / NORMAL / MAXIMUM (less to more side-lobe suppression,
at the cost of resolution), and **VELOCITY F.** (the cable's velocity factor, so the axis reads
in metres as well as nanoseconds). The frequency line then shows the time and distance span;
the resolution is set by the sweep's span and the range by its point spacing.[^td]

The formats a trace can take follow.

---

[^guide]: cho45, *NanoVNA User Guide* (nanovna.com translation), "Start measurement" — trace selection, channel, format, and STIMULUS START/STOP/CENTER/SPAN/CW/PAUSE, reworded; the guide's "up to 101 points" is the H's maximum, the H4 allows 401.
[^range]: `nanovna.h` `FREQUENCY_MIN 600`, `FREQUENCY_MAX 2700000000`, `FREQUENCY_THRESHOLD 300000100`; `SWEEP_POINTS_MAX` 401 (F303) / 101 (F072); `POINTS_SET {51, 101, 201, 301, SWEEP_POINTS_MAX}`.
[^bw]: `main.c` `get_bandwidth_frequency()`: bandwidth = (ADC rate / 48) / (n + 1) with the ADC at 192 kHz — the six menu values; the measurement integrates over 1/bandwidth at each point.
[^defaults]: `main.c` `def_trace[]`: {LOGMAG ch0, LOGMAG ch1, SMITH ch0, PHASE ch1}, scales 10 dB, 10 dB, 1.0, 90°.
[^scale]: `ui.c` `menu_scale[]`, `menu_auto_scale_cb()`, `input_amplitude()`, `input_scale()`; SWR grid shift via `SWR_TYPE_MASK` in `plot.c`.
[^smooth]: `ui.c` `menu_smooth_count[]` (data 1, 2, 4, 5, 6); `main.c` `set_smooth_factor()` / the complex-data smoothing pass ("smooth power depend from count"); `plot.c` `draw_cal_status()` prints `s%d`.
[^td]: `ui.c` `menu_transform[]`, `menu_transform_window_acb()`; `main.c` `transform_domain()` (`TD_FUNC_LOWPASS_IMPULSE`, `TD_FUNC_LOWPASS_STEP`, `TD_FUNC_BANDPASS`; `TD_WINDOW_MINIMUM/NORMAL/MAXIMUM`); `time_of_index()`, `distance_of_index()` in `plot.c`.
