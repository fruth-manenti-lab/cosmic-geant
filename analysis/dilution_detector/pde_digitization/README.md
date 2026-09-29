# SiPM PDE Weighting

This update adds wavelength-dependent SiPM photon-detection efficiency (PDE) to
the dilution-detector coincidence analysis.

What changed:

- `sipm_pde_digitized.csv` stores the digitised PDE curves from the supplied
  plot for 5.0 V and 2.5 V overvoltage.
- `count_sipm_double_coincidences.py` can now weight each SiPM optical photon by
  interpolated `PDE(wavelength) / 100`.
- The photon wavelength is calculated from the hit ntuple `InitialEnergy`
  column, which is written in keV:

```text
wavelength_nm = 1239.841984 / (InitialEnergy_keV * 1000)
```

Generated figures kept in Git:

- `analysis/dilution_detector/results/cry_10M_double_coincidence_pde5v_signal_threshold_scan_per_hour.png`
- `analysis/dilution_detector/results/cry_10M_wavelength_spectrum_with_pde.png`

For the 10M run, using the 5.0 V PDE curve, a 20 mV threshold corresponds to
13.33 PDE-weighted detected photons and gives 193 double-coincidence events, or
16.54 coincidences per hour for a 700 minute run.
