# Stage Fridge 10M CRY Comparison

Date: 2026-07-24

This comparison uses the same CRY setup, same detector position, same `1100 x 2000 x 1100 mm` world, and the same `200 x 10 x 200 mm` muon clock at world `y=900 mm`.

The only intended geometry difference is:
- No-fridge run: aluminium compact-stage cans and MXC plate removed.
- Fridge run: aluminium compact-stage cans and MXC plate included.

Both runs use `macros/stage_fridge_cry_10M.mac`.

| Quantity | No Fridge | With Fridge |
|---|---:|---:|
| Generated CRY events | 10,000,000 | 10,000,000 |
| Lower SiPM optical-hit EventIDs | 1,587 | 1,429 |
| Upper SiPM optical-hit EventIDs | 1,696 | 1,473 |
| Raw double coincidences | 780 | 747 |
| Raw double coincidences per 1M CRY events | 78.0 ± 2.8 | 74.7 ± 2.7 |
| Direct primary clock-muon EventIDs | 408,991 | 411,531 |
| Direct primary clock-muon tracks | 409,224 | 411,769 |
| Clock direct `mu-` tracks | 197,111 | 197,646 |
| Clock direct `mu+` tracks | 212,113 | 214,123 |
| Raw double coincidences per direct clock-muon EventID | 0.00191 | 0.00182 |

PDE weighting uses `analysis/dilution_detector/pde_digitization/sipm_pde_digitized.csv`, column `pde_5v_percent`, with wavelength computed from each optical photon's `InitialEnergy`.

| PDE-Weighted Quantity | No Fridge | With Fridge |
|---|---:|---:|
| Lower SiPM expected detected photoelectrons | 409,706.17 | 447,895.87 |
| Upper SiPM expected detected photoelectrons | 411,406.55 | 459,847.35 |
| Double coincidences, `>=1` expected detected PE in both SiPMs | 141 | 152 |
| PDE-weighted DCs per 1M CRY events | 14.1 ± 1.2 | 15.2 ± 1.2 |
| PDE-weighted DCs per direct clock-muon EventID | 0.000345 | 0.000369 |
| Non-zero PDE-weighted DCs | 780 | 747 |
| SiPM photon wavelength range | 190.747-826.479 nm | 190.784-826.440 nm |
| SiPM photons below 305 nm | 54,848 / 2,898,066 (1.89%) | 58,631 / 3,201,387 (1.83%) |

Interpretation:

The raw double-coincidence counts are statistically compatible: `78.0 ± 2.8` per 1M without the fridge and `74.7 ± 2.7` per 1M with the fridge. The PDE-weighted counts are also statistically compatible: `14.1 ± 1.2` per 1M without the fridge and `15.2 ± 1.2` per 1M with the fridge.

This suggests the compact aluminium fridge/plate geometry is not causing a large change in the double-coincidence rate for the current CRY source, detector placement, and above-clock setup.

Note: both CRY time files contain `inf`, so these are normalized by generated CRY events and direct clock-muon EventIDs, not by simulated elapsed time.
