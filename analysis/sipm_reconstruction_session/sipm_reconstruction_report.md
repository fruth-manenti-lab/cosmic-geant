# SiPM Muon Position Reconstruction Logbook

## Table of Contents

- [Purpose](#purpose)
- [Detector Readout Geometries](#detector-readout-geometries)
- [Simulation Samples](#simulation-samples)
- [Reconstruction Inputs](#reconstruction-inputs)
- [Methods](#methods)
- [Results](#results)
- [Design Interpretation](#design-interpretation)
- [Conclusions](#conclusions)
- [Data Provenance](#data-provenance)
- [Appendix: Training Statistics Checks](#appendix-training-statistics-checks)
- [Packaged Artifacts](#packaged-artifacts)

## Purpose

The goal of this study is to reconstruct the transverse muon hit position in the detector from the SiPM count pattern produced by a single simulated muon. Most initial studies used a 32-channel fiber-end readout, the double-ended geometry uses 64 channels, and the newest face-mount/hybrid studies use 32 channels mounted around a 1 m x 1 m slab. The target comparison point is the existing simple SiPM-weighting estimate, which gives roughly 2 cm one-sigma position deviation on a single hit.

The central design question became:

```text
Does the reconstruction improve because we remove fiber stubs,
or because we change the SiPM readout pattern?
```

To answer that, eight geometries are compared in a controlled order:

1. Baseline geometry with stubs and all SiPMs on positive sides.
2. No-stub geometry with the same positive-side SiPM pattern.
3. No-stub geometry with alternating SiPM sides.
4. Stubbed geometry with alternating SiPM sides.
5. Stubbed geometry with SiPMs on both ends of every fiber.
6. 1 m face-mount slab geometry with 32 SiPMs placed beside quadrant diagonals.
7. 1 m face-mount slab geometry with the same SiPM layout but absorbing black sidewalls.
8. Hybrid 1 m slab geometry with 16 face-mount SiPMs and 16 selected fiber-end SiPMs.

## Detector Readout Geometries

The first four geometries use 32 SiPM channels:

- `sipm_100` to `sipm_115`: one fiber family.
- `sipm_300` to `sipm_315`: the orthogonal fiber family.

The double-ended geometry adds the opposite readout ends and is represented by 64 channels:

- `sipm_100` to `sipm_115`: z-running fibers read out on `+z`.
- `sipm_200` to `sipm_215`: z-running fibers read out on `-z`.
- `sipm_300` to `sipm_315`: x-running fibers read out on `+x`.
- `sipm_400` to `sipm_415`: x-running fibers read out on `-x`.

The face-mount geometry uses a different 32-channel convention:

- `sipm_0` to `sipm_31`: 6 mm x 6 mm SiPMs above a 1 m x 1 m slab.
- The slab is divided into 16 squares.
- Each quadrant contains two diagonals, and each of the 16 small squares contains two SiPMs.
- The SiPM pair centers are offset 5.9 cm from the relevant diagonal.

The hybrid geometry combines the two ideas:

- `sipm_0` to `sipm_15`: 6 mm x 6 mm face-mount SiPMs at the centers of the 16 slab cells.
- `sipm_100` to `sipm_115`: 1 mm fiber-end SiPMs on selected real groove lanes.
- Four fiber-end SiPMs are placed on each side of the detector using the specified side-row pattern.

The schematics below are top views in the detector x-z plane. Blue lines are the z-running fiber family, orange lines are the x-running fiber family, black squares are SiPMs, green squares are grease/contact regions, and dashed gray extensions are external fiber stubs.

![Geometry schematic comparison](figures/geometry_schematic_comparison.png)

### Geometry A: Baseline Stubs, Positive-Side SiPMs

- Geometry ID: `geom-final-stubs-pos`
- GDML: `geometry/final.gdml`
- Stub state: external fiber stubs present.
- Readout pattern: all SiPMs on positive detector sides.
- `sipm_100` to `sipm_115`: read out on `+z`.
- `sipm_300` to `sipm_315`: read out on `+x`.
- Reason for testing: this is the original reference geometry.

![Baseline geometry schematic](figures/geom-final-stubs-pos_schematic.png)

### Geometry B: No Stubs, Positive-Side SiPMs

- Geometry ID: `geom-nostubs-pos`
- GDML: `geometry/final_no_stubs_pos_sipms.gdml`
- Stub state: no external fiber stubs.
- Readout pattern: all SiPMs still on positive detector sides.
- `sipm_100` to `sipm_115`: read out on `+z`.
- `sipm_300` to `sipm_315`: read out on `+x`.
- Reason for testing: isolates the effect of removing stubs while keeping the old readout pattern.

![No-stubs positive-side geometry schematic](figures/geom-nostubs-pos_schematic.png)

### Geometry C: No Stubs, Alternating-Side SiPMs

- Geometry ID: `geom-nostubs-alt`
- GDML: `geometry/final_no_stubs.gdml`
- Stub state: no external fiber stubs.
- Readout pattern: SiPM side alternates lane-by-lane.
- `sipm_100` to `sipm_115`: readout alternates between `+z` and `-z`.
- `sipm_300` to `sipm_315`: readout alternates between `+x` and `-x`.
- Reason for testing: gives the same number of SiPMs but changes the spatial information content of the 32-channel pattern.

![No-stubs alternating-side geometry schematic](figures/geom-nostubs-alt_schematic.png)

### Geometry D: Stubs, Alternating-Side SiPMs

- Geometry ID: `geom-stubs-alt`
- GDML: `geometry/final_stubs_alternating.gdml`
- Stub state: external coated fiber stubs present.
- Readout pattern: SiPM side alternates lane-by-lane.
- Readout ends use `geometry/fiber_kuraray_stub.gdml`, the coated stub with an open readout face.
- Opposite ends use `geometry/fiber_kuraray_stub_capped.gdml`, the coated stub with a mirrored outer cap.
- Reason for testing: isolates whether the alternating readout pattern remains useful when the original stub optics are restored.

![Stubs alternating-side geometry schematic](figures/geom-stubs-alt_schematic.png)

### Geometry E: Stubs, Double-Ended SiPMs

- Geometry ID: `geom-stubs-double-ended`
- GDML: `geometry/final_stubs_double_ended_sipms.gdml`
- Stub state: external coated fiber stubs present.
- Readout pattern: every fiber is read out on both ends.
- `sipm_100` to `sipm_115`: z-running fibers read out on `+z`.
- `sipm_200` to `sipm_215`: z-running fibers read out on `-z`.
- `sipm_300` to `sipm_315`: x-running fibers read out on `+x`.
- `sipm_400` to `sipm_415`: x-running fibers read out on `-x`.
- Reason for testing: checks whether direct information from both ends of each fiber improves localization enough to justify doubling the SiPM channel count.

This geometry is symmetric under x and z reflections. To reduce simulation time, the training and random test scans were generated only in the positive quadrant of the slab. During kNN fitting, the positive-quadrant training events are reflected virtually into the other three quadrants by mapping both the position labels and the SiPM count columns.

![Positive-quadrant virtual mapping](figures/positive_quadrant_virtual_mapping.svg)

### Geometry F: 1 m Face-Mount Diagonal SiPMs

- Geometry ID: `geom-facemount-1m-diagonal`
- GDML: `geometry/faceMountGeometry_1m_diagonal_sipms.gdml`
- Stub state: no fiber stubs.
- Readout pattern: 32 SiPMs face-mounted above the slab, with two SiPMs per 25 cm x 25 cm small square.
- `sipm_0` to `sipm_31`: 6 mm x 6 mm SiPMs arranged beside quadrant diagonals.
- Reason for testing: checks whether direct face-mounted SiPMs can outperform fiber-end readout with the same 32-channel count.

![Face-mount 1 m diagonal SiPM layout](../../geometry/facemount_1m_diagonal_sipm_preview.png)

The face-mount layout is also symmetric under x and z reflections. The positive-quadrant training scan can therefore be expanded virtually by reflecting the hit position and permuting the 32 SiPM columns according to the geometric copy-number map below.

![Face-mount virtual SiPM mapping](../../geometry/facemount_1m_virtual_sipm_mapping.png)

### Geometry G: 1 m Hybrid Face-Mount + Fiber-End SiPMs

- Geometry ID: `geom-hybrid-1m-16face-16fiber`
- GDML: `geometry/faceMountGeometry_1m_hybrid_16face_16fiber.gdml`
- Stub state: no external fiber stubs.
- Readout pattern: 16 face-mounted 6 mm SiPMs plus 16 no-stub fiber-end 1 mm SiPMs.
- `sipm_0` to `sipm_15`: face-mounted SiPMs at the 16 cell centers.
- `sipm_100` to `sipm_115`: selected fiber-end SiPMs.
- Reason for testing: keeps the 32-channel budget while trading half of the face-mount channels for sparse fiber-end information to reduce the face-mount tail.

![Hybrid face-mount/fiber-end layout](../../geometry/hybrid_facemount_fiber_preview.png)

### Geometry H: 1 m Face-Mount Diagonal SiPMs With Black Sidewalls

- Geometry ID: `geom-facemount-1m-diagonal-black-sidewalls`
- GDML: `geometry/faceMountGeometry_1m_diagonal_sipms_black_sidewalls.gdml`
- Stub state: no fiber stubs.
- Readout pattern: same 32 face-mounted 6 mm SiPMs as Geometry F.
- Optical change: only the large top and bottom slab faces keep the diffuse teflon reflector; the four side wraps are `VantaBlack` with 0.01 reflectivity.
- Reason for testing: checks whether the original face-mount 95% tail is caused by sidewall reflections near slab edges and corners.

## Simulation Samples

The simulations are Geant4 single-muon scans. Two types of samples are used:

- Fixed-position training scans: muons are generated at known grid positions.
- Random-position test scans: muons are generated at random positions not restricted to the training grid.

For newer `ADD_SCAN` runs, one Geant4 run can contain many source positions. The event label is taken from the source-truth ntuple:

```text
EventID -> SourceIndex -> generated source position
SourceCycle -> repeated pass through the source-position table
```

This is preferred over inferring labels from thread-split output filenames.

## Reconstruction Inputs

The raw Geant4 hit ntuples are converted into one compact event vector. For the 32-channel geometries:

```text
[sipm_100, ..., sipm_115, sipm_300, ..., sipm_315]
```

Each value is the number of unique `OpWLS` photon tracks detected by that SiPM in that event.

For the double-ended geometry the same convention is extended to:

```text
[sipm_100, ..., sipm_115,
 sipm_200, ..., sipm_215,
 sipm_300, ..., sipm_315,
 sipm_400, ..., sipm_415]
```

For the face-mount geometry the event vector is:

```text
[sipm_0, ..., sipm_31]
```

These are direct SiPM sensitive-detector hits in `sipm_PV`. Unlike the fiber WLS analyses, the face-mount conversion counts all SiPM hits with `--process-name any`, because the relevant hit records are tagged as `Scintillation` and `Cerenkov` rather than `OpWLS`.

For the hybrid geometry the event vector is:

```text
[sipm_0, ..., sipm_15,
 sipm_100, ..., sipm_115]
```

The hybrid conversion also uses `--process-name any`, because the face SiPMs see direct `Scintillation`/`Cerenkov` hits while the fiber-end SiPMs see `OpWLS` hits.

The conversion scripts are:

- `scripts/unique_wls_sipm_counts_pipeline.py`
- `scripts/prepare_random_test_scan_data.py`
- `scripts/prepare_add_scan_test_data.py`

The converted per-event CSVs are generated data products and are kept outside Git. Compact summaries, figures, and metadata files are kept in this report package.

## Methods

### kNN Event Library

k-nearest neighbors treats each event as a point in SiPM-count space. For a test event:

1. Build its SiPM count vector.
2. Compare it to the training event library.
3. Find the closest training examples.
4. Predict the hit position from the known positions of those neighbors.

The best settings varied slightly by geometry, but the useful configurations were all event-library kNN models using Euclidean distance with either raw, square-root, or L1-normalized counts. Inverse or inverse-square distance weighting generally helped. Averaging events into per-position templates was tested earlier, but individual training events generally performed better and are used for the double-ended study.

### Virtual Quadrant Expansion

The double-ended training scan covers only the positive quadrant, but the detector geometry is symmetric under x and z reflections. To avoid bias near the `x=0` and `z=0` symmetry borders, the kNN reference set is expanded in memory:

```text
(x, z) -> ( x,  z), (-x,  z), ( x, -z), (-x, -z)
```

The SiPM count columns are permuted consistently with each reflection. For example:

- reflecting across `x=0` reverses the z-running lane index and swaps the x-running readout side: `100+i -> 100+(15-i)` and `300+i -> 400+i`.
- reflecting across `z=0` swaps the z-running readout side and reverses the x-running lane index: `100+i -> 200+i` and `300+i -> 300+(15-i)`.

The virtual rows are not written as duplicate training files. They are created only in memory for the kNN nearest-neighbor search. The 1000-event random test set remains the real positive-quadrant sample.

The same virtual expansion was used for the face-mount geometry. In that case the copy-number permutation is derived from the 32 physical SiPM coordinates, so each reflection maps `sipm_0` to `sipm_31` by the actual diagonal layout rather than by fiber lane index.

### One-Axis Readout Masking

The double-ended event data can also be re-analyzed as if only one opposite pair of detector sides had SiPMs installed. This is done by masking the kNN feature vector, not by rerunning Geant4:

- `+x/-x` sides only: use copy families `sipm_300` to `sipm_315` and `sipm_400` to `sipm_415`.
- `+z/-z` sides only: use copy families `sipm_100` to `sipm_115` and `sipm_200` to `sipm_215`.

Both one-axis tests use the same positive-quadrant training and random test samples as the full 64-channel double-ended result, with the same virtual quadrant expansion.

### Projection Centroid

The projection centroid is a transparent baseline, not a trained model. It treats the two SiPM families as independent 1D projections:

```text
predicted coordinate = sum(sipm_position * sipm_count) / sum(sipm_count)
```

This is useful as a sanity check, but for the 32-channel studies it compresses the full light pattern into two weighted averages and cannot represent nonlinear light-sharing patterns well.

## Results

All quoted test results below use 1000 random single-muon test events. Configurations are ranked by 68% radial error, best to worst.

### Ranked Configuration Comparison

| Rank | Configuration | Channels | Stub state | SiPM pattern | Training library | Best kNN setting | Mean radial error | Median radial error | 68% radial error | 95% radial error |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|
| 1 | `geom-facemount-1m-diagonal` | 32 | no fiber stubs | face-mounted diagonal pairs, teflon sides | positive quadrant: 256 positions x 10 events, reflected virtually | k=16, euclidean, L1 counts, inverse-square | 1.75 cm | 1.23 cm | 1.74 cm | 5.05 cm |
| 2 | `geom-facemount-1m-diagonal-black-sidewalls` | 32 | no fiber stubs | face-mounted diagonal pairs, black absorbing sides | positive quadrant: 256 positions x 10 events, reflected virtually | k=24, euclidean, log1p counts, inverse-square | 1.62 cm | 1.42 cm | 1.84 cm | 3.46 cm |
| 3 | `geom-hybrid-1m-16face-16fiber` | 32 | no fiber stubs | 16 face SiPMs + 16 selected fiber-end SiPMs | positive quadrant: 256 positions x 10 events, no virtual reflection | k=8, euclidean, sqrt-L1 counts, inverse-square | 1.75 cm | 1.48 cm | 1.97 cm | 4.11 cm |
| 4 | `geom-stubs-double-ended`, all four sides | 64 | stubs present | both ends of every fiber | positive quadrant: 2500 positions x 10 events, reflected virtually | k=16, euclidean, L1 counts, inverse | 1.89 cm | 1.62 cm | 2.21 cm | 4.42 cm |
| 5 | `geom-stubs-double-ended`, density control | 64 | stubs present | both ends of every fiber | positive quadrant: 256 positions x 10 events, reflected virtually | k=16, euclidean, L1 counts, inverse | 2.14 cm | 1.83 cm | 2.44 cm | 4.85 cm |
| 6 | `geom-nostubs-alt` | 32 | no stubs | alternating sides | 1024 positions x 10 events | k=12, euclidean, L1 counts, inverse-square | 2.58 cm | 2.25 cm | 2.99 cm | 5.60 cm |
| 7 | `geom-stubs-alt` | 32 | stubs present | alternating sides | 1024 positions x 10 events | k=12, euclidean, L1 counts, inverse-square | 2.70 cm | 2.35 cm | 3.11 cm | 6.24 cm |
| 8 | `geom-stubs-double-ended`, `+z/-z` sides only | 32 | stubs present | one opposite side pair only | positive quadrant: 2500 positions x 10 events, reflected virtually | k=32, euclidean, L1 counts, inverse | 3.58 cm | 3.13 cm | 4.18 cm | 7.99 cm |
| 9 | `geom-stubs-double-ended`, `+x/-x` sides only | 32 | stubs present | one opposite side pair only | positive quadrant: 2500 positions x 10 events, reflected virtually | k=32, euclidean, L1 counts, inverse-square | 3.69 cm | 3.22 cm | 4.37 cm | 8.49 cm |
| 10 | `geom-final-stubs-pos` | 32 | stubs present | positive sides only | 1024 positions x 100 events | k=48, euclidean, raw counts, inverse-square | 4.30 cm | 2.87 cm | 4.40 cm | 13.73 cm |
| 11 | `geom-nostubs-pos` | 32 | no stubs | positive sides only | 1024 positions x 10 events | k=12, euclidean, sqrt counts, inverse-square | 4.64 cm | 3.22 cm | 4.71 cm | 14.12 cm |

The ranking shows four useful regimes. The original 32-channel face-mount diagonal layout gives the best median and 68% radial errors in this report. The black-sidewall face-mount variant gives up a little central resolution but now has the best 95% tail. The hybrid layout has worse central resolution than both full face-mount variants, but it also improves the 95% tail relative to the original teflon-sidewall face-mount geometry. Full double-ended readout is still the best fiber-end configuration, even when its training density is reduced to match the older effective full-slab density. Alternating 32-channel fiber-end readout is the next tier. One-axis opposite-side readout is better than the weakest positive-side configurations in tail behavior, but it is not competitive with face-mounted, hybrid, full double-ended, or alternating-side 32-channel readout.

The key fiber-end 32-channel comparisons are Geometry A versus Geometry D, and Geometry B versus Geometry C. In both pairs, the alternating readout pattern improves reconstruction substantially. Comparing Geometry C and Geometry D suggests that restoring stubs slightly worsens the alternating-readout performance, but the effect is much smaller than the effect of changing the readout pattern. Geometry E is a larger design change because it doubles the readout to 64 channels and uses positive-quadrant symmetry to reduce the simulation load. Geometry F is different again: it removes the fiber-end readout assumption and places the 32 SiPMs directly above the slab.

### Baseline: Stubs, Positive-Side SiPMs

| Method | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---:|---:|---:|---:|---:|---:|
| kNN event library | 4.30 cm | 2.87 cm | 4.40 cm | 13.73 cm | 4.13 cm | 4.38 cm |
| Projection centroid | 16.24 cm | 12.96 cm | 19.09 cm | 41.50 cm | 14.22 cm | 14.56 cm |

![Baseline kNN and centroid comparison](figures/knn_centroid_comparison.png)

### No Stubs, Positive-Side SiPMs

| Method | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---:|---:|---:|---:|---:|---:|
| kNN event library | 4.64 cm | 3.22 cm | 4.71 cm | 14.12 cm | 4.53 cm | 4.46 cm |
| Projection centroid | 17.02 cm | 13.47 cm | 20.45 cm | 42.98 cm | 14.98 cm | 14.95 cm |

![No-stubs positive-side kNN and centroid comparison](nostubs_pos_may8/figures/knn_centroid_comparison.png)

### No Stubs, Alternating-Side SiPMs

| Method | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---:|---:|---:|---:|---:|---:|
| kNN event library | 2.58 cm | 2.25 cm | 2.99 cm | 5.60 cm | 2.09 cm | 2.21 cm |
| Projection centroid | 10.61 cm | 9.62 cm | 12.66 cm | 22.04 cm | 8.70 cm | 8.55 cm |

![No-stubs alternating-side kNN and centroid comparison](new_geometry_may7/figures/knn_centroid_comparison.png)

### Stubs, Alternating-Side SiPMs

| Method | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---:|---:|---:|---:|---:|---:|
| kNN event library | 2.70 cm | 2.35 cm | 3.11 cm | 6.24 cm | 2.26 cm | 2.35 cm |
| Projection centroid | 10.13 cm | 9.17 cm | 11.72 cm | 21.47 cm | 8.23 cm | 8.33 cm |

![Stubs alternating-side kNN and centroid comparison](stubs_alt_may8/figures/knn_centroid_comparison.png)

### Stubs, Double-Ended SiPMs

This configuration uses a different readout size: 64 SiPM channels instead of 32. The training scan was generated only in the positive quadrant:

- Training macro: `macros/muon_scan_positive_quadrant_2500x10_one_run.mac`
- Training positions: `macros/muon_scan_positive_quadrant_2500_positions.mac`
- Training library: 2500 positive-quadrant positions x 10 events = 25000 real training events.
- Random test macro: `macros/random_muon_scan_positive_quadrant_1000_one_run.mac`
- Random test sample: 1000 positive-quadrant events.
- kNN reference: individual training events expanded virtually into four quadrants, giving 100000 in-memory reference vectors.

| Method | Training density | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---|---:|---:|---:|---:|---:|---:|
| kNN event library with virtual quadrants | 2500 positions x 10 events | 1.89 cm | 1.62 cm | 2.21 cm | 4.42 cm | 1.58 cm | 1.58 cm |
| kNN event library with virtual quadrants | 256 positions x 10 events | 2.14 cm | 1.83 cm | 2.44 cm | 4.85 cm | 1.81 cm | 1.78 cm |

The second row is a density-control test. It keeps the double-ended SiPM geometry but uses only a 16 x 16 evenly spread subset of the positive-quadrant grid. After virtual reflection, this corresponds to the old full-slab training density: 1024 effective positions total.

The result gets worse when the training density is reduced, but it remains better than the 32-channel stubbed alternating geometry. This suggests the double-ended readout is contributing real information, not merely benefiting from the denser scan.

### Double-Ended One-Axis Readout Tests

These tests use the same converted double-ended event data but mask the kNN input vector to only one opposite side pair. This approximates detector layouts with SiPMs on two opposite sides only.

| Readout mask | Channels | Best kNN setting | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| all four sides | 64 | k=16, euclidean, L1 counts, inverse | 1.89 cm | 1.62 cm | 2.21 cm | 4.42 cm | 1.58 cm | 1.58 cm |
| `+z/-z` sides only | 32 | k=32, euclidean, L1 counts, inverse | 3.58 cm | 3.13 cm | 4.18 cm | 7.99 cm | 1.92 cm | 3.56 cm |
| `+x/-x` sides only | 32 | k=32, euclidean, L1 counts, inverse-square | 3.69 cm | 3.22 cm | 4.37 cm | 8.49 cm | 3.70 cm | 1.95 cm |

The one-axis masks lose precision mainly in the coordinate along the readout-side direction. With only `+z/-z` sides, `sigma z` grows to 3.56 cm while `sigma x` stays near 1.92 cm. With only `+x/-x` sides, the pattern flips: `sigma x` grows to 3.70 cm while `sigma z` stays near 1.95 cm.

An explicit light-sharing feature test was also run for the one-axis masks. For
each opposite SiPM pair, 16 ratio features were appended to the 32 count
channels after count normalization. Two definitions were tested:
`(positive-negative)/(positive+negative)` and
`positive/(positive+negative)`, with small scale factors from 0.02 to 0.5.
This did not improve the kNN result; the best configuration for both axes
remained the count-only baseline in the table above. The ratio features appear
to mostly reweight information already present in the normalized count vector,
and larger ratio weights worsened the nearest-neighbor metric.

### Face-Mount 1 m Diagonal SiPMs

This configuration uses 32 direct face-mounted SiPM channels instead of fiber-end SiPM families. The training and random test scans were generated in the positive quadrant:

- Geometry: `geometry/faceMountGeometry_1m_diagonal_sipms.gdml`
- Training macro: `macros/muon_scan_positive_quadrant_256x10_one_run.mac`
- Training positions: `macros/muon_scan_positive_quadrant_256_positions.mac`
- Training library: 256 positive-quadrant positions x 10 events = 2560 real training events.
- Random test macro: `macros/random_muon_scan_positive_quadrant_1000_one_run.mac`
- Random test sample: 1000 positive-quadrant events.
- kNN reference: individual training events expanded virtually into four quadrants, giving 10240 in-memory reference vectors.

The face-mount conversion uses copy numbers `0..31` and counts all `sipm_PV` sensitive-detector hits. This is different from the WLS fiber studies, where the conversion counts unique `OpWLS` photon tracks.

| Method | Training density | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---|---:|---:|---:|---:|---:|---:|
| kNN event library with virtual quadrants | 256 positions x 10 events | 1.75 cm | 1.23 cm | 1.74 cm | 5.05 cm | 1.81 cm | 1.81 cm |
| kNN event library, positive quadrant only | 256 positions x 10 events | 1.76 cm | 1.26 cm | 1.75 cm | 5.05 cm | 1.82 cm | 1.81 cm |

The virtual reference is slightly better on the positive-quadrant test set. The nearest neighbors remain mostly in the real positive quadrant, with `991/1000` best matches from `Q++`; the few adjacent-quadrant matches are consistent with events near symmetry boundaries.

![Face-mount random scan reconstruction](facemount_may12/figures/random_scan_reconstruction.png)

![Face-mount radial error histogram](facemount_may12/figures/radial_error_histogram.png)

### Face-Mount 1 m Diagonal SiPMs With Black Sidewalls

This configuration keeps the same 32 SiPM positions as the original diagonal face-mount geometry but changes the side boundary condition:

- Geometry: `geometry/faceMountGeometry_1m_diagonal_sipms_black_sidewalls.gdml`
- Training raw data: `new_build/training_facemount_only_black_sides_may13`
- Random test raw data: `new_build/random_facemount_only_black_sides_may13`
- Training library: 256 positive-quadrant positions x 10 events = 2560 real training events.
- Random test sample: 1000 positive-quadrant events.
- kNN reference: individual training events expanded virtually into four quadrants, giving 10240 in-memory reference vectors.

The best setting uses `k=24`, Euclidean distance, `log1p` counts, and inverse-square distance weighting.

| Method | Training density | Mean radial error | Median radial error | 68% radial error | 90% radial error | 95% radial error | sigma x | sigma z |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| kNN event library with virtual quadrants | 256 positions x 10 events | 1.62 cm | 1.42 cm | 1.84 cm | 2.86 cm | 3.46 cm | 1.27 cm | 1.55 cm |

Compared with the original teflon-sidewall face-mount geometry, the black sidewalls slightly worsen the central 68% radial error, from 1.74 cm to 1.84 cm, but they strongly improve the 95% tail, from 5.05 cm to 3.46 cm. This supports the hypothesis that some of the original face-mount outliers were sidewall/corner reflection artifacts.

![Black-sidewall face-mount random scan reconstruction](facemount_black_sidewalls_may13/figures/random_scan_reconstruction.png)

![Black-sidewall face-mount radial error histogram](facemount_black_sidewalls_may13/figures/radial_error_histogram.png)

### Hybrid Face-Mount + Fiber-End SiPMs

This configuration keeps the 32-channel budget but combines 16 central face-mounted SiPMs with 16 selected fiber-end SiPMs:

- Geometry: `geometry/faceMountGeometry_1m_hybrid_16face_16fiber.gdml`
- Training raw data: `new_build/256_training_hybrid_may_13`
- Random test raw data: `new_build/random_hybrid_may_13`
- Training library: 256 positive-quadrant positions x 10 events = 2560 real training events.
- Random test sample: 1000 positive-quadrant events.
- kNN reference: positive-quadrant training events only; the full 32-channel hybrid vector is not virtually reflected because the selected fiber-end channel pattern is not closed under x/z reflection.

The best all-channel hybrid setting uses `k=8`, Euclidean distance, square-root then L1-normalized counts, and inverse-square distance weighting.

| Feature group | Channels | Mean radial error | Median radial error | 68% radial error | 90% radial error | 95% radial error | sigma x | sigma z |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all channels | 32 | 1.75 cm | 1.48 cm | 1.97 cm | 3.38 cm | 4.11 cm | 1.59 cm | 1.43 cm |
| face only | 16 | 2.62 cm | 1.89 cm | 2.74 cm | 5.83 cm | 7.38 cm | 2.37 cm | 2.50 cm |
| fiber only | 16 | 3.97 cm | 3.34 cm | 4.61 cm | 7.42 cm | 9.17 cm | 3.38 cm | 3.35 cm |

Compared with the 32-channel diagonal face-mount geometry, the hybrid layout sacrifices central resolution but improves the high-error tail: the 68% radial error worsens from 1.74 cm to 1.97 cm, while the 95% radial error improves from 5.05 cm to 4.11 cm.

![Hybrid random scan reconstruction](hybrid_may13/figures/random_scan_reconstruction.png)

![Hybrid radial error histogram](hybrid_may13/figures/radial_error_histogram.png)

## Design Interpretation

### What Removing Stubs Did

Removing stubs while keeping all SiPMs on positive sides did not improve the reconstruction. The kNN 68% radial error changed from 4.40 cm in the baseline to 4.71 cm in the no-stubs positive-side geometry. That is not an improvement and is within the range where differences in training statistics and geometry details matter.

This suggests that the stubs themselves are not the main limitation for the 32-channel reconstruction.

### What Alternating SiPM Sides Did

The alternating readout pattern changed the information content of the event vector. Instead of every channel being read out from the same side of each fiber family, neighboring lanes are read out from opposite ends.

This appears to reduce degeneracy in the SiPM pattern. The kNN 68% radial error improved from 4.71 cm in the no-stubs positive-side geometry to 2.99 cm in the no-stubs alternating geometry. The 95% radial error improved from 14.12 cm to 5.60 cm.

The alternating pattern therefore looks like the main reason for the improved reconstruction.

### What Keeping Stubs With Alternating Readout Did

The stubbed alternating geometry tests the opposite control case: keep the stubs, but change the readout pattern. It gives 3.11 cm 68% radial error, much better than the stubbed positive-side baseline at 4.40 cm.

That reinforces the same conclusion: the readout pattern is the dominant improvement. However, the stubbed alternating result is slightly worse than the no-stubs alternating result, 3.11 cm versus 2.99 cm at 68% radial error. This suggests that stubs are not beneficial for reconstruction in this configuration, although the difference is modest compared with the positive-side versus alternating-side change.

### What Double-Ended Readout Did

The double-ended geometry changes the problem more strongly than alternating sides. Instead of choosing one readout side per fiber, it measures both ends of every fiber. That doubles the count vector from 32 channels to 64 channels and gives the model direct information about light sharing along each fiber.

With the dense positive-quadrant scan and virtual quadrant expansion, the 68% radial error improves to 2.21 cm. That is the best fiber-end result in this report so far. It is also close to the original 2 cm one-sigma target from the simple weighting method, but with a much better 95% tail than the positive-side geometries.

To separate geometry improvement from training density, the same analysis was repeated using only 256 evenly spread positive-quadrant positions. This gives 1024 effective full-slab positions after reflection, matching the old training density. The 68% radial error becomes 2.44 cm. Therefore, the denser 2500-position quadrant grid helps, but the double-ended readout itself appears to be the larger improvement over the previous 32-channel geometries.

Masking the same double-ended data down to one opposite side pair gives intermediate performance: 4.18 cm 68% radial error for `+z/-z` only and 4.37 cm for `+x/-x` only. These masks preserve useful information from opposite-end light sharing, but they lose the orthogonal pair needed for balanced x-z reconstruction. The result is much worse than full double-ended readout and also worse than the alternating-side 32-channel layouts.

### What Face-Mount Diagonal Readout Did

The face-mount diagonal layout is the first 32-channel geometry in this study to beat the dense 64-channel double-ended fiber-end result on the central error metrics. With only 256 positive-quadrant training positions, virtual expansion, and 1000 random positive-quadrant test events, it reaches 1.74 cm 68% radial error and 1.23 cm median radial error.

This is not a direct stub-versus-no-stub control, because the optical collection mechanism is different. The important result is that direct face-mounted SiPM placement appears to carry stronger local position information per channel than the fiber-end layouts tested so far. The 95% error tail remains about 5.05 cm, so the next useful check is whether the outliers are dominated by edge events, optical-statistics fluctuations, or residual mapping symmetry.

### What The Hybrid Layout Did

The hybrid layout was designed to test whether sparse fiber-end information could reduce the face-mount tail while staying within the same 32-channel budget. That is broadly what happened: the 95% radial error improves from 5.05 cm in the diagonal face-mount layout to 4.11 cm in the hybrid layout.

The tradeoff is central precision. Replacing half of the face-mounted SiPMs with fiber-end channels worsens the 68% radial error from 1.74 cm to 1.97 cm and the median from 1.23 cm to 1.48 cm. The face-only and fiber-only controls show that the two subsystems are complementary, with the 16 face SiPMs carrying most of the central localization power and the fiber channels helping constrain the tail when combined with them.

### What The Black Sidewalls Did

The black-sidewall face-mount variant was designed to test whether the large-error tail came from photons reflecting around the slab sidewalls and making corner/edge events look less local. The result is a clean tradeoff: the central error gets slightly worse, but the tail improves substantially. The 68% radial error changes from 1.74 cm to 1.84 cm, while the 95% radial error improves from 5.05 cm to 3.46 cm.

That is the best tail behavior in the report so far, including the hybrid layout. It suggests that keeping teflon only on the large top/bottom slab faces and absorbing sidewall light is a useful direction if the design priority is robust worst-case reconstruction rather than the best possible median.

### Why kNN Beats Centroid

The centroid assumes a simple monotonic mapping between count-weighted SiPM position and hit position. That assumption is too simple for these simulations. kNN keeps the full SiPM pattern and compares it to simulated examples, so it can use asymmetric light sharing, edge behavior, and nonlinear detector response.

Centroid remains useful as a baseline and sanity check, but it is not competitive here.

## Conclusions

1. kNN on the full SiPM event vector is consistently better than projection centroid.
2. Removing stubs alone does not explain the reconstruction improvement.
3. Alternating SiPM sides gives a large improvement in single-event localization, both with and without stubs.
4. Among 32-channel geometries with the standard 1024-position x 10-event training scale, `geom-nostubs-alt` remains best, at 2.99 cm 68% radial error.
5. The stubbed alternating geometry is close but slightly worse, at 3.11 cm 68% radial error.
6. The 64-channel double-ended fiber-end geometry gives the best fiber-end result so far: 2.21 cm 68% radial error with the dense positive-quadrant scan and virtual quadrant expansion.
7. Reducing the double-ended training density to 256 positive-quadrant positions, equivalent to 1024 full-slab positions after reflection, gives 2.44 cm 68% radial error. This is worse than the dense scan but still better than the previous 32-channel fiber-end geometries.
8. Masking the double-ended data to only one opposite side pair gives 4.18 cm 68% radial error for `+z/-z` only and 4.37 cm for `+x/-x` only. This is not a good replacement for full double-ended or alternating-side readout.
9. The 32-channel face-mount diagonal geometry gives the best central result in this report so far: 1.74 cm 68% radial error and 1.23 cm median radial error using 256 positive-quadrant positions x 10 events with virtual quadrant expansion.
10. The black-sidewall face-mount variant gives the best tail result so far: 3.46 cm 95% radial error, while its 68% radial error is slightly worse at 1.84 cm.
11. The 32-channel hybrid geometry also improves the tail relative to original full face-mount, with 4.11 cm 95% radial error, but its 68% radial error worsens to 1.97 cm.
12. The next improvement probably needs either a better statistical model of single-event fluctuations, a learned regression model beyond nearest-neighbor matching, or additional feature engineering that uses local face-mount topology and edge behavior explicitly.

## Data Provenance

Geometry definitions are tracked in:

- `geometry/GEOMETRY_REGISTRY.md`

Dataset tracking guidance and templates are in:

- `docs/simulation_data_tracking.md`
- `docs/RUN_METADATA.template.yml`

Specific metadata files:

- `analysis/sipm_reconstruction_session/new_geometry_may7/RUN_METADATA.yml`
- `analysis/sipm_reconstruction_session/nostubs_pos_may8/RUN_METADATA.yml`
- `analysis/sipm_reconstruction_session/stubs_alt_may8/RUN_METADATA.yml`
- `analysis/sipm_reconstruction_session/double_ended_quad_may10/RUN_METADATA.yml`
- `analysis/sipm_reconstruction_session/facemount_may12/README.md`
- `analysis/sipm_reconstruction_session/facemount_black_sidewalls_may13/README.md`
- `analysis/sipm_reconstruction_session/hybrid_may13/README.md`

The recommended naming rule is:

```text
<campaign_id>_<geometry_id>_<sample>_<source>_<version>
```

The metadata files should be kept in Git even when the large raw and converted CSV files are stored separately.

## Appendix: Training Statistics Checks

### Baseline Event Count Check

For the original baseline geometry, the kNN sweep was repeated using only the first 10 events from each fixed training position.

| Training events per position | Best k | Mean radial error | Median radial error | 68% radial error | 95% radial error |
|---:|---:|---:|---:|---:|---:|
| 100 | 48 | 4.30 cm | 2.87 cm | 4.40 cm | 13.73 cm |
| 10 | 24 | 4.48 cm | 3.17 cm | 4.75 cm | 13.10 cm |

Using only 10 events per scan position made the 68% radial error worse by about 0.35 cm, or roughly 8%.

![Baseline training event count comparison](figures/knn_training_event_count_comparison.png)

### Dense Training Grid Check For Alternating Geometry

A denser training set was generated for `geom-nostubs-alt`:

- Position macro: `macros/muon_scan_10000_1event_positions.mac`
- One-run driver macro: `macros/muon_scan_one_run_10000_1event.mac`
- Training library: 10000 fixed positions x 1 event.
- Grid spacing: about 0.99 cm in x and z.

| Training library | Best kNN setting | Mean radial error | Median radial error | 68% radial error | 95% radial error | sigma x | sigma z |
|---|---|---:|---:|---:|---:|---:|---:|
| 1024 positions x 10 events | k=12, euclidean, L1, inverse-square | 2.58 cm | 2.25 cm | 2.99 cm | 5.60 cm | 2.09 cm | 2.21 cm |
| 10000 positions x 1 event | k=16, euclidean, L1, inverse | 2.54 cm | 2.26 cm | 2.95 cm | 5.50 cm | 2.03 cm | 2.23 cm |

The denser grid helps only slightly. This suggests that the remaining error is not dominated by grid spacing alone.

![Alternating geometry training library comparison](new_geometry_may7/figures/knn_training_library_comparison.png)

## Packaged Artifacts

This folder collects the SiPM reconstruction work touched during the session:

- `scripts/`: conversion, test-data preparation, kNN sweep, centroid baseline, schematic plotting, and report plotting code.
- `notebooks/`: exploratory notebooks.
- `results/`: compact summary CSVs tracked in Git; detailed generated prediction CSVs are saved separately.
- `figures/`: plots and schematics used in this report.
- `training_scan_data_1024/`: original converted fixed-position training data, stored locally/saved separately.
- `test_scan_data_1000/`: original converted random-position test data, stored locally/saved separately.
- `new_geometry_may7/`: `geom-nostubs-alt` reconstruction results.
- `nostubs_pos_may8/`: `geom-nostubs-pos` reconstruction results.
- `stubs_alt_may8/`: `geom-stubs-alt` reconstruction results.
- `double_ended_quad_may10/`: `geom-stubs-double-ended` positive-quadrant reconstruction results.
- `facemount_may12/`: `geom-facemount-1m-diagonal` positive-quadrant reconstruction results.
- `facemount_black_sidewalls_may13/`: `geom-facemount-1m-diagonal-black-sidewalls` positive-quadrant reconstruction results.
- `hybrid_may13/`: `geom-hybrid-1m-16face-16fiber` positive-quadrant reconstruction results.

Primary report outputs:

- `sipm_reconstruction_report.md`
- `figures/geometry_schematic_comparison.png`
- `figures/knn_centroid_comparison.png`
- `new_geometry_may7/figures/knn_centroid_comparison.png`
- `nostubs_pos_may8/figures/knn_centroid_comparison.png`
- `stubs_alt_may8/figures/knn_centroid_comparison.png`
- `figures/positive_quadrant_virtual_mapping.svg`
- `../../geometry/facemount_1m_diagonal_sipm_preview.png`
- `../../geometry/facemount_1m_virtual_sipm_mapping.png`
- `facemount_may12/figures/random_scan_reconstruction.png`
- `facemount_may12/figures/radial_error_histogram.png`
- `facemount_black_sidewalls_may13/figures/random_scan_reconstruction.png`
- `facemount_black_sidewalls_may13/figures/radial_error_histogram.png`
- `hybrid_may13/figures/random_scan_reconstruction.png`
- `hybrid_may13/figures/radial_error_histogram.png`
- `facemount_may12/results/knn_virtual_quadrant_sweep_results.csv`
- `facemount_black_sidewalls_may13/results/knn_virtual_quadrant_sweep_results.csv`
- `facemount_may12/results/knn_virtual_vs_positive_summary.csv`
- `hybrid_may13/results/knn_positive_quadrant_sweep_results.csv`
- `hybrid_may13/results/knn_positive_quadrant_feature_group_summary.csv`
- `double_ended_quad_may10/results/knn_virtual_density_comparison_summary.csv`
- `double_ended_quad_may10/results/knn_virtual_axis_readout_comparison_summary.csv`
- `double_ended_quad_may10/results/knn_virtual_axis_ratio_feature_comparison_summary.csv`
