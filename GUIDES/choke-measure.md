# Measure a choke
S21 series-through: the NanoVNA shows the choke's
impedance directly, no arithmetic.
## Fixture
1. Two connectors on a scrap of double-sided board,
   the choke wired in series between the centre pins,
   short leads
2. Calibrate with the fixture bridged (THRU), SOL at
   the ports for S11
## Measure
3. Insert the choke
4. DISPLAY -> FORMAT S21 -> |Zser| on trace 0,
   Rser and Xser on traces 1 and 2
5. Sweep 1-30 MHz (wider for 6 m); marker per band
6. Record R and X, not just |Z|
---
## On the device (H4)
MEASURE -> MORE (S21) -> CHOKE (S21) does
steps 4-6 above for you, band by band.
1. THRU cal the span (as above); with the
   choke OUT, sweep the open jig, STORE
   FIXTURE
2. Insert the choke; DISPLAY -> SCALE ->
   HAM BANDS picks which bands get judged
3. Each row: band, de-embedded R_S and X,
   frequency, a verdict (POOR/WEAK/MARGINAL/
   GOOD/MEETS/HIGH PWR) - X is shown, never
   the verdict
4. A JIG row: past what the null resolves.
   The ohms shown are the RAW ceiling - what
   this jig does with NO fixture stored;
   nulled, it judges ~20x higher
5. Zpeak row: |Z| peak where X crosses from
   + to -, the parallel (anti-)resonance
6. STORE REF (after a fixture) to compare
   the worst band across a rewind; turns
   tables are in choke-recipe
---
## Pass criteria (K9YC)
- R at least 1 kohm on every band you use;
  3-5 kohm is better
- R greater than |X|: a lossy, resistive choke.
  A reactive choke can series-resonate with the
  feedline and INCREASE common-mode current
## Quick S21 rule (no fixture math)
| S21 | choke |Z| about |
|--:|--:|
| -20 dB | 1 kohm |
| -26 dB | 2 kohm |
| -34 dB | 5 kohm |
| -40 dB | 10 kohm |

Z = 2 Z0 (1/S21 - 1), about 100/|S21| ohm above 1 k.
Design targets: G3TXQ choke charts, K9YC cookbook.

Source: K9YC RFI, Ferrites and Common Mode Chokes
