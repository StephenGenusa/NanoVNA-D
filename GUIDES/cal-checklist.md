# Cal checklist
## Before you start
- Warm up 5 min; set START/STOP or CENTER/SPAN first
- Bandwidth: cal uses 100 Hz or narrower automatically
- Attach the cable/adapter you will measure through;
  the standards go where the antenna will connect
- CAL -> RESET clears the old calibration
## SOLT (S11 + S21)
1. OPEN on CH0 -> OPEN
2. SHORT on CH0 -> SHORT
3. LOAD on CH0 -> LOAD
4. LOAD on CH0 and CH1 -> ISOLN (optional)
5. THRU CH0-CH1 -> THRU
6. DONE, then SAVE n (one slot per band or fixture)
---
## Verify it
- LOAD: LOGMAG far down the scale across the range
- OPEN: LOGMAG near 0 dB, Smith marker at right end
- SHORT: near 0 dB, Smith marker at left end
- THRU: S21 LOGMAG near 0 dB
- Status shows **C** + slot; **c** means interpolated
  (range or points differ from the cal): recalibrate
## Recalibrate after
- any START/STOP, points or power change
- swapping the cable, adapter or fixture
- moving the reference plane (or use EDELAY)
- an inline attenuator (use S21 OFFSET instead)

Source: manual ch. 3, main.c cal_collect()/cal_done()
