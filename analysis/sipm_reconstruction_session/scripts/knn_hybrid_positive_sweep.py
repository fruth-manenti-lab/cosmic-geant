#!/usr/bin/env python3
"""Positive-quadrant kNN sweep for the 16 face + 16 fiber hybrid layout."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.neighbors import NearestNeighbors
except ImportError:
    NearestNeighbors = None


RUN_FILE_RE = re.compile(r"MUON-run(?P<run>\d+)_sipm_counts_by_event\.csv$")
FACE_COPIES = tuple(range(16))
FIBER_COPIES = tuple(range(100, 116))
SIPM_COPIES = FACE_COPIES + FIBER_COPIES
SIPM_COLUMNS = [f"sipm_{copy}" for copy in SIPM_COPIES]
FEATURE_GROUPS = {
    "all": SIPM_COLUMNS,
    "face": [f"sipm_{copy}" for copy in FACE_COPIES],
    "fiber": [f"sipm_{copy}" for copy in FIBER_COPIES],
}
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep kNN settings for hybrid positive-quadrant data.")
    parser.add_argument("--training-dir", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predictions-output", type=Path, required=True)
    parser.add_argument("--feature-groups", default="all,face,fiber")
    parser.add_argument("--ks", default="1,3,5,8,12,16,24,32")
    parser.add_argument("--metrics", default="euclidean")
    parser.add_argument("--normalizations", default="l1,sqrt_l1")
    parser.add_argument("--weightings", default="uniform,inverse,inverse2")
    return parser.parse_args()


def parse_csv_arg(value: str, cast=str) -> list:
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


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


def load_events_with_truth(path: Path) -> pd.DataFrame:
    manifest_path = path / "test_manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    manifest = pd.read_csv(manifest_path)
    labels = manifest[["run_id", "true_x_cm", "true_z_cm"]].copy()
    labels = labels.rename(columns={"true_x_cm": "x_cm", "true_z_cm": "z_cm"})
    labels["position_id"] = manifest.get("source_index", manifest["run_id"]).astype(int)
    events = load_event_folder(path)
    return events.merge(labels, on="run_id", validate="one_to_one")


def load_test_events(path: Path) -> pd.DataFrame:
    events = load_events_with_truth(path)
    events["true_x_cm"] = events["x_cm"]
    events["true_z_cm"] = events["z_cm"]
    return events


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


def kneighbors_numpy(
    x_ref: np.ndarray,
    x_test: np.ndarray,
    k: int,
    metric: str,
    chunk_size: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    if metric not in {"euclidean", "l2"}:
        raise ImportError("scikit-learn is required for non-Euclidean metrics.")
    all_distances = np.empty((len(x_test), k), dtype=np.float64)
    all_indices = np.empty((len(x_test), k), dtype=np.int64)
    ref_norm = np.sum(x_ref * x_ref, axis=1)
    for start in range(0, len(x_test), chunk_size):
        stop = min(start + chunk_size, len(x_test))
        test_chunk = x_test[start:stop]
        dist2 = (
            np.sum(test_chunk * test_chunk, axis=1, keepdims=True)
            + ref_norm[None, :]
            - 2.0 * test_chunk @ x_ref.T
        )
        np.maximum(dist2, 0.0, out=dist2)
        unsorted = np.argpartition(dist2, kth=k - 1, axis=1)[:, :k]
        row_ids = np.arange(stop - start)[:, None]
        order = np.argsort(dist2[row_ids, unsorted], axis=1)
        sorted_indices = unsorted[row_ids, order]
        all_indices[start:stop] = sorted_indices
        all_distances[start:stop] = np.sqrt(dist2[row_ids, sorted_indices])
    return all_distances, all_indices


def predict_knn(
    reference: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
    k: int,
    metric: str,
    norm_mode: str,
    weight_mode: str,
) -> pd.DataFrame:
    x_ref = normalize(reference[feature_columns].to_numpy(), norm_mode)
    x_test = normalize(test[feature_columns].to_numpy(), norm_mode)
    if NearestNeighbors is None:
        distances, indices = kneighbors_numpy(x_ref, x_test, k, metric)
    else:
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
        true_x = float(test.iloc[test_idx]["true_x_cm"])
        true_z = float(test.iloc[test_idx]["true_z_cm"])
        err_x = pred_x - true_x
        err_z = pred_z - true_z
        rows.append(
            {
                "event_id": int(test.iloc[test_idx]["event_id"]),
                "true_x_cm": true_x,
                "true_z_cm": true_z,
                "pred_x_cm": pred_x,
                "pred_z_cm": pred_z,
                "err_x_cm": err_x,
                "err_z_cm": err_z,
                "err_r_cm": float(math.hypot(err_x, err_z)),
                "nearest_position_id": int(neighbors.iloc[0]["position_id"]),
                "nearest_event_id": int(neighbors.iloc[0]["event_id"]),
                "nearest_distance": float(row_distances[0]),
            }
        )
    return pd.DataFrame(rows)


def summarize(predictions: pd.DataFrame) -> dict[str, float]:
    return {
        "mean_err_r_cm": float(predictions["err_r_cm"].mean()),
        "median_err_r_cm": float(predictions["err_r_cm"].median()),
        "p68_err_r_cm": float(predictions["err_r_cm"].quantile(0.68)),
        "p90_err_r_cm": float(predictions["err_r_cm"].quantile(0.90)),
        "p95_err_r_cm": float(predictions["err_r_cm"].quantile(0.95)),
        "rmse_err_r_cm": float(np.sqrt(np.mean(predictions["err_r_cm"] ** 2))),
        "mean_err_x_cm": float(predictions["err_x_cm"].mean()),
        "sigma_err_x_cm": float(predictions["err_x_cm"].std(ddof=1)),
        "mean_err_z_cm": float(predictions["err_z_cm"].mean()),
        "sigma_err_z_cm": float(predictions["err_z_cm"].std(ddof=1)),
    }


def main() -> None:
    args = parse_args()
    training = load_events_with_truth(args.training_dir)
    test = load_test_events(args.test_dir)
    feature_groups = parse_csv_arg(args.feature_groups)
    ks = parse_csv_arg(args.ks, int)
    metrics = parse_csv_arg(args.metrics)
    normalizations = parse_csv_arg(args.normalizations)
    weightings = parse_csv_arg(args.weightings)

    rows = []
    best_predictions = None
    best_row = None
    for group in feature_groups:
        feature_columns = FEATURE_GROUPS[group]
        for metric in metrics:
            for normalization in normalizations:
                for weighting in weightings:
                    for k in [value for value in ks if value <= len(training)]:
                        predictions = predict_knn(
                            training,
                            test,
                            feature_columns,
                            k,
                            metric,
                            normalization,
                            weighting,
                        )
                        row = summarize(predictions)
                        row.update(
                            {
                                "feature_group": group,
                                "n_features": len(feature_columns),
                                "k": k,
                                "metric": metric,
                                "normalization": normalization,
                                "weighting": weighting,
                                "training_events": len(training),
                                "training_positions": training["position_id"].nunique(),
                                "test_events": len(test),
                            }
                        )
                        rows.append(row)
                        if best_row is None or row["p68_err_r_cm"] < best_row["p68_err_r_cm"]:
                            best_row = row
                            best_predictions = predictions.assign(**row)

    results = pd.DataFrame(rows).sort_values(["p68_err_r_cm", "p95_err_r_cm"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    if best_predictions is None:
        raise RuntimeError("No configurations evaluated.")
    best_predictions.to_csv(args.predictions_output, index=False)

    print(f"Training events: {len(training)}")
    print(f"Training positions: {training['position_id'].nunique()}")
    print(f"Test events: {len(test)}")
    print(f"Wrote sweep results to {args.output}")
    print(f"Wrote best predictions to {args.predictions_output}")
    print(results.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
