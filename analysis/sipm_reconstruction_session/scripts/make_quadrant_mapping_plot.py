#!/usr/bin/env python3
"""Write an SVG/CSV explaining positive-quadrant virtual mappings."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
RESULTS_DIR = ROOT / "results"

LANE_COUNT = 16
EXAMPLE_POINTS = [5, 15, 25, 35, 45]
QUADRANTS = [
    ("Q++", "+x,+z", 1, 1, "#16a34a"),
    ("Q-+", "-x,+z", -1, 1, "#2563eb"),
    ("Q+-", "+x,-z", 1, -1, "#ea580c"),
    ("Q--", "-x,-z", -1, -1, "#9333ea"),
]


def mirror_index(index: int) -> int:
    return LANE_COUNT - 1 - index


def map_copy(copy: int, x_sign: int, z_sign: int) -> int:
    """Map a positive-quadrant SiPM copy to a virtual quadrant copy."""
    if 100 <= copy <= 115:
        index = copy - 100
        if x_sign < 0:
            index = mirror_index(index)
        family = 200 if z_sign < 0 else 100
        return family + index
    if 200 <= copy <= 215:
        index = copy - 200
        if x_sign < 0:
            index = mirror_index(index)
        family = 100 if z_sign < 0 else 200
        return family + index
    if 300 <= copy <= 315:
        index = copy - 300
        if z_sign < 0:
            index = mirror_index(index)
        family = 400 if x_sign < 0 else 300
        return family + index
    if 400 <= copy <= 415:
        index = copy - 400
        if z_sign < 0:
            index = mirror_index(index)
        family = 300 if x_sign < 0 else 400
        return family + index
    raise ValueError(f"Unsupported SiPM copy number: {copy}")


def svg_text(x: float, y: float, text: str, **attrs: str) -> str:
    defaults = {"font-size": "14", "fill": "#111827"}
    defaults.update(attrs)
    attr_text = " ".join(f'{key}="{escape(value)}"' for key, value in defaults.items())
    return f'<text x="{x:.1f}" y="{y:.1f}" {attr_text}>{escape(text)}</text>'


def svg_line(x1: float, y1: float, x2: float, y2: float, **attrs: str) -> str:
    defaults = {"stroke": "#111827", "stroke-width": "1"}
    defaults.update(attrs)
    attr_text = " ".join(f'{key}="{escape(value)}"' for key, value in defaults.items())
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {attr_text}/>'


def svg_rect(x: float, y: float, w: float, h: float, **attrs: str) -> str:
    defaults = {"fill": "none", "stroke": "#111827", "stroke-width": "1"}
    defaults.update(attrs)
    attr_text = " ".join(f'{key}="{escape(value)}"' for key, value in defaults.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" {attr_text}/>'


def svg_circle(cx: float, cy: float, r: float, **attrs: str) -> str:
    defaults = {"fill": "#111827"}
    defaults.update(attrs)
    attr_text = " ".join(f'{key}="{escape(value)}"' for key, value in defaults.items())
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" {attr_text}/>'


def map_plot_x(x_cm: float) -> float:
    return 90 + (x_cm + 55) * 5.0


def map_plot_y(z_cm: float) -> float:
    return 640 - (z_cm + 55) * 5.0


def channel_plot_x(x_cm: float) -> float:
    return 965 + (x_cm + 63) * 2.95


def channel_plot_y(z_cm: float) -> float:
    return 875 - (z_cm + 63) * 2.95


def grouped_mapping_text(x_sign: int, z_sign: int) -> list[str]:
    groups = [
        (100, "+z z-fiber", "100+i"),
        (200, "-z z-fiber", "200+i"),
        (300, "+x x-fiber", "300+i"),
        (400, "-x x-fiber", "400+i"),
    ]
    rows = []
    for base, label, source in groups:
        mapped_first = map_copy(base, x_sign, z_sign)
        mapped_last = map_copy(base + 15, x_sign, z_sign)
        if mapped_first < mapped_last:
            target = f"{mapped_first}-{mapped_last}"
        else:
            target = f"{mapped_first}-{mapped_last} reversed"
        rows.append(f"{source:5s} ({label}) -> {target}")
    return rows


def write_mapping_csv(path: Path) -> None:
    copies = list(range(100, 116)) + list(range(200, 216)) + list(range(300, 316)) + list(range(400, 416))
    rows = []
    for qkey, qlabel, x_sign, z_sign, _ in QUADRANTS:
        for copy in copies:
            rows.append(
                {
                    "quadrant": qkey,
                    "quadrant_label": qlabel,
                    "source_copy_positive_quadrant": copy,
                    "virtual_copy_in_quadrant": map_copy(copy, x_sign, z_sign),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def build_svg() -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="980" viewBox="0 0 1500 980">',
        "<defs>",
        '<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">',
        '<path d="M0,0 L8,4 L0,8 z" fill="context-stroke"/>',
        "</marker>",
        "</defs>",
        svg_rect(0, 0, 1500, 980, fill="#ffffff", stroke="none"),
        svg_text(
            45,
            45,
            "Positive-quadrant virtual training mapping for double-ended SiPM geometry",
            **{"font-size": "24", "font-weight": "700"},
        ),
        svg_text(
            45,
            75,
            "Use reflections in x and z, not 90-degree rotations, so x-running and z-running fiber families stay distinct.",
            **{"font-size": "15", "fill": "#374151"},
        ),
    ]

    # Position mapping panel.
    parts.append(svg_text(55, 120, "1. Position labels", **{"font-size": "19", "font-weight": "700"}))
    for coord in range(-50, 51, 10):
        x = map_plot_x(coord)
        y = map_plot_y(coord)
        parts.append(svg_line(x, map_plot_y(-50), x, map_plot_y(50), stroke="#e5e7eb"))
        parts.append(svg_line(map_plot_x(-50), y, map_plot_x(50), y, stroke="#e5e7eb"))
    parts.append(svg_rect(map_plot_x(-50), map_plot_y(50), 500, 500, stroke="#111827", **{"stroke-width": "2"}))
    parts.append(svg_rect(map_plot_x(0), map_plot_y(50), 250, 250, fill="#dcfce7", stroke="#16a34a", opacity="0.55"))
    parts.append(svg_line(map_plot_x(0), map_plot_y(-52), map_plot_x(0), map_plot_y(52), stroke="#111827", **{"stroke-width": "1.5"}))
    parts.append(svg_line(map_plot_x(-52), map_plot_y(0), map_plot_x(52), map_plot_y(0), stroke="#111827", **{"stroke-width": "1.5"}))
    parts.append(svg_text(map_plot_x(7), map_plot_y(53), "simulated training quadrant", **{"font-size": "13", "fill": "#166534"}))
    parts.append(svg_text(map_plot_x(51), map_plot_y(-2), "x", **{"font-size": "13"}))
    parts.append(svg_text(map_plot_x(2), map_plot_y(52), "z", **{"font-size": "13"}))

    for qkey, _, x_sign, z_sign, color in QUADRANTS:
        for x in EXAMPLE_POINTS:
            for z in EXAMPLE_POINTS:
                vx, vz = x_sign * x, z_sign * z
                if x_sign < 0 or z_sign < 0:
                    parts.append(
                        svg_line(
                            map_plot_x(vx),
                            map_plot_y(vz),
                            map_plot_x(x),
                            map_plot_y(z),
                            stroke=color,
                            opacity="0.22",
                            **{"stroke-width": "0.8", "marker-end": "url(#arrow)"},
                        )
                    )
                parts.append(svg_circle(map_plot_x(vx), map_plot_y(vz), 3.0, fill=color, opacity="0.9"))
        label_x = 31 * x_sign if x_sign > 0 else 35 * x_sign
        label_z = 31 * z_sign if z_sign > 0 else 35 * z_sign
        parts.append(svg_text(map_plot_x(label_x) - 16, map_plot_y(label_z), qkey, fill=color, **{"font-size": "18", "font-weight": "700"}))

    parts.append(svg_text(55, 700, "Positive training point (x,z) becomes virtual labels (x,z), (-x,z), (x,-z), (-x,-z).", **{"font-size": "14", "fill": "#374151"}))
    parts.append(svg_text(55, 723, "The arrows show folding direction for test events: a measured point in any quadrant folds to (abs(x), abs(z)).", **{"font-size": "14", "fill": "#374151"}))

    # SiPM mapping table.
    parts.append(svg_text(760, 120, "2. SiPM count-vector permutation", **{"font-size": "19", "font-weight": "700"}))
    y = 153
    for qkey, qlabel, x_sign, z_sign, color in QUADRANTS:
        x_expr = "x" if x_sign > 0 else "-x"
        z_expr = "z" if z_sign > 0 else "-z"
        parts.append(svg_text(775, y, f"{qkey} ({qlabel}): label -> ({x_expr}, {z_expr})", fill=color, **{"font-size": "15", "font-weight": "700"}))
        y += 24
        for row in grouped_mapping_text(x_sign, z_sign):
            parts.append(svg_text(800, y, row, **{"font-size": "13", "font-family": "Consolas,monospace"}))
            y += 20
        y += 16
    parts.append(svg_text(775, y + 5, "Mappings are source positive-quadrant copy -> virtual quadrant copy.", **{"font-size": "13", "fill": "#374151"}))
    parts.append(svg_text(775, y + 26, "Each reflection is self-inverse, so the same rule can be read backward when folding test events.", **{"font-size": "13", "fill": "#374151"}))

    # Channel schematic.
    parts.append(svg_text(760, 640, "3. Double-ended channel families", **{"font-size": "19", "font-weight": "700"}))
    parts.append(svg_rect(channel_plot_x(-50), channel_plot_y(50), 295, 295, stroke="#111827", **{"stroke-width": "2"}))
    lanes = [-46.875 + i * 6.25 for i in range(16)]
    for i, x in enumerate(lanes):
        parts.append(svg_line(channel_plot_x(x), channel_plot_y(-50), channel_plot_x(x), channel_plot_y(50), stroke="#2563eb", opacity="0.52", **{"stroke-width": "1.5"}))
        parts.append(svg_text(channel_plot_x(x) - 10, channel_plot_y(58), str(100 + i), **{"font-size": "8"}))
        parts.append(svg_text(channel_plot_x(x) - 10, channel_plot_y(-60), str(200 + i), **{"font-size": "8"}))
    for i, z in enumerate(lanes):
        parts.append(svg_line(channel_plot_x(-50), channel_plot_y(z), channel_plot_x(50), channel_plot_y(z), stroke="#ea580c", opacity="0.52", **{"stroke-width": "1.5"}))
        parts.append(svg_text(channel_plot_x(55), channel_plot_y(z) + 3, str(300 + i), **{"font-size": "8"}))
        parts.append(svg_text(channel_plot_x(-64), channel_plot_y(z) + 3, str(400 + i), **{"font-size": "8"}))
    parts.append(svg_text(channel_plot_x(3), channel_plot_y(62), "+z: 100-115", **{"font-size": "13"}))
    parts.append(svg_text(channel_plot_x(3), channel_plot_y(-66), "-z: 200-215", **{"font-size": "13"}))
    parts.append(svg_text(channel_plot_x(58), channel_plot_y(0), "+x: 300-315", **{"font-size": "13"}))
    parts.append(svg_text(channel_plot_x(-92), channel_plot_y(0), "-x: 400-415", **{"font-size": "13"}))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    svg_path = FIGURES_DIR / "positive_quadrant_virtual_mapping.svg"
    svg_path.write_text(build_svg(), encoding="utf-8")
    write_mapping_csv(RESULTS_DIR / "positive_quadrant_sipm_mapping.csv")

    print(f"Wrote {svg_path}")
    print(f"Wrote {RESULTS_DIR / 'positive_quadrant_sipm_mapping.csv'}")


if __name__ == "__main__":
    main()
