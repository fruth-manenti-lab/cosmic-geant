# Face-Mount Black-Sidewall Reconstruction, May 13 2026

This folder contains the compact reconstruction products for the 1 m diagonal
face-mount SiPM geometry with absorbing sidewalls.

## Geometry

- GDML: `geometry/faceMountGeometry_1m_diagonal_sipms_black_sidewalls.gdml`
- Base layout: same 32 face-mounted `6 mm x 6 mm` SiPMs as
  `geometry/faceMountGeometry_1m_diagonal_sipms.gdml`
- Optical change: top and bottom `1 m x 1 m` slab faces keep teflon diffuse
  reflectivity; four side wraps use `VantaBlack` with reflectivity `0.01`.

## Raw Inputs

- Training: `new_build/training_facemount_only_black_sides_may13`
- Random test: `new_build/random_facemount_only_black_sides_may13`

## Conversion

```powershell
C:\Users\joeyl\miniconda3\python.exe analysis\sipm_reconstruction_session\scripts\prepare_add_scan_test_data.py --input-dir new_build\training_facemount_only_black_sides_may13 --output-dir analysis\sipm_reconstruction_session\facemount_black_sidewalls_may13\training_scan_data_256x10 --sipm-preset facemount --process-name any --overwrite
C:\Users\joeyl\miniconda3\python.exe analysis\sipm_reconstruction_session\scripts\prepare_add_scan_test_data.py --input-dir new_build\random_facemount_only_black_sides_may13 --output-dir analysis\sipm_reconstruction_session\facemount_black_sidewalls_may13\test_scan_data_1000 --sipm-preset facemount --process-name any --overwrite
```

## Reconstruction

```powershell
C:\Users\joeyl\miniconda3\python.exe analysis\sipm_reconstruction_session\scripts\knn_facemount_virtual_sweep.py --training-dir analysis\sipm_reconstruction_session\facemount_black_sidewalls_may13\training_scan_data_256x10 --test-dir analysis\sipm_reconstruction_session\facemount_black_sidewalls_may13\test_scan_data_1000 --output analysis\sipm_reconstruction_session\facemount_black_sidewalls_may13\results\knn_virtual_quadrant_sweep_results.csv --predictions-output analysis\sipm_reconstruction_session\facemount_black_sidewalls_may13\results\knn_virtual_quadrant_best_predictions.csv --normalizations l1,sqrt_l1,log1p --ks 1,3,5,8,12,16,24,32 --weightings uniform,inverse,inverse2
```

Best setting:

- `k=24`
- Euclidean distance
- `log1p` counts
- inverse-square distance weighting
- virtual quadrant expansion enabled

## Result

| Mean radial error | Median radial error | 68% radial error | 90% radial error | 95% radial error | sigma x | sigma z |
|---:|---:|---:|---:|---:|---:|---:|
| 1.62 cm | 1.42 cm | 1.84 cm | 2.86 cm | 3.46 cm | 1.27 cm | 1.55 cm |

Compared with the original teflon-sidewall face-mount geometry, the absorbing
sidewalls slightly worsen the central p68 error but strongly improve the p95
tail.
