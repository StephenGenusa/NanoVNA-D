# Choke recipe
K9YC 2018 Choke Cookbook, one Fair-Rite #31 toroid,
2.4 in / 61 mm o.d., part 2631803802.
## Multiband
- 13 turns RG400 (or Teflon #12, or THHN #12):
  at least 5 kohm on 80, 40, 30 and 20 m
## Single band, RG400 turns (R_s achieved)
| Band | Turns |
|---|---|
| 160 m | 18 (10 k), 17 (6 k) |
| 80 m | 16 (8 k), 15 (7 k), 14 (6 k) |
| 40 m | 14 (6.2 k), 15 (5.4 k) |
| 30 m | 14 |
| 20 m | 13 |
| 15 m | 11 |
| 10 m | 10 |
---
## Rules
- #31, not #43, for HF chokes
- Toroid, not beads: impedance goes as turns squared
- Target 5 kohm, not 500 ohm: every doubling of Z is
  6 dB less feedline noise on receive
- Feedpoint choke is mandatory: it keeps the coax from
  becoming radial number two
- Add a second choke if the run exceeds 1/4 wave
  (34.6 ft on 40 m, which most POTA runs do)
- A choke does not isolate anything; it raises the
  impedance of the shield's outer surface
- Check it with the analyser: choke-measure

Source: K9YC 2018 Choke Cookbook Table 2; portvert s4.7
