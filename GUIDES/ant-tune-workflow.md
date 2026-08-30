# TUNE panel workflow
## On the device (H4)
- MEASURE -> TUNE (S11): target frequency,
  ADD/REMOVE verdict, sensitivity - one panel
- TARGET: the frequency you want resonant.
  Also sets the sweep -10%..+5% around it
  (within your cal range) unless you already
  narrowed in. TARGET, then cal, then STORE REF
- "TARGET outside cal": recalibrate to include it
- ANTENNA: cycles UNKNOWN / DIPOLE / VERTICAL /
  EFHW - sets the assumed element length.
  UNKNOWN skips the model: store a reference
  and measure your own kHz/cm instead
- WIRE CHANGE: length added (+) or removed (-)
  since STORE REF; per leg on a dipole
- Enter WIRE CHANGE in metres, e.g. 0.04 for
  4 cm - the keypad's m key means milli, not
  metre
- "no dip inside sweep": the SWR minimum sits
  at a span edge or is above 5:1, so no verdict.
  Widen the sweep (a long wire dips BELOW the
  band), find the dip, then narrow onto it
---
## The ADD/REMOVE rule
- f0 above TARGET (too high) -> element too
  SHORT -> ADD wire
- f0 below TARGET (too low) -> element too
  LONG -> REMOVE (trim to the SWR minimum)
- Adding length always lowers resonance; same
  rule ant-trim's fold table relies on

## Measured beats assumed
1. STORE REF before changing anything
2. Fold the change in (do not cut), re-sweep
3. WIRE CHANGE: enter the folded length
4. Panel now reports actual kHz/cm from your
   antenna [measured], not the model [assumed]
5. [loaded?] flags a shift much faster than
   full-size wire - a coil or trap is at work

## Fold first, why a fold is not a cut
- A folded lead still carries current and
  couples to the wire it lies against, so it
  is not quite the same load as a clean cut
  (ARRL Antenna Book Vol. 2, s11.1.1)
- Treat the fold-derived length as your best
  estimate: verify with one more sweep, then
  make the permanent cut
- Fold-and-secure technique, per-inch numbers
  for a loaded whip: see ant-trim
---
## Full-size sensitivity (unloaded, df/dL)
| Band | kHz/cm |
|---|--:|
| 80 m | 2.0 |
| 40 m | 7.2 |
| 20 m | 28 |
| 15 m | 63 |
| 10 m | 114 |

Calculated, not measured: a resonant quarter-
wave section, L = 71.32/f_MHz m. Loaded or
trapped elements move several times faster;
the panel's [loaded?] tag catches that case
so this table is not mistaken for one.

REPEAT CHECK reports the noise floor (max
|dGamma|) against the stored reference; if it
is not near 0, distrust small [measured]
deltas until it is.

Source: measure.c draw_tune(); vna_workflow_
math.c tune_fullsize_hz_per_m(); ant-trim;
ARRL Antenna Book Vol. 2 s11.1.1
