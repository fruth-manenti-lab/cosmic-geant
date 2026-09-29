#!/usr/bin/env python3
"""Plot upper/lower SiPM photon spectra with optional CRY and PDE overlays."""

from __future__ import annotations

import argparse
import csv
import itertools
import os
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MPLCONFIGDIR = SCRIPT_DIR / ".mplconfig"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPLCONFIGDIR / "cache"))

import matplotlib.pyplot as plt  # noqa: E402


DEFAULT_COLUMNS = [
    "EventID",
    "TrackID",
    "Particle",
    "EnergyDeposited",
    "XPosition",
    "YPosition",
    "ZPosition",
    "LocalTime",
    "Volume",
    "Copynumber",
    "InitialEnergy",
    "OriginVolume",
    "ParentID",
    "ProcessName",
    "StepID",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot optical-photon wavelength spectra detected in "
            "sipm_upper_phys and sipm_lower_phys."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Primary hit CSV files, directories, or run directories containing MUON-run*_nt_hits_t*.csv.",
    )
    parser.add_argument(
        "--comparison-input",
        action="append",
        default=[],
        help=(
            "Optional comparison hit CSV file, directory, or run directory. "
            "May be repeated; all comparison SiPM photons are combined."
        ),
    )
    parser.add_argument(
        "--comparison-label",
        default="CRY 10M, combined SiPMs",
        help="Legend label for the optional comparison spectrum.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "results" / "background_sipm_upper_lower_wavelength_spectra_with_cry_and_pde.png",
        help="Output image path.",
    )
    parser.add_argument(
        "--pde-csv",
        type=Path,
        default=SCRIPT_DIR / "pde_digitization" / "sipm_pde_digitized.csv",
        help="Digitised SiPM PDE CSV from the earlier plot digitisation.",
    )
    parser.add_argument("--bin-width-nm", type=float, default=2.0, help="Histogram bin width in nm.")
    parser.add_argument("--x-min", type=float, default=None, help="Optional minimum wavelength shown.")
    parser.add_argument("--x-max", type=float, default=None, help="Optional maximum wavelength shown.")
    parser.add_argument(
        "--normalise",
        action="store_true",
        help="Plot each spectrum as a unit-area density rather than raw counts.",
    )
    return parser.parse_args()


def find_hit_files(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_input in inputs:
        path = Path(raw_input).expanduser()
        matches = sorted(Path().glob(raw_input)) if any(ch in raw_input for ch in "*?[]") else []
        if matches:
            files.extend(match for match in matches if match.is_file())
            continue
        if path.is_file():
            files.append(path)
            continue
        if not path.is_dir():
            raise FileNotFoundError(f"Input does not exist: {raw_input}")

        candidates = [path / "work" / "output", path / "output", path]
        found: list[Path] = []
        for directory in candidates:
            if directory.is_dir():
                found.extend(sorted(directory.glob("MUON-run*_nt_hits_t*.csv")))
                found.extend(sorted(directory.glob("*_nt_hits_t*.csv")))
        if not found:
            found = sorted(path.rglob("MUON-run*_nt_hits_t*.csv"))
        files.extend(found)

    unique_files = sorted({file.resolve() for file in files})
    if not unique_files:
        raise FileNotFoundError("No hit ntuple CSV files found.")
    return unique_files


def iter_hit_rows(path: Path):
    columns: list[str] = []
    with path.open(newline="") as handle:
        for line in handle:
            if line.startswith("#column "):
                parts = line.strip().split(maxsplit=2)
                if len(parts) == 3:
                    columns.append(parts[2])
                continue
            if line.startswith("#") or not line.strip():
                continue

            reader = csv.reader(itertools.chain([line], handle))
            header = columns or DEFAULT_COLUMNS
            for fields in reader:
                if fields:
                    yield dict(zip(header, fields))
            return


def wavelength_nm(row: dict[str, str]) -> float:
    initial_energy_kev = float(row["InitialEnergy"])
    if initial_energy_kev <= 0:
        raise ValueError(f"Optical photon has non-positive InitialEnergy: {initial_energy_kev} keV")
    return 1239.841984 / (initial_energy_kev * 1000.0)


def collect_wavelengths(files: list[Path]) -> dict[str, list[float]]:
    spectra = {
        "Lower SiPM": [],
        "Upper SiPM": [],
    }
    for path in files:
        for row in iter_hit_rows(path):
            if row.get("Particle") != "opticalphoton":
                continue
            volume = row.get("Volume", "")
            if volume == "sipm_lower_phys":
                spectra["Lower SiPM"].append(wavelength_nm(row))
            elif volume == "sipm_upper_phys":
                spectra["Upper SiPM"].append(wavelength_nm(row))
    return spectra


def collect_combined_sipm_wavelengths(files: list[Path]) -> list[float]:
    wavelengths = []
    for path in files:
        for row in iter_hit_rows(path):
            if row.get("Particle") != "opticalphoton":
                continue
            if row.get("Volume") in {"sipm_lower_phys", "sipm_upper_phys"}:
                wavelengths.append(wavelength_nm(row))
    return wavelengths


def read_pde(path: Path) -> tuple[list[float], list[float], list[float]]:
    wavelengths = []
    pde_5v = []
    pde_2p5v = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            wavelengths.append(float(row["wavelength_nm"]))
            pde_5v.append(float(row["pde_5v_percent"]))
            pde_2p5v.append(float(row["pde_2p5v_percent"]))
    return wavelengths, pde_5v, pde_2p5v


def make_bins(values: list[float], width: float, x_min: float | None, x_max: float | None) -> list[float]:
    if width <= 0:
        raise ValueError("--bin-width-nm must be greater than zero")
    if not values:
        raise ValueError("No optical photons found in either SiPM.")

    lower = x_min if x_min is not None else width * int(min(values) // width)
    upper = x_max if x_max is not None else width * (int(max(values) // width) + 2)
    bins = []
    current = lower
    while current <= upper + width * 0.5:
        bins.append(current)
        current += width
    return bins


def plot_spectra(
    spectra: dict[str, list[float]],
    comparison_wavelengths: list[float],
    pde_wavelengths: list[float],
    pde_5v: list[float],
    pde_2p5v: list[float],
    args: argparse.Namespace,
) -> None:
    all_values = [value for values in spectra.values() for value in values] + comparison_wavelengths
    bins = make_bins(all_values, args.bin_width_nm, args.x_min, args.x_max)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    pde_ax = ax.twinx()
    colours = {
        "Lower SiPM": "#2f80ed",
        "Upper SiPM": "#d1495b",
    }

    for label, values in spectra.items():
        weights = None
        if args.normalise and values:
            weights = [1.0 / (len(values) * args.bin_width_nm)] * len(values)
        ax.hist(
            values,
            bins=bins,
            weights=weights,
            histtype="step",
            linewidth=2.2,
            color=colours[label],
            label=f"{label} (n = {len(values)})",
        )

    if comparison_wavelengths:
        weights = None
        if args.normalise:
            weights = [1.0 / (len(comparison_wavelengths) * args.bin_width_nm)] * len(comparison_wavelengths)
        ax.hist(
            comparison_wavelengths,
            bins=bins,
            weights=weights,
            histtype="step",
            linewidth=2.4,
            linestyle=(0, (4.0, 2.4)),
            color="#11845b",
            label=f"{args.comparison_label} (n = {len(comparison_wavelengths)})",
        )

    pde_ax.plot(
        pde_wavelengths,
        pde_5v,
        color="#222222",
        linewidth=2.0,
        label="PDE, overvoltage = 5.0V",
    )
    pde_ax.plot(
        pde_wavelengths,
        pde_2p5v,
        color="#222222",
        linewidth=2.0,
        linestyle=(0, (2.2, 3.2)),
        label="PDE, overvoltage = 2.5V",
    )

    ax.set_xlabel("Photon wavelength (nm)")
    if args.normalise:
        ax.set_ylabel("Normalised detected-photon density (1 / nm)")
    else:
        ax.set_ylabel(f"Detected optical photons per {args.bin_width_nm:g} nm bin")
    pde_ax.set_ylabel("Photon Detection Efficiency (%)")
    pde_ax.set_ylim(0, 45)
    if args.x_min is None and args.x_max is None:
        ax.set_xlim(min(min(pde_wavelengths), bins[0]), max(max(pde_wavelengths), bins[-1]))
    ax.grid(True, color="#d0d4da", linewidth=0.9)
    ax.set_axisbelow(True)

    handles, labels = ax.get_legend_handles_labels()
    pde_handles, pde_labels = pde_ax.get_legend_handles_labels()
    ax.legend(handles + pde_handles, labels + pde_labels, frameon=False, loc="upper right")
    ax.set_title("Detected Optical-Photon Spectrum by SiPM with CRY and Digitised PDE")
    fig.tight_layout()
    fig.savefig(args.output, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    files = find_hit_files(args.inputs)
    spectra = collect_wavelengths(files)
    comparison_files = find_hit_files(args.comparison_input) if args.comparison_input else []
    comparison_wavelengths = collect_combined_sipm_wavelengths(comparison_files) if comparison_files else []
    pde_wavelengths, pde_5v, pde_2p5v = read_pde(args.pde_csv)
    plot_spectra(spectra, comparison_wavelengths, pde_wavelengths, pde_5v, pde_2p5v, args)

    all_values = [value for values in spectra.values() for value in values] + comparison_wavelengths
    print(f"input files: {len(files)}")
    if comparison_files:
        print(f"comparison files: {len(comparison_files)}")
    print(f"PDE data: {args.pde_csv}")
    for label, values in spectra.items():
        print(f"{label}: {len(values)} optical photons")
    if comparison_wavelengths:
        print(f"{args.comparison_label}: {len(comparison_wavelengths)} optical photons")
    print(f"wavelength range: {min(all_values):.3f} - {max(all_values):.3f} nm")
    print(f"normalised: {args.normalise}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
