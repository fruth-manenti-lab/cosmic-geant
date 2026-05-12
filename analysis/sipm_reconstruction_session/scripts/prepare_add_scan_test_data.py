#!/usr/bin/env python3
"""Prepare ADD_SCAN one-run test data from Geant4 MT CSV shards.

ADD_SCAN writes many source positions inside one Geant4 run. The hit ntuple is
split by worker thread, and the source ntuple records one truth row per event.
This script merges the shards, counts unique OpWLS photons per event and SiPM,
and writes the same per-event format used by the reconstruction scripts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SIPM_COPY_PRESETS = {
    "standard": tuple(range(100, 116)) + tuple(range(300, 316)),
    "facemount": tuple(range(32)),
    "double-ended": (
        tuple(range(100, 116))
        + tuple(range(200, 216))
        + tuple(range(300, 316))
        + tuple(range(400, 416))
    ),
}
HIT_REQUIRED_COLUMNS = {"EventID", "TrackID", "Volume", "Copynumber", "ProcessName"}
SOURCE_REQUIRED_COLUMNS = {"EventID", "SourceIndex", "SourceCycle", "SourceX", "SourceY", "SourceZ"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert ADD_SCAN one-run output into per-event SiPM count files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("new_build/output"),
        help="Directory containing MUON-run0_nt_hits_t*.csv and MUON-run0_nt_source_t*.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/sipm_reconstruction_session/test_scan_data_add_scan"),
        help="Directory for per-event SiPM count CSVs and test_manifest.csv.",
    )
    parser.add_argument(
        "--process-name",
        default="OpWLS",
        help="Hit ProcessName to count, or 'any' to count all SiPM sensitive-detector hits.",
    )
    parser.add_argument(
        "--sipm-preset",
        choices=sorted(SIPM_COPY_PRESETS),
        default="standard",
        help="SiPM copy-number set to convert.",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def wcsv_columns(path: Path) -> list[str]:
    columns: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#column "):
                columns.append(line.strip().split()[-1])
            elif not line.startswith("#"):
                break
    if not columns:
        raise ValueError(f"No #column metadata found in {path}")
    return columns


def read_wcsv(path: Path, required: set[str]) -> pd.DataFrame:
    columns = wcsv_columns(path)
    missing = required.difference(columns)
    if missing:
        raise KeyError(f"{path} is missing columns: {sorted(missing)}")
    return pd.read_csv(path, comment="#", names=columns, usecols=[c for c in columns if c in required])


def load_source_truth(input_dir: Path) -> pd.DataFrame:
    paths = sorted(input_dir.glob("MUON-run*_nt_source_t*.csv"))
    if not paths:
        raise FileNotFoundError(f"No source truth CSV shards found in {input_dir}")
    frames = [read_wcsv(path, SOURCE_REQUIRED_COLUMNS) for path in paths]
    truth = pd.concat(frames, ignore_index=True)
    truth = truth.drop_duplicates(subset=["EventID"]).sort_values("EventID").reset_index(drop=True)
    return truth


def load_hit_counts(
    input_dir: Path,
    process_name: str,
    event_ids: pd.Series,
    sipm_copies: tuple[int, ...],
) -> pd.DataFrame:
    paths = sorted(input_dir.glob("MUON-run*_nt_hits_t*.csv"))
    if not paths:
        raise FileNotFoundError(f"No hit CSV shards found in {input_dir}")

    frames = []
    for path in paths:
        df = read_wcsv(path, HIT_REQUIRED_COLUMNS)
        if process_name.lower() not in {"any", "all", "*"}:
            df = df.loc[df["ProcessName"] == process_name]
        if df.empty:
            continue
        sipm_mask = df["Volume"].astype(str).str.contains("sipm", case=False, na=False)
        df = df.loc[sipm_mask, ["EventID", "TrackID", "Copynumber"]].copy()
        if df.empty:
            continue
        df["Copynumber"] = df["Copynumber"].astype(int)
        df = df.loc[df["Copynumber"].isin(sipm_copies)]
        frames.append(df)

    if frames:
        hits = pd.concat(frames, ignore_index=True)
        hits = hits.drop_duplicates(subset=["EventID", "TrackID", "Copynumber"])
        counts = (
            hits.groupby(["EventID", "Copynumber"], sort=True)
            .size()
            .rename("Count")
            .reset_index()
        )
        output = counts.pivot(index="EventID", columns="Copynumber", values="Count")
    else:
        output = pd.DataFrame(index=pd.Index([], name="EventID"))

    output = (
        output.reindex(index=event_ids.to_numpy(), columns=sipm_copies, fill_value=0)
        .fillna(0)
        .astype("int64")
        .rename(columns={copy: f"sipm_{copy}" for copy in sipm_copies})
        .reset_index()
    )
    return output.rename(columns={"index": "EventID"})


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    sipm_copies = SIPM_COPY_PRESETS[args.sipm_preset]
    sipm_columns = [f"sipm_{copy}" for copy in sipm_copies]
    truth = load_source_truth(input_dir)
    counts = load_hit_counts(input_dir, args.process_name, truth["EventID"], sipm_copies)
    merged = truth.merge(counts, on="EventID", validate="one_to_one")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for _, row in merged.iterrows():
        event_id = int(row["EventID"])
        output_name = f"MUON-run{event_id}_sipm_counts_by_event.csv"
        output_path = output_dir / output_name
        if args.overwrite or not output_path.exists():
            out = pd.DataFrame(
                [{"EventID": event_id, **{col: int(row[col]) for col in sipm_columns}}],
                columns=["EventID", *sipm_columns],
            )
            out.to_csv(output_path, index=False)

        manifest_rows.append(
            {
                "event_id": event_id,
                "run_id": event_id,
                "output_file": output_name,
                "raw_file": "ADD_SCAN_one_run",
                "source_index": int(row["SourceIndex"]),
                "source_cycle": int(row["SourceCycle"]),
                "true_x_cm": float(row["SourceX"]),
                "true_y_cm": float(row["SourceY"]),
                "true_z_cm": float(row["SourceZ"]),
            }
        )

    manifest = pd.DataFrame(manifest_rows).sort_values("event_id")
    manifest.to_csv(output_dir / "test_manifest.csv", index=False)
    print(f"Wrote {len(manifest)} per-event files to {output_dir}")
    print(f"Wrote manifest with source truth to {output_dir / 'test_manifest.csv'}")


if __name__ == "__main__":
    main()
