#!/usr/bin/env python3
"""Draw a proposed hybrid face-mount plus fiber-end SiPM layout."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle


OUT = Path(__file__).with_name("hybrid_facemount_fiber_preview.png")

SLAB_MM = 1000.0
CELL_MM = 250.0
FACE_SIPM_MM = 6.0
FIBER_SIPM_MM = 1.0

# 4x4 cell centers.
FACE_CENTERS_MM = [-375.0, -125.0, 125.0, 375.0]

# Real groove/lane positions from the final GDML family:
# lane_start=-468.75 mm, lane_pitch=62.5 mm, 16 lanes.
LANE_START_MM = -468.75
LANE_PITCH_MM = 62.5
LANES_MM = [LANE_START_MM + i * LANE_PITCH_MM for i in range(16)]

# User-specified side row indices. For +z/-z, indices run left-to-right. For
# +x/-x, indices run top-to-bottom, so they are mapped through the reversed
# z-lane list.
PLUS_Z_INDICES = [0, 4, 8, 12]
MINUS_Z_INDICES = [2, 6, 10, 14]
PLUS_X_INDICES = [0, 4, 8, 12]
MINUS_X_INDICES = [2, 6, 10, 14]
PLUS_Z_POSITIONS_MM = [LANES_MM[index] for index in PLUS_Z_INDICES]
MINUS_Z_POSITIONS_MM = [LANES_MM[index] for index in MINUS_Z_INDICES]
TOP_TO_BOTTOM_LANES_MM = list(reversed(LANES_MM))
PLUS_X_POSITIONS_MM = [TOP_TO_BOTTOM_LANES_MM[index] for index in PLUS_X_INDICES]
MINUS_X_POSITIONS_MM = [TOP_TO_BOTTOM_LANES_MM[index] for index in MINUS_X_INDICES]
SIDE_OFFSET_MM = 35.0


def draw_sipm_square(
    ax: plt.Axes,
    x: float,
    z: float,
    size: float,
    color: str,
    label: str,
    text_offset: tuple[float, float] = (0.0, 13.0),
) -> None:
    ax.add_patch(
        Rectangle(
            (x - size / 2.0, z - size / 2.0),
            size,
            size,
            facecolor=color,
            edgecolor="#111827",
            linewidth=0.65,
            zorder=5,
        )
    )
    ax.text(
        x + text_offset[0],
        z + text_offset[1],
        label,
        ha="center",
        va="bottom",
        fontsize=6,
        color="#111827",
        zorder=6,
    )


def main() -> None:
    half = SLAB_MM / 2.0
    fig, ax = plt.subplots(figsize=(9.2, 9.2), dpi=180)

    ax.add_patch(
        Rectangle(
            (-half, -half),
            SLAB_MM,
            SLAB_MM,
            facecolor="#f8fafc",
            edgecolor="#111827",
            linewidth=2.2,
            zorder=1,
        )
    )

    for tick in [-half, -250.0, 0.0, 250.0, half]:
        lw = 2.0 if tick in {-half, 0.0, half} else 0.9
        color = "#111827" if tick in {-half, 0.0, half} else "#9ca3af"
        ax.plot([tick, tick], [-half, half], color=color, linewidth=lw, zorder=2)
        ax.plot([-half, half], [tick, tick], color=color, linewidth=lw, zorder=2)

    # Face-mounted SiPMs: one 6 mm sensor at the center of each 1/16 slab cell.
    face_id = 0
    for z in FACE_CENTERS_MM:
        for x in FACE_CENTERS_MM:
            draw_sipm_square(ax, x, z, FACE_SIPM_MM, "#2563eb", f"F{face_id}")
            face_id += 1

    # Fiber-end SiPMs: four 1 mm sensors on each side, using known groove
    # positions and the explicit side-row index selections above.
    fiber_id = 0
    fiber_color_z = "#16a34a"
    fiber_color_x = "#f97316"
    sipm_color = "#dc2626"
    grease_color = "#38bdf8"

    for x in PLUS_Z_POSITIONS_MM:
        ax.plot([x, x], [-half, half], color=fiber_color_z, linewidth=1.25, alpha=0.5, zorder=3)
        top_z = half + SIDE_OFFSET_MM
        ax.add_patch(Circle((x, half + 8.0), 6.5, facecolor=grease_color, edgecolor="none", alpha=0.55, zorder=4))
        draw_sipm_square(ax, x, top_z, FIBER_SIPM_MM * 8.0, sipm_color, f"S{fiber_id}", (0, 9))
        fiber_id += 1

    for x in MINUS_Z_POSITIONS_MM:
        ax.plot([x, x], [-half, half], color=fiber_color_z, linewidth=1.25, alpha=0.5, zorder=3)
        bottom_z = -half - SIDE_OFFSET_MM
        ax.add_patch(Circle((x, -half - 8.0), 6.5, facecolor=grease_color, edgecolor="none", alpha=0.55, zorder=4))
        draw_sipm_square(ax, x, bottom_z, FIBER_SIPM_MM * 8.0, sipm_color, f"S{fiber_id}", (0, -20))
        fiber_id += 1

    for z in PLUS_X_POSITIONS_MM:
        ax.plot([-half, half], [z, z], color=fiber_color_x, linewidth=1.25, alpha=0.5, zorder=3)
        right_x = half + SIDE_OFFSET_MM
        ax.add_patch(Circle((half + 8.0, z), 6.5, facecolor=grease_color, edgecolor="none", alpha=0.55, zorder=4))
        draw_sipm_square(ax, right_x, z, FIBER_SIPM_MM * 8.0, sipm_color, f"S{fiber_id}", (0, 9))
        fiber_id += 1

    for z in MINUS_X_POSITIONS_MM:
        ax.plot([-half, half], [z, z], color=fiber_color_x, linewidth=1.25, alpha=0.5, zorder=3)
        left_x = -half - SIDE_OFFSET_MM
        ax.add_patch(Circle((-half - 8.0, z), 6.5, facecolor=grease_color, edgecolor="none", alpha=0.55, zorder=4))
        draw_sipm_square(ax, left_x, z, FIBER_SIPM_MM * 8.0, sipm_color, f"S{fiber_id}", (0, 9))
        fiber_id += 1

    corner_clear_mm = 150.0
    for x0 in [-half, half - corner_clear_mm]:
        for z0 in [-half, half - corner_clear_mm]:
            ax.add_patch(
                Rectangle(
                    (x0, z0),
                    corner_clear_mm,
                    corner_clear_mm,
                    facecolor="none",
                    edgecolor="#a855f7",
                    linewidth=1.0,
                    linestyle=":",
                    alpha=0.65,
                    zorder=7,
                )
            )

    handles = [
        Rectangle((0, 0), 1, 1, fc="#2563eb", ec="#111827", label="16 face SiPMs, 6 mm x 6 mm"),
        Rectangle((0, 0), 1, 1, fc="#dc2626", ec="#111827", label="16 fiber-end SiPMs, 1 mm class"),
        Line2D([0], [0], color=fiber_color_z, lw=2, label="selected z-running grooves"),
        Line2D([0], [0], color=fiber_color_x, lw=2, label="selected x-running grooves"),
        Circle((0, 0), 1, fc=grease_color, ec="none", alpha=0.55, label="fiber coupling/grease"),
        Rectangle((0, 0), 1, 1, fc="none", ec="#a855f7", ls=":", label="corner-clear zones"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.065), ncol=2, frameon=False, fontsize=8)

    ax.set_title("Hybrid 32-channel concept: 16 face-mount + 16 alternating fiber-end SiPMs")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("z [mm]")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-610, 610)
    ax.set_ylim(-610, 610)
    ax.text(
        -590,
        585,
        "Fiber grooves use GDML lane_start=-468.75 mm, pitch=62.5 mm\n"
        "+z: 0,4,8,12; -z: 2,6,10,14; +x: 0,4,8,12; -x: 2,6,10,14",
        ha="left",
        va="top",
        fontsize=8.5,
        bbox={"facecolor": "white", "edgecolor": "#d1d5db", "pad": 5},
    )
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
