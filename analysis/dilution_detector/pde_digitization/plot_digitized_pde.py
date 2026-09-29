#!/usr/bin/env python3
"""Plot the manually digitised SiPM photon-detection-efficiency curves."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


PLOT_DIR = Path(__file__).resolve().parent
MPLCONFIGDIR = PLOT_DIR / ".mplconfig"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPLCONFIGDIR / "cache"))

import matplotlib.pyplot as plt  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot digitised SiPM PDE curves.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PLOT_DIR / "sipm_pde_digitized.csv",
        help="Digitised PDE CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PLOT_DIR / "sipm_pde_digitized_check.png",
        help="Output check image.",
    )
    return parser.parse_args()


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


def main() -> int:
    args = parse_args()
    wavelengths, pde_5v, pde_2p5v = read_pde(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    ax.plot(wavelengths, pde_5v, color="black", linewidth=2.2, label="Overvoltage = 5.0V")
    ax.plot(
        wavelengths,
        pde_2p5v,
        color="black",
        linewidth=2.2,
        linestyle=(0, (2.2, 3.2)),
        label="Overvoltage = 2.5V",
    )

    ax.set_xlim(300, 950)
    ax.set_ylim(0, 45)
    ax.set_xticks(range(300, 951, 50))
    ax.set_yticks(range(0, 46, 5))
    ax.set_xlabel("Wavelength (nm)", fontweight="bold")
    ax.set_ylabel("Photon Detection Efficiency (%)", fontweight="bold")
    ax.grid(True, color="#bfbfbf", linewidth=1.6)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Digitised SiPM PDE Curves")
    fig.tight_layout()
    fig.savefig(args.output, dpi=180)
    plt.close(fig)

    print(f"digitised points: {len(wavelengths)}")
    print(f"input: {args.input}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
