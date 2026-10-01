REVISION D / MECHANICAL M3 - COMPACT LAYOUT
PCB shrinks from Rev C 180 x 210 to 160 x 170 mm (28.04% less area).
The M3 enclosure is 180 x 192 x 60 mm (25.52% less footprint than M2).
Eight vertical 50-ohm BNCs retain 30 mm row pitch. Power entry faces outward
at the right edge. Heatsink envelopes remain 35 x 13 x 38.1 mm.
The 36 protected inverting-node copper shapes are rigidly translated intact;
other routing and component placements change. Circuit values, MCU and
firmware are unchanged. No PCB parasitic extraction has been performed.
Use Rev D manufacturing files with M3 mechanics; earlier designs were removed
from the first public release. Confirm temperature and connector fit on a prototype.
compaction.json gives exact component and protected-node translations.
revision_validation.json compares electrical nets and local shapes to Rev C.

4x4 programmable analog matrix - PCB D / electrical A2
2026-10-01

OPEN AND EDIT
Extract the complete package. Open analog_matrix_4x4.kicad_pro in KiCad
8.0.6 or newer, then open the PCB or its root schematic.
Keep the local symbol and footprint libraries beside the project.

There are nine sheets: index, all inputs, four complete output rows,
offset trim, control and power. Each output row now has a continuous
left-to-right signal path. Power units and decouplers stay near the
corresponding signal circuits. The project has 428 components and 18
distinct footprint types. schematic.pdf is exported from this source.
The PCB is 160 x 170 mm, with four copper layers and six M3 holes. All
components are on the front. Four repeated analog rows run from input
conditioning at the left, through the DAC/TIA cells, to 50-ohm output
drivers at the right. Pico control, DC trim and power sit below the rows.
No potentiometers or manual-mode jumpers are included in this revision.

PCB FILES
analog_matrix_4x4.kicad_pcb is the editable board. Read
FABRICATION_AND_BRINGUP.txt for stackup, assembly, cooling and first tests.
pcb_front.svg, pcb_back.svg and assembly_front.svg are physical previews.
assembly_bom.csv includes ratings and DNP flags; placement_front.csv gives
positions in mm. Select actual passive MPNs before an assembly order.
fabrication/ contains Gerbers and separate PTH/NPTH drill files.
drc.json is the native PCB-check report; pcb_audit.json compares every
electrical pad/net assignment with the checked schematic.
Rerun checks after edits. DRC does not establish measured analog performance.
The A2 SPICE results below are circuit-level results, not PCB extraction.

A2 CHANGES
- Consolidated the earlier 16-sheet schematic into nine readable sheets.
- Changed all 32 RBRP/RBRN branch resistors from 49.9 ohms to 150 ohms.
  Feedback-input loop tests found only about 33 degrees phase margin in
  the original loaded positive buffer. Final polarity-buffer estimates
  are approximately 61-66 degrees. R_OUT and RMUTE remain 49.9 ohms.
- Corrected AD5544BRSZ to SSOP-28, 5.3 x 10.2 mm body, 0.65 mm pitch.
  The A1 TSSOP assignment was wrong. Pad-number checks alone missed it.
- Coax labels now explicitly identify BNC 031-5329-52RFX connectors.
- Pico GPIO mapping is unchanged. Firmware estimated full-code gain is
  now 1.021, reflecting the 150-ohm branches. It is NOT measured calibration.
  Re-measure calibration after the resistor change; an existing Pico
  calibration.json overrides the factory estimates at startup.

CIRCUIT SCOPE
Four high-impedance inputs, +/-1 V peak each, DC through 1 MHz target.
Four outputs, up to +/-4 V peak at an EXTERNAL 50-ohm termination.
The on-board 49.9-ohm series resistor is the source termination. A high-
impedance receiver sees approximately twice the specified loaded voltage.
Coefficients range from -1 to +1. The MCU programs static coefficients;
it does not sample or synthesize the signal waveform.

Nominal final SPICE: about 0.758% amplitude reduction at 1 MHz after DC
normalization, approximately 7.24 MHz sampled -3 dB frequency, 3.971 V peak
from the full-scale matched-row surrogate, and 119 ns 1% step settling
with a 50-ohm / 20p load. Read the included SPICE report and MODEL_SCOPE.txt
before interpreting those figures. The AD5544 model is approximate, full-
matrix trim is idealized, and transient switches use a static reduction.

The report does NOT establish 1% relative accuracy at every coefficient.
An illustrative feedthrough model gives roughly 14.6% amplitude error at
M=0.01 and 0.00573 V/V residual for M=0 at 1 MHz. Absolute coefficient error
and relative coefficient error are different specifications. The 1 nF
load step stalled numerically and remains unresolved. Phase matching,
PCB parasitics, thermal behavior and hardware calibration remain unproven.

POWER AND CONTROL
Use external regulated +/-15 V and USB power for the original Raspberry Pi
Pico. +5A and -5A are +/-5 V analog rail names, not current ratings. Apply
analog supplies before powering the Pico; there is no automatic supply
supervisor. Firmware starts muted. L7805/L7905 heat dissipation and heat-
sinking must be checked as part of PCB/mechanical work.

AD5544 sets coefficient magnitude; TMUX6219 selects polarity. Shared LDAC
updates the four row DACs; two 74HC595 devices latch sixteen sign bits.
The fifth AD5544 controls four DC trim voltages. Refer to firmware/CONTROL.txt
for USB JSON commands, pin mapping, both-sign calibration and persistence.

FOOTPRINT AND PART NOTES
- ADA4899 ordering code is ADA4899-1YRDZ. Its custom RD-8-1 footprint has
  a 2.29 x 2.29 mm exposed paddle mapped to schematic pad 9, connected to GND.
- THS3091DDAR uses the DDA PowerPAD footprint with ground pad and thermal
  vias. Keep its 1.21k feedback resistor and do not fit a feedback capacitor.
- Pico footprint is for the original Pico with two 20-pin rows 17.78 mm
  apart; verify sockets or headers before ordering.
- Coax footprint is Amphenol 031-5329-52RFX vertical 50-ohm BNC. Reassign the footprint
  before substituting another connector geometry.
- Polarized capacitors use pad 1 positive and pad 2 negative, including
  those on negative rails. Rating fields specify voltage/power needs.
  Select actual purchasable parts that fit; this is not a procurement BOM.
- L7905 tab is -15 V; L7805 tab is GND. Account for heatsink insulation.
- OriginalRef fields and reference_map.json preserve the descriptive
  identifiers used by the simulation and prior design.

VALIDATION
Native KiCad parsing, ERC, PDF/netlist export and footprint SVG parsing
passed. ERC has zero violations; all 428 components match the intended
pin/net sets; all assigned symbol pins match footprint pads. Reports are
erc.json, connectivity_audit.json, footprint_audit.json and package_audit.json.
All nine schematic pages were visually inspected.

Repeat from this project directory:
kicad-cli sch erc --format json --severity-all --exit-code-violations --output erc.json analog_matrix_4x4.kicad_sch
kicad-cli sch export netlist --format kicadxml --output validation_netlist.xml analog_matrix_4x4.kicad_sch
python tools/audit_kicad.py .
python tools/audit_footprints.py .
kicad-cli sch export pdf --output schematic.pdf analog_matrix_4x4.kicad_sch

Audits are snapshots; rerun them after editing. design_instances.json is
the intended part/pin list and must reflect deliberate circuit changes.
ERC does not prove analog stability or accuracy. The simulation package
contains editable .cir files, complete successful traces and model sources.

LIBRARIES AND LICENSES
Project library tables use ${KIPRJMOD}. Standard footprints are copied from
KiCad 8.0.6; see KiCad-footprints-LICENSE.txt and footprint_provenance.json.
3D models optionally use the installed KiCad library and are not required
to inspect copper/pad geometry. Vendor SPICE models retain their original
copyright/disclaimer notices; they are not represented as open-source code.

PRIMARY PACKAGE REFERENCES
https://www.analog.com/media/en/technical-documentation/data-sheets/AD5544_5554.pdf
https://www.analog.com/media/en/technical-documentation/data-sheets/ADA4899-1.pdf
https://www.ti.com/lit/ds/symlink/ths3091.pdf
https://www.ti.com/lit/ds/symlink/tmux6219.pdf
https://www.ti.com/lit/ds/symlink/opa810.pdf
https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf
