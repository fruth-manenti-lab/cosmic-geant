#!/usr/bin/env python3
"""Convert the decoded David lab spectrum to a Geant4 GPS Arb spectrum file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_INPUT = Path(__file__).with_name("decoded_spectrum.csv")
DEFAULT_OUTPUT = Path(__file__).with_name("gps_background_arb_spectrum.dat")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert decoded_spectrum.csv energy/count rows to the two-column "
            "MeV weight format used by /gps/hist/file with /gps/ene/type Arb."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Decoded spectrum CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"GPS spectrum output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--drop-last-channel",
        action="store_true",
        help=(
            "Drop the final spectrum channel. Keep this off by default so the "
            "GPS file exactly follows the measured spectrum."
        ),
    )
    return parser.parse_args()


def read_spectrum(path: Path, drop_last_channel: bool) -> list[tuple[int, float, int]]:
    rows: list[tuple[int, float, int]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                (
                    int(row["channel"]),
                    float(row["energy_keV"]),
                    int(row["counts"]),
                )
            )

    if drop_last_channel and rows:
        rows = rows[:-1]
    return rows


def write_gps_spectrum(path: Path, rows: list[tuple[int, float, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="\n") as handle:
        for _channel, energy_kev, counts in rows:
            handle.write(f"{energy_kev / 1000.0:.9g} {counts}\n")


def main() -> None:
    args = parse_args()
    rows = read_spectrum(args.input, args.drop_last_channel)
    if not rows:
        raise SystemExit(f"No spectrum rows found in {args.input}")

    write_gps_spectrum(args.output, rows)

    total_counts = sum(counts for _channel, _energy_kev, counts in rows)
    first_energy = rows[0][1]
    last_energy = rows[-1][1]
    print(f"Wrote {len(rows)} GPS points to {args.output}")
    print(f"Energy range: {first_energy:.3f} to {last_energy:.3f} keV")
    print(f"Total histogram counts: {total_counts}")


if __name__ == "__main__":
    main()
