#!/usr/bin/env python3
"""Overlay SiPM optical-photon wavelength spectrum with digitised PDE curves."""

from __future__ import annotations

import argparse
import csv
import itertools
import os
from pathlib import Path


PLOT_DIR = Path(__file__).resolve().parent
MPLCONFIGDIR = PLOT_DIR / ".mplconfig"
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
        description="Plot detected SiPM optical-photon wavelength spectrum over the digitised PDE curve."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Hit CSV files, directories, or run directories containing MUON-run*_nt_hits_t*.csv.",
    )
    parser.add_argument(
        "--pde-csv",
        type=Path,
        default=PLOT_DIR / "sipm_pde_digitized.csv",
        help="Digitised PDE CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PLOT_DIR / "sipm_wavelength_spectrum_with_pde.png",
        help="Output overlay plot.",
    )
    parser.add_argument("--bin-width-nm", type=float, default=5.0, help="Histogram bin width in nm.")
    parser.add_argument("--x-min", type=float, default=250.0, help="Minimum wavelength shown.")
    parser.add_argument("--x-max", type=float, default=950.0, help="Maximum wavelength shown.")
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
        found = []
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
    initial_energy_eV = float(row["InitialEnergy"]) * 1000.0
    return 1239.841984 / initial_energy_eV


def collect_sipm_wavelengths(files: list[Path]) -> list[float]:
    wavelengths = []
    for path in files:
        for row in iter_hit_rows(path):
            if row.get("Particle") != "opticalphoton":
                continue
            if "sipm" not in row.get("Volume", "").lower():
                continue
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


def bins(x_min: float, x_max: float, width: float) -> list[float]:
    if width <= 0:
        raise ValueError("--bin-width-nm must be greater than zero")
    values = []
    current = x_min
    while current <= x_max + width * 0.5:
        values.append(current)
        current += width
    return values


def plot_overlay(
    wavelengths: list[float],
    pde_wavelengths: list[float],
    pde_5v: list[float],
    pde_2p5v: list[float],
    args: argparse.Namespace,
) -> None:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig, pde_ax = plt.subplots(figsize=(11, 6.4))
    spectrum_ax = pde_ax.twinx()

    histogram_bins = bins(args.x_min, args.x_max, args.bin_width_nm)
    spectrum_ax.hist(
        wavelengths,
        bins=histogram_bins,
        color="#4c78a8",
        alpha=0.35,
        label="SiPM optical photons",
    )
    spectrum_ax.set_ylabel(f"Detected SiPM photons per {args.bin_width_nm:g} nm bin", color="#2f5f8f")
    spectrum_ax.tick_params(axis="y", labelcolor="#2f5f8f")

    pde_ax.plot(pde_wavelengths, pde_5v, color="black", linewidth=2.2, label="PDE, overvoltage = 5.0V")
    pde_ax.plot(
        pde_wavelengths,
        pde_2p5v,
        color="black",
        linewidth=2.0,
        linestyle=(0, (2.2, 3.2)),
        label="PDE, overvoltage = 2.5V",
    )
    pde_ax.set_xlim(args.x_min, args.x_max)
    pde_ax.set_ylim(0, 45)
    pde_ax.set_xlabel("Wavelength (nm)")
    pde_ax.set_ylabel("Photon Detection Efficiency (%)")
    pde_ax.grid(True, color="#d0d4da", linewidth=0.9)
    pde_ax.set_axisbelow(True)

    handles_left, labels_left = pde_ax.get_legend_handles_labels()
    handles_right, labels_right = spectrum_ax.get_legend_handles_labels()
    pde_ax.legend(handles_left + handles_right, labels_left + labels_right, frameon=False, loc="upper right")

    fig.suptitle("SiPM Photon Wavelength Spectrum Over Digitised PDE")
    fig.tight_layout()
    fig.savefig(args.output, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    files = find_hit_files(args.inputs)
    wavelengths = collect_sipm_wavelengths(files)
    pde_wavelengths, pde_5v, pde_2p5v = read_pde(args.pde_csv)
    plot_overlay(wavelengths, pde_wavelengths, pde_5v, pde_2p5v, args)

    below = sum(1 for value in wavelengths if value < min(pde_wavelengths))
    above = sum(1 for value in wavelengths if value > max(pde_wavelengths))
    print(f"input files: {len(files)}")
    print(f"SiPM optical photons: {len(wavelengths)}")
    print(f"wavelength range: {min(wavelengths):.3f} - {max(wavelengths):.3f} nm")
    print(f"below digitised PDE range: {below}")
    print(f"above digitised PDE range: {above}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
