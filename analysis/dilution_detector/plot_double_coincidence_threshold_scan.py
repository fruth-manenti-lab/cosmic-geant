#!/usr/bin/env python3
"""Plot double-coincidence count versus per-SiPM photon threshold."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


MPLCONFIGDIR = Path(__file__).resolve().parent / ".mplconfig"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPLCONFIGDIR / "cache"))

import matplotlib.pyplot as plt  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan per-SiPM photon thresholds and plot how many events remain "
            "as double coincidences."
        )
    )
    parser.add_argument(
        "counts_csv",
        type=Path,
        help="Per-event SiPM count CSV from count_sipm_double_coincidences.py.",
    )
    parser.add_argument("--step", type=int, default=10, help="Threshold step in photons. Default: 10.")
    parser.add_argument("--start", type=int, default=10, help="First threshold in photons. Default: 10.")
    parser.add_argument(
        "--max-threshold",
        type=int,
        help="Maximum threshold to scan. Default: largest min(SiPM0, SiPM1) rounded down to step.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("analysis/dilution_detector/results/cry_10M_double_coincidence_threshold_scan.csv"),
        help="Output threshold scan CSV.",
    )
    parser.add_argument(
        "--output-plot",
        type=Path,
        default=Path("analysis/dilution_detector/results/cry_10M_double_coincidence_threshold_scan.png"),
        help="Output plot image.",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        help="Run duration in minutes. If provided, plot double-coincidence rate per hour.",
    )
    parser.add_argument(
        "--mark-threshold",
        action="append",
        type=int,
        default=[],
        help="Threshold to mark with a vertical guide. May be passed more than once.",
    )
    parser.add_argument(
        "--sigma-alpha",
        type=float,
        default=0.5,
        help="Alpha value for the Poisson 1-sigma uncertainty band. Default: 0.5.",
    )
    parser.add_argument(
        "--x-efficiency",
        type=float,
        help="Efficiency used to convert incident photons to detected photons on the x-axis.",
    )
    parser.add_argument(
        "--mv-per-detected-photon",
        type=float,
        help="Signal size in mV per detected photon for x-axis conversion.",
    )
    return parser.parse_args()


def read_event_counts(path: Path) -> list[tuple[int, int]]:
    counts = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"sipm_copy_0_photons", "sipm_copy_1_photons"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            counts.append((int(row["sipm_copy_0_photons"]), int(row["sipm_copy_1_photons"])))
    if not counts:
        raise ValueError(f"No event counts found in {path}")
    return counts


def build_thresholds(counts: list[tuple[int, int]], start: int, step: int, max_threshold: int | None) -> list[int]:
    if step <= 0:
        raise ValueError("--step must be greater than zero")
    if start < 1:
        raise ValueError("--start must be at least 1 for a meaningful double-coincidence threshold")
    if max_threshold is None:
        max_seen = max(min(lower, upper) for lower, upper in counts)
        max_threshold = (max_seen // step) * step
    if max_threshold < start:
        return [start]
    return list(range(start, max_threshold + 1, step))


def scan_thresholds(counts: list[tuple[int, int]], thresholds: list[int]) -> list[tuple[int, int]]:
    return [
        (threshold, sum(1 for lower, upper in counts if lower >= threshold and upper >= threshold))
        for threshold in thresholds
    ]


def x_axis_scale(args: argparse.Namespace) -> tuple[float, str, str]:
    if args.x_efficiency is None and args.mv_per_detected_photon is None:
        return 1.0, "Photon threshold per SiPM", "photon_threshold_per_sipm"
    if args.x_efficiency is None or args.mv_per_detected_photon is None:
        raise ValueError("--x-efficiency and --mv-per-detected-photon must be used together")
    if not 0 < args.x_efficiency <= 1:
        raise ValueError("--x-efficiency must be greater than 0 and less than or equal to 1")
    if args.mv_per_detected_photon <= 0:
        raise ValueError("--mv-per-detected-photon must be greater than 0")
    return (
        args.x_efficiency * args.mv_per_detected_photon,
        "Signal threshold per SiPM (mV)",
        "signal_threshold_mV_per_sipm",
    )


def write_scan(
    path: Path,
    scan: list[tuple[int, int]],
    duration_minutes: float | None,
    x_scale: float,
    converted_x_column: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        if duration_minutes is None:
            header = ["photon_threshold_per_sipm"]
            if x_scale != 1.0:
                header.append(converted_x_column)
            header.append("double_coincidence_events")
            writer.writerow(header)
            for threshold, coincidences in scan:
                row = [threshold]
                if x_scale != 1.0:
                    row.append(threshold * x_scale)
                row.append(coincidences)
                writer.writerow(row)
            return

        rate_scale = 60.0 / duration_minutes
        header = ["photon_threshold_per_sipm"]
        if x_scale != 1.0:
            header.append(converted_x_column)
        header.extend(["double_coincidence_events", "double_coincidence_events_per_hour"])
        writer.writerow(header)
        for threshold, coincidences in scan:
            row = [threshold]
            if x_scale != 1.0:
                row.append(threshold * x_scale)
            row.extend([coincidences, coincidences * rate_scale])
            writer.writerow(row)


def plot_scan(
    path: Path,
    scan: list[tuple[int, int]],
    marked_thresholds: list[int],
    duration_minutes: float | None,
    sigma_alpha: float,
    x_scale: float,
    x_label: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    thresholds = [threshold for threshold, _ in scan]
    x_values = [threshold * x_scale for threshold in thresholds]
    rate_scale = 60.0 / duration_minutes if duration_minutes is not None else 1.0
    raw_coincidences = [coincidences for _, coincidences in scan]
    coincidences = [count * rate_scale for count in raw_coincidences]
    sigma = [(count**0.5) * rate_scale for count in raw_coincidences]
    lower = [max(0.0, value - error) for value, error in zip(coincidences, sigma)]
    upper = [value + error for value, error in zip(coincidences, sigma)]

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.fill_between(
        x_values,
        lower,
        upper,
        color="#7ca3d8",
        alpha=sigma_alpha,
        linewidth=0,
        label="1 sigma Poisson",
    )
    ax.plot(x_values, coincidences, color="#2457a6", linewidth=2.2, label="DC count")
    ax.scatter(x_values, coincidences, color="#2457a6", s=12, zorder=3)

    for marked in marked_thresholds:
        if thresholds[0] <= marked <= thresholds[-1]:
            marked_x = marked * x_scale
            ax.axvline(marked_x, color="#b23a48", linestyle="--", linewidth=1.2, alpha=0.8)
            ax.text(
                marked_x,
                max(coincidences) * 0.96 if coincidences else 0,
                f"{marked}",
                color="#7a1f2a",
                rotation=90,
                va="top",
                ha="right",
                fontsize=9,
            )

    title_suffix = " Per Hour" if duration_minutes is not None else ""
    threshold_name = "Signal Threshold" if x_scale != 1.0 else "Photon Threshold"
    ax.set_title(f"SiPM Double Coincidences{title_suffix} vs {threshold_name}")
    ax.set_xlabel(x_label)
    if duration_minutes is None:
        ax.set_ylabel("Double-coincidence events")
    else:
        ax.set_ylabel("Double-coincidence events per hour")
    ax.grid(True, color="#d8dce3", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    counts = read_event_counts(args.counts_csv)
    thresholds = build_thresholds(counts, args.start, args.step, args.max_threshold)
    scan = scan_thresholds(counts, thresholds)
    scale, x_label, converted_x_column = x_axis_scale(args)
    write_scan(args.output_csv, scan, args.duration_minutes, scale, converted_x_column)
    plot_scan(args.output_plot, scan, args.mark_threshold, args.duration_minutes, args.sigma_alpha, scale, x_label)

    print(f"read events: {len(counts)}")
    print(f"thresholds scanned: {len(thresholds)}")
    print(f"first threshold: {thresholds[0]}")
    print(f"last threshold: {thresholds[-1]}")
    print(f"first count: {scan[0][1]}")
    print(f"last count: {scan[-1][1]}")
    if args.duration_minutes is not None:
        print(f"duration minutes: {args.duration_minutes}")
        print(f"rate scale per hour: {60.0 / args.duration_minutes}")
    if scale != 1.0:
        print(f"x-axis scale: {scale}")
        print(f"x-axis label: {x_label}")
    print(f"scan CSV: {args.output_csv}")
    print(f"plot: {args.output_plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
