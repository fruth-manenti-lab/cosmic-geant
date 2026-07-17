#!/usr/bin/env python3
"""Evaluate simple SiPM-count centroid localization baselines."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


RUN_FILE_RE = re.compile(r"MUON-run(?P<run>\d+)_sipm_counts_by_event\.csv$")
X_ROW_COPIES = tuple(range(100, 116))
Z_ROW_COPIES = tuple(range(300, 316))
SIPM_COPIES = X_ROW_COPIES + Z_ROW_COPIES
SIPM_COLUMNS = [f"sipm_{copy}" for copy in SIPM_COPIES]

LANE_START_CM = -46.875
LANE_PITCH_CM = 6.25
SIPM_EDGE_CM = 51.035
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate centroid SiPM localization.")
    parser.add_argument("--training-dir", type=Path, default=Path("analysis/training_scan_data_1024"))
    parser.add_argument("--test-dir", type=Path, default=Path("analysis/test_scan_data_1000"))
    parser.add_argument("--macro", type=Path, default=Path("macros/muon_scan.mac"))
    parser.add_argument("--summary-output", type=Path, default=Path("analysis/centroid_sipm_summary.csv"))
    parser.add_argument("--predictions-output", type=Path, default=Path("analysis/centroid_sipm_predictions.csv"))
    return parser.parse_args()


def parse_muon_scan_positions(path: Path) -> pd.DataFrame:
    rows = []
    for line in path.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) == 5 and parts[0] == "/gps/position":
            x_cm, _, z_cm = map(float, parts[1:4])
            rows.append({"run_id": len(rows), "true_x_cm": x_cm, "true_z_cm": z_cm})
    if not rows:
        raise ValueError(f"No /gps/position lines found in {path}")
    return pd.DataFrame(rows)


def load_training_events(path: Path, labels: pd.DataFrame) -> pd.DataFrame:
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
        raise FileNotFoundError(f"No training event CSVs found in {path}")
    events = pd.concat(frames, ignore_index=True)
    manifest_path = path / "test_manifest.csv"
    if manifest_path.exists():
        manifest = pd.read_csv(manifest_path)
        manifest_labels = manifest[["run_id", "true_x_cm", "true_z_cm"]].copy()
        return events.merge(manifest_labels, on="run_id", validate="one_to_one")
    return events.merge(labels, on="run_id", validate="many_to_one")


def load_test_events(path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(path / "test_manifest.csv")
    rows = []
    for _, meta in manifest.sort_values("event_id").iterrows():
        df = pd.read_csv(path / meta["output_file"])
        if len(df) != 1:
            raise ValueError(f"Expected one row in {meta['output_file']}, found {len(df)}")
        row = df.iloc[0].to_dict()
        row["event_id"] = int(meta["event_id"])
        row["run_id"] = int(meta["run_id"])
        row["true_x_cm"] = float(meta["true_x_cm"])
        row["true_z_cm"] = float(meta["true_z_cm"])
        rows.append(row)
    return pd.DataFrame(rows).sort_values("event_id").reset_index(drop=True)


def lane_coordinate(copy_number: int) -> float:
    if copy_number in X_ROW_COPIES:
        return LANE_START_CM + (copy_number - 100) * LANE_PITCH_CM
    if copy_number in Z_ROW_COPIES:
        return LANE_START_CM + (copy_number - 300) * LANE_PITCH_CM
    raise ValueError(copy_number)


def sipm_positions() -> pd.DataFrame:
    rows = []
    for copy in X_ROW_COPIES:
        rows.append({"copy": copy, "x_cm": lane_coordinate(copy), "z_cm": SIPM_EDGE_CM})
    for copy in Z_ROW_COPIES:
        rows.append({"copy": copy, "x_cm": SIPM_EDGE_CM, "z_cm": lane_coordinate(copy)})
    return pd.DataFrame(rows)


def add_centroid_predictions(events: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = events.copy()
    counts = out[SIPM_COLUMNS].to_numpy(dtype=np.float64)
    positions = sipm_positions()
    pos_x = positions["x_cm"].to_numpy(dtype=np.float64)
    pos_z = positions["z_cm"].to_numpy(dtype=np.float64)
    total = np.maximum(counts.sum(axis=1), EPS)

    out["pred_x_all_centroid_cm"] = counts.dot(pos_x) / total
    out["pred_z_all_centroid_cm"] = counts.dot(pos_z) / total

    x_counts = out[[f"sipm_{copy}" for copy in X_ROW_COPIES]].to_numpy(dtype=np.float64)
    z_counts = out[[f"sipm_{copy}" for copy in Z_ROW_COPIES]].to_numpy(dtype=np.float64)
    x_lanes = np.array([lane_coordinate(copy) for copy in X_ROW_COPIES])
    z_lanes = np.array([lane_coordinate(copy) for copy in Z_ROW_COPIES])
    out["pred_x_projection_cm"] = x_counts.dot(x_lanes) / np.maximum(x_counts.sum(axis=1), EPS)
    out["pred_z_projection_cm"] = z_counts.dot(z_lanes) / np.maximum(z_counts.sum(axis=1), EPS)

    out["dataset"] = dataset
    return out


def summarize(predictions: pd.DataFrame, method: str, pred_x: str, pred_z: str) -> dict[str, object]:
    err_x = predictions[pred_x] - predictions["true_x_cm"]
    err_z = predictions[pred_z] - predictions["true_z_cm"]
    err_r = np.hypot(err_x, err_z)
    return {
        "dataset": predictions["dataset"].iloc[0],
        "method": method,
        "n_events": len(predictions),
        "mean_err_x_cm": err_x.mean(),
        "sigma_err_x_cm": err_x.std(ddof=1),
        "mean_err_z_cm": err_z.mean(),
        "sigma_err_z_cm": err_z.std(ddof=1),
        "median_err_r_cm": err_r.median(),
        "p68_err_r_cm": err_r.quantile(0.68),
        "p95_err_r_cm": err_r.quantile(0.95),
    }


def main() -> None:
    args = parse_args()
    labels = parse_muon_scan_positions(args.macro)
    training = add_centroid_predictions(load_training_events(args.training_dir, labels), "training")
    test = add_centroid_predictions(load_test_events(args.test_dir), "test")
    predictions = pd.concat([training, test], ignore_index=True)

    summary = pd.DataFrame(
        [
            summarize(training, "all_32_2d_centroid", "pred_x_all_centroid_cm", "pred_z_all_centroid_cm"),
            summarize(training, "projection_centroid", "pred_x_projection_cm", "pred_z_projection_cm"),
            summarize(test, "all_32_2d_centroid", "pred_x_all_centroid_cm", "pred_z_all_centroid_cm"),
            summarize(test, "projection_centroid", "pred_x_projection_cm", "pred_z_projection_cm"),
        ]
    )

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    predictions.to_csv(args.predictions_output, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote {args.summary_output}")
    print(f"Wrote {args.predictions_output}")


if __name__ == "__main__":
    main()
