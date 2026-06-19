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
