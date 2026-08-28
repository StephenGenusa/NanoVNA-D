# Loading coils
- R_coil = X_L / Q. A 40 m whip needs about +j400 ohm:
  Q 100 -> 4.0 ohm of loss, Q 300 -> 1.3 ohm
- High Q: large diameter, air wound, heavy gauge,
  spaced turns. ARRL: 8.6 uH = 16 t #14, 2 in form, 2 in
- Tripling Q buys 1.4 dB over perfect ground but only
  0.35 dB over poor ground. Fix the ground first.
- Above 20 m a 17 ft whip is TOO LONG: collapse it,
  do not add coil (234/17 ft = 13.8 MHz)
## Radiation resistance, 19 ft whip (Sevick, measured)
| Coil position | R_rad |
|---|--:|
| base | 7.5 ohm |
| midpoint | 16.5 ohm |
| 3/4 point | 22 ohm |
| top hat | 23.5 ohm |

Config A: 1/4 wave whip on 20/15/10 m, no coil,
R_rad 36.6 ohm; 10 ohm of ground loss costs 1.05 dB.
Config B: loaded whip on 40/80 m, R_rad 5.8 ohm;
the same 10 ohm costs 4.35 dB.

Measure it: MEASURE -> RESONANCE gives R at X = 0;
Ls/Cs traces read the coil directly at the port.

Source: Sevick QST 3/1973; ARRL Antenna Book; portvert s5
