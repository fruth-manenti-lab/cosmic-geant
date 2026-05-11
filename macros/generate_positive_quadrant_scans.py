from __future__ import annotations

import csv
from pathlib import Path
import random

from generate_muon_scan import (
    format_position_line,
    load_gdml_variables,
    load_template_lines,
)


GRID_POINTS_PER_AXIS = 50
EVENTS_PER_GRID_POSITION = 10
RANDOM_EVENTS = 1000
RANDOM_SEED = 20260509


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_positions_csv(
    path: Path, positions: list[tuple[float, float, float]], unit: str
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "event_id",
                "run_id",
                "x",
                "y",
                "z",
                "unit",
                "true_x_cm",
                "true_y_cm",
                "true_z_cm",
            ],
        )
        writer.writeheader()
        for event_id, (x, y, z) in enumerate(positions):
            writer.writerow(
                {
                    "event_id": event_id,
                    "run_id": event_id,
                    "x": f"{x:.6f}",
                    "y": f"{y:.6f}",
                    "z": f"{z:.6f}",
                    "unit": unit,
                    "true_x_cm": f"{x:.6f}" if unit == "cm" else "",
                    "true_y_cm": f"{y:.6f}" if unit == "cm" else "",
                    "true_z_cm": f"{z:.6f}" if unit == "cm" else "",
                }
            )


def build_quadrant_grid(
    half_width: float, source_y: float, points_per_axis: int
) -> list[tuple[float, float, float]]:
    step = half_width / points_per_axis
    centers = [step * (index + 0.5) for index in range(points_per_axis)]
    return [(x, source_y, z) for z in centers for x in centers]


def build_quadrant_random(
    half_width: float, source_y: float, num_events: int, seed: int
) -> list[tuple[float, float, float]]:
    rng = random.Random(seed)
    return [
        (rng.uniform(0.0, half_width), source_y, rng.uniform(0.0, half_width))
        for _ in range(num_events)
    ]


def main() -> None:
    macros_dir = Path(__file__).resolve().parent
    repo_root = macros_dir.parent

    variables = load_gdml_variables(repo_root / "geometry" / "final.gdml")
    _, _, source_y, unit_scale_from_mm, unit = load_template_lines(macros_dir / "muon.mac")
    half_width = variables["slab_half_xy"] * unit_scale_from_mm

    grid_positions = build_quadrant_grid(half_width, source_y, GRID_POINTS_PER_AXIS)
    random_positions = build_quadrant_random(half_width, source_y, RANDOM_EVENTS, RANDOM_SEED)

    grid_position_file = macros_dir / "muon_scan_positive_quadrant_2500_positions.mac"
    grid_wrapper_file = macros_dir / "muon_scan_positive_quadrant_2500x10_one_run.mac"
    random_position_file = macros_dir / "random_muon_scan_positive_quadrant_1000_positions.mac"
    random_wrapper_file = macros_dir / "random_muon_scan_positive_quadrant_1000_one_run.mac"
    random_csv_file = macros_dir / "random_muon_scan_positive_quadrant_1000_positions.csv"

    grid_step = half_width / GRID_POINTS_PER_AXIS
    write_lines(
        grid_position_file,
        [
            "# Positive-quadrant training positions for ADD_SCAN builds.",
            f"# x,z span [0, {half_width:.6f}] {unit} using {GRID_POINTS_PER_AXIS}x{GRID_POINTS_PER_AXIS} bin centers.",
            f"# Grid pitch: {grid_step:.6f} {unit}.",
            f"# Total positions: {len(grid_positions)}.",
            *[format_position_line(position, unit) for position in grid_positions],
        ],
    )

    write_lines(
        grid_wrapper_file,
        [
            "# One-run positive-quadrant training scan for ADD_SCAN builds.",
            "# Event i uses position i % 2500, so 25000 events gives 10 muons per position.",
            "",
            "/run/initialize",
            "/tracking/verbose 0",
            f"/scan/positionFile macros/{grid_position_file.name}",
            "/vis/viewer/set/autoRefresh false",
            "/vis/scene/endOfEventAction accumulate -1",
            "/vis/scene/endOfRunAction accumulate",
            "/run/printProgress 2500",
            f"/run/beamOn {len(grid_positions) * EVENTS_PER_GRID_POSITION}",
            "/vis/viewer/set/autoRefresh true",
            "/vis/viewer/refresh",
        ],
    )

    write_lines(
        random_position_file,
        [
            "# Positive-quadrant random test positions for ADD_SCAN builds.",
            f"# x,z sampled uniformly on [0, {half_width:.6f}] {unit}.",
            f"# Total positions/events: {len(random_positions)}.",
            f"# Random seed: {RANDOM_SEED}.",
            *[format_position_line(position, unit) for position in random_positions],
        ],
    )

    write_lines(
        random_wrapper_file,
        [
            "# One-run positive-quadrant random test scan for ADD_SCAN builds.",
            "# With 1000 events and 1000 source positions, each random position is used once.",
            "",
            "/run/initialize",
            "/tracking/verbose 0",
            f"/scan/positionFile macros/{random_position_file.name}",
            "/vis/viewer/set/autoRefresh false",
            "/vis/scene/endOfEventAction accumulate -1",
            "/vis/scene/endOfRunAction accumulate",
            "/run/printProgress 100",
            f"/run/beamOn {len(random_positions)}",
            "/vis/viewer/set/autoRefresh true",
            "/vis/viewer/refresh",
        ],
    )
    write_positions_csv(random_csv_file, random_positions, unit)

    print(f"Wrote {grid_position_file}")
    print(f"Wrote {grid_wrapper_file}")
    print(f"Wrote {random_position_file}")
    print(f"Wrote {random_wrapper_file}")
    print(f"Wrote {random_csv_file}")


if __name__ == "__main__":
    main()
