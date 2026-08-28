# Antenna tuning
## Find it
1. Sweep wide: STIMULUS -> START/STOP around the band
2. Trace 0 SWR (S11), marker 1 on
3. MARKER -> SEARCH -> MINIMUM finds the dip
4. Read f0 and SWR at the marker
## Judge it
- MEASURE -> RESONANCE: where X = 0 and R there
- MEASURE -> SWR BW: 2:1 and 3:1 bandwidth, Q
- Broad, shallow dip = loss (cable, ground), not match
- R/X traces: X = 0 at resonance, R is the feed R
## Feedpoint R to expect
| Antenna | R at resonance |
|---|---|
| dipole, 1/2 wave high | 50-75 ohm (height dependent) |
| 1/4 wave vertical, elevated radials | 30-40 ohm |
| 1/4 wave vertical on ground | 25-40 ohm + ground loss |
| loaded short whip (40/80 m) | 6-25 ohm + coil + ground |
| end-fed half wave | 2-5 kohm (via 49:1) |
---
## Adjust it
- Dip too low in frequency -> element too long: shorten
- Too high -> lengthen (or add loading)
- Trim rule: dL/L = -df/f. 100 kHz low on 20 m -> 0.7%
- Each cut: re-sweep, note f0 and R; small steps
- Fold back rather than cut in the field (ant-trim)
## Feedline
- Feedline loss hides SWR. DISPLAY -> FORMAT -> SWR ANT
  with CABLE LOSS (or CABLE TYPE + LENGTH) shows the SWR
  **at the antenna**
- Move the coax: SWR shifts = common-mode, fit a choke
## Ground systems
- Change only the ground between RESONANCE readings;
  gain in dB = 10 log10(R before / R after)
- Save each sweep: SD CARD -> SAVE S1P, an antenna log

Source: manual ch. 5/6; portable-vertical-reference s3, s6
