#!/usr/bin/env python3
"""Draw virtual-quadrant SiPM mappings for the 1 m face-mount layout."""

from __future__ import annotations

from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parent
OUT_PNG = ROOT / "facemount_1m_virtual_sipm_mapping.png"
OUT_CSV = ROOT / "facemount_1m_virtual_sipm_mapping.csv"

SLAB_MM = 1000.0
SIPM_MM = 6.0
PAIR_OFFSET_MM = 59.0
COORD_TOL_MM = 1e-3

QUADRANTS = [
    ("Q++", "+x,+z", 1, 1, "#16a34a"),
    ("Q-+", "-x,+z", -1, 1, "#2563eb"),
    ("Q+-", "+x,-z", 1, -1, "#ea580c"),
    ("Q--", "-x,-z", -1, -1, "#9333ea"),
]


def local_diagonal_direction(xc: float, zc: float) -> tuple[float, float]:
    qx_min = 0.0 if xc > 0 else -500.0
    qz_min = 0.0 if zc > 0 else -500.0
    local_x_index = 0 if xc < qx_min + 250.0 else 1
    local_z_index = 0 if zc < qz_min + 250.0 else 1
    if local_x_index == local_z_index:
        return (1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0))
    return (1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0))


def build_sipm_positions() -> dict[int, tuple[float, float]]:
    positions: dict[int, tuple[float, float]] = {}
    sipm_id = 0
    centers = [-375.0, -125.0, 125.0, 375.0]
    for zc in centers:
        for xc in centers:
            dx, dz = local_diagonal_direction(xc, zc)
            px = -dz
            pz = dx
            for side in [-1, 1]:
                positions[sipm_id] = (
                    xc + side * PAIR_OFFSET_MM * px,
                    zc + side * PAIR_OFFSET_MM * pz,
                )
                sipm_id += 1
    return positions


def find_sipm_id(
    positions: dict[int, tuple[float, float]], x: float, z: float
) -> int:
    best_id = min(
        positions,
        key=lambda sid: math.hypot(positions[sid][0] - x, positions[sid][1] - z),
    )
    best_x, best_z = positions[best_id]
    if math.hypot(best_x - x, best_z - z) > COORD_TOL_MM:
        raise RuntimeError(f"No SiPM found at reflected coordinate ({x}, {z})")
    return best_id


def build_mapping_rows(
    positions: dict[int, tuple[float, float]]
) -> list[dict[str, object]]:
    source_ids = [
        sid for sid, (x, z) in positions.items() if x > 0.0 and z > 0.0
    ]
    rows: list[dict[str, object]] = []
    for source_id in sorted(source_ids):
        source_x, source_z = positions[source_id]
        for quadrant, label, x_sign, z_sign, _ in QUADRANTS:
            target_x = x_sign * source_x
            target_z = z_sign * source_z
            target_id = find_sipm_id(positions, target_x, target_z)
            rows.append(
                {
                    "source_quadrant": "Q++",
                    "source_copy": source_id,
                    "source_x_mm": f"{source_x:.6f}",
                    "source_z_mm": f"{source_z:.6f}",
                    "virtual_quadrant": quadrant,
                    "virtual_quadrant_label": label,
                    "target_copy": target_id,
                    "target_x_mm": f"{target_x:.6f}",
                    "target_z_mm": f"{target_z:.6f}",
                }
            )
    return rows


def draw_layout(
    ax: plt.Axes,
    positions: dict[int, tuple[float, float]],
) -> None:
    half = SLAB_MM / 2.0
    ax.add_patch(
        Rectangle(
            (-half, -half),
            SLAB_MM,
            SLAB_MM,
            facecolor="#f8fafc",
            edgecolor="#111827",
            linewidth=2.2,
        )
    )
    for tick in [-half, -250, 0, 250, half]:
        lw = 2.0 if tick in {0, -half, half} else 0.9
        color = "#111827" if tick in {0, -half, half} else "#9ca3af"
        ax.plot([tick, tick], [-half, half], color=color, linewidth=lw, zorder=1)
        ax.plot([-half, half], [tick, tick], color=color, linewidth=lw, zorder=1)

    for x0 in [-500.0, 0.0]:
        for z0 in [-500.0, 0.0]:
            x1 = x0 + 500.0
            z1 = z0 + 500.0
            ax.plot([x0, x1], [z0, z1], color="#60a5fa", linewidth=1.7, zorder=2)
            ax.plot([x0, x1], [z1, z0], color="#60a5fa", linewidth=1.7, zorder=2)

    for sid, (x, z) in positions.items():
        source = x > 0 and z > 0
        face = "#111827" if source else "#fef3c7"
        edge = "#111827"
        ax.add_patch(
            Rectangle(
                (x - SIPM_MM / 2.0, z - SIPM_MM / 2.0),
                SIPM_MM,
                SIPM_MM,
                facecolor=face,
                edgecolor=edge,
                linewidth=0.65,
                zorder=4,
            )
        )
        ax.text(
            x,
            z + 11,
            str(sid),
            ha="center",
            va="bottom",
            fontsize=6,
            color="#111827",
            zorder=5,
        )


def main() -> None:
    positions = build_sipm_positions()
    rows = build_mapping_rows(positions)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(10, 9), dpi=180)
    draw_layout(ax, positions)

    for row in rows:
        if row["virtual_quadrant"] == "Q++":
            continue
        source_id = int(row["source_copy"])
        target_id = int(row["target_copy"])
        source = positions[source_id]
        target = positions[target_id]
        color = next(q[4] for q in QUADRANTS if q[0] == row["virtual_quadrant"])
        arrow = FancyArrowPatch(
            source,
            target,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.0,
            color=color,
            alpha=0.58,
            shrinkA=7,
            shrinkB=7,
            connectionstyle="arc3,rad=0.06",
            zorder=3,
        )
        ax.add_patch(arrow)

    legend_x = -555
    legend_y = 555
    ax.text(
        legend_x,
        legend_y,
        "Virtual mapping from simulated Q++ SiPM copies\n"
        "Black squares: positive-quadrant source copies\n"
        "Arrows: reflected target copy columns",
        ha="left",
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#d1d5db", "pad": 5},
    )
    y = 445
    for quadrant, label, _, _, color in QUADRANTS[1:]:
        ax.plot([legend_x + 5, legend_x + 45], [y, y], color=color, linewidth=2)
        ax.text(legend_x + 55, y - 7, f"{quadrant} ({label})", fontsize=8)
        y -= 28

    ax.set_title("Face-mount virtual SiPM mapping for quadrant-expanded training")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("z [mm]")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-590, 590)
    ax.set_ylim(-590, 590)
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    print(f"Wrote {OUT_PNG}")
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
