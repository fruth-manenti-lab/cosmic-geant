# Face-mount diagonal SiPM KNN run

Date: 2026-05-12

This run uses the 1 m face-mount diagonal SiPM layout with 32 SiPM copies
numbered `0..31`. The raw ADD_SCAN outputs were converted with the `facemount`
copy-number preset and `--process-name any`, because this geometry records SiPM
sensitive-detector hits with `ProcessName` values `Scintillation` and
`Cerenkov` rather than `OpWLS`.

## Inputs

- Training raw data: `new_build/256_quad_training_may12_facemount`
- Test raw data: `new_build/1000_random_scan_may12_facemount`
- Converted training events: `training_scan_data_256x10`
- Converted test events: `test_scan_data_1000`
- Virtual mapping reference: `../../geometry/facemount_1m_virtual_sipm_mapping.csv`

## Reconstruction

The face-mount KNN sweep is implemented in:

- `../scripts/knn_facemount_virtual_sweep.py`

It reflects positive-quadrant training events into `Q++`, `Q-+`, `Q+-`, and
`Q--` by mirroring the truth coordinates and permuting all 32 SiPM columns using
the same geometric copy mapping as the face-mount preview plot.

## Ranked Results

Best virtual-quadrant configuration:

- `k=16`, `metric=euclidean`, `normalization=l1`, `weighting=inverse2`
- Mean radial error: `1.750380 cm`
- Median radial error: `1.227292 cm`
- P90 radial error: `3.371756 cm`
- RMSE radial error: `2.568123 cm`
- Bias: `+0.121035 cm` in x, `+0.139373 cm` in z

Best positive-only comparison:

- `k=16`, `metric=euclidean`, `normalization=l1`, `weighting=inverse2`
- Mean radial error: `1.762857 cm`
- Median radial error: `1.255099 cm`
- P90 radial error: `3.371756 cm`
- RMSE radial error: `2.573230 cm`
- Bias: `+0.141436 cm` in x, `+0.158802 cm` in z

The virtual-quadrant reference is slightly better on this positive-quadrant test
sample, mostly by reducing the mean and median radial errors. The nearest
neighbors remain overwhelmingly in `Q++` for the positive-quadrant random test
events (`991/1000`), with a few boundary-like matches in adjacent virtual
quadrants.

## Outputs

- `results/knn_virtual_quadrant_sweep_results.csv`
- `results/knn_virtual_quadrant_best_predictions.csv`
- `results/knn_positive_only_sweep_results.csv`
- `results/knn_positive_only_best_predictions.csv`
- `results/knn_virtual_vs_positive_summary.csv`
