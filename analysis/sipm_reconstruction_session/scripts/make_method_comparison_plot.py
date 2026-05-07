#!/usr/bin/env python3
"""Plot kNN and centroid reconstruction errors for one analysis result folder."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create kNN/centroid comparison plots.")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, required=True)
    return parser.parse_args()


def add_errors(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["err_x_cm"] = out["pred_x_cm"] - out["true_x_cm"]
    out["err_z_cm"] = out["pred_z_cm"] - out["true_z_cm"]
    out["err_r_cm"] = np.hypot(out["err_x_cm"], out["err_z_cm"])
    return out


def summarize(group: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "n_events": len(group),
            "mean_radial_err_cm": group["err_r_cm"].mean(),
            "median_radial_err_cm": group["err_r_cm"].median(),
            "p68_radial_err_cm": group["err_r_cm"].quantile(0.68),
            "p95_radial_err_cm": group["err_r_cm"].quantile(0.95),
            "mean_err_x_cm": group["err_x_cm"].mean(),
            "sigma_err_x_cm": group["err_x_cm"].std(ddof=1),
            "mean_err_z_cm": group["err_z_cm"].mean(),
            "sigma_err_z_cm": group["err_z_cm"].std(ddof=1),
        }
    )


def main() -> None:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    figures_dir = args.figures_dir.resolve()
    figures_dir.mkdir(parents=True, exist_ok=True)

    knn = pd.read_csv(results_dir / "knn_sipm_best_predictions.csv")
    knn = knn[["event_id", "true_x_cm", "true_z_cm", "pred_x_cm", "pred_z_cm"]].copy()
    knn["method"] = "kNN"

    centroid_raw = pd.read_csv(results_dir / "centroid_sipm_predictions.csv")
    centroid = centroid_raw[centroid_raw["dataset"] == "test"].rename(
        columns={"pred_x_projection_cm": "pred_x_cm", "pred_z_projection_cm": "pred_z_cm"}
    )
    centroid = centroid[["event_id", "true_x_cm", "true_z_cm", "pred_x_cm", "pred_z_cm"]].copy()
    centroid["method"] = "projection centroid"

    df = add_errors(pd.concat([knn, centroid], ignore_index=True))
    summary = df.groupby("method", sort=False).apply(summarize, include_groups=False)
    summary.to_csv(results_dir / "knn_centroid_comparison_summary.csv")

    methods = ["kNN", "projection centroid"]
    fig, axes = plt.subplots(len(methods), 2, figsize=(12, 7.5), constrained_layout=True)
    max_err = max(25.0, float(df["err_r_cm"].quantile(0.99)))
    bins = np.linspace(0, max_err, 50)
    for row, method in enumerate(methods):
        subset = df[df["method"] == method]
        metrics = summary.loc[method]

        ax = axes[row, 0]
        ax.hist(subset["err_r_cm"], bins=bins, color="#2563eb", alpha=0.82)
        ax.axvline(metrics["mean_radial_err_cm"], color="#111827", lw=2, label="mean")
        ax.axvline(metrics["p68_radial_err_cm"], color="#dc2626", lw=2, label="68%")
        ax.set_title(f"{method}: radial error")
        ax.set_xlabel("radial error [cm]")
        ax.set_ylabel("events")
        ax.grid(alpha=0.25)
        ax.legend()

        ax = axes[row, 1]
        sc = ax.scatter(
            subset["true_x_cm"],
            subset["true_z_cm"],
            c=subset["err_r_cm"],
            s=16,
            cmap="viridis",
            vmin=0,
            vmax=max_err,
            edgecolors="none",
        )
        ax.set_title(
            f"mean={metrics['mean_radial_err_cm']:.2f} cm, "
            f"68%={metrics['p68_radial_err_cm']:.2f} cm"
        )
        ax.set_xlabel("true x [cm]")
        ax.set_ylabel("true z [cm]")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=0.25)
        fig.colorbar(sc, ax=ax, label="radial error [cm]")

    fig.suptitle("New Geometry Random Scan Reconstruction", fontsize=15)
    fig.savefig(figures_dir / "knn_centroid_comparison.png", dpi=180)
    plt.close(fig)
    print(summary.to_string())
    print(f"Wrote {figures_dir / 'knn_centroid_comparison.png'}")


if __name__ == "__main__":
    main()
