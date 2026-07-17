#!/usr/bin/env python3
"""kNN reconstruction for positive-quadrant training with virtual quadrants.

The double-ended SiPM geometry is symmetric under x/z reflections. Training can
therefore be simulated only in the positive quadrant, then expanded in memory by
reflecting positions and permuting SiPM copy-number columns. The reference set
uses individual training events, not averaged position templates.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.neighbors import NearestNeighbors
except ImportError:
    NearestNeighbors = None


RUN_FILE_RE = re.compile(r"MUON-run(?P<run>\d+)_sipm_counts_by_event\.csv$")
SIPM_COPIES = (
    tuple(range(100, 116))
    + tuple(range(200, 216))
    + tuple(range(300, 316))
    + tuple(range(400, 416))
)
SIPM_COLUMNS = [f"sipm_{copy}" for copy in SIPM_COPIES]
READOUT_COLUMNS = {
    "all": SIPM_COLUMNS,
    "z": [f"sipm_{copy}" for copy in tuple(range(100, 116)) + tuple(range(200, 216))],
    "x": [f"sipm_{copy}" for copy in tuple(range(300, 316)) + tuple(range(400, 416))],
}
EPS = 1e-12


QUADRANTS = [
    ("Q++", 1, 1),
    ("Q-+", -1, 1),
    ("Q+-", 1, -1),
    ("Q--", -1, -1),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep kNN settings with virtual quadrant-expanded double-ended SiPM templates."
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
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Sweep summary CSV path.",
    )
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
    parser.add_argument(
        "--readout-axis",
        choices=sorted(READOUT_COLUMNS),
        default="all",
        help=(
            "SiPM channels to use: all sides, only +x/-x side SiPMs, or only "
            "+z/-z side SiPMs."
        ),
    )
    parser.add_argument("--ks", default="1,3,5,8,12,16,24,32")
    parser.add_argument("--metrics", default="euclidean")
    parser.add_argument("--normalizations", default="l1")
    parser.add_argument("--weightings", default="uniform,inverse,inverse2")
    parser.add_argument(
        "--ratio-features",
        default="none",
        help=(
            "Comma-separated ratio feature modes to append after count "
            "normalization: none, signed, or fraction. signed=(pos-neg)/(pos+neg); "
            "fraction=pos/(pos+neg)."
        ),
    )
    parser.add_argument(
        "--ratio-scales",
        default="1.0",
        help="Comma-separated scale factors applied to appended ratio features.",
    )
    parser.add_argument(
        "--limit-grid-per-axis",
        type=int,
        default=None,
        help="Use an evenly spread NxN subset of positive-quadrant training positions.",
    )
    parser.add_argument(
        "--selected-positions-output",
        type=Path,
        default=None,
        help="Optional CSV path recording which training positions were retained.",
    )
    return parser.parse_args()


def parse_csv_arg(value: str, cast=str) -> list:
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def mirror_index(index: int) -> int:
    return 15 - index


def map_copy(copy: int, x_sign: int, z_sign: int) -> int:
    if 100 <= copy <= 115:
        index = copy - 100
        if x_sign < 0:
            index = mirror_index(index)
        return (200 if z_sign < 0 else 100) + index
    if 200 <= copy <= 215:
        index = copy - 200
        if x_sign < 0:
            index = mirror_index(index)
        return (100 if z_sign < 0 else 200) + index
    if 300 <= copy <= 315:
        index = copy - 300
        if z_sign < 0:
            index = mirror_index(index)
        return (400 if x_sign < 0 else 300) + index
    if 400 <= copy <= 415:
        index = copy - 400
        if z_sign < 0:
            index = mirror_index(index)
        return (300 if x_sign < 0 else 400) + index
    raise ValueError(f"Unsupported SiPM copy number: {copy}")


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
    if "source_index" in manifest.columns:
        labels["position_id"] = manifest["source_index"].astype(int)
    else:
        labels["position_id"] = labels["run_id"].astype(int)
    events = load_event_folder(path)
    return events.merge(labels, on="run_id", validate="one_to_one")


def load_test_events(path: Path) -> pd.DataFrame:
    events = load_events_with_truth(path)
    events["true_x_cm"] = events["x_cm"]
    events["true_z_cm"] = events["z_cm"]
    return events


def select_even_position_subset(
    training_events: pd.DataFrame,
    points_per_axis: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if points_per_axis <= 0:
        raise ValueError("--limit-grid-per-axis must be positive")

    positions = (
        training_events[["position_id", "x_cm", "z_cm"]]
        .drop_duplicates("position_id")
        .copy()
    )
    x_values = np.sort(positions["x_cm"].unique())
    z_values = np.sort(positions["z_cm"].unique())
    x_step = np.median(np.diff(x_values)) if len(x_values) > 1 else 0.0
    z_step = np.median(np.diff(z_values)) if len(z_values) > 1 else 0.0
    x_min = float(x_values.min() - x_step / 2.0)
    x_max = float(x_values.max() + x_step / 2.0)
    z_min = float(z_values.min() - z_step / 2.0)
    z_max = float(z_values.max() + z_step / 2.0)
    x_bin_width = (x_max - x_min) / points_per_axis
    z_bin_width = (z_max - z_min) / points_per_axis
    x_targets = x_min + x_bin_width * (np.arange(points_per_axis) + 0.5)
    z_targets = z_min + z_bin_width * (np.arange(points_per_axis) + 0.5)

    selected_rows = []
    selected_ids = set()
    for z_target in z_targets:
        z_value = positions.loc[(positions["z_cm"] - z_target).abs().idxmin(), "z_cm"]
        z_slice = positions.loc[np.isclose(positions["z_cm"], z_value)].copy()
        for x_target in x_targets:
            idx = (z_slice["x_cm"] - x_target).abs().idxmin()
            row = z_slice.loc[idx]
            position_id = int(row["position_id"])
            selected_ids.add(position_id)
            selected_rows.append(
                {
                    "position_id": position_id,
                    "x_cm": float(row["x_cm"]),
                    "z_cm": float(row["z_cm"]),
                    "target_x_cm": float(x_target),
                    "target_z_cm": float(z_target),
                }
            )

    selected = pd.DataFrame(selected_rows).drop_duplicates("position_id")
    expected = points_per_axis * points_per_axis
    if len(selected) != expected:
        raise RuntimeError(f"Expected {expected} selected positions, got {len(selected)}")

    filtered = training_events.loc[training_events["position_id"].isin(selected_ids)].copy()
    return filtered.reset_index(drop=True), selected.sort_values(["z_cm", "x_cm"]).reset_index(drop=True)


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


def ratio_pairs(readout_axis: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    if readout_axis in {"all", "z"}:
        pairs.extend(
            (f"sipm_{100 + index}", f"sipm_{200 + index}", f"z_ratio_{index}")
            for index in range(16)
        )
    if readout_axis in {"all", "x"}:
        pairs.extend(
            (f"sipm_{300 + index}", f"sipm_{400 + index}", f"x_ratio_{index}")
            for index in range(16)
        )
    return pairs


def ratio_matrix(df: pd.DataFrame, readout_axis: str, mode: str, scale: float) -> np.ndarray:
    if mode == "none":
        return np.empty((len(df), 0), dtype=np.float64)
    columns = []
    for positive_col, negative_col, _ in ratio_pairs(readout_axis):
        positive = df[positive_col].to_numpy(dtype=np.float64)
        negative = df[negative_col].to_numpy(dtype=np.float64)
        total = positive + negative
        if mode == "signed":
            ratio = np.divide(
                positive - negative,
                np.maximum(total, EPS),
                out=np.zeros_like(total, dtype=np.float64),
                where=total > 0.0,
            )
        elif mode == "fraction":
            ratio = np.divide(
                positive,
                np.maximum(total, EPS),
                out=np.full_like(total, 0.5, dtype=np.float64),
                where=total > 0.0,
            )
        else:
            raise ValueError(mode)
        columns.append(ratio * scale)
    return np.column_stack(columns) if columns else np.empty((len(df), 0), dtype=np.float64)


def build_feature_matrix(
    df: pd.DataFrame,
    feature_columns: list[str],
    readout_axis: str,
    norm_mode: str,
    ratio_mode: str,
    ratio_scale: float,
) -> np.ndarray:
    counts = normalize(df[feature_columns].to_numpy(), norm_mode)
    ratios = ratio_matrix(df, readout_axis, ratio_mode, ratio_scale)
    if ratios.shape[1] == 0:
        return counts
    return np.hstack([counts, ratios])


def kneighbors_numpy(
    x_ref: np.ndarray,
    x_test: np.ndarray,
    k: int,
    metric: str,
    chunk_size: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    if metric not in {"euclidean", "l2"}:
        raise ImportError(
            "scikit-learn is required for non-Euclidean metrics; install sklearn "
            "or use --metrics euclidean."
        )

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
    feature_columns: list[str],
    readout_axis: str,
    k: int,
    metric: str,
    norm_mode: str,
    weight_mode: str,
    ratio_mode: str,
    ratio_scale: float,
) -> pd.DataFrame:
    x_ref = build_feature_matrix(
        reference,
        feature_columns,
        readout_axis,
        norm_mode,
        ratio_mode,
        ratio_scale,
    )
    x_test = build_feature_matrix(
        test,
        feature_columns,
        readout_axis,
        norm_mode,
        ratio_mode,
        ratio_scale,
    )
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
        rows.append(
            {
                "event_id": int(test.iloc[test_idx]["event_id"]),
                "true_x_cm": float(test.iloc[test_idx]["true_x_cm"]),
                "true_z_cm": float(test.iloc[test_idx]["true_z_cm"]),
                "pred_x_cm": pred_x,
                "pred_z_cm": pred_z,
                "nearest_position_id": str(neighbors.iloc[0]["position_id"]),
                "nearest_base_position_id": int(neighbors.iloc[0].get("base_position_id", neighbors.iloc[0]["run_id"])),
                "nearest_base_event_id": int(neighbors.iloc[0].get("base_event_id", neighbors.iloc[0]["event_id"])),
                "nearest_virtual_quadrant": str(neighbors.iloc[0].get("virtual_quadrant", "Q++")),
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
        "mean_err_r_cm": predictions["err_r_cm"].mean(),
        "median_err_r_cm": predictions["err_r_cm"].median(),
        "p68_err_r_cm": predictions["err_r_cm"].quantile(0.68),
        "p95_err_r_cm": predictions["err_r_cm"].quantile(0.95),
        "mean_err_x_cm": predictions["err_x_cm"].mean(),
        "sigma_err_x_cm": predictions["err_x_cm"].std(ddof=1),
        "mean_err_z_cm": predictions["err_z_cm"].mean(),
        "sigma_err_z_cm": predictions["err_z_cm"].std(ddof=1),
    }


def main() -> None:
    args = parse_args()
    training_events = load_events_with_truth(args.training_dir)
    if args.limit_grid_per_axis is not None:
        training_events, selected_positions = select_even_position_subset(
            training_events,
            args.limit_grid_per_axis,
        )
        if args.selected_positions_output is not None:
            args.selected_positions_output.parent.mkdir(parents=True, exist_ok=True)
            selected_positions.to_csv(args.selected_positions_output, index=False)
    test_events = load_test_events(args.test_dir)
    reference = training_events if args.no_virtual_quadrants else virtualize_reference(training_events)
    feature_columns = READOUT_COLUMNS[args.readout_axis]
    n_base_positions = training_events["position_id"].nunique()

    ks = parse_csv_arg(args.ks, int)
    metrics = parse_csv_arg(args.metrics)
    norms = parse_csv_arg(args.normalizations)
    weights = parse_csv_arg(args.weightings)
    ratio_modes = parse_csv_arg(args.ratio_features)
    ratio_scales = parse_csv_arg(args.ratio_scales, float)

    summary_rows = []
    best_predictions = None
    best_row = None
    for k in [value for value in ks if value <= len(reference)]:
        for metric in metrics:
            for norm_mode in norms:
                for weight_mode in weights:
                    for ratio_mode in ratio_modes:
                        scales = [0.0] if ratio_mode == "none" else ratio_scales
                        for ratio_scale in scales:
                            n_ratio_features = (
                                0 if ratio_mode == "none" else len(ratio_pairs(args.readout_axis))
                            )
                            config = {
                                "reference": "events",
                                "virtual_quadrants": not args.no_virtual_quadrants,
                                "readout_axis": args.readout_axis,
                                "n_readout_channels": len(feature_columns),
                                "ratio_features": ratio_mode,
                                "ratio_scale": ratio_scale,
                                "n_ratio_features": n_ratio_features,
                                "n_features": len(feature_columns) + n_ratio_features,
                                "k": k,
                                "metric": metric,
                                "normalization": norm_mode,
                                "weighting": weight_mode,
                                "n_reference": len(reference),
                                "n_base_positions": n_base_positions,
                            }
                            predictions = predict_knn(
                                reference,
                                test_events,
                                feature_columns,
                                args.readout_axis,
                                k,
                                metric,
                                norm_mode,
                                weight_mode,
                                ratio_mode,
                                ratio_scale,
                            )
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

    print(f"Training events: {len(training_events)}")
    print(f"Base positions: {n_base_positions}")
    print(f"Readout axis: {args.readout_axis} ({len(feature_columns)} channels)")
    print(f"Reference rows used by kNN: {len(reference)}")
    print(f"Test events: {len(test_events)}")
    print(f"Wrote sweep results to {args.output}")
    print(f"Wrote best predictions to {args.predictions_output}")
    print(results.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
