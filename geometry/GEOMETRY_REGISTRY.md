# Geometry Registry

This file tracks the detector geometry variants used for SiPM reconstruction studies. Use the `geometry_id` values in run metadata files so analysis folders can be traced back to the exact detector layout.

## `geom-dilutiondetector`

- File: `geometry/dilutiondetector.gdml`
- Layout: two `8 mm x 8 mm x 14 mm` polystyrene scintillators stacked along `y`, centers 25 mm apart.
- Readout: one SiPM centered on each `+z` square face with a 0.5 mm vacuum gap.
- Muon clock: centered `100 mm x 10 mm x 100 mm` vacuum sensitive detector below the stack.
- World: `2 m x 2 m x 2 m` vacuum cube, large enough to contain the CRY `subboxLength 1` footprint above the detector.
- Wrapper: ESR film on all scintillator faces except the SiPM-facing `+z` faces.
- Purpose: muon-clock-based rate normalization for the dilution detector study.

## `geom-final-stubs-pos`

- File: `geometry/final.gdml`
- Readout: all SiPMs on positive sides only.
- `sipm_100` to `sipm_115`: z-running fibers read out on `+z`.
- `sipm_300` to `sipm_315`: x-running fibers read out on `+x`.
- Fiber ends: external fiber stubs are present.
- Foil holes: side faces are perforated for the stub/readout penetrations.
- Purpose: original baseline geometry for the first reconstruction studies.

## `geom-nostubs-alt`

- File: `geometry/final_no_stubs.gdml`
- Readout: SiPM sides alternate lane-by-lane.
- `sipm_100` to `sipm_115`: z-running fibers alternate between `+z` and `-z` as x changes.
- `sipm_300` to `sipm_315`: x-running fibers alternate between `+x` and `-x` as z changes.
- Fiber ends: no external stubs; SiPMs couple directly to embedded fiber ends through grease.
- Foil holes: positive and negative side faces are perforated because readout exists on both sides.
- Purpose: tests direct fiber-end coupling plus alternating readout pattern.

## `geom-stubs-alt`

- File: `geometry/final_stubs_alternating.gdml`
- Readout: SiPM sides alternate lane-by-lane.
- `sipm_100` to `sipm_115`: z-running fibers alternate between `+z` and `-z` as x changes.
- `sipm_300` to `sipm_315`: x-running fibers alternate between `+x` and `-x` as z changes.
- Fiber ends: external coated fiber stubs are present on both ends.
- Readout ends: use `geometry/fiber_kuraray_stub.gdml`, the coated stub with an open readout face.
- Non-readout ends: use `geometry/fiber_kuraray_stub_capped.gdml`, the coated stub with a mirrored outer end cap.
- Foil holes: positive and negative side faces are perforated for the stub penetrations.
- Purpose: isolates the effect of alternating the SiPM readout pattern while keeping the original stub optics.

## `geom-stubs-double-ended`

- File: `geometry/final_stubs_double_ended_sipms.gdml`
- Readout: every fiber is read out on both ends.
- `sipm_100` to `sipm_115`: z-running fibers read out on `+z`.
- `sipm_200` to `sipm_215`: z-running fibers read out on `-z`.
- `sipm_300` to `sipm_315`: x-running fibers read out on `+x`.
- `sipm_400` to `sipm_415`: x-running fibers read out on `-x`.
- Fiber ends: external coated fiber stubs are present on both ends.
- Readout ends: all external stubs use `geometry/fiber_kuraray_stub.gdml`, the coated stub with an open readout face.
- Foil holes: positive and negative side faces are perforated for the stub/readout penetrations.
- Purpose: tests whether collecting light from both fiber ends improves reconstruction enough to justify doubling the readout channel count.

## `geom-nostubs-pos`

- File: `geometry/final_no_stubs_pos_sipms.gdml`
- Readout: all SiPMs on positive sides only, matching `geometry/final.gdml`.
- `sipm_100` to `sipm_115`: z-running fibers read out on `+z`.
- `sipm_300` to `sipm_315`: x-running fibers read out on `+x`.
- Fiber ends: no external stubs; SiPMs couple directly to embedded fiber ends through grease.
- Foil holes: only positive readout side faces are perforated; negative side faces are closed foil.
- Purpose: isolates the effect of removing fiber stubs while keeping the original positive-side readout pattern.
