# Agent Notes

## Dilution Detector

- Work on the dilution detector belongs on branch `dilutiondetector`.
- The dilution detector geometry is `geometry/dilutiondetector.gdml`.
- Materials for this geometry should remain GDML-defined. Do not add C++ material-property hooks for the polystyrene scintillator unless explicitly requested later.
- The scintillator material is named `G4_POLYSTYRENE` in GDML and carries the previous scintillator optical/scintillation property tables directly in the material definition.
- The two scintillators are stacked along `y`, with centers 25 mm apart. The long scintillator axis is `z`, and the SiPMs face the `+z` square ends.
- The muon clock is a vacuum sensitive detector volume below the scintillators for downward-going muon tests. The shared sensitive detector records zero-energy steps because the zero-energy return in `SensitiveDetector::ProcessHits` is commented out.
- `SensitiveDetector::ProcessHits` intentionally kills each track after inserting the hit. This makes SiPM photon counts one hit per detected photon and stops downward muons after the below-detector muon clock records them.
- The dilution detector world is a 2 m vacuum cube so the CRY `subboxLength 1` footprint can fit above the detector with margin.
- `geometry/dilutiondetector.gdml` validates against `geometry/schema/gdml.xsd`; keep new GDML files schema-clean when practical.
- Do not attach a `dielectric_metal` detecting skin surface to the dilution SiPMs when using the shared sensitive detector for photon counts. A direct optical-photon test showed the skin absorbs the photon at the boundary before it takes a step inside `sipm`; without the skin, photons can enter the SiPM volume and be recorded.
- Count dilution-detector SiPM double coincidences with `analysis/dilution_detector/count_sipm_double_coincidences.py`. A double coincidence is one `EventID` where SiPM copy `0` and copy `1` both have a non-zero optical-photon count.

## CRY

- `cry_v1.7/` is intentionally ignored by Git. If it is missing, extract it from `cry_v1.7.tar.gz` and build the CRY library locally before configuring the Geant4 executable.
- CRY was confirmed to load `setup.file` and produce muons with the local `cry_v1.7/test/testMain` executable.
- The no-muon/geantino symptom came from `PrimaryGeneratorAction.cc`: `generator->genEvent(vect)` was running, but the CRY particle definition, energy, position, and direction setters on `G4ParticleGun` were commented out. Re-enable those setters when using CRY macros without `/gun/...` overrides.

## Local Build Notes

- CMake requires a discoverable Geant4 installation. Locally, source `/Users/matildalawton/geant4/geant4-install/bin/geant4.sh` before configuring/building.
