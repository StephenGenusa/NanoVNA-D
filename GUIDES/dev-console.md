# Console cheat-sheet
USB serial, 115200, prompt ch>. Type help for all.
| Task | Command |
|---|---|
| CW source for receiver tests | freq 14250000 |
| set the sweep | sweep {start} {stop} [pts] |
| calibrate from a script | cal open/short/load/thru |
| finish and apply | cal done, cal on |
| save / recall a slot | save 2 / recall 2 |
| shift the reference plane | edelay {seconds} |
| inline attenuator | s21offset {dB} |
| MEASURE panel | measure resonance |
| quieter traces | bandwidth {n}, smooth 0-9 |
| drive level | power 0-3 or power 255 |
| harmonic crossover | threshold {Hz} |
| time domain | transform on, transform step |
| markers, traces | marker 1 on, trace 0 swr 0 |
| sweep data | data 0 (S11), data 1 (S21) |
| screenshot to the PC | capture |
| battery | vbat |
| pause / resume the sweep | pause / resume |

Source: main.c commands[]; manual ch. 8
