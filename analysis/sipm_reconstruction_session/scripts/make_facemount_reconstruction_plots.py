#!/usr/bin/env python3
"""Plot face-mount random-scan kNN reconstruction diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Make reconstruction scatter and error histogram plots."
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=Path(
            "analysis/sipm_reconstruction_session/facemount_may12/results/"
            "knn_virtual_quadrant_best_predictions.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/sipm_reconstruction_session/facemount_may12/figures"),
    )
    parser.add_argument("--reconstruction-title", default="Face-mount random scan reconstruction")
    parser.add_argument("--histogram-title", default="Face-mount radial reconstruction error")
    return parser.parse_args()


def add_error_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "err_x_cm" not in out:
        out["err_x_cm"] = out["pred_x_cm"] - out["true_x_cm"]
    if "err_z_cm" not in out:
        out["err_z_cm"] = out["pred_z_cm"] - out["true_z_cm"]
    if "err_r_cm" not in out:
        out["err_r_cm"] = np.hypot(out["err_x_cm"], out["err_z_cm"])
    return out


def plot_reconstruction(df: pd.DataFrame, output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 7.1), dpi=180)
    sc = ax.scatter(
        df["true_x_cm"],
        df["true_z_cm"],
        c=df["err_r_cm"],
        s=20,
        cmap="viridis",
        vmin=0.0,
        vmax=max(6.0, float(df["err_r_cm"].quantile(0.98))),
        edgecolors="none",
        alpha=0.92,
        label="true random-scan position",
        zorder=3,
    )

    # Draw every event as a faint true-to-predicted displacement vector. The
    # line cloud is more useful here than a subsample because the event count is
    # only 1000 and the plot remains readable.
    for row in df.itertuples(index=False):
        ax.plot(
            [row.true_x_cm, row.pred_x_cm],
            [row.true_z_cm, row.pred_z_cm],
            color="#111827",
            alpha=0.13,
            linewidth=0.45,
            zorder=2,
        )
    ax.scatter(
        df["pred_x_cm"],
        df["pred_z_cm"],
        s=7,
        color="#ef4444",
        alpha=0.45,
        edgecolors="none",
        label="kNN prediction",
        zorder=4,
    )

    ax.set_title(title)
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("z [cm]")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-1.5, 51.5)
    ax.set_ylim(-1.5, 51.5)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", frameon=True)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.86)
    cbar.set_label("radial error [cm]")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_histogram(df: pd.DataFrame, output_path: Path, title: str) -> None:
    mean = df["err_r_cm"].mean()
    median = df["err_r_cm"].median()
    p68 = df["err_r_cm"].quantile(0.68)
    p95 = df["err_r_cm"].quantile(0.95)
    p99 = df["err_r_cm"].quantile(0.99)
    max_edge = max(8.0, float(np.ceil(p99 + 1.0)))
    bins = np.linspace(0.0, max_edge, 45)

    fig, ax = plt.subplots(figsize=(8.2, 4.9), dpi=180)
    ax.hist(df["err_r_cm"], bins=bins, color="#2563eb", alpha=0.82)
    ax.axvline(mean, color="#111827", linewidth=2.0, label=f"mean {mean:.2f} cm")
    ax.axvline(median, color="#16a34a", linewidth=2.0, label=f"median {median:.2f} cm")
    ax.axvline(p68, color="#f97316", linewidth=2.0, label=f"68% {p68:.2f} cm")
    ax.axvline(p95, color="#dc2626", linewidth=2.0, label=f"95% {p95:.2f} cm")
    ax.set_title(title)
    ax.set_xlabel("radial position error [cm]")
    ax.set_ylabel("events")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    df = add_error_columns(pd.read_csv(args.predictions))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plot_reconstruction(
        df,
        args.output_dir / "random_scan_reconstruction.png",
        args.reconstruction_title,
    )
    plot_histogram(
        df,
        args.output_dir / "radial_error_histogram.png",
        args.histogram_title,
    )
    print(f"Wrote {args.output_dir / 'random_scan_reconstruction.png'}")
    print(f"Wrote {args.output_dir / 'radial_error_histogram.png'}")


if __name__ == "__main__":
    main()
