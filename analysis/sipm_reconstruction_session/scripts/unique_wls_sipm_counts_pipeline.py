#!/usr/bin/env python3
"""Batch unique OpWLS SiPM photon counts per event.

Reads Geant4 tools::wcsv ntuple CSV shards named like
MUON-run590_nt_hits_t27.csv, groups shards by run, and writes one output CSV
per run. Each output has one row per EventID and one column per SiPM copy
number containing the unique OpWLS photon count for that event/copy.
"""

from __future__ import annotations

import argparse
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


RUN_RE = re.compile(r"MUON-run(?P<run>\d+)_nt_hits_t(?P<thread>\d+)\.csv$")
DEFAULT_SIPM_COPIES = tuple(range(100, 116)) + tuple(range(300, 316))
REQUIRED_COLUMNS = {"EventID", "TrackID", "Volume", "Copynumber", "ProcessName"}


@dataclass(frozen=True)
class RunTask:
    run_id: int
    input_paths: tuple[Path, ...]
    output_path: Path
    sipm_copies: tuple[int, ...]
    process_name: str
    count_mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one per-run CSV of per-event SiPM OpWLS photon counts."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("build/1024_muon_scan_may1st_2026"),
        help="Directory containing MUON-run*_nt_hits_t*.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/unique_wls_sipm_counts"),
        help="Directory where per-run count CSV files will be written.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 1),
        help="Number of runs to process in parallel.",
    )
    parser.add_argument(
        "--glob",
        default="MUON-run*_nt_hits_t*.csv",
        help="Input file glob within --input-dir.",
    )
    parser.add_argument(
        "--process-name",
        default="OpWLS",
        help="ProcessName value to count.",
    )
    parser.add_argument(
        "--count-mode",
        choices=("unique-track", "hits"),
        default="unique-track",
        help=(
            "unique-track counts unique (EventID, TrackID, Copynumber); "
            "hits counts every matching row."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute runs even when the output CSV already exists.",
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


def read_relevant_hits(path: Path, process_name: str) -> pd.DataFrame:
    columns = wcsv_columns(path)
    missing = REQUIRED_COLUMNS.difference(columns)
    if missing:
        raise KeyError(f"{path} is missing columns: {sorted(missing)}")

    usecols = [col for col in columns if col in REQUIRED_COLUMNS]
    df = pd.read_csv(path, comment="#", names=columns, usecols=usecols)
    df = df.loc[df["ProcessName"] == process_name]
    if df.empty:
        return df[["EventID", "TrackID", "Volume", "Copynumber"]]

    sipm_mask = df["Volume"].astype(str).str.contains("sipm", case=False, na=False)
    df = df.loc[sipm_mask, ["EventID", "TrackID", "Volume", "Copynumber"]].copy()
    if not df.empty:
        df["Copynumber"] = df["Copynumber"].astype(int)
    return df


def group_input_files(input_dir: Path, glob_pattern: str) -> dict[int, list[Path]]:
    runs: dict[int, list[Path]] = {}
    for path in input_dir.glob(glob_pattern):
        match = RUN_RE.match(path.name)
        if not match:
            continue
        runs.setdefault(int(match.group("run")), []).append(path)

    for paths in runs.values():
        paths.sort(key=lambda p: int(RUN_RE.match(p.name).group("thread")))  # type: ignore[union-attr]
    return dict(sorted(runs.items()))


def process_run(task: RunTask) -> tuple[int, int, int, Path]:
    frames = [read_relevant_hits(path, task.process_name) for path in task.input_paths]
    hits = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if hits.empty:
        output = pd.DataFrame(columns=["EventID", *[f"sipm_{copy}" for copy in task.sipm_copies]])
    else:
        hits = hits.loc[hits["Copynumber"].isin(task.sipm_copies)]
        if task.count_mode == "unique-track":
            hits = hits.drop_duplicates(subset=["EventID", "TrackID", "Copynumber"])

        counts = (
            hits.groupby(["EventID", "Copynumber"], sort=True)
            .size()
            .rename("Count")
            .reset_index()
        )
        output = (
            counts.pivot(index="EventID", columns="Copynumber", values="Count")
            .reindex(columns=task.sipm_copies, fill_value=0)
            .fillna(0)
            .astype("int64")
            .rename(columns={copy: f"sipm_{copy}" for copy in task.sipm_copies})
            .reset_index()
        )

    task.output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(task.output_path, index=False)
    return task.run_id, len(task.input_paths), len(output), task.output_path


def build_tasks(args: argparse.Namespace, runs: dict[int, list[Path]]) -> list[RunTask]:
    tasks: list[RunTask] = []
    for run_id, input_paths in runs.items():
        output_path = args.output_dir / f"MUON-run{run_id}_sipm_counts_by_event.csv"
        if output_path.exists() and not args.overwrite:
            continue
        tasks.append(
            RunTask(
                run_id=run_id,
                input_paths=tuple(input_paths),
                output_path=output_path,
                sipm_copies=DEFAULT_SIPM_COPIES,
                process_name=args.process_name,
                count_mode=args.count_mode,
            )
        )
    return tasks


def run_parallel(tasks: Iterable[RunTask], workers: int) -> None:
    task_list = list(tasks)
    if not task_list:
        print("No runs need processing.")
        return

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_run, task): task for task in task_list}
        completed = 0
        total = len(futures)
        for future in as_completed(futures):
            task = futures[future]
            completed += 1
            try:
                run_id, shard_count, event_count, output_path = future.result()
            except Exception as exc:
                raise RuntimeError(f"Run {task.run_id} failed") from exc
            print(
                f"[{completed}/{total}] run {run_id}: "
                f"{shard_count} shards, {event_count} events -> {output_path}"
            )


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    runs = group_input_files(input_dir, args.glob)
    if not runs:
        raise FileNotFoundError(f"No matching run CSV files found in {input_dir}")

    shard_count = sum(len(paths) for paths in runs.values())
    print(f"Found {len(runs)} runs and {shard_count} input shards.")
    print(f"Writing per-run outputs to {output_dir}")

    args.output_dir = output_dir
    tasks = build_tasks(args, runs)
    skipped = len(runs) - len(tasks)
    if skipped:
        print(f"Skipping {skipped} existing outputs. Use --overwrite to recompute.")

    run_parallel(tasks, workers=max(1, args.workers))


if __name__ == "__main__":
    main()
