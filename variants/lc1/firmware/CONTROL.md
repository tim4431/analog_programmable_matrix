# LC1 Pico control and calibration

Use the original Raspberry Pi Pico (RP2040) with MicroPython and this folder's `main.py`. **Revision D's firmware is incompatible with LC1.** Uploading LC1 firmware does not convert a Revision D PCB. Calibration is saved as `calibration_lc1.json` and includes the hardware revision; the original `calibration.json` is not read.

Apply the external analog ±15 V supply before connecting USB. The Pico uses USB power and shares ground with the analog circuit. GPIO-controlled analog ICs do not have guaranteed powered-off input isolation, so this order matters. Start with a current-limited supply, zero input signals, properly fitted insulated heatsinks, and external 50 Ω output terminations.

## Pin assignment

| Pico GPIO | Function |
| --- | --- |
| GP0 / GP1 | MCP4728 SDA / SCL, I²C0, 100 kHz, address 0x60 |
| GP2 / GP3 | DAC7811 clock / data, SPI0, 1 MHz, mode 2 |
| GP4–GP7 | Row 0–3 DAC SYNC, active low |
| GP10 / GP11 / GP12 | Two 74HC595 sign-register data / clock / latch |
| GP14 | RUN: low mutes all outputs, high enables them |

GP14 has a hardware pulldown and is driven low before initialization. Four DAC7811s form each row chain. The closest device is column 0; send column 3 first and column 0 last. Each command is a 16-bit word `0x1000 | code`, with code 0–4095. The rising SYNC edge applies a row's update. Mode 2 captures on falling clock edges and returns high on the trailing rising edge before SYNC rises, following the datasheet's SDO timing requirement. DAC serial outputs are 5 V logic and connect only to the next DAC, never to a Pico input.

Sign bit `4*row + column` selects the negative path when high. The two shift registers receive bit 15 first. The TMUX6136 supply is ±15 V but its input thresholds accept 3.3 V logic.

MCP4728 writes explicitly select the internal 2.048 V reference, gain of one and normal operation. The firmware uses volatile multi-write commands; it does not write the DAC EEPROM. A three-byte channel write is `[0x40 | (channel << 1), 0x80 | (code >> 8), code & 255]`. LDAC is tied low. Default trim code is 2500.

Every update first mutes, waits 20 µs, sends the sign word and all four DAC rows, updates the four trim channels, and waits 2 ms for the offset filters. The old armed state is then restored. Row updates are sequential while muted; this is intended for static coefficients, not audio-rate glitch-free modulation. Keep digital traffic quiet during measurements.

The DAC7811 has no readback verification here. Host tests validate the transmitted protocol; successful transmission cannot prove that a physical device received a command. SPI/I²C exceptions and short I²C acknowledgements keep outputs muted, invalidate the programmed state, and prevent `arm` until a successful matrix update.

## USB commands

Send one JSON object per line through MicroPython USB serial. Read the returned JSON line and check `ok`, `armed`, `program_valid`, `calibrated` and `warning`. Boot starts with all coefficients zero and outputs muted. Default gains are model estimates; a `calibrated: false` response is intentional until measurements are entered.

Set an identity matrix, then explicitly enable outputs:

```json
{"cmd":"set","matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}
{"cmd":"arm"}
```

Other commands:

```json
{"cmd":"status"}
{"cmd":"mute"}
{"cmd":"trim","codes":[2500,2500,2500,2500]}
{"cmd":"raw","row":0,"column":0,"code":4095,"negative":false}
{"cmd":"save"}
```

`raw` zeros every other coefficient and is for calibration. `save` mutes outputs, stores gains/trim in Pico flash, and leaves outputs muted. It does not store the active matrix for automatic output at boot. A malformed or invalid command received by the USB server also mutes outputs. Shutdown or exiting the server mutes outputs in its cleanup handler; loss of MCU execution is not a certified hardware interlock.

## Calibration procedure

Use a source and voltmeter/scope whose combined error is comfortably below 1%, with the same external 50 Ω termination and cabling intended for use. Warm up the board and avoid clipping. A generator's displayed amplitude can assume a 50 Ω load: measure actual input voltage at this high-impedance input.

1. With zero inputs, set the zero matrix and arm. Measure each loaded output's offset. Increase the corresponding trim code to increase the output voltage. A first estimate is `new_code = old_code - offset_volts / 0.0000551`, rounded and limited to 0–4095. Iterate while checking that the correction is in range.
2. For each row/column, use `raw` at code 4095 with the positive sign. Measure the output at actual input +0.5 V and −0.5 V, with all other inputs grounded. The measured full-code gain is `abs((b_plus - b_minus)/(a_plus - a_minus))`; using two input polarities removes the static offset.
3. Repeat with `negative: true`. Record **positive magnitudes** in separate 4 × 4 `positive` and `negative` arrays, indexed by output row and input column. Expected full-code magnitude is approximately 1.0687, but use the measured value. Firmware accepts 0.9–1.2; a channel below 1 cannot realize a unit coefficient and should be investigated.
4. Send `{"cmd":"calibration","positive":YOUR_4X4_ARRAY,"negative":YOUR_4X4_ARRAY}` with real JSON numeric arrays substituted. This command mutes and leaves the board muted; it clears raw mode. Recheck zero-input offsets, adjust trim if needed, then send `save`.
5. Set the required matrix and `arm`. Verify amplitude and phase at DC/low frequency and through 1 MHz on every path; test all-positive and all-negative full sums. Scalar DC calibration cannot remove frequency-dependent errors. If the matrix changes residual DC offset, trim again for that matrix.

The gain arrays describe the measured gain at code **4095**, hence the firmware uses `round(abs(coefficient)/gain * 4095)`. This differs from the ideal multiplying-DAC transfer denominator of 4096 and is intentional. Quantization is included in the code selection. The model's 1.0687 defaults are only an initial estimate.

## Host regression checks

Run `python variants/lc1/tools/test_firmware.py` from the repository root. Tests use fake Pico peripherals and check all relevant byte sequences and failure handling. They do not replace an oscilloscope/logic-analyzer check of hardware timing, boot sequencing and output muting.
