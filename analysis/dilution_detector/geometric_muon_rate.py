#!/usr/bin/env python3
"""Straight-line muon acceptance for the aligned dilution-detector blocks.

Intensity is per area NORMAL to the ray: I(theta) = I0 cos(theta)**n.
--flux is the angle-integrated flux through a HORIZONTAL plane, in /cm²/min.
An optional linear amplitude-to-path calibration models a threshold in BOTH
blocks. No transport, photon fluctuations, or shielding model is included.
"""

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def read_geometry(path):
    """Read this detector's equal, aligned boxes in its local vertical-y frame."""
    root = ET.parse(path).getroot()
    box = root.find("./solids/box[@name='scintillator_solid']")
    if box is None or box.get('lunit') != 'mm':
        raise ValueError('Expected scintillator_solid box with literal mm dimensions')
    a, h, b = (float(box.get(k)) / 10 for k in ('x', 'y', 'z'))
    placements = [root.find(f".//physvol[@name='scintillator_{s}_phys']")
                  for s in ('lower', 'upper')]
    centers = []
    for p in placements:
        if p is None or p.find('volumeref').get('ref') != 'scintillator':
            raise ValueError('Expected two placements of the scintillator volume')
        if p.find('rotation') is not None or p.find('rotationref') is not None:
            raise ValueError('Rotated scintillators are not supported')
        pos = p.find('position')
        if pos is None or pos.get('unit') != 'mm':
            raise ValueError('Expected literal mm positions')
        centers.append([float(pos.get(k, '0')) / 10 for k in ('x', 'y', 'z')])
    if centers[0][0] != centers[1][0] or centers[0][2] != centers[1][2]:
        raise ValueError('This integration requires vertically aligned blocks')
    d = abs(centers[1][1] - centers[0][1])
    if min(a, h, b) <= 0 or d <= h:
        raise ValueError('Expected positive dimensions and a positive gap')
    return a, h, b, d


def coincidence_area(a, b, gap, exponent=2.0, order=64,
                     minimum_path_cm=0.0, thickness_cm=None):
    """Flux-weighted effective area in cm², using Gauss-Legendre quadrature.

    Slopes u=tan(theta)cos(phi), v=tan(theta)sin(phi).
    A_overlap=(a-gap*abs(u))_+ (b-gap*abs(v))_+.
    cos(theta)**(n+1) dOmega = (1+u²+v²)**(-(n+4)/2) du dv.
    Integrate one quadrant and multiply by four.

    For a minimum chord L in each block, require points L*cos(theta) deeper
    than each facing surface. Their separation is gap+2*L*cos(theta).
    The required depth must not exceed the block thickness.
    """
    if minimum_path_cm < 0 or not math.isfinite(minimum_path_cm):
        raise ValueError('Minimum path must be finite and nonnegative')
    if minimum_path_cm > 0 and (thickness_cm is None or thickness_cm <= 0):
        raise ValueError('A positive thickness is required for a path cut')
    nodes, weights = np.polynomial.legendre.leggauss(order)
    u = (nodes[:, None] + 1) * a / (2 * gap)
    v = (nodes[None, :] + 1) * b / (2 * gap)
    depth = minimum_path_cm / np.sqrt(1 + u*u + v*v)
    separation = gap + 2 * depth
    integrand = (np.maximum(0, a - separation * u) * np.maximum(0, b - separation * v)
                 / (1 + u*u + v*v)**((exponent + 4) / 2))
    if minimum_path_cm > 0:
        integrand = np.where(depth <= thickness_cm, integrand, 0)
    integral = a*b / gap**2 * np.sum(weights[:, None] * weights[None, :] * integrand)
    return float((exponent + 2) / (2 * math.pi) * integral)


def single_area(a, h, b, exponent):
    # Projected box footprint on a horizontal plane: ab+h*b*|u|+h*a*|v|.
    mean_abs_slope = math.exp(math.lgamma((exponent + 1) / 2)
                             - math.lgamma((exponent + 2) / 2)) / math.sqrt(math.pi)
    return a*b + h*(a+b)*mean_abs_slope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', type=Path,
                        default=ROOT / 'geometry/dilutiondetector_simplified_fridge.gdml')
    parser.add_argument('--flux', type=float, default=1.0,
                        help='Integrated horizontal-plane muon flux [/cm²/min], default 1')
    parser.add_argument('--exponent', type=float, default=2.0,
                        help='Exponent n of normal-area intensity I0*cos(theta)^n')
    parser.add_argument('--order', type=int, default=64)
    parser.add_argument('--threshold-mv', type=float,
                        help='Same amplitude threshold in each channel; requires calibration')
    parser.add_argument('--reference-amplitude-mv', type=float,
                        help='Amplitude corresponding to --reference-path-mm')
    parser.add_argument('--reference-path-mm', type=float,
                        help='Calibrated path length, NOT automatically inferred from mean amplitude')
    args = parser.parse_args()
    if not math.isfinite(args.flux) or args.flux < 0:
        parser.error('--flux must be finite and nonnegative')
    if not math.isfinite(args.exponent) or args.exponent < 0:
        parser.error('--exponent must be finite and nonnegative')
    if args.order < 4:
        parser.error('--order must be at least 4')
    calibration = (args.threshold_mv, args.reference_amplitude_mv, args.reference_path_mm)
    if any(value is not None for value in calibration):
        if any(value is None for value in calibration):
            parser.error('Supply --threshold-mv, --reference-amplitude-mv and --reference-path-mm together')
        if (not all(math.isfinite(value) for value in calibration)
                or args.threshold_mv < 0 or min(calibration[1:]) <= 0):
            parser.error('Threshold must be nonnegative and reference values positive; all must be finite')
    a, h, b, d = read_geometry(args.geometry)
    thick = coincidence_area(a, b, d-h, args.exponent, args.order)
    thin = coincidence_area(a, b, d, args.exponent, args.order)
    single = single_area(a, h, b, args.exponent)
    refined = coincidence_area(a, b, d-h, args.exponent, 2*args.order)
    print(f'Geometry: {args.geometry}')
    print(f'Local vertical axis: y; assumes detector frame is upright in world')
    print(f'Each block (x,y,z): {10*a:g} x {10*h:g} x {10*b:g} mm')
    print(f'Centre separation: {10*d:g} mm; facing-surface gap: {10*(d-h):g} mm')
    print(f'Horizontal flux: {args.flux:g} /cm²/min; normal-area intensity exponent: {args.exponent:g}')
    print(f'I0 = {args.flux*(args.exponent+2)/(2*math.pi):.6g} /cm²/min/sr')
    print('\nSelection                               Effective cm²      Muons/hour')
    for name, area in [('One horizontal scintillator face', a*b),
                       ('One full scintillator (including sides)', single),
                       ('Both centre planes (thin approximation)', thin),
                       ('Both full scintillators', thick),
                       ('Either full scintillator (unique muons)', 2*single-thick)]:
        print(f'{name:40s} {area:12.6f} {60*args.flux*area:15.6f}')
    print(f'\nCoincidence fraction of one-block crossings: {thick/single:.4%}')
    print(f'Quadrature change ({args.order} -> {2*args.order}): {abs(refined-thick):.3g} cm²')
    print('Rates assume perfect detection and no attenuation/scattering in the fridge or building.')
    if args.threshold_mv is not None:
        path = args.reference_path_mm * args.threshold_mv / args.reference_amplitude_mv / 10
        # Clipping at the threshold boundary needs more nodes than the uncut integral.
        cut_order = max(args.order, 512)
        cut = coincidence_area(a, b, d-h, args.exponent, cut_order, path, h)
        cut_refined = coincidence_area(a, b, d-h, args.exponent, 2*cut_order, path, h)
        print(f'\nLinear calibration: {args.reference_amplitude_mv:g} mV for {args.reference_path_mm:g} mm')
        print(f'Threshold in EACH channel: {args.threshold_mv:g} mV -> minimum path {10*path:.6f} mm')
        print(f'Coincidences after path cut: {60*args.flux*cut_refined:.6f} /hour')
        print(f'Reduction relative to geometric coincidences: {100*(1-cut_refined/thick):.4f}%')
        print(f'Cut quadrature change ({cut_order} -> {2*cut_order}): {abs(cut_refined-cut):.3g} cm²')
        print('This is a deterministic path cut; photon/energy-loss fluctuations and channel differences are omitted.')


if __name__ == '__main__':
    main()
