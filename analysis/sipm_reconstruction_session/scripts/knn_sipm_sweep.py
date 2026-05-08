#!/usr/bin/env python3
"""Sweep kNN localization settings for 32-SiPM muon hit vectors."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors


RUN_FILE_RE = re.compile(r"MUON-run(?P<run>\d+)_sipm_counts_by_event\.csv$")
SIPM_COLUMNS = [f"sipm_{i}" for i in range(100, 116)] + [
    f"sipm_{i}" for i in range(300, 316)
]
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep kNN SiPM localization settings.")
    parser.add_argument(
        "--training-dir",
        type=Path,
        default=Path("analysis/sipm_reconstruction_session/training_scan_data_1024"),
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path("analysis/sipm_reconstruction_session/test_scan_data_1000"),
    )
    parser.add_argument("--macro", type=Path, default=Path("macros/muon_scan.mac"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis/sipm_reconstruction_session/results/knn_sipm_sweep_results.csv"),
    )
    parser.add_argument(
        "--predictions-output",
        type=Path,
        default=Path("analysis/sipm_reconstruction_session/results/knn_sipm_best_predictions.csv"),
    )
    parser.add_argument(
        "--reference",
        choices=("templates", "events", "both"),
        default="both",
        help="Compare against run-averaged templates, individual training events, or both.",
    )
    parser.add_argument(
        "--max-events-per-run",
        type=int,
        default=None,
        help="Use only the first N events from each training run before fitting kNN.",
    )
    return parser.parse_args()


def parse_muon_scan_positions(path: Path) -> pd.DataFrame:
    rows = []
    for line in path.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) == 5 and parts[0] == "/gps/position":
            x_cm, _, z_cm = map(float, parts[1:4])
            rows.append({"run_id": len(rows), "x_cm": x_cm, "z_cm": z_cm})
    if not rows:
        raise ValueError(f"No /gps/position lines found in {path}")
    return pd.DataFrame(rows)


def load_event_folder(path: Path) -> pd.DataFrame:
    frames = []
    for csv_path in sorted(path.glob("MUON-run*_sipm_counts_by_event.csv")):
        match = RUN_FILE_RE.match(csv_path.name)
        if not match:
            continue
        df = pd.read_csv(csv_path)
        missing = [col for col in ["EventID", *SIPM_COLUMNS] if col not in df.columns]
        if missing:
            raise KeyError(f"{csv_path} is missing columns: {missing}")
        df = df[["EventID", *SIPM_COLUMNS]].copy()
        df.insert(0, "run_id", int(match.group("run")))
        df = df.rename(columns={"EventID": "event_id"})
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No event CSVs found in {path}")
    return pd.concat(frames, ignore_index=True)


def load_training_events(training_dir: Path, macro: Path) -> pd.DataFrame:
    events = load_event_folder(training_dir)
    manifest_path = training_dir / "test_manifest.csv"
    if manifest_path.exists():
        manifest = pd.read_csv(manifest_path)
        labels = manifest[["run_id", "true_x_cm", "true_z_cm"]].copy()
        labels = labels.rename(columns={"true_x_cm": "x_cm", "true_z_cm": "z_cm"})
        if "source_index" in manifest.columns:
            labels["position_id"] = manifest["source_index"].astype(int)
        else:
            labels["position_id"] = labels["run_id"].astype(int)
        return events.merge(labels, on="run_id", validate="one_to_one")

    labels = parse_muon_scan_positions(macro)
    labels["position_id"] = labels["run_id"]
    return events.merge(labels, on="run_id", validate="many_to_one")


def load_test_events(test_dir: Path) -> pd.DataFrame:
    manifest = pd.read_csv(test_dir / "test_manifest.csv")
    frames = []
    for _, meta in manifest.sort_values("event_id").iterrows():
        df = pd.read_csv(test_dir / meta["output_file"])
        if len(df) != 1:
            raise ValueError(f"Expected one row in {meta['output_file']}, found {len(df)}")
        row = df.iloc[0].to_dict()
        row["event_id"] = int(meta["event_id"])
        row["run_id"] = int(meta["run_id"])
        row["raw_file"] = meta["raw_file"]
        row["true_x_cm"] = float(meta["true_x_cm"])
        row["true_z_cm"] = float(meta["true_z_cm"])
        frames.append(row)
    return pd.DataFrame(frames)


def normalize(x: np.ndarray, mode: str) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if mode == "none":
        return x
    if mode == "l1":
        return x / np.maximum(x.sum(axis=1, keepdims=True), EPS)
    if mode == "sqrt":
        return np.sqrt(np.maximum(x, 0.0))
    if mode == "sqrt_l1":
        y = np.sqrt(np.maximum(x, 0.0))
        return y / np.maximum(y.sum(axis=1, keepdims=True), EPS)
    if mode == "log1p":
        return np.log1p(np.maximum(x, 0.0))
    raise ValueError(mode)


def predict_knn(
    reference: pd.DataFrame,
    test: pd.DataFrame,
    k: int,
    metric: str,
    norm_mode: str,
    weight_mode: str,
) -> pd.DataFrame:
    x_ref = normalize(reference[SIPM_COLUMNS].to_numpy(), norm_mode)
    x_test = normalize(test[SIPM_COLUMNS].to_numpy(), norm_mode)
    nn = NearestNeighbors(n_neighbors=k, metric=metric)
    nn.fit(x_ref)
    distances, indices = nn.kneighbors(x_test)

    rows = []
    for test_idx, (row_distances, row_indices) in enumerate(zip(distances, indices)):
        neighbors = reference.iloc[row_indices]
        if weight_mode == "uniform" or k == 1:
            weights = np.ones(k, dtype=np.float64) / k
        elif weight_mode == "inverse":
            weights = 1.0 / np.maximum(row_distances, EPS)
            weights /= weights.sum()
        elif weight_mode == "inverse2":
            weights = 1.0 / np.maximum(row_distances, EPS) ** 2
            weights /= weights.sum()
        else:
            raise ValueError(weight_mode)

        pred_x = float(np.dot(weights, neighbors["x_cm"].to_numpy()))
        pred_z = float(np.dot(weights, neighbors["z_cm"].to_numpy()))
        rows.append(
            {
                "event_id": int(test.iloc[test_idx]["event_id"]),
                "true_x_cm": float(test.iloc[test_idx]["true_x_cm"]),
                "true_z_cm": float(test.iloc[test_idx]["true_z_cm"]),
                "pred_x_cm": pred_x,
                "pred_z_cm": pred_z,
                "nearest_run_id": int(neighbors.iloc[0]["run_id"]),
                "nearest_distance": float(row_distances[0]),
            }
        )
    out = pd.DataFrame(rows)
    out["err_x_cm"] = out["pred_x_cm"] - out["true_x_cm"]
    out["err_z_cm"] = out["pred_z_cm"] - out["true_z_cm"]
    out["err_r_cm"] = np.hypot(out["err_x_cm"], out["err_z_cm"])
    return out


def summarize(predictions: pd.DataFrame, config: dict[str, object]) -> dict[str, object]:
    return {
        **config,
        "n_events": len(predictions),
        "mean_err_x_cm": predictions["err_x_cm"].mean(),
        "sigma_err_x_cm": predictions["err_x_cm"].std(ddof=1),
        "mean_err_z_cm": predictions["err_z_cm"].mean(),
        "sigma_err_z_cm": predictions["err_z_cm"].std(ddof=1),
        "median_err_r_cm": predictions["err_r_cm"].median(),
        "p68_err_r_cm": predictions["err_r_cm"].quantile(0.68),
        "p95_err_r_cm": predictions["err_r_cm"].quantile(0.95),
    }


def main() -> None:
    args = parse_args()
    train_events = load_training_events(args.training_dir, args.macro)
    if args.max_events_per_run is not None:
        if args.max_events_per_run <= 0:
            raise ValueError("--max-events-per-run must be positive")
        train_events = (
            train_events.sort_values(["run_id", "event_id"])
            .groupby("position_id", group_keys=False)
            .head(args.max_events_per_run)
            .reset_index(drop=True)
        )
    test_events = load_test_events(args.test_dir)
    templates = (
        train_events.groupby("position_id", as_index=False)[SIPM_COLUMNS].mean()
        .merge(
            train_events[["position_id", "x_cm", "z_cm"]].drop_duplicates("position_id"),
            on="position_id",
            validate="one_to_one",
        )
    )
    templates["run_id"] = templates["position_id"]

    references = {}
    if args.reference in ("templates", "both"):
        references["templates"] = templates
    if args.reference in ("events", "both"):
        references["events"] = train_events

    ks = [1, 3, 5, 8, 12, 16, 24, 32, 48, 64]
    metrics = ["cosine", "euclidean"]
    norms = ["none", "l1", "sqrt", "sqrt_l1", "log1p"]
    weights = ["uniform", "inverse", "inverse2"]

    summary_rows = []
    best_predictions = None
    best_row = None

    for ref_name, ref_df in references.items():
        max_k = min(max(ks), len(ref_df))
        for k in [value for value in ks if value <= max_k]:
            for metric in metrics:
                for norm_mode in norms:
                    for weight_mode in weights:
                        config = {
                            "reference": ref_name,
                            "k": k,
                            "metric": metric,
                            "normalization": norm_mode,
                            "weighting": weight_mode,
                        }
                        predictions = predict_knn(ref_df, test_events, k, metric, norm_mode, weight_mode)
                        row = summarize(predictions, config)
                        summary_rows.append(row)
                        if best_row is None or row["p68_err_r_cm"] < best_row["p68_err_r_cm"]:
                            best_row = row
                            best_predictions = predictions.assign(**config)

    results = pd.DataFrame(summary_rows).sort_values("p68_err_r_cm").reset_index(drop=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    if best_predictions is not None:
        best_predictions.to_csv(args.predictions_output, index=False)

    print(f"Wrote sweep results to {args.output}")
    print(f"Wrote best predictions to {args.predictions_output}")
    print(results.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
