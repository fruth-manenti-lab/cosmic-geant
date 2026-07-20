#!/usr/bin/env python3
"""Count SiPM double coincidences from Geant4 hit ntuple CSV files.

A double coincidence is an event where both requested SiPM copy numbers record
at least the requested number of optical photon hits or PDE-weighted detected
photoelectrons.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


DEFAULT_COLUMNS = [
    "EventID",
    "TrackID",
    "Particle",
    "EnergyDeposited",
    "XPosition",
    "YPosition",
    "ZPosition",
    "LocalTime",
    "Volume",
    "Copynumber",
    "InitialEnergy",
    "OriginVolume",
    "ParentID",
    "ProcessName",
    "StepID",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count events where both dilution-detector SiPMs saw a non-zero "
            "number of optical photons."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help=(
            "Hit CSV files, directories containing hit CSV files, or run "
            "directories containing work/output/MUON-run0_nt_hits_t*.csv."
        ),
    )
    parser.add_argument(
        "--sipm-copies",
        default="0,1",
        help="Comma-separated SiPM copy numbers to require. Default: 0,1.",
    )
    parser.add_argument(
        "--min-photons-per-sipm",
        type=int,
        default=1,
        help=(
            "Minimum recorded optical-photon count required in each requested "
            "SiPM for a double coincidence. Default: 1."
        ),
    )
    parser.add_argument(
        "--sipm-efficiency",
        type=float,
        help=(
            "SiPM detection efficiency used with "
            "--min-detected-photons-per-sipm. Example: 0.4."
        ),
    )
    parser.add_argument(
        "--min-detected-photons-per-sipm",
        type=int,
        help=(
            "Detected-photon threshold after SiPM efficiency. The script "
            "converts this to a recorded/incident photon threshold with "
            "ceil(threshold / efficiency)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional CSV of per-event SiPM photon counts for events with SiPM hits.",
    )
    parser.add_argument(
        "--double-events-output",
        type=Path,
        help="Optional CSV containing only double-coincidence event IDs and counts.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        help="Optional JSON summary output.",
    )
    parser.add_argument(
        "--pde-csv",
        type=Path,
        help=(
            "Optional digitised SiPM PDE CSV. If supplied, each optical photon "
            "is weighted by interpolated PDE(wavelength) / 100 using InitialEnergy."
        ),
    )
    parser.add_argument(
        "--pde-column",
        default="pde_5v_percent",
        help="PDE percentage column to use from --pde-csv. Default: pde_5v_percent.",
    )
    parser.add_argument(
        "--weighted-column-suffix",
        default="pde_weighted_detected_photons",
        help=(
            "Column suffix for per-SiPM output when --pde-csv is used. "
            "Default: pde_weighted_detected_photons."
        ),
    )
    parser.add_argument(
        "--unique-tracks",
        action="store_true",
        help=(
            "Count each EventID/TrackID/SiPM-copy combination once. This uses "
            "more memory, but guards against repeated steps from the same photon."
        ),
    )
    return parser.parse_args()


def parse_copy_numbers(value: str) -> list[int]:
    copies = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        copies.append(int(item))
    if len(copies) < 2:
        raise ValueError("At least two SiPM copy numbers are required.")
    return copies


def effective_photon_threshold(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    if args.min_detected_photons_per_sipm is None:
        return args.min_photons_per_sipm, {
            "threshold_mode": "recorded_photons",
            "sipm_efficiency": None,
            "min_detected_photons_per_sipm": None,
            "effective_min_recorded_photons_per_sipm": args.min_photons_per_sipm,
        }

    if args.sipm_efficiency is None:
        raise ValueError("--min-detected-photons-per-sipm requires --sipm-efficiency")
    if not 0 < args.sipm_efficiency <= 1:
        raise ValueError("--sipm-efficiency must be greater than 0 and less than or equal to 1")

    effective_threshold = math.ceil(args.min_detected_photons_per_sipm / args.sipm_efficiency)
    return effective_threshold, {
        "threshold_mode": "efficiency_scaled_detected_photons",
        "sipm_efficiency": args.sipm_efficiency,
        "min_detected_photons_per_sipm": args.min_detected_photons_per_sipm,
        "effective_min_recorded_photons_per_sipm": effective_threshold,
    }


class PdeCurve:
    def __init__(self, points: list[tuple[float, float]], source: Path, column: str):
        if len(points) < 2:
            raise ValueError(f"At least two PDE points are required in {source}")
        self.points = sorted(points)
        self.source = source
        self.column = column

    def interpolate_percent(self, wavelength_nm: float) -> float:
        if wavelength_nm <= self.points[0][0]:
            return self.points[0][1]
        if wavelength_nm >= self.points[-1][0]:
            return self.points[-1][1]

        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            if x0 <= wavelength_nm <= x1:
                if x1 == x0:
                    return y0
                fraction = (wavelength_nm - x0) / (x1 - x0)
                return y0 + fraction * (y1 - y0)
        return self.points[-1][1]


def load_pde_curve(path: Path | None, column: str) -> PdeCurve | None:
    if path is None:
        return None

    points = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"wavelength_nm", column}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            points.append((float(row["wavelength_nm"]), float(row[column])))
    return PdeCurve(points, path, column)


def find_hit_files(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_input in inputs:
        path = Path(raw_input).expanduser()
        matches = sorted(Path().glob(raw_input)) if any(ch in raw_input for ch in "*?[]") else []

        if matches:
            files.extend(match for match in matches if match.is_file())
            continue

        if path.is_file():
            files.append(path)
            continue

        if not path.is_dir():
            raise FileNotFoundError(f"Input does not exist: {raw_input}")

        candidates = [
            path / "work" / "output",
            path / "output",
            path,
        ]
        found = []
        for directory in candidates:
            if directory.is_dir():
                found.extend(sorted(directory.glob("MUON-run*_nt_hits_t*.csv")))
                found.extend(sorted(directory.glob("*_nt_hits_t*.csv")))
        if not found:
            found = sorted(path.rglob("MUON-run*_nt_hits_t*.csv"))
        files.extend(found)

    unique_files = sorted({file.resolve() for file in files})
    if not unique_files:
        raise FileNotFoundError("No hit ntuple CSV files found.")
    return unique_files


def iter_hit_rows(path: Path):
    columns: list[str] = []
    with path.open(newline="") as handle:
        for line in handle:
            if line.startswith("#column "):
                parts = line.strip().split(maxsplit=2)
                if len(parts) == 3:
                    columns.append(parts[2])
                continue

            if line.startswith("#") or not line.strip():
                continue

            reader = csv.reader(itertools.chain([line], handle))
            header = columns or DEFAULT_COLUMNS
            for fields in reader:
                if not fields:
                    continue
                yield dict(zip(header, fields))
            return


def parse_int_field(row: dict[str, str], field: str) -> int:
    return int(float(row[field]))


def optical_wavelength_nm_from_initial_energy(row: dict[str, str]) -> float:
    initial_energy_keV = float(row["InitialEnergy"])
    initial_energy_eV = initial_energy_keV * 1000.0
    if initial_energy_eV <= 0:
        raise ValueError(f"Optical photon has non-positive InitialEnergy: {initial_energy_keV} keV")
    return 1239.841984 / initial_energy_eV


def photon_weight(row: dict[str, str], pde_curve: PdeCurve | None) -> tuple[float, float | None, float | None]:
    if pde_curve is None:
        return 1.0, None, None

    wavelength_nm = optical_wavelength_nm_from_initial_energy(row)
    pde_percent = pde_curve.interpolate_percent(wavelength_nm)
    return pde_percent / 100.0, wavelength_nm, pde_percent


def count_double_coincidences(
    files: list[Path],
    sipm_copies: list[int],
    unique_tracks: bool,
    pde_curve: PdeCurve | None,
) -> tuple[dict[int, list[float]], dict[str, float | int | str | None]]:
    copy_to_index = {copy_number: index for index, copy_number in enumerate(sipm_copies)}
    event_counts: dict[int, list[float]] = defaultdict(lambda: [0.0] * len(sipm_copies))
    seen_tracks: set[tuple[int, int, int]] = set()
    stats: dict[str, float | int | str | None] = {
        "files": len(files),
        "rows_read": 0,
        "sipm_photon_rows": 0,
        "ignored_sipm_copies": 0,
        "weighting_mode": "pde_weighted" if pde_curve is not None else "raw_photon_count",
        "pde_source": str(pde_curve.source) if pde_curve is not None else None,
        "pde_column": pde_curve.column if pde_curve is not None else None,
        "wavelength_min_nm": None,
        "wavelength_max_nm": None,
        "pde_percent_min": None,
        "pde_percent_max": None,
    }

    for path in files:
        for row in iter_hit_rows(path):
            stats["rows_read"] += 1
            if row.get("Particle") != "opticalphoton":
                continue
            if "sipm" not in row.get("Volume", "").lower():
                continue

            copy_number = parse_int_field(row, "Copynumber")
            if copy_number not in copy_to_index:
                stats["ignored_sipm_copies"] += 1
                continue

            event_id = parse_int_field(row, "EventID")
            if unique_tracks:
                track_id = parse_int_field(row, "TrackID")
                track_key = (event_id, track_id, copy_number)
                if track_key in seen_tracks:
                    continue
                seen_tracks.add(track_key)

            weight, wavelength_nm, pde_percent = photon_weight(row, pde_curve)
            if wavelength_nm is not None and pde_percent is not None:
                stats["wavelength_min_nm"] = (
                    wavelength_nm
                    if stats["wavelength_min_nm"] is None
                    else min(float(stats["wavelength_min_nm"]), wavelength_nm)
                )
                stats["wavelength_max_nm"] = (
                    wavelength_nm
                    if stats["wavelength_max_nm"] is None
                    else max(float(stats["wavelength_max_nm"]), wavelength_nm)
                )
                stats["pde_percent_min"] = (
                    pde_percent
                    if stats["pde_percent_min"] is None
                    else min(float(stats["pde_percent_min"]), pde_percent)
                )
                stats["pde_percent_max"] = (
                    pde_percent
                    if stats["pde_percent_max"] is None
                    else max(float(stats["pde_percent_max"]), pde_percent)
                )

            event_counts[event_id][copy_to_index[copy_number]] += weight
            stats["sipm_photon_rows"] += 1

    return event_counts, stats


def passes_cut(counts: list[float], min_photons_per_sipm: float) -> bool:
    return all(count >= min_photons_per_sipm for count in counts)


def summarize(
    event_counts: dict[int, list[float]],
    sipm_copies: list[int],
    stats: dict[str, float | int | str | None],
    min_photons_per_sipm: int,
    threshold_details: dict[str, object],
) -> dict[str, object]:
    double_events = {
        event_id: counts
        for event_id, counts in event_counts.items()
        if passes_cut(counts, min_photons_per_sipm)
    }
    total_photons_by_copy = {
        str(copy_number): sum(counts[index] for counts in event_counts.values())
        for index, copy_number in enumerate(sipm_copies)
    }
    events_with_photons_by_copy = {
        str(copy_number): sum(1 for counts in event_counts.values() if counts[index] > 0)
        for index, copy_number in enumerate(sipm_copies)
    }
    events_with_any_sipm_photon = len(event_counts)
    return {
        **stats,
        "sipm_copies": sipm_copies,
        "min_photons_per_sipm": min_photons_per_sipm,
        **threshold_details,
        "events_with_any_sipm_photon": events_with_any_sipm_photon,
        "double_coincidence_events": len(double_events),
        "double_coincidence_fraction_of_sipm_events": (
            len(double_events) / events_with_any_sipm_photon if events_with_any_sipm_photon else 0.0
        ),
        "total_photons_by_copy": total_photons_by_copy,
        "events_with_photons_by_copy": events_with_photons_by_copy,
    }


def write_counts(
    path: Path,
    event_counts: dict[int, list[float]],
    sipm_copies: list[int],
    min_photons_per_sipm: int,
    column_suffix: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["EventID", *[f"sipm_copy_{copy}_{column_suffix}" for copy in sipm_copies], "double_coincidence"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for event_id in sorted(event_counts):
            counts = event_counts[event_id]
            row = {
                "EventID": event_id,
                "double_coincidence": int(passes_cut(counts, min_photons_per_sipm)),
            }
            for index, copy_number in enumerate(sipm_copies):
                row[f"sipm_copy_{copy_number}_{column_suffix}"] = f"{counts[index]:.10g}"
            writer.writerow(row)


def write_double_events(
    path: Path,
    event_counts: dict[int, list[float]],
    sipm_copies: list[int],
    min_photons_per_sipm: int,
    column_suffix: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["EventID", *[f"sipm_copy_{copy}_{column_suffix}" for copy in sipm_copies]]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for event_id in sorted(event_counts):
            counts = event_counts[event_id]
            if not passes_cut(counts, min_photons_per_sipm):
                continue
            row = {"EventID": event_id}
            for index, copy_number in enumerate(sipm_copies):
                row[f"sipm_copy_{copy_number}_{column_suffix}"] = f"{counts[index]:.10g}"
            writer.writerow(row)


def print_summary(summary: dict[str, object], files: list[Path]) -> None:
    print("SiPM double-coincidence analysis")
    print(f"  input files: {summary['files']}")
    print(f"  first file: {files[0]}")
    if len(files) > 1:
        print(f"  last file:  {files[-1]}")
    print(f"  rows read: {summary['rows_read']}")
    print(f"  SiPM photon rows counted: {summary['sipm_photon_rows']}")
    print(f"  weighting mode: {summary['weighting_mode']}")
    if summary["pde_source"] is not None:
        print(f"  PDE source: {summary['pde_source']}")
        print(f"  PDE column: {summary['pde_column']}")
        print(f"  wavelength range: {summary['wavelength_min_nm']:.3f} - {summary['wavelength_max_nm']:.3f} nm")
        print(f"  interpolated PDE range: {summary['pde_percent_min']:.3f} - {summary['pde_percent_max']:.3f} %")
    print(f"  threshold mode: {summary['threshold_mode']}")
    if summary["sipm_efficiency"] is not None:
        print(f"  SiPM efficiency: {summary['sipm_efficiency']}")
        print(f"  minimum detected photons per required SiPM: {summary['min_detected_photons_per_sipm']}")
    print(
        "  effective minimum recorded photons per required SiPM: "
        f"{summary['effective_min_recorded_photons_per_sipm']}"
    )
    print(f"  events with any SiPM photon: {summary['events_with_any_sipm_photon']}")
    print(f"  double-coincidence events: {summary['double_coincidence_events']}")
    print(
        "  DC fraction among SiPM-hit events: "
        f"{summary['double_coincidence_fraction_of_sipm_events']:.6g}"
    )
    print(f"  total photons by SiPM copy: {summary['total_photons_by_copy']}")
    print(f"  events with photons by SiPM copy: {summary['events_with_photons_by_copy']}")


def main() -> int:
    args = parse_args()
    try:
        sipm_copies = parse_copy_numbers(args.sipm_copies)
        min_photons_per_sipm, threshold_details = effective_photon_threshold(args)
        files = find_hit_files(args.inputs)
        pde_curve = load_pde_curve(args.pde_csv, args.pde_column)
        column_suffix = args.weighted_column_suffix if pde_curve is not None else "photons"
        event_counts, stats = count_double_coincidences(files, sipm_copies, args.unique_tracks, pde_curve)
        summary = summarize(event_counts, sipm_copies, stats, min_photons_per_sipm, threshold_details)

        if args.output:
            write_counts(args.output, event_counts, sipm_copies, min_photons_per_sipm, column_suffix)
        if args.double_events_output:
            write_double_events(
                args.double_events_output,
                event_counts,
                sipm_copies,
                min_photons_per_sipm,
                column_suffix,
            )
        if args.summary_json:
            args.summary_json.parent.mkdir(parents=True, exist_ok=True)
            args.summary_json.write_text(json.dumps(summary, indent=2) + "\n")

        print_summary(summary, files)
        if args.output:
            print(f"  per-event output: {args.output}")
        if args.double_events_output:
            print(f"  double-event output: {args.double_events_output}")
        if args.summary_json:
            print(f"  summary JSON: {args.summary_json}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
