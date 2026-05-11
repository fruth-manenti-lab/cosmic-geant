#!/usr/bin/env python3
"""Draw the proposed 1 m x 1 m face-mount SiPM layout."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


OUT = Path(__file__).with_name("facemount_1m_diagonal_sipm_preview.png")
SLAB_MM = 1000.0
CELL_MM = 250.0
SIPM_MM = 6.0
PAIR_OFFSET_MM = 59.0


def quadrant_sign(value: float) -> int:
    return 1 if value > 0 else -1


def local_diagonal_direction(xc: float, zc: float) -> tuple[float, float]:
    """Return the diagonal direction for the 250 mm square containing x/z.

    Each 500 mm quadrant contains an X. Squares on that quadrant's bottom-left
    to top-right diagonal use +45 degrees, and the other two use -45 degrees.
    The rule is applied in quadrant-local coordinates.
    """
    qx_min = 0.0 if xc > 0 else -500.0
    qz_min = 0.0 if zc > 0 else -500.0
    local_x_index = 0 if xc < qx_min + 250.0 else 1
    local_z_index = 0 if zc < qz_min + 250.0 else 1
    if local_x_index == local_z_index:
        return (1.0 / 2**0.5, 1.0 / 2**0.5)
    return (1.0 / 2**0.5, -1.0 / 2**0.5)


def main() -> None:
    fig, ax = plt.subplots(figsize=(8, 8), dpi=180)
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
        ax.plot([tick, tick], [-half, half], color=color, linewidth=lw)
        ax.plot([-half, half], [tick, tick], color=color, linewidth=lw)

    # Each 500 mm quadrant has its own X: two diagonals in each of ++, +-, -+,
    # and --.
    for x0 in [-500.0, 0.0]:
        for z0 in [-500.0, 0.0]:
            x1 = x0 + 500.0
            z1 = z0 + 500.0
            ax.plot([x0, x1], [z0, z1], color="#2563eb", linewidth=2.0, alpha=0.8)
            ax.plot([x0, x1], [z1, z0], color="#2563eb", linewidth=2.0, alpha=0.8)

    sipm_id = 0
    centers = [-375, -125, 125, 375]
    for zc in centers:
        for xc in centers:
            dx, dz = local_diagonal_direction(xc, zc)
            px = -dz
            pz = dx
            for side, color in [(-1, "#dc2626"), (1, "#16a34a")]:
                x = xc + side * PAIR_OFFSET_MM * px
                z = zc + side * PAIR_OFFSET_MM * pz
                ax.add_patch(
                    Rectangle(
                        (x - SIPM_MM / 2.0, z - SIPM_MM / 2.0),
                        SIPM_MM,
                        SIPM_MM,
                        facecolor=color,
                        edgecolor="#111827",
                        linewidth=0.5,
                    )
                )
                ax.text(
                    x,
                    z + 10,
                    str(sipm_id),
                    ha="center",
                    va="bottom",
                    fontsize=5.5,
                    color="#111827",
                )
                sipm_id += 1

    ax.set_title("Proposed face-mount layout: 1 m slab, 32 SiPMs, 2 per 250 mm square")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("z [mm]")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-560, 560)
    ax.set_ylim(-560, 560)
    ax.grid(False)
    ax.text(
        -540,
        535,
        "Blue: two diagonals per quadrant\nRed/green: paired 6 mm x 6 mm SiPMs",
        ha="left",
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#d1d5db", "pad": 4},
    )
    fig.tight_layout()
    fig.savefig(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
