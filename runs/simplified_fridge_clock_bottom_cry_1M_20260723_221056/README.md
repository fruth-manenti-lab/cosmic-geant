# Simplified Fridge CRY 1M, Clock Below Fridge

Run date: 2026-07-23

Command:

```sh
cd build_simplified_fridge_cry_1m_clock_bottom
source /Users/matildalawton/geant4/geant4-install/bin/geant4.sh
./sim ../geometry/dilutiondetector_simplified_fridge.gdml ../macros/dilutiondetector_simplified_fridge_cry_1M.mac
```

Important setup:

- Geometry: `geometry/dilutiondetector_simplified_fridge.gdml`
- Macro: `macros/dilutiondetector_simplified_fridge_cry_1M.mac`
- CRY setup: muons only, `subboxLength 1`, 1 to 100 particles per event
- Muon clock: centered at `y=-900 mm`, below the fridge

Output:

- Hit CSVs: `output/MUON-run0_nt_hits_t*.csv`
- CRY simulated-time file: `MUON-run0-time.csv`

Counts:

- Total sensitive-detector rows: 93,752
- Lower SiPM optical-photon EventIDs: 35
- Upper SiPM optical-photon EventIDs: 38
- Double-coincidence EventIDs: 26
- Lower SiPM optical-photon rows: 44,450
- Upper SiPM optical-photon rows: 44,497
- Direct muon-clock EventIDs: 1,614
- Direct muon-clock tracks: 1,614
- Direct muon-clock EventIDs by particle: `mu-` 780, `mu+` 834
- Direct muon-clock tracks by particle: `mu-` 780, `mu+` 834
- Any-particle muon-clock EventIDs, including secondaries/optical photons: 1,958

Caveat:

- `MUON-run0-time.csv` is malformed for this 1M multi-threaded run (`inf` followed by another fragment), so do not use it for rate scaling until the CRY time output is investigated.
