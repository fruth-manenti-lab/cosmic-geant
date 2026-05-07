#!/usr/bin/env python3
"""Compare reconstruction error for different training library choices."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare kNN training library choices.")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, required=True)
    return parser.parse_args()


def load_predictions(path: Path, label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[["event_id", "true_x_cm", "true_z_cm", "pred_x_cm", "pred_z_cm"]].copy()
    df["library"] = label
    df["err_x_cm"] = df["pred_x_cm"] - df["true_x_cm"]
    df["err_z_cm"] = df["pred_z_cm"] - df["true_z_cm"]
    df["err_r_cm"] = np.hypot(df["err_x_cm"], df["err_z_cm"])
    return df


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

    df = pd.concat(
        [
            load_predictions(results_dir / "knn_sipm_best_predictions.csv", "1024 positions x 10 events"),
            load_predictions(
                results_dir / "knn_sipm_best_predictions_10000_1event.csv",
                "10000 positions x 1 event",
            ),
        ],
        ignore_index=True,
    )
    summary = df.groupby("library", sort=False).apply(summarize, include_groups=False)
    summary.to_csv(results_dir / "knn_training_library_comparison_summary.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    bins = np.linspace(0, max(8.0, float(df["err_r_cm"].quantile(0.99))), 50)
    colors = ["#2563eb", "#dc2626"]

    ax = axes[0]
    for color, (label, subset) in zip(colors, df.groupby("library", sort=False)):
        metrics = summary.loc[label]
        ax.hist(subset["err_r_cm"], bins=bins, histtype="step", lw=2, color=color, label=label)
        ax.axvline(metrics["p68_radial_err_cm"], color=color, lw=1.5, linestyle="--")
    ax.set_title("kNN radial error")
    ax.set_xlabel("radial error [cm]")
    ax.set_ylabel("events")
    ax.grid(alpha=0.25)
    ax.legend()

    ax = axes[1]
    labels = list(summary.index)
    x = np.arange(len(labels))
    ax.bar(x - 0.18, summary["mean_radial_err_cm"], width=0.36, label="mean")
    ax.bar(x + 0.18, summary["p68_radial_err_cm"], width=0.36, label="68%")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=12, ha="right")
    ax.set_ylabel("radial error [cm]")
    ax.set_title("summary")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()

    fig.suptitle("New Geometry kNN Training Library Comparison", fontsize=14)
    fig.savefig(figures_dir / "knn_training_library_comparison.png", dpi=180)
    plt.close(fig)
    print(summary.to_string())
    print(f"Wrote {figures_dir / 'knn_training_library_comparison.png'}")


if __name__ == "__main__":
    main()
