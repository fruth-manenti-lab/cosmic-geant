# Hybrid face-mount plus fiber-end KNN run

Date: 2026-05-13

This run uses `geometry/faceMountGeometry_1m_hybrid_16face_16fiber.gdml`,
with 16 direct face-mounted 6 mm SiPMs and 16 selected fiber-end 1 mm SiPMs.

## Inputs

- Training raw data: `new_build/256_training_hybrid_may_13`
- Test raw data: `new_build/random_hybrid_may_13`
- Converted training events: `training_scan_data_256x10`
- Converted test events: `test_scan_data_1000`

The converter uses the `hybrid` copy-number preset:

- Face SiPMs: `sipm_0` to `sipm_15`
- Fiber-end SiPMs: `sipm_100` to `sipm_115`

The conversion used `--process-name any` because the hybrid geometry includes
direct face SiPM hits tagged as `Scintillation`/`Cerenkov` and fiber hits tagged
as `OpWLS`.

## Reconstruction

The KNN sweep is implemented in:

- `../scripts/knn_hybrid_positive_sweep.py`

This is a positive-quadrant direct train/test analysis. Unlike the fully
symmetric face-mount and double-ended layouts, the selected hybrid fiber-end
channels are not closed under x/z reflection, so the virtual-quadrant column
permutation is not applied to the full 32-channel hybrid vector.

## Best Results

Best all-channel configuration:

- Feature group: all 32 channels
- `k=8`, `metric=euclidean`, `normalization=sqrt_l1`, `weighting=inverse2`
- Mean radial error: `1.747375 cm`
- Median radial error: `1.483940 cm`
- 68% radial error: `1.969914 cm`
- 90% radial error: `3.383966 cm`
- 95% radial error: `4.108195 cm`

Best feature-group controls:

| feature group | channels | best setting | mean error | 68% error | 95% error |
| --- | ---: | --- | ---: | ---: | ---: |
| all | 32 | k=8, sqrt_l1, inverse2 | 1.75 cm | 1.97 cm | 4.11 cm |
| face only | 16 | k=5, sqrt_l1, inverse2 | 2.62 cm | 2.74 cm | 7.38 cm |
| fiber only | 16 | k=16, l1, inverse2 | 3.97 cm | 4.61 cm | 9.17 cm |

The hybrid result improves the 95% tail relative to the full 32-channel
diagonal face-mount study, but its central 68% error is worse. That is
consistent with the design goal: the added fiber-end channels help constrain
outliers, while losing half of the face-mounted channels costs some central
resolution.

## Outputs

- `results/knn_positive_quadrant_sweep_results.csv`
- `results/knn_positive_quadrant_feature_group_summary.csv`
- `results/knn_positive_quadrant_best_predictions.csv`
- `figures/random_scan_reconstruction.png`
- `figures/radial_error_histogram.png`
