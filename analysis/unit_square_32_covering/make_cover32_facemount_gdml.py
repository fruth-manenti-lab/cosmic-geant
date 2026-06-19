#!/usr/bin/env python3
"""Generate a 1 m face-mount GDML with SiPMs at cover32 centers."""

from __future__ import annotations

import csv
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
POINTS_CSV = PACKAGE / "results" / "best_points.csv"
SOURCE_GDML = ROOT / "geometry" / "faceMountGeometry_1m_diagonal_sipms.gdml"
OUT_GDML = ROOT / "geometry" / "faceMountGeometry_1m_cover32_sipms.gdml"
OUT_MAPPING = PACKAGE / "results" / "cover32_sipm_mapping_mm.csv"
SLAB_MM = 1000.0


def load_points(path: Path) -> list[tuple[float, float]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        points = [(float(row["x"]), float(row["y"])) for row in reader]
    if len(points) != 32:
        raise ValueError(f"Expected 32 points in {path}, found {len(points)}")
    for idx, (x, y) in enumerate(points):
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError(f"Point {idx} is outside the unit square: {(x, y)}")
    return points


def unit_to_mm(point: tuple[float, float]) -> tuple[float, float]:
    x_unit, z_unit = point
    return (x_unit - 0.5) * SLAB_MM, (z_unit - 0.5) * SLAB_MM


def replace_sipm_variables(text: str, points_mm: list[tuple[float, float]]) -> str:
    for idx, (x_mm, z_mm) in enumerate(points_mm):
        text, count_x = re.subn(
            rf'    <variable name="sipm{idx}_x" value="[^"]+"/>',
            f'    <variable name="sipm{idx}_x" value="{x_mm:.6f}"/>',
            text,
            count=1,
        )
        text, count_z = re.subn(
            rf'    <variable name="sipm{idx}_z" value="[^"]+"/>',
            f'    <variable name="sipm{idx}_z" value="{z_mm:.6f}"/>',
            text,
            count=1,
        )
        if count_x != 1 or count_z != 1:
            raise ValueError(f"Could not replace sipm{idx}_x/z variables in {SOURCE_GDML}")
    return text


def write_mapping(points: list[tuple[float, float]], points_mm: list[tuple[float, float]]) -> None:
    OUT_MAPPING.parent.mkdir(parents=True, exist_ok=True)
    with OUT_MAPPING.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sipm_id", "copy_number", "x_unit", "z_unit", "x_mm", "z_mm"])
        for idx, ((x_unit, z_unit), (x_mm, z_mm)) in enumerate(zip(points, points_mm)):
            writer.writerow([idx, idx, f"{x_unit:.10f}", f"{z_unit:.10f}", f"{x_mm:.6f}", f"{z_mm:.6f}"])


def main() -> None:
    points = load_points(POINTS_CSV)
    points_mm = [unit_to_mm(point) for point in points]
    text = SOURCE_GDML.read_text(encoding="utf-8")
    text = replace_sipm_variables(text, points_mm)
    OUT_GDML.write_text(text, encoding="utf-8")
    write_mapping(points, points_mm)
    print(f"Wrote {OUT_GDML}")
    print(f"Wrote {OUT_MAPPING}")


if __name__ == "__main__":
    main()
