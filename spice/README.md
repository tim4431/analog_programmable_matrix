# Circuit simulation evidence

`BENCH_MANIFEST.json` lists the final 28 delivered benches, their hashes and their status. Failed/unresolved cases are retained and are not used as successful waveform evidence. Earlier exploratory revisions have been removed.

Read `MODEL_SCOPE.txt` and the [validation report](../pcb/analog_matrix_4x4_rev_d/circuit_spice_validation_A2.pdf) before using the numerical results. This is circuit-level simulation, not extracted-PCB or thermal validation.

## Replay

1. Install LTspice for Windows.
2. Run `python spice/fetch_models.py`. It downloads the manufacturer TI packages and locates the ADA4899 model in LTspice. Use `--ada4899 PATH` if needed. These downloads remain local and retain the manufacturers' terms.
3. Run `python spice/replay.py --bench a2_row_sine_rc.cir --ltspice "PATH/TO/LTspice.exe"`.

Replay output goes into `spice/reruns/`, leaving the recorded evidence unchanged. The authored static switch reduction is supplied, while official manufacturer model files are not redistributed in Git. Model revisions may change; compare hashes with the manifest before comparing results.
