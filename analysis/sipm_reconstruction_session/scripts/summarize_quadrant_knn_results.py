#!/usr/bin/env python3
"""Summarize positive-only vs virtual-quadrant kNN predictions."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize quadrant kNN prediction CSVs.")
    parser.add_argument("--virtual-predictions", type=Path, required=True)
    parser.add_argument("--positive-predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sigma(values: pd.Series) -> float:
    return float(values.std(ddof=1)) if len(values) > 1 else float("nan")


def summarize_one(df: pd.DataFrame, method: str, subset: str) -> dict[str, object]:
    return {
        "method": method,
        "subset": subset,
        "n_events": len(df),
        "mean_err_r_cm": df["err_r_cm"].mean(),
        "median_err_r_cm": df["err_r_cm"].median(),
        "p68_err_r_cm": df["err_r_cm"].quantile(0.68),
        "p95_err_r_cm": df["err_r_cm"].quantile(0.95),
        "mean_err_x_cm": df["err_x_cm"].mean(),
        "sigma_err_x_cm": sigma(df["err_x_cm"]),
        "mean_err_z_cm": df["err_z_cm"].mean(),
        "sigma_err_z_cm": sigma(df["err_z_cm"]),
    }


def summarize(path: Path, method: str) -> list[dict[str, object]]:
    df = pd.read_csv(path)
    symmetry_edge_5 = (df["true_x_cm"] < 5.0) | (df["true_z_cm"] < 5.0)
    symmetry_edge_10 = (df["true_x_cm"] < 10.0) | (df["true_z_cm"] < 10.0)
    outer_edge_5 = (df["true_x_cm"] > 45.0) | (df["true_z_cm"] > 45.0)
    interior_10 = (
        (df["true_x_cm"] >= 10.0)
        & (df["true_z_cm"] >= 10.0)
        & (df["true_x_cm"] <= 40.0)
        & (df["true_z_cm"] <= 40.0)
    )
    subsets = {
        "all": np.ones(len(df), dtype=bool),
        "symmetry_edge_lt5cm": symmetry_edge_5,
        "symmetry_edge_lt10cm": symmetry_edge_10,
        "outer_edge_gt45cm": outer_edge_5,
        "interior_10_to_40cm": interior_10,
    }
    return [summarize_one(df.loc[mask].copy(), method, name) for name, mask in subsets.items()]


def main() -> None:
    args = parse_args()
    rows = []
    rows.extend(summarize(args.virtual_predictions, "virtual_quadrants"))
    rows.extend(summarize(args.positive_predictions, "positive_only"))
    out = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(out.to_string(index=False))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
