#!/usr/bin/env python3
"""Generate ADD_SCAN macros for cover32 full-slab random and training muon runs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
MACROS = ROOT / "macros"
DEFAULT_RANDOM_EVENTS = 1000
DEFAULT_TRAINING_EVENTS = 10000
DEFAULT_SEED = 20260619
SOURCE_Y_CM = 5.0
SLAB_HALF_CM = 50.0


def position_line(x_cm: float, z_cm: float) -> str:
    return f"/gps/position {x_cm:.6f} {SOURCE_Y_CM:.6f} {z_cm:.6f} cm"


def write_positions(path: Path, positions: list[tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [position_line(x, z) for x, z in positions]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_random_truth(path: Path, positions: list[tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_id", "source_index", "x_cm", "y_cm", "z_cm"])
        for idx, (x_cm, z_cm) in enumerate(positions):
            writer.writerow([idx, idx, f"{x_cm:.6f}", f"{SOURCE_Y_CM:.6f}", f"{z_cm:.6f}"])


def write_one_run_macro(path: Path, position_file: Path, events: int, label: str) -> None:
    rel_position_file = f"macros/{position_file.name}"
    text = f"""# {label} for ADD_SCAN builds.
# Positions are in {rel_position_file}.

/run/initialize
/tracking/verbose 0
/scan/positionFile {rel_position_file}
/vis/viewer/set/autoRefresh false
/vis/scene/endOfEventAction accumulate -1
/vis/scene/endOfRunAction accumulate
/run/printProgress 100
/run/beamOn {events}
/vis/viewer/set/autoRefresh true
/vis/viewer/refresh
"""
    path.write_text(text, encoding="ascii")


def build_random_positions(events: int, seed: int) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    return [
        (rng.uniform(-SLAB_HALF_CM, SLAB_HALF_CM), rng.uniform(-SLAB_HALF_CM, SLAB_HALF_CM))
        for _ in range(events)
    ]


def build_training_positions(events: int) -> list[tuple[float, float]]:
    side = int(events**0.5)
    if side * side != events:
        raise ValueError("Training events must be a perfect square for an even x-z grid")
    step = (2.0 * SLAB_HALF_CM) / side
    coords = [-SLAB_HALF_CM + (idx + 0.5) * step for idx in range(side)]
    return [(x, z) for z in coords for x in coords]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-events", type=int, default=DEFAULT_RANDOM_EVENTS)
    parser.add_argument("--training-events", type=int, default=DEFAULT_TRAINING_EVENTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random_positions = build_random_positions(args.random_events, args.seed)
    training_positions = build_training_positions(args.training_events)

    random_positions_file = MACROS / "cover32_random_muon_1000_positions.mac"
    random_macro = MACROS / "cover32_random_muon_1000.mac"
    random_truth = MACROS / "cover32_random_muon_1000_positions.csv"
    training_positions_file = MACROS / "cover32_training_muon_10000_positions.mac"
    training_macro = MACROS / "cover32_training_muon_10000.mac"

    write_positions(random_positions_file, random_positions)
    write_random_truth(random_truth, random_positions)
    write_one_run_macro(
        random_macro,
        random_positions_file,
        len(random_positions),
        "Full-slab random 1000-event cover32 face-mount muon scan",
    )
    write_positions(training_positions_file, training_positions)
    write_one_run_macro(
        training_macro,
        training_positions_file,
        len(training_positions),
        "Full-slab 100x100 one-muon-per-position cover32 face-mount training scan",
    )

    print(f"Wrote {random_macro}")
    print(f"Wrote {random_positions_file}")
    print(f"Wrote {random_truth}")
    print(f"Wrote {training_macro}")
    print(f"Wrote {training_positions_file}")


if __name__ == "__main__":
    main()
