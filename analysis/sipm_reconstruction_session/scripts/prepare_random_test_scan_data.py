#!/usr/bin/env python3
"""Prepare random single-muon test data from multithreaded Geant4 CSV shards.

The random macro uses one `/run/beamOn 1` per source position. In multithreaded
Geant4 output, the `runN` part of the shard filename should be the global
source-position index. Older output made before the RunAction filename fix can
still be converted by passing `--order write-time`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


RUN_RE = re.compile(r"MUON-run(?P<run>\d+)_nt_hits_t(?P<thread>\d+)\.csv$")
SIPM_COPIES = tuple(range(100, 116)) + tuple(range(300, 316))
SIPM_COLUMNS = [f"sipm_{copy}" for copy in SIPM_COPIES]
REQUIRED_COLUMNS = {"EventID", "TrackID", "Volume", "Copynumber", "ProcessName"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert random single-muon raw hit CSVs into clean per-event test files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("build/output"),
        help="Directory containing raw MUON-run*_nt_hits_t*.csv output files.",
    )
    parser.add_argument(
        "--positions-csv",
        type=Path,
        default=Path("macros/random_muon_scan_positions.csv"),
        help="Truth positions CSV generated with random_muon_scan.mac.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/test_scan_data_1000"),
        help="Directory for clean per-event SiPM count CSVs and labels.",
    )
    parser.add_argument(
        "--process-name",
        default="OpWLS",
        help="ProcessName value to count.",
    )
    parser.add_argument(
        "--order",
        choices=("run-id", "write-time"),
        default="run-id",
        help=(
            "How to map raw files to random source positions. Use run-id for "
            "output produced after the RunAction filename fix; use write-time "
            "only for older output with worker-local run IDs."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
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


def read_event_counts(path: Path, process_name: str) -> dict[str, int]:
    columns = wcsv_columns(path)
    missing = REQUIRED_COLUMNS.difference(columns)
    if missing:
        raise KeyError(f"{path} is missing columns: {sorted(missing)}")

    usecols = [col for col in columns if col in REQUIRED_COLUMNS]
    df = pd.read_csv(path, comment="#", names=columns, usecols=usecols)
    df = df.loc[df["ProcessName"] == process_name]
    if not df.empty:
        sipm_mask = df["Volume"].astype(str).str.contains("sipm", case=False, na=False)
        df = df.loc[sipm_mask, ["EventID", "TrackID", "Copynumber"]].copy()
    if df.empty:
        return {column: 0 for column in SIPM_COLUMNS}

    df["Copynumber"] = df["Copynumber"].astype(int)
    df = df.loc[df["Copynumber"].isin(SIPM_COPIES)]
    df = df.drop_duplicates(subset=["EventID", "TrackID", "Copynumber"])
    counts = df.groupby("Copynumber").size().to_dict()
    return {f"sipm_{copy}": int(counts.get(copy, 0)) for copy in SIPM_COPIES}


def run_id_from_path(path: Path) -> int:
    match = RUN_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected raw hit filename: {path.name}")
    return int(match.group("run"))


def sorted_raw_files(input_dir: Path, order: str) -> list[Path]:
    paths = list(input_dir.glob("MUON-run*_nt_hits_t*.csv"))
    if not paths:
        raise FileNotFoundError(f"No raw hit CSV files found in {input_dir}")

    if order == "write-time":
        return sorted(paths, key=lambda path: (path.stat().st_mtime_ns, path.name))

    paths = sorted(paths, key=lambda path: (run_id_from_path(path), path.name))
    run_ids = [run_id_from_path(path) for path in paths]
    if len(set(run_ids)) != len(run_ids):
        duplicates = sorted({run_id for run_id in run_ids if run_ids.count(run_id) > 1})
        raise ValueError(
            f"Expected one raw file per run for --order run-id; duplicate run IDs: {duplicates[:10]}"
        )
    return paths


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    positions_csv = args.positions_csv.resolve()

    raw_files = sorted_raw_files(input_dir, args.order)
    labels = pd.read_csv(positions_csv)
    if len(raw_files) != len(labels):
        raise ValueError(
            f"Raw file count ({len(raw_files)}) does not match truth rows ({len(labels)}). "
            "Do not use write-time order unless these are equal."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    for sequence_id, raw_path in enumerate(raw_files):
        event_id = sequence_id if args.order == "write-time" else run_id_from_path(raw_path)
        output_path = output_dir / f"MUON-run{event_id}_sipm_counts_by_event.csv"
        if output_path.exists() and not args.overwrite:
            continue

        counts = read_event_counts(raw_path, args.process_name)
        row = {"EventID": event_id, **counts}
        pd.DataFrame([row], columns=["EventID", *SIPM_COLUMNS]).to_csv(output_path, index=False)

        truth = labels.iloc[event_id].to_dict()
        manifest_rows.append(
            {
                "event_id": event_id,
                "run_id": event_id,
                "output_file": output_path.name,
                "raw_file": raw_path.name,
                "raw_run_id": run_id_from_path(raw_path),
                "raw_mtime_ns": raw_path.stat().st_mtime_ns,
                **truth,
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(output_dir / "test_manifest.csv", index=False)
    print(f"Wrote {len(manifest)} per-event files to {output_dir}")
    print(f"Wrote manifest with truth labels to {output_dir / 'test_manifest.csv'}")


if __name__ == "__main__":
    main()
