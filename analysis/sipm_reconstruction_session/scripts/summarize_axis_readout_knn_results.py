#!/usr/bin/env python3
"""Summarize full-readout vs one-axis virtual-quadrant kNN results."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect the best row from each readout-axis kNN sweep."
    )
    parser.add_argument("--full-sweep", type=Path, required=True)
    parser.add_argument("--x-sweep", type=Path, required=True)
    parser.add_argument("--z-sweep", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def best_row(path: Path, label: str, n_channels: int) -> pd.Series:
    df = pd.read_csv(path)
    row = df.sort_values("p68_err_r_cm").iloc[0].copy()
    row["readout_label"] = label
    if "readout_axis" not in row:
        row["readout_axis"] = "all"
    if "n_readout_channels" not in row:
        row["n_readout_channels"] = n_channels
    return row


def main() -> None:
    args = parse_args()
    rows = [
        best_row(args.full_sweep, "all four sides", 64),
        best_row(args.x_sweep, "+x/-x sides only", 32),
        best_row(args.z_sweep, "+z/-z sides only", 32),
    ]
    out = pd.DataFrame(rows)
    first_cols = [
        "readout_label",
        "readout_axis",
        "n_readout_channels",
        "k",
        "metric",
        "normalization",
        "weighting",
        "mean_err_r_cm",
        "median_err_r_cm",
        "p68_err_r_cm",
        "p95_err_r_cm",
        "mean_err_x_cm",
        "sigma_err_x_cm",
        "mean_err_z_cm",
        "sigma_err_z_cm",
    ]
    out = out[[col for col in first_cols if col in out.columns]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(out.to_string(index=False))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
