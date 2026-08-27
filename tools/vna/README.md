# PC-side scripts for the NanoVNA (fork-authored)

Small Python tools that drive the device over its USB console (see
`docs/manual/08-console.md`). Upstream's own client lives in `python/`; these are separate so
the two are not confused. Requires Python 3 and pyserial: `pip install -r tools/vna/requirements.txt`.

| Script | Purpose |
|---|---|
| `resonance_log.py` | Log f0 and R at X = 0 across ground-system changes and report each step's gain in dB vs the first reading (`10·log10(R_before/R_after)`); `--csv` to record, `--s1p` to analyse a saved sweep offline. |

Protocol notes: the console is a USB CDC serial port (any baud), prompt `ch> `, commands end
with `\r`; the scripts `pause` the sweep before reading `frequencies` + `data 0` and `resume`
afterwards. Calibration must be applied on the device for the numbers to mean anything.
