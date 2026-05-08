#!/usr/bin/env python3
"""Draw schematic top views of the three SiPM readout geometries."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "figures"
LANES = np.linspace(-46.875, 46.875, 16)


GEOMETRIES = [
    {
        "key": "geom-final-stubs-pos",
        "title": "Baseline: stubs, positive-side SiPMs",
        "stubbed": True,
        "mode": "positive",
        "notes": ["external fiber stubs", "SiPMs on +z and +x"],
    },
    {
        "key": "geom-nostubs-pos",
        "title": "No stubs, positive-side SiPMs",
        "stubbed": False,
        "mode": "positive",
        "notes": ["direct fiber-end coupling", "same readout pattern as baseline"],
    },
    {
        "key": "geom-nostubs-alt",
        "title": "No stubs, alternating-side SiPMs",
        "stubbed": False,
        "mode": "alternating",
        "notes": ["direct fiber-end coupling", "readout alternates by lane"],
    },
    {
        "key": "geom-stubs-alt",
        "title": "Stubs, alternating-side SiPMs",
        "stubbed": True,
        "mode": "alternating",
        "notes": ["external fiber stubs", "readout alternates by lane"],
    },
]


def draw_schematic(ax: plt.Axes, config: dict[str, object]) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-63, 63)
    ax.set_ylim(-63, 63)
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("z [cm]")
    ax.grid(alpha=0.18)
    ax.add_patch(Rectangle((-50, -50), 100, 100, fill=False, lw=2.2, ec="#111827"))
    ax.text(-49, 52.5, "detector face", fontsize=8, color="#111827")

    fiber_z_color = "#2563eb"
    fiber_x_color = "#ea580c"
    stub_color = "#6b7280"
    sipm_color = "#111827"
    grease_color = "#22c55e"

    for i, x in enumerate(LANES):
        ax.plot([x, x], [-50, 50], color=fiber_z_color, lw=1.4, alpha=0.55)
        if config["stubbed"]:
            ax.plot([x, x], [-56, -50], color=stub_color, lw=1.2, ls="--", alpha=0.85)
            ax.plot([x, x], [50, 56], color=stub_color, lw=1.2, ls="--", alpha=0.85)

        side = 1 if config["mode"] == "positive" or i % 2 == 0 else -1
        z_sipm = side * 57
        z_grease = side * 52.5
        ax.add_patch(Rectangle((x - 0.9, z_grease - 0.9), 1.8, 1.8, fc=grease_color, ec="none"))
        ax.add_patch(Rectangle((x - 1.4, z_sipm - 1.4), 2.8, 2.8, fc=sipm_color, ec="white", lw=0.5))

    for i, z in enumerate(LANES):
        ax.plot([-50, 50], [z, z], color=fiber_x_color, lw=1.4, alpha=0.55)
        if config["stubbed"]:
            ax.plot([-56, -50], [z, z], color=stub_color, lw=1.2, ls="--", alpha=0.85)
            ax.plot([50, 56], [z, z], color=stub_color, lw=1.2, ls="--", alpha=0.85)

        side = 1 if config["mode"] == "positive" or i % 2 == 0 else -1
        x_sipm = side * 57
        x_grease = side * 52.5
        ax.add_patch(Rectangle((x_grease - 0.9, z - 0.9), 1.8, 1.8, fc=grease_color, ec="none"))
        ax.add_patch(Rectangle((x_sipm - 1.4, z - 1.4), 2.8, 2.8, fc=sipm_color, ec="white", lw=0.5))

    ax.set_title(config["title"], fontsize=11, weight="bold")
    note = "\n".join(config["notes"])
    ax.text(-61, -61, note, fontsize=8, va="bottom", color="#374151")


def add_legend(fig: plt.Figure) -> None:
    handles = [
        Line2D([0], [0], color="#2563eb", lw=2, label="z-running fiber set, SiPM 100-115"),
        Line2D([0], [0], color="#ea580c", lw=2, label="x-running fiber set, SiPM 300-315"),
        Line2D([0], [0], color="#6b7280", lw=2, ls="--", label="external stub"),
        Rectangle((0, 0), 1, 1, fc="#22c55e", label="grease/contact"),
        Rectangle((0, 0), 1, 1, fc="#111827", label="SiPM"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=9)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(11, 11), constrained_layout=True)
    axes = axes.ravel()
    for ax, config in zip(axes, GEOMETRIES):
        draw_schematic(ax, config)
    fig.suptitle("SiPM Readout Geometry Schematics", fontsize=15, weight="bold")
    add_legend(fig)
    fig.savefig(OUT_DIR / "geometry_schematic_comparison.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    for config in GEOMETRIES:
        fig, ax = plt.subplots(figsize=(6.2, 6.2), constrained_layout=True)
        draw_schematic(ax, config)
        add_legend(fig)
        fig.savefig(OUT_DIR / f"{config['key']}_schematic.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

    print(f"Wrote schematics to {OUT_DIR}")


if __name__ == "__main__":
    main()
