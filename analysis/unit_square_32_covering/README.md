# 32-Point Unit-Square Covering

This folder contains a numerical search for arranging 32 points in the unit square so that the maximum Euclidean distance from any point in the square to the nearest chosen point is as small as possible.

Equivalently, it searches for 32 equal-radius disks whose centers lie in `[0, 1] x [0, 1]` and whose union covers the unit square with minimum radius.

## Objective

For centers `p_i`, minimize

```text
R = max_{x in [0,1]^2} min_i ||x - p_i||_2
```

The square side length is normalized to `1`, so a radius of `0.124` means `12.4%` of the side length. For a `1 m x 1 m` square, that is about `12.4 cm`.

## Contents

- `optimize_32_cover.py` - parallel SciPy optimizer with configurable starts, grids, and worker count.
- `results/best_points.csv` - best 32 centers from the long 32-worker run.
- `results/best_points.png` - plot of the best point set and sampled covering circles.
- `results/long_32_worker_run.log` - full console log from the 1004-start run.
- `make_cover32_facemount_gdml.py` - creates `geometry/faceMountGeometry_1m_cover32_sipms.gdml` from the best points.
- `generate_cover32_scan_macros.py` - creates the full-slab random and training ADD_SCAN macros.
- `run_cover32_muon_scans.sh` - detached launcher for the random and training Geant4 runs.
- `results/cover32_sipm_mapping_mm.csv` - unit-square points mapped to SiPM copy numbers and millimeter coordinates.

## Best Result From This Run

The best candidate in `results/best_points.csv` came from the `random_181` start in a 1004-start parallel sweep.

```text
Rectangular 8x4 grid radius: 0.139754249
Best sampled radius:         0.123880541
Plot sampled radius:         0.124066067
```

The sampled radius values differ slightly because they are evaluated on different finite grids. They should be read as numerical estimates, not a proof of global optimality.

## Reproducing The Long Run

From the repository root:

```bash
python3 -u analysis/unit_square_32_covering/optimize_32_cover.py \
  --jobs 32 \
  --opt-grid 90 \
  --check-grid 901 \
  --maxiter 300 \
  --jitter 100 \
  --random 600 \
  --seed 2026061902 \
  --csv-out analysis/unit_square_32_covering/results/best_points.csv \
  --plot-out analysis/unit_square_32_covering/results/best_points.png
```

Dependencies used in WSL user Python:

```text
numpy
scipy
matplotlib
```

## Notes

The optimizer uses a smooth power-mean approximation to the max distance during local optimization, then checks each candidate on a dense sampled grid. Starts are evaluated in parallel with `ProcessPoolExecutor`; each worker keeps internal nearest-neighbor queries single-threaded to avoid nested CPU oversubscription.

## Cover32 Face-Mount Geant4 Runs

The best unit-square centers are mapped to a `1 m x 1 m` slab by

```text
x_mm = (x_unit - 0.5) * 1000
z_mm = (y_unit - 0.5) * 1000
```

Those coordinates replace the 32 top face-mount SiPM positions in `geometry/faceMountGeometry_1m_diagonal_sipms.gdml`, preserving the existing 6 mm x 6 mm SiPM solid, grease layer, Teflon top/bottom/side wrapping, sensitive detector auxiliary tag, and copy-number convention.

Generated source files:

- `geometry/faceMountGeometry_1m_cover32_sipms.gdml`
- `macros/cover32_random_muon_1000.mac`
- `macros/cover32_random_muon_1000_positions.mac`
- `macros/cover32_random_muon_1000_positions.csv`
- `macros/cover32_training_muon_10000.mac`
- `macros/cover32_training_muon_10000_positions.mac`

The random run uses 1000 single-muon events sampled uniformly over the full slab, `x,z in [-50, 50] cm`, with source height `y = 5 cm` and direction inherited from the scan build particle gun, `(0, -1, 0)`.

The training run uses 10000 single-muon events on a `100 x 100` full-slab grid. Grid points are cell centers from `-49.5 cm` to `49.5 cm` in both x and z, so each event has a unique source location while covering the whole `1 m x 1 m` area.

To generate the GDML and macros without running Geant4:

```bash
python3 analysis/unit_square_32_covering/make_cover32_facemount_gdml.py
python3 analysis/unit_square_32_covering/generate_cover32_scan_macros.py
```

To launch both runs in the existing `new_build` ADD_SCAN build:

```bash
bash analysis/unit_square_32_covering/run_cover32_muon_scans.sh
```

The launcher starts a detached `screen` session when `screen` is installed; otherwise it uses `nohup`. It creates an isolated work area under `new_build/cover32_facemount_work` and writes final outputs under:

```text
new_build/cover32_facemount_runs/random_1000_full_slab/
new_build/cover32_facemount_runs/training_10000_full_slab/
```

The launcher sources `/home/joeyl/geant4/install/bin/geant4.sh` by default so detached jobs can find the Geant4 shared libraries. Override with `GEANT4_ENV=/path/to/geant4.sh` if needed.
