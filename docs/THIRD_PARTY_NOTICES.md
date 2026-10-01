# Third-party material

- The local KiCad footprint subset retains [KiCad-footprints-LICENSE.txt](../pcb/analog_matrix_4x4_rev_d/KiCad-footprints-LICENSE.txt).
- KiCad 3D library models retain [KiCad_models_LICENSE.md](../mechanical/analog_matrix_package_m3/KiCad_models_LICENSE.md). Custom BNC, Pico and heatsink models are simplified clearance models authored for this project.
- Manufacturer SPICE models are downloaded locally from Texas Instruments or obtained from the user's Analog Devices LTspice installation. They are excluded from Git. The model hashes and source URLs are recorded in `spice/models/provenance.json` and `spice/BENCH_MANIFEST.json`.
- `TMUX6219_static_RC.lib` is a static model reduction described in `spice/MODEL_SCOPE.txt`. Its numerical resistance table and capacitance estimates come from the TI model; it is not a manufacturer-validated substitute.

Publishing this repository does not grant rights to third-party material beyond the applicable upstream terms. No project-wide license for the original hardware, software, or documentation has been selected yet.
