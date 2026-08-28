# SWR diagnostics
## SWR misbehaving? Test in this order
1. **Move the coax.** SWR shifts?
   -> common-mode current on the shield.
   Choke at the feedpoint (and at the radio).
2. **Touch or move one radial.** SWR shifts?
   -> too few radials, one carries the return current.
   Add more, shorter; keep pairs opposed.
3. **Is the dip broad and shallow?**
   -> that is loss, not a match. Compare SWR with
   SWR ANT: a big gap is feedline loss.
4. **Using a tuner? Feel it** after a long over.
   -> warm = watts. Ten tunings of one load all read
   1:1 while spanning 0.2-8.5 dB. Smallest L wins.
---
## SWR high everywhere (>5)
- Open or short in the feedline: MEASURE -> CABLE (S11)
- Connector not tight; adapter missing from the cal
- Calibration off: status column shows no C letter
## Dip in the wrong place
- Element length: 468/f ft (dipole), 234/f (1/4 wave)
- Nearby metal or low height shifts f0 down
- Coax on a vertical acts as a radial: add a choke
- Ground system changed since tuning: retune
## Reading jumps around
- Loose connector, cable moving during the sweep
- Nearby transmitter: pause the sweep, retry
- Battery low: charge; noise shows first at 900 MHz

Source: portable-vertical-reference s8.2; manual ch. 5
