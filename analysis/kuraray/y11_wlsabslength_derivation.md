# Deriving the Geant4 `WLSABSLENGTH` Curve for Kuraray Y-11 Fiber

The wavelength-dependent WLS absorption length was derived from a digitized Kuraray Y-11 absorption spectrum by treating the digitized absorption curve as a relative spectral shape and normalising it using the absolute transmission measurement reported by Herzkamp. This curve is intended for the Geant4 `WLSABSLENGTH` material property, i.e. absorption of blue scintillation photons by the WLS dye followed by re-emission at longer wavelength. It is distinct from the effective long-distance fiber attenuation length used for transported photons, which is normally implemented separately as `ABSLENGTH`.

## Model

The dye absorption was modelled using Beer--Lambert attenuation:

```math
I(\lambda)=I_0(\lambda)\exp[-k(\lambda)\rho_{\rm dye}d],
```

where:

- `I(λ)/I₀(λ)` is the measured transmission at wavelength `λ`;
- `k(λ)` is the dye absorption coefficient in `ppm⁻¹ mm⁻¹`;
- `ρ_dye` is the dye concentration in `ppm`;
- `d` is the optical path length through the sample in `mm`.

The WLS absorption length for a fiber with dye concentration `ρ_fiber` is then:

```math
L_{\rm WLS}(\lambda)=\frac{1}{k(\lambda)\rho_{\rm fiber}}.
```

## Normalisation point for Y-11

For Kuraray Y-11, Herzkamp reports the following absolute transmission measurement at the absorption peak:

```math
\rho_{\rm dye}=18.2\,\mathrm{ppm},
\qquad
d=10\,\mathrm{mm},
\qquad
I/I_0=0.0689,
\qquad
\lambda_p=430\,\mathrm{nm}.
```

The peak absorption coefficient is therefore:

```math
k(\lambda_p)
=
-\frac{\ln(I/I_0)}{\rho_{\rm dye}d}
=
-\frac{\ln(0.0689)}{18.2\times 10}
\approx
0.0147\,\mathrm{ppm^{-1}\,mm^{-1}}.
```

## Applying the digitized Kuraray spectrum

Let the digitized relative Kuraray absorption curve be `A_rel(λ)`. First normalise it to its peak value:

```math
A_{\rm norm}(\lambda)
=
\frac{A_{\rm rel}(\lambda)}{A_{\rm rel}(\lambda_p)}.
```

Then scale the absorption coefficient as:

```math
k(\lambda)=k(\lambda_p)A_{\rm norm}(\lambda).
```

Combining this with the expression for the WLS absorption length gives:

```math
L_{\rm WLS}(\lambda)
=
\frac{1}{0.0147\,\rho_{\rm fiber}\,A_{\rm norm}(\lambda)}.
```

Here, `L_WLS(λ)` is in `mm` when `ρ_fiber` is given in `ppm`.

For example, for a Y-11 fiber with `ρ_fiber = 200 ppm`, the peak WLS absorption length is:

```math
L_{\rm WLS}(430\,\mathrm{nm})
=
\frac{1}{0.0147\times 200}
\approx
0.34\,\mathrm{mm}.
```

## Geant4 use

The resulting wavelength-dependent curve should be used as:

```cpp
mptFiber->AddProperty("WLSABSLENGTH", photonEnergy, wlsAbsLength);
```

where `photonEnergy` is the photon energy corresponding to each wavelength,

```math
E\,[\mathrm{eV}] = \frac{1240}{\lambda\,[\mathrm{nm}]}.
```

Geant4 material-property vectors should be ordered by increasing photon energy, so a table digitized in increasing wavelength usually needs to be reversed before being passed to Geant4.

## Distinction from fiber attenuation length

The `WLSABSLENGTH` curve above describes absorption of incident scintillation photons by the WLS dye. It should not be confused with the effective attenuation length of already wavelength-shifted photons propagating along the fiber.

For the latter, the NOvA Technical Design Report gives wavelength-dependent attenuation lengths derived from fits to light exiting fibers illuminated at distances between 4 and 9 m. Those values are suitable as an effective Geant4 `ABSLENGTH` curve if one wants to reproduce long-distance light loss in the fiber. The NOvA TDR reports attenuation lengths exceeding 18 m near 580 nm and a sharp drop to approximately 7 m near 610 nm, attributed to an absorption resonance in polystyrene-core fibers.

## References

[1] M. Herzkamp, *Simulation and Optimization of a Position Sensitive Scintillation Detector with Wavelength Shifting Fibers for Thermal Neutrons*, PhD thesis, RWTH Aachen University, 2016. See Section 4.3, especially the discussion around Figs. 4.14--4.15 and Table 4.4, where the Kuraray-provided Y-11 absorption/emission spectra are converted into an absolute dye absorption length using Beer--Lambert attenuation.

[2] Kuraray Co., Ltd., *Plastic Scintillating Fibers Catalog*. Current Kuraray product documentation for plastic scintillating and wavelength-converting fibers, including basic Y-11 spectral and attenuation data. The current public catalog gives representative product data but may not contain the full historical Y-11 absorption/emission plot used in older simulations.

[3] Kuraray Co., Ltd., *Kuraray's Scintillation Materials: Plastic Scintillating Fibers*. Older Kuraray datasheet/catalog copy, mirrored by experimental groups, containing absorption and emission spectra for WLS fibers including Y-7, Y-8, and Y-11.

[4] J. Cooper, R. Ray, and N. Grossman, *NOνA: NuMI Off-Axis νe Appearance Experiment Technical Design Report*, Fermilab/NOvA Collaboration, October 8, 2007. See Chapter 11, Section 11.4.1 and Fig. 11.5 for wavelength-dependent attenuation lengths of Kuraray WLS fibers; these are attenuation lengths for transported light and are separate from WLS dye absorption lengths.

[5] A. S. Wilhelm, G. Wendel, B. Collins, D. Cowen, and I. Jovanovic, “Evaluation of light collection from highly scattering media using wavelength-shifting fibers,” *Nuclear Instruments and Methods in Physics Research Section A*, vol. 1049, 168085, 2023. This paper uses separate Geant4 inputs for WLS absorption length, WLS emission spectrum, and Y-11 bulk/effective attenuation length.
