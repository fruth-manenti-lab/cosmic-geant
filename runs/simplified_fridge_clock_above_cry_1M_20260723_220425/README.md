# Simplified Fridge CRY 1M, Clock Above Fridge

Run date: 2026-07-23

Command:

```sh
cd build_simplified_fridge_cry_1m
source /Users/matildalawton/geant4/geant4-install/bin/geant4.sh
./sim ../geometry/dilutiondetector_simplified_fridge.gdml ../macros/dilutiondetector_simplified_fridge_cry_1M.mac
```

Important setup:

- Geometry: `geometry/dilutiondetector_simplified_fridge.gdml`
- Macro: `macros/dilutiondetector_simplified_fridge_cry_1M.mac`
- CRY setup: muons only, `subboxLength 1`, 1 to 100 particles per event
- Muon clock: centered at `y=900 mm`, above the fridge and below the CRY plane
- Sensitive-detector behavior: `mu+`/`mu-` tracks in `muon_clock_phys` are recorded but not killed, so they can continue into the fridge/detector.

Output:

- Hit CSVs: `output/MUON-run0_nt_hits_t*.csv`
- CRY simulated-time file: `MUON-run0-time.csv`

Counts:

- Total sensitive-detector rows: 125,161
- Lower SiPM optical-photon EventIDs: 35
- Upper SiPM optical-photon EventIDs: 40
- Double-coincidence EventIDs: 28
- Lower SiPM optical-photon rows: 42,107
- Upper SiPM optical-photon rows: 51,798
- Direct muon-clock EventIDs: 10,875
- Direct muon-clock tracks: 10,879
- Direct muon-clock EventIDs by particle: `mu-` 5,193, `mu+` 5,684
- Direct muon-clock tracks by particle: `mu-` 5,193, `mu+` 5,686
- Any-particle muon-clock EventIDs, including secondaries/optical photons: 11,262

Caveat:

- `MUON-run0-time.csv` contains `inf` for this 1M run, so do not use it for rate scaling until the CRY time output is investigated.
