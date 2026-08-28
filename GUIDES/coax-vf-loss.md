# Coax VF and loss
## Velocity factor
| Cable | VF |
|---|--:|
| RG-58, RG-213, RG-8 (solid PE) | 0.66 |
| RG-174, RG-316, RG-142 (PTFE) | 0.69-0.70 |
| RG-8X, LMR-240 (foam PE) | 0.78-0.82 |
| LMR-400, 9913 (foam) | 0.84-0.85 |
| 1/2 in hardline, air core | 0.88-0.90 |
| 300 ohm twin lead | 0.82 |
| 450 ohm window line | 0.91 (0.88-0.95) |
| open-wire line | 0.95-0.98 |

Set it: DISPLAY -> TRANSFORM -> VELOCITY FACTOR. Better:
MEASURE -> CABLE measures your cable's VF and loss.
---
## Matched loss, dB per 100 ft (new, dry cable)
| MHz | LMR-400 | RG-213 | RG-8X | RG-58 | RG-174 |
|--:|--:|--:|--:|--:|--:|
| 1.8 | 0.16 | 0.25 | 0.49 | 0.56 | 1.10 |
| 3.6 | 0.23 | 0.37 | 0.68 | 0.82 | 1.50 |
| 7.1 | 0.32 | 0.55 | 1.00 | 1.20 | 2.10 |
| 14.2 | 0.46 | 0.75 | 1.40 | 1.70 | 3.10 |
| 21.2 | 0.56 | 1.00 | 1.70 | 2.00 | 3.80 |
| 28.4 | 0.65 | 1.20 | 1.90 | 2.40 | 4.40 |
| 50.1 | 0.87 | 1.60 | 2.50 | 3.20 | 5.90 |

% power lost at 25/50 ft on 20 m:
  LMR-400 3/5 . RG-213 4/8 . RG-8X 8/15
  RG-58 9/18 . RG-174 16/30
On 10 m roughly double. Loss rises with SWR on the line.

Source: ARRL Antenna Book Vol 3 Table 23.4 (vna_coax.c)
