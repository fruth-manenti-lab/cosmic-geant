#!/usr/bin/env python3
"""kNN reconstruction for the 1 m face-mount diagonal SiPM layout.

The face-mount layout has 32 copy-numbered SiPMs arranged symmetrically under
x/z reflections. Positive-quadrant training events can be expanded in memory by
reflecting the truth position and permuting SiPM copy-number columns using the
same construction as the GDML preview/mapping plot.
"""

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
SIPM_COPIES = tuple(range(32))
SIPM_COLUMNS = [f"sipm_{copy}" for copy in SIPM_COPIES]
EPS = 1e-12

SLAB_MM = 1000.0
PAIR_OFFSET_MM = 59.0
COORD_TOL_MM = 1e-3

QUADRANTS = [
    ("Q++", 1, 1),
    ("Q-+", -1, 1),
    ("Q+-", 1, -1),
    ("Q--", -1, -1),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep kNN settings with virtual-quadrant face-mount SiPM templates."
    )
    parser.add_argument(
        "--training-dir",
        type=Path,
        required=True,
        help="Converted positive-quadrant training directory with test_manifest.csv.",
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        required=True,
        help="Converted positive-quadrant random test directory with test_manifest.csv.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Sweep summary CSV path.")
    parser.add_argument(
        "--predictions-output",
        type=Path,
        required=True,
        help="Best-configuration predictions CSV path.",
    )
    parser.add_argument(
        "--no-virtual-quadrants",
        action="store_true",
        help="Disable virtual quadrant expansion for a direct positive-only comparison.",
    )
    parser.add_argument("--ks", default="1,3,5,8,12,16,24,32")
    parser.add_argument("--metrics", default="euclidean")
    parser.add_argument("--normalizations", default="l1")
    parser.add_argument("--weightings", default="uniform,inverse,inverse2")
    return parser.parse_args()


def parse_csv_arg(value: str, cast=str) -> list:
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def local_diagonal_direction(xc: float, zc: float) -> tuple[float, float]:
    qx_min = 0.0 if xc > 0 else -SLAB_MM / 2.0
    qz_min = 0.0 if zc > 0 else -SLAB_MM / 2.0
    local_x_index = 0 if xc < qx_min + SLAB_MM / 4.0 else 1
    local_z_index = 0 if zc < qz_min + SLAB_MM / 4.0 else 1
    if local_x_index == local_z_index:
        return (1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0))
    return (1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0))


def build_sipm_positions() -> dict[int, tuple[float, float]]:
    positions: dict[int, tuple[float, float]] = {}
    sipm_id = 0
    centers = [-375.0, -125.0, 125.0, 375.0]
    for zc in centers:
        for xc in centers:
            dx, dz = local_diagonal_direction(xc, zc)
            px = -dz
            pz = dx
            for side in [-1, 1]:
                positions[sipm_id] = (
                    xc + side * PAIR_OFFSET_MM * px,
                    zc + side * PAIR_OFFSET_MM * pz,
                )
                sipm_id += 1
    return positions


SIPM_POSITIONS = build_sipm_positions()


def find_sipm_id(x: float, z: float) -> int:
    best_id = min(
        SIPM_POSITIONS,
        key=lambda sid: math.hypot(SIPM_POSITIONS[sid][0] - x, SIPM_POSITIONS[sid][1] - z),
    )
    best_x, best_z = SIPM_POSITIONS[best_id]
    if math.hypot(best_x - x, best_z - z) > COORD_TOL_MM:
        raise RuntimeError(f"No SiPM found at reflected coordinate ({x}, {z})")
    return best_id


def map_copy(copy: int, x_sign: int, z_sign: int) -> int:
    source_x, source_z = SIPM_POSITIONS[copy]
    return find_sipm_id(x_sign * source_x, z_sign * source_z)


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


def reflect_features(df: pd.DataFrame, x_sign: int, z_sign: int) -> pd.DataFrame:
    out = df.copy()
    out.loc[:, SIPM_COLUMNS] = 0.0
    for source_copy in SIPM_COPIES:
        target_copy = map_copy(source_copy, x_sign, z_sign)
        out[f"sipm_{target_copy}"] = df[f"sipm_{source_copy}"].to_numpy()
    out["x_cm"] = x_sign * df["x_cm"].abs()
    out["z_cm"] = z_sign * df["z_cm"].abs()
    return out


def virtualize_reference(reference: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for quadrant, x_sign, z_sign in QUADRANTS:
        reflected = reflect_features(reference, x_sign, z_sign)
        reflected["virtual_quadrant"] = quadrant
        reflected["base_position_id"] = reference["position_id"].to_numpy()
        reflected["base_event_id"] = reference["event_id"].to_numpy()
        reflected["position_id"] = [
            f"{quadrant}:pos{int(position_id)}:event{int(event_id)}"
            for position_id, event_id in zip(reference["position_id"], reference["event_id"])
        ]
        frames.append(reflected)
    return pd.concat(frames, ignore_index=True)


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
        unsorted_dist2 = dist2[row_ids, unsorted]
        order = np.argsort(unsorted_dist2, axis=1)
        sorted_indices = unsorted[row_ids, order]
        all_indices[start:stop] = sorted_indices
        all_distances[start:stop] = np.sqrt(dist2[row_ids, sorted_indices])

    return all_distances, all_indices


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
                "nearest_position_id": str(neighbors.iloc[0]["position_id"]),
                "nearest_base_position_id": int(
                    neighbors.iloc[0].get("base_position_id", neighbors.iloc[0]["run_id"])
                ),
                "nearest_base_event_id": int(
                    neighbors.iloc[0].get("base_event_id", neighbors.iloc[0]["event_id"])
                ),
                "nearest_virtual_quadrant": str(neighbors.iloc[0].get("virtual_quadrant", "Q++")),
                "nearest_distance": float(row_distances[0]),
                "k": k,
                "metric": metric,
                "normalization": norm_mode,
                "weighting": weight_mode,
            }
        )
    return pd.DataFrame(rows)


def summarize(predictions: pd.DataFrame) -> dict[str, float]:
    dx = predictions["pred_x_cm"] - predictions["true_x_cm"]
    dz = predictions["pred_z_cm"] - predictions["true_z_cm"]
    radius = np.sqrt(dx * dx + dz * dz)
    return {
        "mae_x_cm": float(dx.abs().mean()),
        "mae_z_cm": float(dz.abs().mean()),
        "mae_radius_cm": float(radius.mean()),
        "median_radius_cm": float(radius.median()),
        "p90_radius_cm": float(radius.quantile(0.90)),
        "rmse_radius_cm": float(np.sqrt(np.mean(radius * radius))),
        "bias_x_cm": float(dx.mean()),
        "bias_z_cm": float(dz.mean()),
    }


def main() -> None:
    args = parse_args()
    ks = parse_csv_arg(args.ks, int)
    metrics = parse_csv_arg(args.metrics)
    normalizations = parse_csv_arg(args.normalizations)
    weightings = parse_csv_arg(args.weightings)

    training = load_events_with_truth(args.training_dir)
    test = load_test_events(args.test_dir)
    reference = training if args.no_virtual_quadrants else virtualize_reference(training)

    rows = []
    best_predictions = None
    best_score = math.inf
    for metric in metrics:
        for normalization in normalizations:
            for weighting in weightings:
                for k in ks:
                    if k > len(reference):
                        continue
                    predictions = predict_knn(reference, test, k, metric, normalization, weighting)
                    summary = summarize(predictions)
                    summary.update(
                        {
                            "k": k,
                            "metric": metric,
                            "normalization": normalization,
                            "weighting": weighting,
                            "virtual_quadrants": not args.no_virtual_quadrants,
                            "training_events": len(training),
                            "reference_events": len(reference),
                            "test_events": len(test),
                        }
                    )
                    rows.append(summary)
                    score = summary["mae_radius_cm"]
                    if score < best_score:
                        best_score = score
                        best_predictions = predictions

    results = pd.DataFrame(rows).sort_values(
        ["mae_radius_cm", "p90_radius_cm", "median_radius_cm"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    if best_predictions is None:
        raise RuntimeError("No KNN configurations were evaluated.")
    best_predictions.to_csv(args.predictions_output, index=False)

    print(f"Training events: {len(training)}")
    print(f"Reference events: {len(reference)}")
    print(f"Test events: {len(test)}")
    print(f"Wrote sweep results to {args.output}")
    print(f"Wrote best predictions to {args.predictions_output}")
    print(results.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
