import os
import glob
import pandas as pd
import numpy as np


def line_intersection(p1, p2, p3, p4):
    """
    Finds the intersection of segment P1-P2 and segment P3-P4.
    Returns (x, z) if they intersect, or None if they don't.
    """
    x1, z1 = p1
    x2, z2 = p2
    x3, z3 = p3
    x4, z4 = p4

    denom = (x1 - x2) * (z3 - z4) - (z1 - z2) * (x3 - x4)
    if denom == 0:
        return None  # Parallel lines

    # Determinant approach for line-segment intersection
    t = ((x1 - x3) * (z3 - z4) - (z1 - z3) * (x3 - x4)) / denom
    u = ((x1 - x2) * (z1 - z3) - (z1 - z2) * (x1 - x3)) / denom

    # If t and u are between 0 and 1, the segments intersect
    if 0 <= t <= 1 and 0 <= u <= 1:
        intersect_x = x1 + t * (x2 - x1)
        intersect_z = z1 + t * (z2 - z1)
        return (intersect_x, intersect_z)
    
    return None

def filter_photons_by_sipm(
    input_file, # str - Path to the source CSV
    output_file, # str - Path to save the trimmed CSV
    sipm_centers, # list of tuples/lists, 8 pairs of (x, y) coordinates
    sipm_size=6.0, 
):
    ID_COL = "TrackID"
    STEP_COL = "StepID"
    X_COL = "XPosition"
    Y_COL = "YPosition"
    
    half_size = sipm_size / 2.0
    sipm_bounds = []
    for cx, cy in sipm_centers:
        sipm_bounds.append({
            'x_min': cx - half_size, 'x_max': cx + half_size,
            'y_min': cy - half_size, 'y_max': cy + half_size
        })

    dead_photons = set() # To track dead photons 
    first_chunk = True

    # Read the file in chunks
    chunks = pd.read_csv(input_file, chunksize=chunk_size)

   for chunk in chunks:
        chunk = chunk.sort_values(by=[ID_COL, STEP_COL]).reset_index(drop=True)
        keep_rows = []

        for idx, row in chunk.iterrows():
            p_id = row[ID_COL]

            if p_id in dead_photons:
                continue

            current_x = row[X_COL]
            current_z = row[Z_COL]
            current_pos = (current_x, current_z)

            if p_id not in last_positions:
                last_positions[p_id] = current_pos
                keep_rows.append(row)
                continue

            last_pos = last_positions[p_id]
            
            hit_detected = False
            for s_p1, s_p2 in sipm_segments:
                # Check if photon path intersects this SiPM segment
                intersection = line_intersection(last_pos, current_pos, s_p1, s_p2)
                if intersection is not None:
                    hit_detected = True
                    break

            if hit_detected:
                dead_photons.add(p_id)
                # Overwrite this row's position with the exact hit location on the SiPM before saving it as its final step
                row[X_COL] = intersection[0]
                row[Z_COL] = intersection[1]
                keep_rows.append(row)
                del last_positions[p_id]
            else:
                # No hit, photon continues moving
                keep_rows.append(row)
                last_positions[p_id] = current_pos

        if keep_rows:
            output_df = pd.DataFrame(keep_rows)
            if first_chunk:
                output_df.to_csv(output_file, index=False, mode="w")
                first_chunk = False
            else:
                output_df.to_csv(output_file, index=False, mode="a", header=False)

    print(f"Successfully processed: {os.path.basename(input_file)}")



if __name__ == "__main__":
    MY_8_SIPMS = [
        (50, 50),   (100, 50),  (150, 50),  (200, 50),
        (50, 150),  (100, 150), (150, 150), (200, 150)
    ]
    
    INPUT_DIR = "path/to/input_csvs"
    OUTPUT_DIR = "path/to/output_csvs"
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    csv_files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
    
    for file_path in csv_files:
        out_path = os.path.join(OUTPUT_DIR, f"truncated_{os.path.basename(file_path)}")
        
        # Calling your custom function
        filter_photons_by_sipm(
            input_file=file_path,
            output_file=out_path,
            sipm_centers=MY_8_SIPMS,
            sipm_size=6,          # Explicitly set SiPM size to 6
            chunk_size=100000     # Adjust based on your RAM limits
        )