#!/usr/bin/env python3
"""Break down SiPM photon events and double coincidences by source particle."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
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
            "Count SiPM optical-photon events and double coincidences caused "
            "by muon- and gamma-initiated tracks."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Hit CSV files, output directories, or run directories containing hit ntuples.",
    )
    parser.add_argument(
        "--sipm-copies",
        default="0,1",
        help="Comma-separated SiPM copy numbers to require for coincidences. Default: 0,1.",
    )
    parser.add_argument(
        "--min-photons-per-sipm",
        type=float,
        default=1.0,
        help=(
            "Minimum raw or PDE-weighted detected photons required in each SiPM "
            "for a double coincidence. Default: 1."
        ),
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
        "--output",
        type=Path,
        help="Optional CSV with one row per source category.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        help="Optional JSON summary.",
    )
    return parser.parse_args()


def parse_copy_numbers(value: str) -> list[int]:
    copies = [int(item.strip()) for item in value.split(",") if item.strip()]
    if len(copies) < 2:
        raise ValueError("At least two SiPM copies are required.")
    return copies


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

        candidates = [path / "work" / "output", path / "output", path]
        found: list[Path] = []
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
                if fields:
                    yield dict(zip(header, fields))
            return


def parse_int_field(row: dict[str, str], field: str) -> int:
    return int(float(row[field]))


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


def optical_wavelength_nm_from_initial_energy(row: dict[str, str]) -> float:
    initial_energy_kev = float(row["InitialEnergy"])
    initial_energy_ev = initial_energy_kev * 1000.0
    if initial_energy_ev <= 0:
        raise ValueError(f"Optical photon has non-positive InitialEnergy: {initial_energy_kev} keV")
    return 1239.841984 / initial_energy_ev


def photon_weight(row: dict[str, str], pde_curve: PdeCurve | None) -> tuple[float, float | None, float | None]:
    if pde_curve is None:
        return 1.0, None, None

    wavelength_nm = optical_wavelength_nm_from_initial_energy(row)
    pde_percent = pde_curve.interpolate_percent(wavelength_nm)
    return pde_percent / 100.0, wavelength_nm, pde_percent


def source_category(row: dict[str, str]) -> str:
    source_particle = row.get("SourceParticle", "").strip()
    if source_particle in {"mu-", "mu+"}:
        return "muon"
    if source_particle == "gamma":
        return "gamma"
    if not source_particle:
        return "untagged"
    return source_particle


def count_by_source(
    files: list[Path],
    sipm_copies: list[int],
    pde_curve: PdeCurve | None,
) -> tuple[dict[str, dict[int, list[float]]], dict[str, object]]:
    copy_to_index = {copy_number: index for index, copy_number in enumerate(sipm_copies)}
    event_counts: dict[str, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(lambda: [0.0] * len(sipm_copies))
    )
    stats: dict[str, object] = {
        "files": len(files),
        "rows_read": 0,
        "sipm_photon_rows": 0,
        "ignored_sipm_copies": 0,
        "missing_source_particle_rows": 0,
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
            stats["rows_read"] = int(stats["rows_read"]) + 1
            if row.get("Particle") != "opticalphoton":
                continue
            if "sipm" not in row.get("Volume", "").lower():
                continue

            copy_number = parse_int_field(row, "Copynumber")
            if copy_number not in copy_to_index:
                stats["ignored_sipm_copies"] = int(stats["ignored_sipm_copies"]) + 1
                continue
            if "SourceParticle" not in row:
                stats["missing_source_particle_rows"] = int(stats["missing_source_particle_rows"]) + 1

            category = source_category(row)
            event_id = parse_int_field(row, "EventID")
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

            event_counts[category][event_id][copy_to_index[copy_number]] += weight
            stats["sipm_photon_rows"] = int(stats["sipm_photon_rows"]) + 1

    return event_counts, stats


def passes_cut(counts: list[float], threshold: float) -> bool:
    return all(count >= threshold for count in counts)


def summarize_source(
    source: str,
    counts_by_event: dict[int, list[float]],
    sipm_copies: list[int],
    threshold: float,
) -> dict[str, object]:
    double_events = {
        event_id: counts
        for event_id, counts in counts_by_event.items()
        if passes_cut(counts, threshold)
    }
    return {
        "source": source,
        "events_with_any_sipm_photon": len(counts_by_event),
        "double_coincidence_events": len(double_events),
        "total_photons_by_copy": {
            str(copy_number): sum(counts[index] for counts in counts_by_event.values())
            for index, copy_number in enumerate(sipm_copies)
        },
        "events_with_photons_by_copy": {
            str(copy_number): sum(1 for counts in counts_by_event.values() if counts[index] > 0)
            for index, copy_number in enumerate(sipm_copies)
        },
    }


def summarize(
    event_counts: dict[str, dict[int, list[float]]],
    stats: dict[str, object],
    sipm_copies: list[int],
    threshold: float,
) -> dict[str, object]:
    preferred_order = ["muon", "gamma", "untagged"]
    sources = [source for source in preferred_order if source in event_counts]
    sources.extend(sorted(source for source in event_counts if source not in preferred_order))
    return {
        **stats,
        "sipm_copies": sipm_copies,
        "min_photons_per_sipm": threshold,
        "sources": [
            summarize_source(source, event_counts[source], sipm_copies, threshold)
            for source in sources
        ],
    }


def write_csv(path: Path, summary: dict[str, object], sipm_copies: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source",
        "events_with_any_sipm_photon",
        "double_coincidence_events",
        *[f"total_photons_copy_{copy}" for copy in sipm_copies],
        *[f"events_with_photons_copy_{copy}" for copy in sipm_copies],
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for source_summary in summary["sources"]:
            row = {
                "source": source_summary["source"],
                "events_with_any_sipm_photon": source_summary["events_with_any_sipm_photon"],
                "double_coincidence_events": source_summary["double_coincidence_events"],
            }
            for copy in sipm_copies:
                row[f"total_photons_copy_{copy}"] = source_summary["total_photons_by_copy"][str(copy)]
                row[f"events_with_photons_copy_{copy}"] = source_summary["events_with_photons_by_copy"][str(copy)]
            writer.writerow(row)


def print_summary(summary: dict[str, object], files: list[Path]) -> None:
    print("SiPM source-breakdown analysis")
    print(f"  input files: {summary['files']}")
    print(f"  first file: {files[0]}")
    if len(files) > 1:
        print(f"  last file:  {files[-1]}")
    print(f"  rows read: {summary['rows_read']}")
    print(f"  SiPM photon rows counted: {summary['sipm_photon_rows']}")
    print(f"  missing SourceParticle rows: {summary['missing_source_particle_rows']}")
    print(f"  weighting mode: {summary['weighting_mode']}")
    if summary["pde_source"] is not None:
        print(f"  PDE source: {summary['pde_source']}")
        print(f"  PDE column: {summary['pde_column']}")
        print(f"  wavelength range: {summary['wavelength_min_nm']:.3f} - {summary['wavelength_max_nm']:.3f} nm")
        print(f"  interpolated PDE range: {summary['pde_percent_min']:.3f} - {summary['pde_percent_max']:.3f} %")
    print(f"  min photons per SiPM for DC: {summary['min_photons_per_sipm']}")
    for source_summary in summary["sources"]:
        print(f"  source: {source_summary['source']}")
        print(f"    SiPM events: {source_summary['events_with_any_sipm_photon']}")
        print(f"    double coincidences: {source_summary['double_coincidence_events']}")
        print(f"    total photons by copy: {source_summary['total_photons_by_copy']}")
        print(f"    events with photons by copy: {source_summary['events_with_photons_by_copy']}")


def main() -> int:
    args = parse_args()
    try:
        sipm_copies = parse_copy_numbers(args.sipm_copies)
        files = find_hit_files(args.inputs)
        pde_curve = load_pde_curve(args.pde_csv, args.pde_column)
        event_counts, stats = count_by_source(files, sipm_copies, pde_curve)
        summary = summarize(event_counts, stats, sipm_copies, args.min_photons_per_sipm)
        if args.output:
            write_csv(args.output, summary, sipm_copies)
        if args.summary_json:
            args.summary_json.parent.mkdir(parents=True, exist_ok=True)
            args.summary_json.write_text(json.dumps(summary, indent=2) + "\n")
        print_summary(summary, files)
        if args.output:
            print(f"  output CSV: {args.output}")
        if args.summary_json:
            print(f"  summary JSON: {args.summary_json}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
