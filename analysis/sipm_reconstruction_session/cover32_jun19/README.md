# Cover32 Face-Mount KNN Reconstruction, June 19 2026

This folder contains the KNN reconstruction products for the 1 m face-mount geometry whose 32 SiPMs are placed at the numerically optimized unit-square covering centers.

## Geometry And Runs

- GDML: `geometry/faceMountGeometry_1m_cover32_sipms.gdml`
- SiPMs: 32 top face-mount `6 mm x 6 mm` SiPMs, copy numbers `0..31`
- Mapping: `analysis/unit_square_32_covering/results/cover32_sipm_mapping_mm.csv`
- Training raw data: `new_build/cover32_facemount_runs/training_10000_full_slab`
- Random test raw data: `new_build/cover32_facemount_runs/random_1000_full_slab`

The training set is a full-slab `100 x 100` grid, one muon per position. The random test set has 1000 full-slab positions sampled uniformly over `x,z in [-50, 50] cm`.

## Conversion

The Geant4 ADD_SCAN shards were converted with the facemount copy-number preset and `--process-name any`, matching the earlier facemount analyses where SiPM hits are recorded as sensitive-detector hits rather than only `OpWLS` process rows.

```bash
python3 analysis/sipm_reconstruction_session/scripts/prepare_add_scan_test_data.py \
  --input-dir new_build/cover32_facemount_runs/training_10000_full_slab \
  --output-dir analysis/sipm_reconstruction_session/cover32_jun19/training_scan_data_10000 \
  --sipm-preset facemount \
  --process-name any \
  --overwrite

python3 analysis/sipm_reconstruction_session/scripts/prepare_add_scan_test_data.py \
  --input-dir new_build/cover32_facemount_runs/random_1000_full_slab \
  --output-dir analysis/sipm_reconstruction_session/cover32_jun19/test_scan_data_1000 \
  --sipm-preset facemount \
  --process-name any \
  --overwrite
```

## KNN Sweep

Because the cover32 layout is not mirror-symmetric, the KNN analysis uses the direct full-slab training set and disables virtual quadrant expansion.

```bash
python3 analysis/sipm_reconstruction_session/scripts/knn_facemount_virtual_sweep.py \
  --training-dir analysis/sipm_reconstruction_session/cover32_jun19/training_scan_data_10000 \
  --test-dir analysis/sipm_reconstruction_session/cover32_jun19/test_scan_data_1000 \
  --output analysis/sipm_reconstruction_session/cover32_jun19/results/knn_direct_full_slab_sweep_results.csv \
  --predictions-output analysis/sipm_reconstruction_session/cover32_jun19/results/knn_direct_full_slab_best_predictions.csv \
  --no-virtual-quadrants \
  --normalizations l1,sqrt_l1,log1p \
  --ks 1,3,5,8,12,16,24,32 \
  --weightings uniform,inverse,inverse2
```

## Best Result

Best setting:

- `k = 8`
- metric: Euclidean
- normalization: `l1`
- weighting: inverse-square distance weighting
- reference events: 10000
- test events: 1000

| Metric | Value |
|---|---:|
| Mean radial error | 1.230 cm |
| Median radial error | 0.952 cm |
| 68% radial error | 1.333 cm |
| 90% radial error | 2.488 cm |
| 95% radial error | 3.319 cm |
| RMSE radial error | 1.576 cm |
| MAE x | 0.747 cm |
| MAE z | 0.770 cm |
| Bias x | -0.056 cm |
| Bias z | -0.007 cm |
| Sigma x | 1.082 cm |
| Sigma z | 1.145 cm |


## Random-Scan Max-SiPM Count Histogram

For each of the 1000 random full-slab muon events, the 32 SiPM count columns were reduced to the single largest SiPM count in that event. The histogram therefore shows the distribution of

```text
max(sipm_0, sipm_1, ..., sipm_31)
```

over random muon events.

Summary of the per-event maximum SiPM count:

| Metric | Value |
|---|---:|
| Events | 1000 |
| Minimum | 59 |
| Mean | 430.0 |
| Median | 338 |
| 90% quantile | 763.7 |
| 95% quantile | 1030.3 |
| Maximum | 5986 |

Histogram outputs:

- `results/random_scan_max_sipm_count_histogram.png` - linear x-axis, 50-count bins, with overflow annotation.
- `results/random_scan_max_sipm_count_histogram_bins.csv` - explicit linear histogram bin counts.
- `results/random_scan_max_sipm_count_histogram_logx.png` - log-scaled x-axis version.
- `results/random_scan_max_sipm_count_histogram_logx_bins.csv` - explicit log-x histogram bin counts.
- `results/random_scan_max_sipm_count_by_event.csv` - event-level max SiPM ID and max count.
- `results/random_scan_max_sipm_count_summary.csv` - compact summary table.

## Outputs

- `results/knn_direct_full_slab_sweep_results.csv`
- `results/knn_direct_full_slab_best_predictions.csv`
- `results/knn_direct_full_slab_summary.csv`
- `results/knn_direct_full_slab_error_map.png`
- `results/knn_direct_full_slab_error_cdf.png`

## Caveat

This result uses a denser full-slab training library than some earlier facemount studies, so direct performance comparisons should account for both the new SiPM geometry and the larger/more uniform training set.
