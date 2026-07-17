# Dilution Detector SiPM Coincidence Analysis

This workflow counts double coincidences in the two dilution-detector SiPMs.

A human-readable development report for the current 10M-run plots is available
at `analysis/dilution_detector/plot_development_report.md`.

A double coincidence is one `EventID` where both SiPM copy numbers have a
number of detected optical photons greater than or equal to the selected
threshold. The default threshold is `1`, which means non-zero photon counts. For
the current dilution detector, copy `0` is the lower SiPM and copy `1` is the
upper SiPM.

Run on a completed CRY run directory:

```sh
python3 analysis/dilution_detector/count_sipm_double_coincidences.py \
  runs/cry_10M_live_20260717_152927 \
  --output analysis/dilution_detector/results/cry_10M_sipm_counts_by_event.csv \
  --double-events-output analysis/dilution_detector/results/cry_10M_double_events.csv
```

The script streams the Geant4 hit ntuple CSV files and only keeps per-event SiPM
counts in memory, so it can handle large multi-file runs. By default it counts
rows, which matches the current `SensitiveDetector` behavior where each photon
is killed after its first sensitive-detector hit. Add `--unique-tracks` if you
want to guard against multiple rows from the same optical photon track.

Apply an 80-photon cut to each SiPM:

```sh
python3 analysis/dilution_detector/count_sipm_double_coincidences.py \
  runs/cry_10M_live_20260717_152927 \
  --min-photons-per-sipm 80 \
  --output analysis/dilution_detector/results/cry_10M_sipm_counts_by_event_cut80.csv \
  --double-events-output analysis/dilution_detector/results/cry_10M_double_events_cut80.csv
```

If the threshold is 80 detected photons after a 40% SiPM efficiency, use the
efficiency-scaled mode. This applies an effective incident/recorded-photon cut
of `ceil(80 / 0.40) = 200` photons in each SiPM:

```sh
python3 analysis/dilution_detector/count_sipm_double_coincidences.py \
  runs/cry_10M_live_20260717_152927 \
  --sipm-efficiency 0.40 \
  --min-detected-photons-per-sipm 80 \
  --output analysis/dilution_detector/results/cry_10M_sipm_counts_by_event_eff40_cut80det.csv \
  --double-events-output analysis/dilution_detector/results/cry_10M_double_events_eff40_cut80det.csv
```

Plot double coincidences versus photon threshold in 10-photon steps:

```sh
python3 analysis/dilution_detector/plot_double_coincidence_threshold_scan.py \
  analysis/dilution_detector/results/cry_10M_sipm_counts_by_event.csv \
  --step 10 \
  --mark-threshold 80 \
  --mark-threshold 200
```

Plot the final signal-threshold curve with a 40% SiPM efficiency and 1.5 mV per
detected photon:

```sh
python3 analysis/dilution_detector/plot_double_coincidence_threshold_scan.py \
  analysis/dilution_detector/results/cry_10M_sipm_counts_by_event.csv \
  --step 10 \
  --duration-minutes 700 \
  --x-efficiency 0.40 \
  --mv-per-detected-photon 1.5 \
  --output-csv analysis/dilution_detector/results/cry_10M_double_coincidence_signal_threshold_scan_per_hour.csv \
  --output-plot analysis/dilution_detector/results/cry_10M_double_coincidence_signal_threshold_scan_per_hour.png
```
