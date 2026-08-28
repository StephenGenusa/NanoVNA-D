# Formulas
## Match
- G = (ZL - Z0) / (ZL + Z0)
- SWR = (1 + |G|) / (1 - |G|)
- RL dB = -20 log10 |G|
- Mismatch loss dB = -10 log10 (1 - |G|^2)
- RL at antenna = RL measured - 2 L,
  L = one-way feedline loss dB (SWR ANT does this)
## Reactance
- XL = 2 pi f L        XC = 1 / (2 pi f C)
- f0 = 1 / (2 pi sqrt(L C))
- Q = f0 / BW(3 dB) = |X| / R
- Rp = Rs (1 + Q^2)
---
## Lengths
- Free space 1/4 wave: 246/f ft, 75/f m (f in MHz)
- Resonant 1/4 wave element: 234/f ft
- Dipole: 468/f ft, 142.6/f m
- In coax multiply by the velocity factor
- Trim: dL/L = -df/f
## Chokes and ground
- Series-through: Z = 2 Z0 (1/S21 - 1)
  |Z| about 100/|S21| ohm when |Z| >> 100 ohm
  -20 dB = 1 kohm, -40 dB = 10 kohm
- Ground improvement dB = 10 log10 (R before / R after)
- Radial tip voltage: V ~ sqrt(P), V ~ 1/N radials
- Coil loss: R_coil = X_L / Q
