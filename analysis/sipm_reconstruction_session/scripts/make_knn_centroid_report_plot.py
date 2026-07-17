from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
OUT_DIR = ROOT / "figures"


def load_predictions() -> pd.DataFrame:
    knn = pd.read_csv(RESULTS_DIR / "knn_sipm_best_predictions_events.csv")
    knn = knn[["event_id", "true_x_cm", "true_z_cm", "pred_x_cm", "pred_z_cm"]].copy()
    knn["method"] = "kNN event library"

    centroid_raw = pd.read_csv(RESULTS_DIR / "centroid_sipm_predictions.csv")
    centroid = centroid_raw[centroid_raw["dataset"] == "test"].copy()
    centroid = centroid.rename(
        columns={
            "pred_x_projection_cm": "pred_x_cm",
            "pred_z_projection_cm": "pred_z_cm",
        }
    )
    centroid = centroid[["event_id", "true_x_cm", "true_z_cm", "pred_x_cm", "pred_z_cm"]]
    centroid["method"] = "Projection centroid"

    df = pd.concat([knn, centroid], ignore_index=True)
    df["err_x_cm"] = df["pred_x_cm"] - df["true_x_cm"]
    df["err_z_cm"] = df["pred_z_cm"] - df["true_z_cm"]
    df["err_r_cm"] = np.hypot(df["err_x_cm"], df["err_z_cm"])
    return df


def summarize(group: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_predictions()
    summary = df.groupby("method", sort=False).apply(summarize, include_groups=False)
    summary.to_csv(RESULTS_DIR / "knn_centroid_summary.csv")

    methods = ["kNN event library", "Projection centroid"]
    fig, axes = plt.subplots(
        nrows=len(methods),
        ncols=2,
        figsize=(12, 7.5),
        constrained_layout=True,
    )
    bins = np.linspace(0, 50, 51)

    for row, method in enumerate(methods):
        subset = df[df["method"] == method]
        metrics = summary.loc[method]

        ax_hist = axes[row, 0]
        ax_hist.hist(subset["err_r_cm"], bins=bins, color="#3b82f6", alpha=0.82)
        ax_hist.axvline(metrics["mean_radial_err_cm"], color="#111827", lw=2, label="mean")
        ax_hist.axvline(metrics["p68_radial_err_cm"], color="#ef4444", lw=2, label="68%")
        ax_hist.set_title(f"{method}: radial error distribution")
        ax_hist.set_xlabel("radial position error [cm]")
        ax_hist.set_ylabel("events")
        ax_hist.legend()
        ax_hist.grid(alpha=0.25)

        ax_map = axes[row, 1]
        sc = ax_map.scatter(
            subset["true_x_cm"],
            subset["true_z_cm"],
            c=subset["err_r_cm"],
            s=18,
            cmap="viridis",
            vmin=0,
            vmax=25,
            edgecolors="none",
        )
        ax_map.set_aspect("equal", adjustable="box")
        ax_map.set_title(
            f"hit map: mean={metrics['mean_radial_err_cm']:.2f} cm, "
            f"68%={metrics['p68_radial_err_cm']:.2f} cm"
        )
        ax_map.set_xlabel("true x [cm]")
        ax_map.set_ylabel("true z [cm]")
        ax_map.grid(alpha=0.25)
        fig.colorbar(sc, ax=ax_map, label="radial error [cm]")

    fig.suptitle("SiPM Reconstruction: kNN vs Projection Centroid", fontsize=16)
    fig.savefig(OUT_DIR / "knn_centroid_comparison.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
