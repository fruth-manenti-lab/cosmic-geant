# Geometric muon rate for the fridge detector

For rendered equations and executable numerical integrals for every rate,
open [the Jupyter notebook](geometric_muon_rate.ipynb). It includes both angular
quadrature and a direct position-and-angle integral using 3D ray–box chords.

Run from the repository root (Python 3 and NumPy):

```sh
python3 analysis/dilution_detector/geometric_muon_rate.py
python3 analysis/dilution_detector/geometric_muon_rate.py --flux 1.0 --exponent 2
```

The script reads the scintillator dimensions and local placements from
`geometry/dilutiondetector_simplified_fridge.gdml`. Use `--geometry` to select
the detector-only or stage geometry. It assumes the detector's local y axis
is vertical, as in these geometries; it does not interpret arbitrary mother
rotations or model fridge material transport.

## Inputs and normalization

Two aligned polystyrene blocks each have dimensions (x,y,z) = (8,8,14) mm,
with centres separated vertically by 25 mm. Their facing surfaces are 17 mm
apart. In centimetres, let a=0.8, b=1.4, thickness h=0.8 and gap g=1.7.

The illustrative default is the approximate sea-level horizontal flux
F = 1 muon cm^-2 min^-1, summed over muon charges, and an azimuthally uniform
normal-area intensity I(theta) = I0 cos^n(theta), with n=2.
The [PDG cosmic-ray review](https://pdgweb.lbl.gov/2022/reviews/rpp2022-rev-cosmic-rays.pdf)
describes this approximate flux and angular law. These are reference assumptions,
not a measurement inside this lab. The flux and angular shape depend on the
energy range, site and overburden.

Here intensity is per unit area **perpendicular to the ray**, per unit solid
angle. Flux F is integrated over all downward directions through a horizontal
plane. Thus

    F = integral I(theta) cos(theta) dOmega = 2*pi*I0/(n+2),
    I0 = F*(n+2)/(2*pi).

For the defaults I0=0.636620 cm^-2 min^-1 sr^-1. Do not separately impose another
vertical intensity while retaining F=1: these two normalizations are linked.
If a supplied cos^n law is already differential flux per horizontal area,
its exponent is n+1 in this convention. A zenith-angle histogram also includes
the sin(theta) solid-angle factor.

## Integration

For a downward trajectory, let u=tan(theta)cos(phi) and v=tan(theta)sin(phi)
be its horizontal slopes. The overlap area of the two facing rectangles is

    A(u,v) = max(0, a-g*abs(u)) * max(0, b-g*abs(v)).

For these aligned identical convex boxes, a straight line crossing both blocks
must cross their facing surfaces: once it leaves the shared x/z footprint
through a side, it cannot return. Conversely a line through both facing
surfaces crosses both blocks. This makes the facing-surface overlap exact for
any nonzero path length, including side entry/exit; grazing trajectories have
zero measure. A finite energy-deposit threshold can reduce this acceptance.

The coincidence rate is

    R_both = integral I(theta)*cos(theta)*A(theta,phi) dOmega
           = F * A_eff,

    A_eff = (n+2)/(2*pi) * integral integral
            A(u,v) / (1+u*u+v*v)^((n+4)/2) du dv.

The slope bounds are |u|<a/g, |v|<b/g. The script integrates one quadrant by
Gauss-Legendre quadrature and multiplies by four. A_eff has units of cm²;
multiply by F and by 60 for counts/hour. Using the centre separation g=2.5 cm
instead gives the thin-centre-plane approximation, which misses valid paths
through the finite blocks.

For one block, the projected footprint on a horizontal plane is
ab + h*b*|u| + h*a*|v|. Under the normalized angular law,

    mean(|u|) = mean(|v|) = Gamma((n+1)/2)/(sqrt(pi)*Gamma((n+2)/2)).

At n=2 this is 1/2, giving a single-block effective area of 2.0 cm².

## Reference result

For F=1 cm^-2 min^-1 and n=2:

| Selection | Effective area (cm²) | Muons/hour |
| --- | ---: | ---: |
| One horizontal 8 x 14 mm face | 1.120000 | 67.20 |
| One full scintillator, including side crossings | 2.000000 | 120.00 |
| Both centre planes, thin approximation | 0.106577 | 6.39 |
| Both full scintillators | 0.195439 | 11.73 |
| Either scintillator, unique muons | 3.804561 | 228.27 |

The coincidence fraction is 9.77% of the crossings of either individual block.
The mean interval between coincidences is about 5.12 minutes. Every rate scales
linearly with F at fixed n; changing n requires repeating the integration.

Numerical validation: 64- and 128-point quadratures agree to below 1e-12 cm².
An independent 1,000,000-ray box-intersection Monte Carlo with seed 20260924
gave 0.195396 +/- 0.000425 cm² (one standard error), consistent with 0.195439.
Axis-swap symmetry, quadratic length scaling, and decreasing acceptance with
increasing gap were also checked.

These are geometrical muon crossing rates, not predicted SiPM trigger rates.
The active collection geometry is the plastic volume; the 6 x 6 mm SiPM area
does not set the muon acceptance. Optical collection, photon statistics and
thresholds determine detection efficiency. With a constant joint efficiency
epsilon_both and live fraction L, R_observed=11.7264*(F/1)*epsilon_both*L per
hour for n=2. Only if conditional efficiencies can be treated as independent
and constant is epsilon_both=epsilon_upper*epsilon_lower. SiPM photon PDE is
not the same as per-muon trigger efficiency.

This estimate neglects attenuation, scattering and secondary production in
the building, fridge cans and plate. Their dimensions do not reduce a pure
straight-line acceptance by themselves. Use a flux measured at the detector
or a separate transport calculation to account for these effects.

## Signal threshold as a minimum path length

For a linear calibration A = A_ref * L/L_ref, the threshold in each channel
requires L >= L_min = L_ref * A_threshold/A_ref. The CLI requires all three
calibration inputs explicitly; a measured mean amplitude alone does not
determine L_ref. The mean path depends on the sample selection and angular
distribution, and an already thresholded sample has selection bias.

As a conditional example, **if 20.5 mV corresponds to an 8 mm path**, run:

```sh
python3 analysis/dilution_detector/geometric_muon_rate.py \
  --threshold-mv 1 --reference-amplitude-mv 20.5 --reference-path-mm 8
```

This gives L_min = 0.390244 mm in each scintillator. At the reference flux
and angular law, the coincidence rate falls from 11.7264 to 11.0417/hour,
a reduction of 5.84%. This is conditional on the 8 mm calibration, the same
calibration and threshold in both channels, and a deterministic linear response.
It is not a calibrated prediction based solely on the stated mean amplitude.

The integration retains the full 3D chord requirement. For direction theta,
accumulating L_min inside each block requires a vertical depth
q = L_min*cos(theta). A coincident track must connect a point q inside the
upper block to a point q inside the lower block. For the aligned equal boxes,
the allowed area is therefore

    A_cut(u,v) = max(0, a-(g+2*q)*abs(u)) * max(0, b-(g+2*q)*abs(v)),
    q = L_min/sqrt(1+u*u+v*v).

Set the area to zero when q exceeds the block thickness h. Integrate this area
with the same angular weight and flux normalization as above. At L_min=0 this
recovers the uncut result. The removed fraction is calculated from the chord
distribution; it is not simply A_threshold/A_ref.

Validation for the 0.390244 mm cut: 512- and 1024-point quadratures differ by
6.16e-9 cm². An independent million-ray 3D box-chord calculation gives
0.184050 +/- 0.000415 cm², versus 0.184028 cm² from quadrature. Further chord
cuts at 4, 8, 10 and 20 mm were checked, including cuts that reject all events.

The model omits energy-loss and photon-count fluctuations, position-dependent
light collection, electronics noise and differences between channels. Those
effects replace the sharp path cut with a probability of passing the signal
threshold for each trajectory.
