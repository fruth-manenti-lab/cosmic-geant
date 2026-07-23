# Agent Notes

## Dilution Detector

- Work on the dilution detector belongs on branch `dilutiondetector`.
- The dilution detector geometry is `geometry/dilutiondetector.gdml`.
- The simplified dilution-fridge version is `geometry/dilutiondetector_fridge.gdml`; it keeps the detector inside an innermost vacuum hierarchy and uses an air world outside the fridge.
- `geometry/dilutiondetector_fridge_visual.gdml` is a visual-inspection copy of the earlier four-layer fridge geometry. It has been toggled between cutaway and full-cylinder forms during inspection; check the tube `deltaphi` values before using it for a specific visual question.
- `geometry/dilutiondetector_simplified_fridge.gdml` is the current simplified three-can geometry derived from the newer simplified STEP file. Prefer this file for the next fridge placement checks unless the user asks to return to the four-layer approximation.
- Materials for this geometry should remain GDML-defined. Do not add C++ material-property hooks for the polystyrene scintillator unless explicitly requested later.
- The scintillator material is named `G4_POLYSTYRENE` in GDML and carries the previous scintillator optical/scintillation property tables directly in the material definition.
- The two scintillators are stacked along `y`, with centers 25 mm apart. The long scintillator axis is `z`, and the SiPMs face the `+z` square ends.
- In the current simplified three-can fridge geometry, the muon clock is a vacuum sensitive detector block placed below the bottom of the fridge. In the detector-only geometry it remains below the scintillators for the earlier downward-going muon tests. The shared sensitive detector records zero-energy steps because the zero-energy return in `SensitiveDetector::ProcessHits` is commented out.
- `SensitiveDetector::ProcessHits` intentionally kills each track after inserting the hit, except for `mu+`/`mu-` steps in `muon_clock_phys`. This keeps SiPM photon counts one hit per detected photon while allowing above-fridge clock muons to continue into the fridge/detector.
- The dilution detector world is a 2 m vacuum cube so the CRY `subboxLength 1` footprint can fit above the detector with margin.
- `geometry/dilutiondetector.gdml` validates against `geometry/schema/gdml.xsd`; keep new GDML files schema-clean when practical.
- Do not attach a `dielectric_metal` detecting skin surface to the dilution SiPMs when using the shared sensitive detector for photon counts. A direct optical-photon test showed the skin absorbs the photon at the boundary before it takes a step inside `sipm`; without the skin, photons can enter the SiPM volume and be recorded.
- Count dilution-detector SiPM double coincidences with `analysis/dilution_detector/count_sipm_double_coincidences.py`. A double coincidence is one `EventID` where SiPM copy `0` and copy `1` both have a non-zero optical-photon count.

## Dilution Fridge Geometry

- CAD source for the simplified fridge pass was `/Users/matildalawton/Desktop/Fridgedetector/bf-crst015_asm.stp`. OpenCascade/FreeCAD Python bindings were not available locally, so dimensions were inferred from STEP product names plus extracted circle radii rather than a full BREP conversion.
- `geometry/dilutiondetector_fridge.gdml` currently models four transparent aluminium can/shield levels: outer vacuum can radius 250 mm, height 1641 mm; 50 K shield radius 202 mm, height 1390 mm; 4 K shield radius 166 mm, height 785 mm; still shield radius 152 mm, height 515 mm.
- The volume outside the fridge is `Air`; each nested can interior is `Vacuum`. Missing material data from the STEP pass was treated as aluminium, following the working assumption that unspecified can material is most likely aluminium.
- The requested fourth-down plate is included as volume `M00346-FLA-LD-MXC-AU_ASM`, simplified as a transparent aluminium disk with radius 147 mm and thickness 6 mm.
- The fridge can axis is rotated onto world `y`; the detector envelope is counter-rotated so the existing detector convention is preserved: scintillator stack along `y`, SiPMs on the `+z` scintillator faces, and the muon clock below the scintillators.
- Current detector placement in the fridge puts the detector envelope 103 mm radially from the MXC plate centre, leaving the scintillator package about 4 cm from the 147 mm plate edge. The detector envelope centre is at local fridge `z=-80.4 mm`; the retained MXC plate centre is at `z=-100 mm`, so the lower scintillator/wrap sits on the top side of that plate for visual/geometry purposes.
- The earlier four-layer fridge muon clock is a world-volume placement at `y=900 mm`, centered above the top of the fridge. It is intentionally outside the nested fridge vacuum volumes.
- Solved overlap issues in the first fridge pass: can side shells were shortened so they do not overlap end caps, the still and detector envelope were lifted clear of lower caps, the detector envelope was reduced to the detector package instead of a large 140 mm cube, and the ESR x/y wrap widths in the fridge GDML were trimmed to remove corner-strip overlaps while keeping face coverage.
- Reusable geometry check macro is `macros/dilutiondetector_fridge_check.mac`; it ran cleanly with no `GeomVol1002` overlap warnings after the fixes.
- For visual inspection of concentric cans, launch `build/sim ../geometry/dilutiondetector_fridge_visual.gdml` from the `build/` directory after sourcing Geant4.

## Simplified Three-Can Fridge

- CAD source for the current simplified three-can geometry is `/Users/matildalawton/Desktop/Fridgedetector/simplifieddilutionfridge.step`.
- The STEP file is in millimetres with the fridge cylinder axis along CAD `y`. GDML `tube` solids are therefore rotated onto world `y` with `rot_fridge_to_world`; the detector envelope is counter-rotated so the existing detector convention is preserved.
- `geometry/dilutiondetector_simplified_fridge.gdml` models three nested closed aluminium cans with vacuum interiors and an air world outside the outer can:
  - Outer VC can: radius 250 mm, height 1641 mm, wall/cap thickness 4.1 mm from the 250/245.9 mm radii.
  - 50 K shield can: radius 202 mm, height 1390 mm, wall/cap thickness 2 mm.
  - Still shield can: radius 152 mm, height 515 mm, wall/cap thickness 0.5 mm from the 152/151.5 mm radii.
- The MXC plate volume remains named `M00346-FLA-LD-MXC-AU_ASM` and is simplified as a full aluminium cylinder with radius 147 mm and thickness 8 mm, matching the extracted plate radius and point-cloud `y` range.
- The 4 K product family (`P02463-IF-LD-4K-785-3C_AF0_ASM`) was not placed as a can in the simplified three-can file because the user-requested simplified STEP was interpreted as plate plus three concentric cans, and that product is named as an interface assembly rather than a can/shield tube. Revisit this if visual inspection shows the intended three cans were outer VC, 50 K, and 4 K instead.
- The detector envelope is placed at radius 103 mm on the MXC plate, so the active scintillator package is roughly 4 cm from the 147 mm plate edge. The lower detector envelope face is flush with the plate top.
- The simplified fridge was flipped after visual inspection showed the plate/detector end was upside down. Current local placements are `shield50_vacuum_pos z=120 mm`, `still_vacuum_pos z=430 mm`, `mxc_plate_pos z=252.75 mm` inside the still vacuum, and `detector_envelope_pos z=232.15 mm` inside the still vacuum.
- CRY particles are generated from the CRY `z=0` plane and mapped into Geant4 with world `y = CRY z + 95 cm`. With the simplified fridge spanning roughly `y=-820.5 mm` to `y=+820.5 mm`, this places the CRY sky at about `y=+950 mm`, above all cans while remaining inside the older 2 m detector-only world.
- The simplified-fridge muon clock is currently centered at `y=-900 mm`, below the outer can bottom at about `y=-820.5 mm`. For the above-fridge comparison run it was temporarily centered at `y=900 mm`, above the outer can top and below the CRY source plane at about `y=950 mm`.
- Can and plate visual transparency is 0.80. The scintillator and SiPM transparencies were reduced to 0.05 and 0.0 respectively so the detector remains visible through the cans.
- `xmllint --schema geometry/schema/gdml.xsd geometry/dilutiondetector_simplified_fridge.gdml` passed, and `build/sim geometry/dilutiondetector_simplified_fridge.gdml macros/dilutiondetector_fridge_check.mac` loaded the geometry with all overlap checks reporting OK.
- `geometry/dilutiondetector_simplified_fridge_filled_visual.gdml` is a visual-only copy where the three can shell solids have `rmin=0` so the can material appears as filled translucent cylinders in OpenGL. Do not use it for physics or overlap checks; it intentionally overlaps the nested vacuum/detector contents to make the can extents easy to see.
- First simplified-fridge CRY count check: `macros/dilutiondetector_simplified_fridge_cry_10k.mac` ran 10,000 events with `geometry/dilutiondetector_simplified_fridge.gdml`. Archived output is under `runs/simplified_fridge_cry_10k_20260723_2156/`. Result: 0 upper-SiPM events, 0 lower-SiPM events, 0 double coincidences, 11 direct primary muon clock crossings, and 13 muon-clock EventIDs if secondary/optical hits are included.
- After moving the simplified-fridge muon clock above the fridge, `macros/dilutiondetector_simplified_fridge_cry_1M.mac` ran 1,000,000 CRY events from `build_simplified_fridge_cry_1m`. Archived output is under `runs/simplified_fridge_clock_above_cry_1M_20260723_220425/`. Result: 35 lower-SiPM optical-hit EventIDs, 40 upper-SiPM optical-hit EventIDs, 28 double-coincidence EventIDs, 10,875 direct muon-clock EventIDs, and 10,879 direct muon-clock tracks. The CRY simulated-time file for this run contains `inf`, so do not use it for rate scaling until investigated.
- After moving the simplified-fridge muon clock back below the fridge, the same 1,000,000-event CRY macro ran from `build_simplified_fridge_cry_1m_clock_bottom`. Archived output is under `runs/simplified_fridge_clock_bottom_cry_1M_20260723_221056/`. Result: 35 lower-SiPM optical-hit EventIDs, 38 upper-SiPM optical-hit EventIDs, 26 double-coincidence EventIDs, 1,614 direct muon-clock EventIDs/tracks, with 780 `mu-` and 834 `mu+` clock tracks. The CRY simulated-time file is malformed for this run (`inf` plus an extra fragment), so do not use it for rate scaling until investigated.

## CRY

- `cry_v1.7/` is intentionally ignored by Git. If it is missing, extract it from `cry_v1.7.tar.gz` and build the CRY library locally before configuring the Geant4 executable.
- CRY was confirmed to load `setup.file` and produce muons with the local `cry_v1.7/test/testMain` executable.
- The no-muon/geantino symptom came from `PrimaryGeneratorAction.cc`: `generator->genEvent(vect)` was running, but the CRY particle definition, energy, position, and direction setters on `G4ParticleGun` were commented out. Re-enable those setters when using CRY macros without `/gun/...` overrides.

## David Lab Background

- The measured RadiaCode background spectrum lives in `david_lab_background/Spectrum 21-07-2026.xml`.
- Treat the RadiaCode spectrum as a measured detector response, not a direct ambient gamma fluence. A GPS gamma source built from it is useful as an empirical first model, but the absolute normalization should be validated against the dilution-detector rates.
- Implemented first background step: `ADD_BACKGROUND_GPS` builds `PrimaryGeneratorAction` with `G4GeneralParticleSource`, `david_lab_background/make_gps_spectrum.py` converts the decoded spectrum to `gps_background_arb_spectrum.dat`, and `macros/dilutiondetector_background_gps.mac` fires gamma particles from a 50 cm spherical surface focused at the detector centre.
- `gps_background_arb_spectrum.dat` must contain only numeric `energy_MeV weight` rows. A comment/header row caused the GPS histogram reader to segfault during the first smoke test.
- Background smoke test on 2026-07-22 ran 10,000 gamma events and wrote 12,365 sensitive-detector rows across 7,050 events with hits: 7,791 `muon_clock_phys`, 2,145 `sipm_lower_phys`, and 2,429 `sipm_upper_phys`.
- Combined CRY plus measured gamma background mode is `ADD_CRY_BACKGROUND_GPS`, configured by `macros/dilutiondetector_cry_background.mac`. This mode adds `ADD_SOURCE_TAGGING`, writes a `SourceParticle` hit-ntuple column, and runs both CRY muons and one GPS gamma in each Geant4 event.
- `SourceParticle` is assigned to primary tracks (`mu-`, `mu+`, or `gamma`) and inherited by secondaries, so scintillation photons can be attributed to their initiating source in analysis.
- Combined 100k smoke run on 2026-07-22: `build_cry_background/output`, analysis in `analysis/dilution_detector/results/cry_background_100k_source_breakdown.*`. Raw SiPM optical-photon source breakdown: muon SiPM events 21 with 7 double coincidences; gamma SiPM events 1,153 with 11 double coincidences.
- The source-breakdown script supports `--pde-csv`/`--pde-column` for wavelength-dependent SiPM PDE weighting. For the combined 100k run with 5.0 V PDE and a `>=1` PDE-weighted detected-photon threshold in both SiPMs, both muon and gamma double coincidences were 0. With a non-zero weighted threshold, the event IDs match the raw 7 muon and 11 gamma coincidences.
- The shared sensitive detector still kills tracks after first sensitive-detector hit. This affects background studies if a gamma/electron reaches the muon clock before the scintillator/SiPMs.
- The final RadiaCode channel may be overflow-like; the default GPS conversion preserves it to match the uploaded measurement. Use `--drop-last-channel` only for a deliberate sensitivity check.
- More physical later option: model concrete/lab/fridge materials with U/Th/K activities and use Geant4 radioactive decay or explicit isotope gamma lines, then tune or validate against the measured RadiaCode spectrum.

## Local Build Notes

- CMake requires a discoverable Geant4 installation. Locally, source `/Users/matildalawton/geant4/geant4-install/bin/geant4.sh` before configuring/building.
