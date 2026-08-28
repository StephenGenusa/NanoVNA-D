# MEASURE panels
| Panel | Port | Result |
|---|:-:|---|
| L/C MATCH | S11 | L-network to match the marker Z to 50 |
| CABLE | S11 | length, VF, Z0, loss, loss per 100 m |
| RESONANCE | S11 | every X = 0 crossing with R and X |
| SWR BW | S11 | 2:1 and 3:1 bandwidth, Q of the dip |
| SHUNT LC | S21 | f0, L, C, R, Q of a shunt resonator |
| SERIES LC | S21 | f0, L, C, R, Q of a series resonator |
| SERIES XTAL | S21 | Fs, Fp, dF, Lm, Cm, Rm, Q, Cp |
| FILTER | S21 | centre, -3/-6 dB BW, Q, loss, roll-off |

- MENU: MEASURE -> panel. Panels are off in TDR mode.
- CABLE: far end OPEN; for length, set VF first
- XTAL: span +/-50 kHz, max points; fixture strays
  add to Cp
- FILTER: shape factor = BW(-60)/BW(-3) from markers;
  the instrument floor is about 50-70 dB
- Console: measure resonance | cable | filter | xtal ...

Source: manual ch. 5; measure.c
