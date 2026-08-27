# Orientation: the screen, the wheel and the touch panel

This chapter is about reading the sweep screen and driving the device. Everything here is
taken from the drawing and input code in `plot.c` and `ui.c`; where a behaviour was checked on
hardware the date is given, and anything not yet checked is marked `[verify on hardware]`.

## The sweep screen

The screen has four regions. Coordinates differ between the NanoVNA-H (320×240) and the H4
(480×320); the layout is the same.

**Plot area** — the grid with the traces. Eight horizontal divisions on both devices
(`NGRIDY`); ten vertical divisions in frequency (or time, in time-domain mode). Rectangular
formats draw left to right from the start frequency to the stop frequency; Smith and polar
formats draw a circle. Trace colours: trace 1 yellow, trace 2 cyan, trace 3 green, trace 4
magenta (the default palette, changeable with the `color` console command).

**Trace labels and marker readouts** — the two text columns across the top of the plot
(`marker_pos[]` in `plot.c`: up to eight lines, four per column). What they show depends on
the marker mode:

- *Trace mode* (one marker enabled, the usual case): one line per enabled trace —
  `▸CH0 LOGMAG 10dB/ -54.19dB`. The `▸` marks the **active trace** (the one SCALE, FORMAT and
  the touch scale gestures act on); `CH0` is S11, `CH1` is S21; then the format, the scale per
  division, and the trace's value at the active marker, whose frequency is shown on the right
  (`▸M1: 10.000 000 MHz`).
- *Marker mode* (two or more markers enabled): one line per enabled marker — its number,
  frequency and the active trace's value there. The `▸` marks the **active marker**, the one the
  wheel moves. The right-hand side shows `Δ1-2:` with the frequency difference between the
  active marker and the previously active one, or, with MARKER → DELTA on, every marker's
  readout relative to the active one.[^mkmode]

**Status column** — the narrow strip down the left edge (`draw_cal_status()` in `plot.c`),
in the small font, starting at y = 100. From the top:

| Text | Meaning |
|---|---|
| `C0` … `C6` | Calibration is **applied**, loaded from save slot 0–6. `C*` = a calibration made but not saved to a slot. |
| `c0` … `c6` (lower case, coloured) | Same, but the calibration is being **interpolated**: the sweep range or point count differs from the range the calibration was made on. Accuracy degrades the further you stray. |
| `O` | OPEN standard collected |
| `S` (first) | SHORT standard collected |
| `D` | Directivity term Ed computed (from LOAD) |
| `R` | Reflection-tracking term Er computed |
| `S` (second) | Source-match term Es computed |
| `T` | Transmission-tracking term Et computed (from THRU) |
| `t` | THRU standard collected (before DONE) |
| `X` | Isolation term Ex computed (from ISOLN) |
| `E` | Enhanced-response correction enabled |
| `P2` `P4` `P6` `P8` | Source drive current 2/4/6/8 mA (STIMULUS → POWER) |
| `Pa` | Source drive **automatic** — the default. *Not* "paused": the firmware draws no pause indicator anywhere.[^pa] |
| `s1` … `s8` | Trace smoothing factor (DISPLAY → SMOOTH); absent when 0 |

The letters are drawn dimmed (the "disabled calibration" colour) when the calibration was
made at a different drive power than the current one — the correction is still applied, the
colour is a warning that it may not be valid.[^calpower]

**Frequency line** — the bottom text row (`draw_frequencies()` in `plot.c`). In the frequency
domain it shows `START … STOP …`, `CENTER … SPAN …`, or `CW …` depending on how the sweep was
last set; a small `▸` in front of START/CENTER or STOP/SPAN shows which one the wheel is
currently adjusting (see *Lever modes* below). The middle of the line shows `BW:1000Hz 101p` —
the IF bandwidth and the number of sweep points. In time-domain mode the line shows the
distance and time span with the velocity factor instead.

**Battery** — the icon at the top-left corner (`draw_battery_status()`): a battery outline
filled in proportion to the voltage between 3.2 V and 4.1 V, drawn in the low-battery colour
below 3.3 V. `CONFIG → VERSION` shows the measured voltage in numbers.

## The jog wheel

The wheel is a three-way switch: roll up, roll down, and push. Push and hold for 500 ms is
detected as a long press but does nothing on the sweep screen (`ui_normal_lever()` only acts
on the single click); there is no double-click.[^btn]

| Action on the sweep screen | Effect |
|---|---|
| Push | Open the menu (right-hand column of buttons) |
| Roll | Depends on the **lever mode** (below) |

**Lever modes** (`LM_*` in `nanovna.h`; selected by tapping, see *Touch*):

| Mode | Roll up / down does | How you know it's active |
|---|---|---|
| Marker (default) | Moves the active marker one point per click; holding the wheel accelerates (`MARKER_SPEEDUP`) | `▸` in front of the marker readout |
| Frequency 0 | Steps START (or CENTER) in decade-rounded steps | `▸` in front of START/CENTER on the frequency line |
| Frequency 1 | Steps STOP (or SPAN) | `▸` in front of STOP/SPAN |
| E-delay | Changes the active trace's electrical delay by ±20 % per click (or by the VAR DELAY step if one is set) | `▸` in front of the delay readout; only available while an electrical delay is non-zero |

Rolling in marker mode with no marker enabled does nothing.

## The touch panel

On the sweep screen a touch is interpreted in this order (`ui_normal_touch()`), and the first
rule that matches wins:

1. **Near a marker** (within 20 px on the H, 30 px on the H4): picks the marker up and drags it
   along its trace while your finger is down. It becomes the active marker.
2. **On the `BW:… p` text in the frequency line**: takes a screenshot to the SD card, in the
   format selected under SD CARD (BMP by default).
3. **On the frequency line, left half** (START/CENTER text): selects Frequency-0 lever mode;
   tapping it again when already selected opens the keypad to type the value. **Right half**
   (STOP/SPAN): the same for Frequency 1.
4. **On the top text rows** (above y = 30): left half selects E-delay mode if an electrical
   delay is set, otherwise marker mode; tapping again opens the E-delay keypad.
5. **On the left or right edge of the plot** (the scale/reference gesture area, not on a Smith
   chart): tapping in the top quarter moves the reference position up by half a division; the
   second quarter doubles the scale; the third halves it; the bottom quarter moves the reference
   down. Applies to the active trace.
6. **Anywhere else**: opens the menu on release.

Touch is debounced: a second tap within 100 ms of releasing the first is ignored (this fork,
issue #109).

## Menus and keypads

The menu is a column of buttons at the right edge. Roll the wheel to move the highlight (the
highlighted button is drawn darker with its bevel reversed) and push to activate; or tap a
button directly. Every menu ends with `‹ BACK`; `› MORE` continues a long menu on a second
page. Buttons that show a value draw it in blue on a second line; buttons that toggle a
setting show a check box or a radio mark. The full tree is in the
[menu map](09-menu-map.md).

Numeric entry uses an on-screen keypad. On a frequency keypad the right-hand column holds
`G`, `M`, `k` and `×1`: each accepts the typed value in that unit (`×1` = hertz). Other keypads
have `↵` to accept; `←` deletes the last character. The keypad title names the quantity and
its unit. Text entry (file names) uses a QWERTY keypad; the wheel
moves the highlight and push types the key. To **cancel** a keypad, press an accept key (`↵`,
or `G`/`M`/`k`/`×1`) or `←` while the field is still empty — both return to the previous
screen without changing anything.[^kpcancel] Taps outside the keypad are ignored.

## Time-domain mode

With DISPLAY → TRANSFORM on, the horizontal axis is time/distance instead of frequency, the
frequency line shows the span in nanoseconds and metres (using the VELOCITY F. setting), and
the frequency lever modes are unavailable (`touch_lever_mode_select()` only offers them in the
frequency domain).

---

[^pa]: `plot.c` `draw_cal_status()`: `lcd_printf(x, y, "P%c", _power > 3 ? 'a' : _power*2 + '2')`. A search of `plot.c`, `ui.c`, `main.c` and `lcd.c` finds no code that draws a pause marker; the only visible sign of a paused sweep is that the traces stop updating.
[^calpower]: `plot.c` `draw_cal_status()`: foreground set to `LCD_DISABLE_CAL_COLOR` when `cal_power != current_props._power`.
[^mkmode]: `plot.c` `cell_draw_marker_info()`: marker display mode when `previous_marker != MARKER_INVALID`, i.e. more than one marker is enabled; otherwise the trace list is drawn.
[^kpcancel]: `ui.c` `num_keypad_click()` / `txt_keypad_click()`: return `K_CANCEL` when the accept key or backspace is pressed with `kp_index == 0`.
[^btn]: `ui.c` `btn_check()`: returns `EVT_BUTTON_DOWN_LONG` after `BUTTON_DOWN_LONG_TICKS` (500 ms); `EVT_BUTTON_DOUBLE_CLICK` is defined but never produced. `[verify on hardware]` that a long press on the sweep screen is indeed inert.
