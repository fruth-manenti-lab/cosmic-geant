# Double-Ended Positive-Quadrant Study

This folder tracks the `geom-stubs-double-ended` SiPM reconstruction study.

- Geometry: `geometry/final_stubs_double_ended_sipms.gdml`
- Training raw data: `new_build/25000_quad_training_scan_may9_sipm_all_sides`
- Test raw data: `new_build/1000_quad_ranom_scan_may10_sipm_all_sides`
- Training sample: 2500 positive-quadrant positions x 10 events.
- Test sample: 1000 random positive-quadrant events.
- Reconstruction: individual-event kNN with virtual x/z quadrant reflection.

Large converted per-event CSVs and detailed prediction files are ignored by Git. Compact sweep summaries, selected-position summaries, and metadata are kept here.

## One-axis readout test

The same converted all-side event data can be re-analyzed as if only one
opposite pair of SiPM sides were instrumented:

- `+x/-x` sides only: copy families `300-315` and `400-415`
- `+z/-z` sides only: copy families `100-115` and `200-215`

Run with `knn_quadrant_virtual_sweep.py --readout-axis x` or
`--readout-axis z`. The compact comparison is in
`results/knn_virtual_axis_readout_comparison_summary.csv`.

Best p68 radial errors from the May 10 virtual-quadrant sweep:

| readout | channels | best k/weighting | p68 error (cm) | p95 error (cm) |
| --- | ---: | --- | ---: | ---: |
| all four sides | 64 | k=16 inverse | 2.21 | 4.42 |
| +x/-x only | 32 | k=32 inverse2 | 4.37 | 8.49 |
| +z/-z only | 32 | k=32 inverse | 4.18 | 7.99 |

## One-axis ratio feature test

The one-axis masks were also tested with explicit positive/negative side
light-sharing features appended to the 32 count channels. The count channels
were normalized first, then 16 ratio features were appended:

- signed ratio: `(positive_side - negative_side) / (positive_side + negative_side)`
- positive fraction: `positive_side / (positive_side + negative_side)`

Focused sweeps around the previous optimum (`k=32`, inverse and inverse-square
weighting, ratio scales 0.02 to 0.5) did not improve the one-axis results. The
best row remained the count-only baseline for both axes:

| readout | best feature set | p68 error (cm) | p95 error (cm) |
| --- | --- | ---: | ---: |
| +x/-x only | counts only | 4.37 | 8.49 |
| +z/-z only | counts only | 4.18 | 7.99 |

The compact ratio-feature comparison is in
`results/knn_virtual_axis_ratio_feature_comparison_summary.csv`.
