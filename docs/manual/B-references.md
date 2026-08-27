# Appendix B — References

## Firmware and hardware

- DiSlord, *NanoVNA-D* firmware — <https://github.com/DiSlord/NanoVNA-D> (the upstream of this
  fork; issues referenced in the text as "upstream #N" are at
  <https://github.com/DiSlord/NanoVNA-D/issues>).
- StephenGenusa, *NanoVNA-D* fork — <https://github.com/StephenGenusa/NanoVNA-D> (this
  firmware, this manual, releases with binaries).
- hugen79, *NanoVNA-H* hardware repository — <https://github.com/hugen79/NanoVNA-H>: user
  guide (2019) and schematics for the NanoVNA-H (REV3.4–3.7) and NanoVNA-H4 (REV4.3, 4.4);
  copies are in this repository's `doc/` directory.
- edy555, the original NanoVNA — <https://github.com/ttrftech/NanoVNA>.
- cho45, *NanoVNA User Guide* (Japanese; English translation on nanovna.com) —
  <https://cho45.github.io/NanoVNA-manual/>. The procedures in chapters 3, 4 and 10 were
  checked against it.
- nanovna.com, "Calibration NanoVNA", "How to read NanoVNA screen", "Start measurement",
  "Upgrade NanoVNA use DFU" — <https://nanovna.com/?page_id=21> and linked pages.
- Texas Instruments, *TLV320AIC3204 Ultra Low Power Stereo Audio Codec* data sheet — input
  routing registers (page 1, 0x34–0x39) referenced in the raw-S21 discussion.

## Measurement theory used in the text

- A. D. Yaghjian and S. R. Best, "Impedance, Bandwidth, and Q of Antennas," *IEEE Transactions
  on Antennas and Propagation*, vol. 53, no. 4, pp. 1298–1324, April 2005. (SWR BW's Q.)
- A. D. Yaghjian, "Fundamentals of Antenna Bandwidth and Quality Factor," arXiv:2501.03146,
  2025 — equations 7, 12 and 21 (open-access restatement of the above).
- M. W. Maxwell, W2DU, *Reflections III: Transmission Lines and Antennas*, CQ Communications,
  2010 — appendix 6, SWR referred through line loss (SWR ANT's relation; the 3:1 through 0.5 dB
  = 2.61:1 check).
- ARRL, *The ARRL Antenna Book for Radio Communications*, 24th/25th ed. — Vol. 1, "Q of
  Antennas" (the 2:1 SWR bandwidth convention); Vol. 3, Table 23.4, "Cable Attenuation (dB per
  100 feet)" (the coax presets).
- J. Sevick, W2FMI, *QST*, March 1973 — measured feedpoint resistance of ground-mounted
  verticals with different loading and ground systems; the feedpoint-resistance method behind
  the RESONANCE panel's ground-system comparison (R_feed = R_rad + R_ground).

## Tools

- dfu-util — <https://dfu-util.sourceforge.net/> (flashing, chapter 10).
- NanoVNA-Saver — <https://github.com/nanovna-saver/nanovna-saver>; NanoVNA-App (OneOfEleven)
  — PC applications that use the console protocol of chapter 8.
- pandoc and XeLaTeX — this manual is built from Markdown by `tools/manual/build.py`.
