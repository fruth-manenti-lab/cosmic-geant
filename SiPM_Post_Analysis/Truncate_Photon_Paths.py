'''
Run the file through: (it reads all CSV files in a directory and outputs to a 'trimmed' subfolder)

python Truncate_Photo_Paths.py /path/to/build/output
'''

import os
import glob
import argparse
import pandas as pd


def line_intersection(p1, p2, p3, p4):
    """Intersection of segment P1-P2 with segment P3-P4 in the (x, z) plane.

    Returns (x, z) if the two segments cross, else None.
    """
    x1, z1 = p1
    x2, z2 = p2
    x3, z3 = p3
    x4, z4 = p4

    denom = (x1 - x2) * (z3 - z4) - (z1 - z2) * (x3 - x4)
    if denom == 0:
        return None  # parallel / degenerate

    t = ((x1 - x3) * (z3 - z4) - (z1 - z3) * (x3 - x4)) / denom
    u = ((x1 - x3) * (z1 - z2) - (z1 - z3) * (x1 - x2)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        return (x1 + t * (x2 - x1), z1 + t * (z2 - z1))
    return None


def _read_ntuple_chunks(input_file, chunk_size):
    """Yield DataFrame chunks, transparently handling either a raw tools::wcsv
    ntuple (with '#column' / '#separator' header lines) or a plain headered CSV.
    """
    columns, sep, is_wcsv = [], ",", False
    with open(input_file) as f:
        for line in f:
            if not line.startswith("#"):
                break
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0] == "#column":
                columns.append(parts[-1]); is_wcsv = True
            elif len(parts) >= 2 and parts[0] == "#separator":
                sep = chr(int(parts[1]))

    if is_wcsv:
        return pd.read_csv(input_file, sep=sep, comment="#", header=None,
                           names=columns, chunksize=chunk_size)
    return pd.read_csv(input_file, chunksize=chunk_size)


def filter_photons_by_sipm(
    input_file,
    output_file,
    sipm_centers,         # list of (x, z) centres
    sipm_size=6.0,
    chunk_size=100000,
):
    EVENT_COL = "EventID"
    ID_COL = "TrackID"
    STEP_COL = "StepID"
    X_COL = "XPosition"
    Z_COL = "ZPosition"

    half = sipm_size / 2.0
    # Each SiPM is a horizontal segment at depth z = cz spanning x in [cx-h, cx+h].
    sipm_segments = [((cx - half, cz), (cx + half, cz)) for cx, cz in sipm_centers]

    dead = set()            # keys (event, track) already absorbed at a SiPM
    last_pos = {}           # key -> last (x, z) seen
    first_chunk = True

    for chunk in _read_ntuple_chunks(input_file, chunk_size):
        has_event = EVENT_COL in chunk.columns
        sort_cols = ([EVENT_COL] if has_event else []) + [ID_COL, STEP_COL]
        chunk = chunk.sort_values(by=sort_cols).reset_index(drop=True)
        keep_rows = []

        for _, row in chunk.iterrows():
            key = (row[EVENT_COL] if has_event else 0, row[ID_COL])

            if key in dead:
                continue

            cur = (row[X_COL], row[Z_COL])

            if key not in last_pos:          # first point of this trajectory
                last_pos[key] = cur
                keep_rows.append(row)
                continue

            hit_pt = None
            for s_p1, s_p2 in sipm_segments:
                hit_pt = line_intersection(last_pos[key], cur, s_p1, s_p2)
                if hit_pt is not None:
                    break

            if hit_pt is not None:
                # snap the final recorded step onto the SiPM face, then retire it
                row[X_COL], row[Z_COL] = hit_pt[0], hit_pt[1]
                keep_rows.append(row)
                dead.add(key)
                last_pos.pop(key, None)
            else:
                keep_rows.append(row)
                last_pos[key] = cur

        if keep_rows:
            out = pd.DataFrame(keep_rows)
            out.to_csv(output_file, index=False,
                       mode="w" if first_chunk else "a", header=first_chunk)
            first_chunk = False

    print(f"Successfully processed: {os.path.basename(input_file)}")

def parse_sipms(spec):
    """Parse SiPM centres from an inline spec 'x,z;x,z;...' or a file path.

    A file may contain one 'x,z' per line, or be a CSV with two columns
    (header optional). Returns a list of (x, z) tuples, or [] if spec is None.
    """
    if not spec:
        return []
    centers = []
    if os.path.exists(spec):
        with open(spec) as f:
            for line in f:
                line = line.strip()
                if not line or line[0].isalpha():   # skip blanks / header rows
                    continue
                parts = line.replace(",", " ").split()
                centers.append((float(parts[0]), float(parts[1])))
    else:
        for pair in spec.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            x, z = (float(v) for v in pair.split(","))
            centers.append((x, z))
    return centers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trim photon paths at SiPM crossings for every CSV in a directory. "
                    "Output goes to a 'trimmed' subfolder inside the input directory."
    )
    parser.add_argument("input_dir",
                        help="directory containing the input ntuple CSV files")
    parser.add_argument("--sipms", default=None,
                   help="SiPM centres to overlay: inline 'x,z;x,z;...' or a path to "
                        "a file with one 'x,z' per line")
    args = parser.parse_args()

    INPUT_DIR = args.input_dir
    OUTPUT_DIR = os.path.join(INPUT_DIR, "trimmed")

    MY_SIPMS = parse_sipms(args.sipms)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {INPUT_DIR}")

    for file_path in csv_files:
        out_path = os.path.join(OUTPUT_DIR, f"truncated_{os.path.basename(file_path)}")
        filter_photons_by_sipm(
            input_file=file_path,
            output_file=out_path,
            sipm_centers=MY_SIPMS,
            sipm_size=6,
            chunk_size=500,
        )

