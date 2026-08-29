# MEASURE panels

**MEASURE** on the top-level menu opens a list of built-in calculations. Selecting one draws
a small text panel over the plot that updates with every sweep (and, for panels that depend on
the marker, whenever the marker moves); **OFF** removes it. Each panel works on the current
sweep data, so set the sweep, calibrate, and connect the device first. The nanovna.com guide
predates all of these; this chapter is from `measure.c`.[^src]

| Panel | Needs | What it reports |
|---|---|---|
| L/C MATCH | S11, a marker | An L-network to match the impedance at the marker to 50 Ω |
| CABLE (S11) | S11 of an open-ended cable | Cable length (or velocity factor), characteristic impedance, loss |
| RESONANCE (S11) | S11 | Every frequency where the reactance crosses zero, with R + jX there |
| SWR BW (S11) | S11 | Bandwidth and Q of the SWR dip near the marker — see [chapter 6](06-fork-features.md) |
| TUNE (S11) | S11, a target frequency | ADD/REMOVE wire verdict and sensitivity for trimming an antenna — H4 only, see below |
| SHUNT LC (S21) | S21 of an L–C in shunt across the through path | Series-resonant frequency, L, C, R, Q of the part |
| SERIES LC (S21) | S21 of an L–C in series with the through path | The same, for a part in series |
| SERIES XTAL (S21) | S21 of a crystal in series | Motional parameters and the parallel resonance |
| FILTER (S21) | S21 of a filter | Centre, −3 dB and −6 dB bandwidths, Q, and the roll-off on each side |

## L/C MATCH

Reads the impedance at the **active marker** and computes lumped L-networks that would
transform it to the port impedance (50 Ω) at that frequency, showing up to three topologies
side by side under the headings *Src shunt*, *Series* and *Load shunt* — a component across
the source side, a component in series, and a component across the load side — each with its
inductance or capacitance value.[^lc] The panel says "No need for LC match" when the marker
impedance is already close to 50 Ω, and "No LC match for this" when no two-element network
solves it. Sweep the band of interest, put the marker on the operating frequency, and read
the network; the values are exact only at the marker frequency, so a broadband match needs
more than this.

## CABLE (S11)

Connect a cable with its far end **open** and sweep from a low frequency up past the point
where the cable is a quarter-wavelength long. The panel finds the first frequency at which the
reactance passes through zero — where the open-ended cable is exactly a quarter wave — and
from it computes the electrical length. With a velocity factor set (DISPLAY → TRANSFORM →
VELOCITY F., or MEASURE → CABLE → VELOCITY F.) it reports the physical **Length**; alternatively enter the real length
(MEASURE → CABLE → CABLE LENGTH) and it reports the cable's **VF**. **Z0** is taken from the
magnitude of the reactance at half the quarter-wave frequency (where the open line behaves as
a pure reactance of |Z0|). **Loss** is the one-way loss at the marker frequency, from a fit of
the return loss against √f over the sweep — the same figure `SWR ANT` needs
([chapter 6](06-fork-features.md)) — and **Att** the same per 100 m.[^cable]

## RESONANCE (S11)

Lists every frequency in the sweep where the reactance X of the port impedance crosses zero,
with the resistance and (near-zero) reactance at each, up to six. If X never crosses zero it
reports the point where |X| is smallest instead. With the ZERO marker search
([chapter 4](04-markers.md)) this is the tool for the antenna-builder's basic question — where
is it resonant and what is R there — and, by changing only the ground system between readings,
for comparing ground systems: the improvement in dB is 10·log₁₀(R_before / R_after) at
resonance.[^res] The R and X traces in [chapter 2](02-sweep-and-traces.md) show what the
panel measures: the zero crossing of X.

**H4 only:** with a reference sweep stored (MEASURE → RESONANCE → STORE REF), the panel adds
a row above the list: `REF: Δf0 ±x.xxx`, the shift of the first zero crossing since the
reference was taken — trim a little, re-sweep, and watch this settle toward zero; `REF: no
X=0 in ref` if the reference sweep itself never crossed zero; `REF: stale (points | span |
cal | proc changed)` when the sweep points, span, calibration status or processing differ
from when the reference was stored, so the comparison is no longer meaningful; or `REF: none`
with nothing stored. STORE REF and CLEAR REF here are the same reference the TUNE panel below
uses, and REPEAT CHECK reports the same max |ΔΓ| noise floor described there.[^wref]

## SWR BW (S11)

Bandwidth at 2:1 and 3:1 and the quality factor of the SWR dip nearest the marker. Described
with the other fork additions in [chapter 6](06-fork-features.md).

## TUNE (S11) — H4 only

<!-- TODO screenshot: MEASURE TUNE panel (H4) -->

A single panel for the trim-and-resweep loop that RESONANCE and SWR BW otherwise take
several button presses to piece together: set a target frequency, read whether to add or
remove wire and how much, and — with a stored reference — get that answer from what the
antenna actually did rather than from a textbook formula.

**MEASURE → TUNE (S11)**, then **TARGET** (frequency keypad) sets the resonance you are
aiming for; the panel reads "TUNE: set TARGET" until it is entered. **ANTENNA** cycles the
assumed element: UNKNOWN, DIPOLE, VERTICAL, EFHW — DIPOLE and EFHW use the 468/f (ft) rule,
VERTICAL the 234/f (ft) rule, and DIPOLE splits the reported change between the two legs;
UNKNOWN reports no assumed length and pushes you straight to the measured workflow below.

With a dip inside the sweep the panel reports, in order: f(SWRmin) and, if the reactance
actually crosses zero, f(X=0) and R there (with a warning if the two disagree by more than
0.5%, which usually means a through line or R far from 50 Ω); SWR at the dip and at TARGET,
and the 2:1 bandwidth (or "BW: re-sweep" when the sweep does not have enough points to
resolve it); how far f0 is from TARGET and by what percentage the element is short or long;
and finally the **ADD/REMOVE** verdict — a positive change (f0 above TARGET, element too
short) always reads ADD, a negative one REMOVE, whether the length comes from the antenna
model or a measured reference. "no dip inside sweep: widen or move span" replaces all of
this when there is nothing to measure.

**The reference workflow**, shared with RESONANCE (S11): **STORE REF** saves the current
sweep; make the change (fold the wire rather than cut it — see the *ant-tune-workflow* guide
on the SD card for why), re-sweep, then enter what you changed under **WIRE CHANGE** — the
length added (+) or removed (−) in metres (e.g. `0.04` for 4 cm), per leg on a dipole; the
keypad's `m` key means *milli*, not metre, so 4 cm is typed `40 m`. Once a valid reference and a
non-zero WIRE CHANGE are both present, the ADD/REMOVE row switches from the antenna model to
the antenna's own measured sensitivity, tagged `[measured]` (or `[loaded?]` when the implied
sensitivity is more than 3× the full-size figure for that frequency — a sign of a loading
coil or trap rather than a plain wire). With a known ANTENNA type but no measured pair yet
(no reference, or no WIRE CHANGE typed) the row instead shows the model's own estimate,
`[assumed x.xxm]` — the total element length the 468/f or 234/f rule assumes. With ANTENNA
left at UNKNOWN and no measured pair, the row is a plain "ADD/REMOVE wire, STORE REF,
re-sweep for kHz/cm" prompt, with no length at all.

Below that, a **REF** row tracks the reference against the current sweep: `Δf0 ±x.xxx` once
both are valid, with a trailing `rpt x.xxx` once REPEAT CHECK has been run; `stale (points |
span | cal | proc)` when the sweep points, start/stop span, calibration status, or processing
(S21 offset, electrical delay, smoothing) differ from when the reference was stored — any of
those invalidates the comparison; or `none` with no reference stored. Every REF state ends
with the hint "fold, re-sweep, cut". **CLEAR REF** discards the stored reference.

**REPEAT CHECK** takes the max |ΔΓ| between the stored reference and the sweep just
completed and shows it in a message box, "REPEATABILITY / max |dG| x.xxx" — a noise floor for
judging whether a small measured change is real or just sweep-to-sweep jitter; with no valid
reference it reads 0.000, which is not a measurement, just nothing to compare against.[^tune]

## SHUNT LC and SERIES LC (S21)

For a two-terminal L–C (or a crystal treated as a plain series resonator) connected between
the ports either **in series** with the through path or **shunt** across it. The panel finds
the S21 peak (series) or notch (shunt), which is the series resonance **Fs**, then locates the
frequencies on either side where the transmission phase is ±45°; their separation is the
resonator's bandwidth and gives **Q**, and with the through loss at resonance gives the
equivalent **Rm**, **Lm**, **Cm** of the part.[^lcs] The panel says "Not found" when no peak
or notch is in the sweep — widen it.

## SERIES XTAL (S21)

The same measurement for a quartz crystal in series between the ports, with two additions:
after the series resonance (**Fs**, Lm, Cm, Rm, Q) it also finds the parallel resonance **Fp**
— the S21 minimum just above Fs — and reports **ΔF** = Fp − Fs and the parallel (holder)
capacitance **Cp** derived from it: Cp = Cm · Fs / (2 ΔF).[^xtal] Sweep a narrow span around
the crystal's nominal frequency with as many points as the firmware allows; the resonance is
extremely sharp.

## FILTER (S21)

For a filter between the ports: finds the S21 maximum and reports it as **f** with the
insertion loss in dB; if the response falls by 3 dB on both sides it reports the **Bw (−3 dB)**
and **Bw (−6 dB)** bandwidths and **Q** = f / Bw₃dB, then a *Low-side* / *High-side* table with
the −3 dB and −6 dB frequencies on each edge and the **roll-off** in dB per decade and per
octave, estimated from the −6 dB and −20 dB points. A high-pass or low-pass response with
only one edge in the sweep is reported as *High-pass* / *Low-pass* with that edge's
figures.[^filt] Responses below −50 dB are treated as noise.

---

[^src]: `measure.c`; the panel table is `measure_list[]` in `plot.c`; menu `menu_measure[]` in `ui.c`.
[^lc]: `measure.c` `prepare_lc_match()` / `lc_match_process()`: impedance at `get_marker_frequency(active_marker)`, `R0 = PORT_Z`; `draw_lc_match()` headings "Src shunt", "Series", "Load shunt".
[^cable]: `measure.c` `prepare_s11_cable()`: first zero of Im S11 (`measure_search_value(…, 0, s11imag, RIGHT)`) → `electric_length = (c/4)/f1`; `Z0 = |X|` at `f1/2`; loss from `parabolic_regression()` of `−½·logmag` against √f; `draw_s11_cable()`.
[^res]: `measure.c` `prepare_s11_resonance()`: up to `MEASURE_RESONANCE_COUNT` = 6 zero crossings of `Im S11`; falls back to the minimum of |X|. The ground-system comparison: feedpoint R = R_rad + R_ground, so with the radiator unchanged the ratio of feedpoint resistances is the efficiency ratio.
[^lcs]: `measure.c` `analysis_lcshunt()` / `analysis_lcseries()` ("Phase Shift Measurement", after the crystal-motional-parameters method referenced in the source): peak or minimum of |S21|², then `measure_search_value()` for the ±45° phase points (`tan45 = 1`), Q from their spacing.
[^xtal]: `measure.c` `analysis_xtalseries()`: series analysis, then `search_peak_value(…, MIN)` for Fp; comment `df = f·c/(2·c1) ⇒ c1 = f·c/(2·df)`.
[^filt]: `measure.c` `prepare_filter()` / `draw_filter_result()` / `find_filter_pass()`; `S21_MEASURE_FILTER_THRESHOLD −50 dB`; `filter_att[] = {3, 6, 10, 20}` dB.
[^wref]: `vna_modules/vna_workref.c` `wref_state()`: the reference is `WREF_OK` only while `sweep_points`, `getFrequency(0)`/`getFrequency(n−1)`, `cal_status`, and processing (`electrical_delayS11/S21`, `s21_offset`, smoothing) all still match the values captured by `wref_store()` — compared by value, not by hooking a setter, so a same-points different-span `scan` console command is still caught. RESONANCE's reference f0 is the first `Im S11` zero crossing of the stored sweep (`wref_first_x0_freq()`), matching how the panel finds its own list.
[^tune]: `measure.c` `prepare_tune()` / `draw_tune()`; `vna_modules/vna_workflow_math.c`. Lengths: `tune_assumed_len_m()` (468/f, 234/f, feet→metres); measured sensitivity `tune_sensitivity_hz_per_m()` = Δf0 / `tune_change_m`; the `[loaded?]` threshold is `tune_fullsize_hz_per_m()` = f_MHz² · 1.402×10⁴ Hz/m (a full-size quarter-wave section, L = 71.32/f_MHz m), ×3. Unlike RESONANCE, TUNE's reference f0 is the reference sweep's own SWR minimum (`swr_bw_analyse()` on the stored S11), not an X=0 crossing — both approximate the same resonance but are not computed identically. `wref_repeat_measure()` (`menu_wref_repeat_cb`): max over the sweep of |Γ_now − Γ_ref|, 0 when the reference is not `WREF_OK`. Host-tested: `tests/host/tune_host.c`, `tests/test_workflow.py`.
