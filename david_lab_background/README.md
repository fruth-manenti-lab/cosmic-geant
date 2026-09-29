# David Lab Background Spectrum

This folder contains the uploaded RadiaCode XML spectrum:

```text
Spectrum 21-07-2026.xml
```

Decode the XML and regenerate the calibrated plot:

```sh
python3 david_lab_background/plot_spectrum.py
```

Outputs:

```text
david_lab_background/decoded_spectrum.csv
david_lab_background/spectrum_21-07-2026.png
```

## Simulation Use

This measured spectrum can be used as an empirical gamma background source for
`geometry/dilutiondetector.gdml`.

Generate the GPS spectrum table:

```sh
python3 david_lab_background/make_gps_spectrum.py
```

Build and run the background-only GPS mode:

```sh
source /Users/matildalawton/geant4/geant4-install/bin/geant4.sh
cmake -S . -B build_background -DADD_BACKGROUND_GPS=ON
cmake --build build_background -j4
cd build_background
./sim ../geometry/dilutiondetector.gdml ../macros/dilutiondetector_background_gps.mac
```

The macro fires `gamma` particles from a 50 cm radius spherical surface and
focuses them toward the detector centre. This is an efficient detector-response
test, not yet an absolute environmental flux model. The measured RadiaCode
spectrum is a detector response, not a direct ambient gamma fluence, so absolute
source normalization should be checked against observed detector rates.

The GPS spectrum file intentionally contains only numeric `energy_MeV weight`
rows. A comment/header row caused a segmentation fault in the GPS histogram
reader during testing.

Smoke test on 2026-07-22:

```text
10,000 generated gamma events
12,365 sensitive-detector rows
7,050 events with at least one sensitive-detector hit
muon_clock_phys: 7,791 rows
sipm_lower_phys: 2,145 rows
sipm_upper_phys: 2,429 rows
```

The shared sensitive detector currently kills tracks after recording a hit.
That behaviour is useful for one-count-per-photon SiPM counting, but it also
means a background gamma/electron that reaches the muon clock first will not
continue to the rest of the geometry.

The final decoded spectrum channel has a relatively large high-energy count and
may be an overflow-like bin from the instrument. The default GPS table keeps it
so the simulation follows the uploaded spectrum exactly. Use
`--drop-last-channel` only for an explicit sensitivity check.

Alternative future model:

```text
Explicit environmental radioactivity model:
lab/fridge/concrete/shield materials + U/Th/K activities + Geant4 decay/gamma transport
```

That approach is more physical if activities and material locations are known,
but it is slower to set up than the measured-spectrum GPS model.
