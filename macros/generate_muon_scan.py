from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import tempfile


DEFAULT_NUM_POINTS = 1000
DEFAULT_POSITION_UNIT = "cm"
UNIT_SCALE_FROM_MM = {
    "mm": 1.0,
    "cm": 0.1,
    "m": 0.001,
}


def eval_expr(expr: str, variables: dict[str, float]) -> float:
    node = ast.parse(expr, mode="eval")

    def _eval(current: ast.AST) -> float:
        if isinstance(current, ast.Expression):
            return _eval(current.body)
        if isinstance(current, ast.Constant) and isinstance(current.value, (int, float)):
            return float(current.value)
        if isinstance(current, ast.UnaryOp) and isinstance(current.op, (ast.UAdd, ast.USub)):
            value = _eval(current.operand)
            return value if isinstance(current.op, ast.UAdd) else -value
        if isinstance(current, ast.BinOp) and isinstance(
            current.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left = _eval(current.left)
            right = _eval(current.right)
            if isinstance(current.op, ast.Add):
                return left + right
            if isinstance(current.op, ast.Sub):
                return left - right
            if isinstance(current.op, ast.Mult):
                return left * right
            return left / right
        if isinstance(current, ast.Name):
            if current.id not in variables:
                raise KeyError(f"Unknown variable in GDML expression: {current.id}")
            return variables[current.id]
        raise ValueError(f"Unsupported GDML expression: {expr}")

    return _eval(node)


def load_gdml_variables(gdml_path: Path) -> dict[str, float]:
    text = gdml_path.read_text()
    pattern = re.compile(r'<variable name="([^"]+)" value="([^"]+)"\s*/>')
    raw_variables = dict(pattern.findall(text))
    resolved: dict[str, float] = {}

    while len(resolved) < len(raw_variables):
        progressed = False
        for name, expr in raw_variables.items():
            if name in resolved:
                continue
            try:
                resolved[name] = eval_expr(expr, resolved)
            except KeyError:
                continue
            progressed = True
        if not progressed:
            missing = sorted(set(raw_variables) - set(resolved))
            raise ValueError(f"Could not resolve GDML variables: {missing}")

    return resolved


def choose_grid_dimensions(num_points: int) -> tuple[int, int]:
    best_pair = (1, num_points)
    best_difference = num_points - 1

    for x_points in range(1, int(num_points**0.5) + 1):
        if num_points % x_points != 0:
            continue
        z_points = num_points // x_points
        difference = abs(z_points - x_points)
        if difference < best_difference:
            best_pair = (x_points, z_points)
            best_difference = difference

    return best_pair


def build_scan_positions(
    slab_half_xy: float, source_y: float, x_points: int, z_points: int
) -> list[tuple[float, float, float]]:
    x_step = (2.0 * slab_half_xy) / (x_points + 1)
    z_step = (2.0 * slab_half_xy) / (z_points + 1)

    xs = [-slab_half_xy + x_step * (index + 1) for index in range(x_points)]
    zs = [-slab_half_xy + z_step * (index + 1) for index in range(z_points)]

    return [(x, source_y, z) for z in zs for x in xs]


def parse_position_line(position_line: str) -> tuple[float, float, str]:
    parts = position_line.split()
    if len(parts) not in (4, 5):
        raise ValueError(f"Unsupported /gps/position line: {position_line}")

    source_y = float(parts[2])
    unit = parts[4] if len(parts) == 5 else DEFAULT_POSITION_UNIT
    if unit not in UNIT_SCALE_FROM_MM:
        raise ValueError(f"Unsupported source position unit in {position_line}: {unit}")

    return source_y, UNIT_SCALE_FROM_MM[unit], unit


def load_template_lines(muon_mac_path: Path) -> tuple[list[str], str, float, float, str]:
    active_lines = []
    beam_on_line = None
    source_y = None
    unit_scale_from_mm = None
    unit = None

    for line in muon_mac_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("/run/beamOn"):
            beam_on_line = stripped
            continue
        if stripped.startswith("/gps/position"):
            source_y, unit_scale_from_mm, unit = parse_position_line(stripped)
            continue
        if stripped.startswith("/gps/pos/centre"):
            continue
        active_lines.append(stripped)

    if beam_on_line is None:
        raise ValueError(f"No active /run/beamOn line found in {muon_mac_path}")
    if source_y is None:
        raise ValueError(f"No active /gps/position line found in {muon_mac_path}")

    return active_lines, beam_on_line, source_y, unit_scale_from_mm, unit


def format_position_line(position: tuple[float, float, float], unit: str) -> str:
    x, y, z = position
    return f"/gps/position {x:.6f} {y:.6f} {z:.6f} {unit}"


def build_header_comments(num_points: int, x_points: int, z_points: int) -> list[str]:
    return [
        f"# Muon scan generated by generate_muon_scan.py",
        f"# Grid dimensions: {z_points} rows by {x_points} columns",
        f"# Total scan points: {num_points}",
    ]


def build_visualization_lines() -> list[str]:
    return [
        "/vis/viewer/set/autoRefresh false",
        "/vis/scene/endOfEventAction accumulate -1",
        "/vis/scene/endOfRunAction accumulate",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a muon scan macro over the top face of the slab."
    )
    parser.add_argument(
        "num_points",
        nargs="?",
        type=int,
        default=DEFAULT_NUM_POINTS,
        help=f"Total number of scan points to generate. Default: {DEFAULT_NUM_POINTS}.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.num_points <= 0:
        raise ValueError("num_points must be a positive integer")

    macros_dir = Path(__file__).resolve().parent
    repo_root = macros_dir.parent

    muon_mac_path = macros_dir / "muon.mac"
    output_mac_path = macros_dir / "muon_scan.mac"
    gdml_path = repo_root / "geometry" / "final.gdml"

    variables = load_gdml_variables(gdml_path)
    slab_half_xy_mm = variables["slab_half_xy"]
    template_lines, beam_on_line, source_y, unit_scale_from_mm, unit = load_template_lines(
        muon_mac_path
    )
    x_points, z_points = choose_grid_dimensions(args.num_points)
    slab_half_xy = slab_half_xy_mm * unit_scale_from_mm
    positions = build_scan_positions(slab_half_xy, source_y, x_points, z_points)

    output_lines = build_header_comments(len(positions), x_points, z_points)
    output_lines.extend(template_lines)
    output_lines.extend(build_visualization_lines())
    for position in positions:
        output_lines.append(format_position_line(position, unit))
        output_lines.append(beam_on_line)
    output_lines.append("/vis/viewer/set/autoRefresh true")
    output_lines.append("/vis/viewer/refresh")

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output_mac_path.parent, delete=False
    ) as handle:
        handle.write("\n".join(output_lines) + "\n")
        temp_path = Path(handle.name)
    temp_path.replace(output_mac_path)

    x_step = (2.0 * slab_half_xy_mm) / (x_points + 1)
    z_step = (2.0 * slab_half_xy_mm) / (z_points + 1)
    print(
        f"Wrote {len(positions)} scan points to {output_mac_path} "
        f"using a {x_points} x {z_points} grid "
        f"(x step {x_step:.6f} mm, z step {z_step:.6f} mm, y {source_y:.6f} {unit})"
    )


if __name__ == "__main__":
    main()
