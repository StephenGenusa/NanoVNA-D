# Antenna tuning
## Find it
1. Sweep wide: STIMULUS -> START/STOP around the band
2. Trace 0 SWR (S11), marker 1 on
3. MARKER -> SEARCH -> MINIMUM finds the dip
4. Read f0 and SWR at the marker
## Judge it
- MEASURE -> SWR BW (S11): 2:1 and 3:1 bandwidth, Q
- Broad, shallow dip = loss (cable, ground), not match
- R/X traces: X = 0 at resonance, R is the feed R there
---
## Adjust it
- Dip too low in frequency -> shorten the element
- Too high -> lengthen (or add loading)
- Each cut: re-sweep, note f0 and R; small steps
- Feedline loss hides SWR: DISPLAY -> FORMAT -> SWR ANT
  with CABLE LOSS or CABLE TYPE shows SWR **at the antenna**
- Save the final sweep: SD CARD -> SAVE S1P
