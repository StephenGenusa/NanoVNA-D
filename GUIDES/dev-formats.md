# Trace formats
DISPLAY -> FORMAT S11 / S21. Console: trace N {format}.
| Format | Unit | Meaning |
|---|---|---|
| LOGMAG | dB | 20 log10 magnitude: RL or IL |
| PHASE | deg | phase, -180..+180 |
| DELAY | s | group delay -dphi/domega |
| SMITH | - | reflection on the Z chart |
| POLAR | - | magnitude and angle, no grid |
| LINEAR | - | linear magnitude 0..1 |
| SWR | - | (1+G)/(1-G); bottom line = 1 |
| REAL | - | real part of S |
| IMAG | - | imaginary part of S |
| R | ohm | series resistance of Z |
| X | ohm | series reactance; 0 at resonance |
| Z | ohm | impedance magnitude |
| Z phase | deg | atan2(X, R) |
| G | S | conductance of Y = G + jB |
| B | S | susceptance |
| Y | S | admittance magnitude |
| Rp | ohm | parallel-equivalent resistance |
| Xp | ohm | parallel-equivalent reactance |
| Cs | F | series-equivalent C (X capacitive) |
| Ls | H | series-equivalent L (X inductive) |
| Cp | F | parallel-equivalent C |
| Lp | H | parallel-equivalent L |
---
## S21 formats: device in series or shunt between ports
| Format | Unit | Meaning |
|---|---|---|
| Q | - | quality factor X/R |
| Rser | ohm | R of a device in series |
| Xser | ohm | X of a device in series |
| Zser | ohm | magnitude, series (chokes) |
| Rsh | ohm | R of a device in shunt |
| Xsh | ohm | X of a device in shunt |
| Zsh | ohm | magnitude, shunt |
| SWR ANT | - | SWR at the antenna, feedline loss removed |

Zser: Z = 2 Z0 (1/S21 - 1). Zsh: Z = Z0 S21 / (2 (1 - S21)).
SWR ANT needs CABLE LOSS or CABLE TYPE + LENGTH set.

Source: plot.c trace_info_list; manual ch. 2
