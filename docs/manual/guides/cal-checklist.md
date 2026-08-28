# Cal checklist
## Before you start
- Warm up 5 min; set START/STOP or CENTER/SPAN first
- Bandwidth: cal uses 100 Hz or narrower automatically
- Attach the cable/adapter you will measure through
- CAL -> RESET clears the old calibration

## SOLT (S11 + S21)
1. OPEN on CH0 -> OPEN
2. SHORT on CH0 -> SHORT
3. LOAD on CH0 -> LOAD
4. LOAD on CH0 and CH1 -> ISOLN (optional)
5. THRU CH0-CH1 -> THRU
6. DONE, then SAVE n
---
## Check it
- LOAD: LOGMAG far down the scale across the range
- OPEN: LOGMAG near 0 dB, Smith marker at right end
- SHORT: near 0 dB, Smith marker at left end
- Status shows **C** + slot; **c** means interpolated
  (range or points differ from the cal) - recalibrate
  for best accuracy
