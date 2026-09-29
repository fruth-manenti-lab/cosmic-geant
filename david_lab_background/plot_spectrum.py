#!/usr/bin/env python3
"""Decode a RadiaCode XML spectrum and plot calibrated counts."""

from __future__ import annotations

import argparse
import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MPLCONFIGDIR = SCRIPT_DIR / ".mplconfig"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPLCONFIGDIR / "cache"))

import matplotlib.pyplot as plt  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decode and plot a RadiaCode XML spectrum.")
    parser.add_argument(
        "--input",
        type=Path,
        default=SCRIPT_DIR / "Spectrum 21-07-2026.xml",
        help="Input XML spectrum file.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=SCRIPT_DIR / "decoded_spectrum.csv",
        help="Decoded CSV output.",
    )
    parser.add_argument(
        "--output-plot",
        type=Path,
        default=SCRIPT_DIR / "spectrum_21-07-2026.png",
        help="Spectrum plot output.",
    )
    parser.add_argument(
        "--log-output-plot",
        type=Path,
        default=SCRIPT_DIR / "spectrum_21-07-2026_log.png",
        help="Log-scale spectrum plot output.",
    )
    return parser.parse_args()


def text_at(parent: ET.Element, path: str) -> str:
    element = parent.find(path)
    return "" if element is None or element.text is None else element.text.strip()


def parse_spectrum(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    result = root.find("./ResultDataList/ResultData")
    if result is None:
        raise ValueError("Could not find ResultData in XML")
    energy_spectrum = result.find("./EnergySpectrum")
    if energy_spectrum is None:
        raise ValueError("Could not find EnergySpectrum in XML")

    coefficients = [
        float(item.text)
        for item in energy_spectrum.findall("./EnergyCalibration/Coefficients/Coefficient")
        if item.text is not None
    ]
    if not coefficients:
        raise ValueError("Could not find energy calibration coefficients")

    counts = [
        int(item.text)
        for item in energy_spectrum.findall("./Spectrum/DataPoint")
        if item.text is not None
    ]
    if not counts:
        raise ValueError("Could not find spectrum DataPoint values")

    measurement_time_s = float(text_at(energy_spectrum, "./MeasurementTime"))
    channels = list(range(len(counts)))
    energies_keV = [
        sum(coefficient * (channel**power) for power, coefficient in enumerate(coefficients))
        for channel in channels
    ]

    return {
        "sample_name": text_at(result, "./SampleInfo/Name"),
        "device_name": text_at(result, "./DeviceConfigReference/Name"),
        "serial_number": text_at(energy_spectrum, "./SerialNumber"),
        "start_time": text_at(result, "./StartTime"),
        "end_time": text_at(result, "./EndTime"),
        "measurement_time_s": measurement_time_s,
        "coefficients": coefficients,
        "channels": channels,
        "energies_keV": energies_keV,
        "counts": counts,
    }


def write_csv(path: Path, spectrum: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    measurement_time_s = float(spectrum["measurement_time_s"])
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["channel", "energy_keV", "counts", "count_rate_cps"])
        for channel, energy, count in zip(
            spectrum["channels"], spectrum["energies_keV"], spectrum["counts"]
        ):
            writer.writerow([channel, f"{energy:.6f}", count, f"{count / measurement_time_s:.10g}"])


def format_duration(seconds: float) -> str:
    hours = seconds / 3600.0
    return f"{seconds:.0f} s ({hours:.2f} h)"


def plot_spectrum(path: Path, spectrum: dict[str, object], log_y: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    energies = spectrum["energies_keV"]
    counts = spectrum["counts"]
    measurement_time_s = float(spectrum["measurement_time_s"])

    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.step(energies, counts, where="mid", color="#2457a6", linewidth=1.3)
    if log_y:
        ax.set_yscale("log")
        ax.set_ylim(bottom=0.8)

    scale_label = " Log Scale" if log_y else ""
    ax.set_title(f"{spectrum['sample_name']} Background Spectrum{scale_label}")
    ax.set_xlabel("Calibrated energy (keV)")
    ax.set_ylabel("Counts per channel")
    ax.grid(True, color="#d6dae0", linewidth=0.8)
    ax.set_axisbelow(True)

    metadata = (
        f"Device: {spectrum['device_name']} ({spectrum['serial_number']})\n"
        f"Measurement time: {format_duration(measurement_time_s)}\n"
        f"Start: {spectrum['start_time']}\n"
        f"End: {spectrum['end_time']}"
    )
    ax.text(
        0.98,
        0.96,
        metadata,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#c8cdd5"},
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    spectrum = parse_spectrum(args.input)
    write_csv(args.output_csv, spectrum)
    plot_spectrum(args.output_plot, spectrum)
    plot_spectrum(args.log_output_plot, spectrum, log_y=True)

    total_counts = sum(spectrum["counts"])
    print(f"input: {args.input}")
    print(f"channels: {len(spectrum['channels'])}")
    print(f"energy range: {min(spectrum['energies_keV']):.3f} - {max(spectrum['energies_keV']):.3f} keV")
    print(f"measurement time: {format_duration(float(spectrum['measurement_time_s']))}")
    print(f"total counts: {total_counts}")
    print(f"mean count rate: {total_counts / float(spectrum['measurement_time_s']):.6g} cps")
    print(f"decoded CSV: {args.output_csv}")
    print(f"plot: {args.output_plot}")
    print(f"log plot: {args.log_output_plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
