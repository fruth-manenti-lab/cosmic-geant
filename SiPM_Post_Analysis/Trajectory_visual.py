'''
You can run these commands using the command line:

python visualize_tracks.py hits.csv --event 775 --tracks 1211-1215
python visualize_tracks.py hits.csv --event 775 --tracks 1,1210,1213
python visualize_tracks.py hits.csv --tracks all                 # auto event
python visualize_tracks.py hits.csv --tracks 1211-1215 --separate # one PNG per track
'''

import argparse
import os
import sys
import matplotlib
matplotlib.use("Agg")  # safe headless default; use --show for an interactive window
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

X_COL, Y_COL, Z_COL = "XPosition", "YPosition", "ZPosition"
TID_COL, EID_COL, STEP_COL, PARENT_COL = "TrackID", "EventID", "StepID", "ParentID"

def read_g4_ntuple(path):
    """Read either a tools::wcsv ntuple (with #column/#separator header lines)
    or a plain headered CSV (e.g. the truncated output of the SiPM filter)."""
    columns, sep, is_wcsv = [], ",", False
    with open(path) as f:
        for line in f:
            if not line.startswith("#"):
                break
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0] == "#column":
                columns.append(parts[-1]); is_wcsv = True   # last token is the name
            elif len(parts) >= 2 and parts[0] == "#separator":
                sep = chr(int(parts[1]))                     # e.g. 44 -> ','
    if is_wcsv:
        return pd.read_csv(path, sep=sep, comment="#", header=None, names=columns)
    return pd.read_csv(path)   # plain CSV with a normal header row

def resolve_event(df, event_arg):
    """Decide which EventID to plot. Auto: the sole event, else the first (warns)."""
    events = sorted(int(e) for e in df[EID_COL].unique())
    if event_arg is not None:
        if event_arg not in events:
            sys.exit(f"EventID {event_arg} not in file. Present: {events}")
        return event_arg
    if len(events) == 1:
        return events[0]
    print(f"--event not given; defaulting to first event {events[0]} of "
          f"{len(events)} present.", file=sys.stderr)
    return events[0]


def parse_track_spec(spec, available):
    """'all' | '1210' | '1211-1215' | '1,1210' | mixes -> sorted present TrackIDs."""
    available = set(int(t) for t in available)
    spec = spec.strip().lower()
    if spec == "all":
        return sorted(available)
    wanted = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            wanted.update(range(lo, hi + 1))
        else:
            wanted.add(int(part))
    present = sorted(wanted & available)
    missing = sorted(wanted - available)
    if missing:
        print(f"warning: tracks not present in this event: {missing}", file=sys.stderr)
    return present


def trajectory(event_df, track_id):
    """Position points of one track within the event, ordered by StepID.

    Returns (xs, ys, zs, is_primary).
    """
    g = event_df[event_df[TID_COL] == track_id].sort_values(STEP_COL)
    is_primary = bool((g[PARENT_COL] == 0).iloc[0]) if len(g) else False
    return g[X_COL].to_numpy(), g[Y_COL].to_numpy(), g[Z_COL].to_numpy(), is_primary

def _plot_one(ax, xs, zs, color, primary):
    lw = 2.4 if primary else 0.9
    c = "k" if primary else color
    z = 5 if primary else 2
    ax.plot(xs, zs, lw=lw, alpha=0.85, color=c, zorder=z, solid_capstyle="round")
    if len(xs):
        ax.plot(xs[0], zs[0], marker="*", ms=8, color=c, zorder=z + 1)
        ax.plot(xs[-1], zs[-1], marker="o", ms=4, color=c, zorder=z + 1)


def _style_xz(ax):
    ax.set_xlabel("X  [mm]"); ax.set_ylabel("Z  [mm]")
    ax.set_title("Lateral projection (X–Z)")
    ax.set_xlim(-500, 500); ax.set_ylim(-500, 500)
    ax.set_aspect("equal"); ax.grid(alpha=0.25)


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


def draw_sipms(ax, centers, size):
    """Draw each SiPM as a horizontal bar at z=cz spanning x in [cx-size/2, cx+size/2],
    matching exactly how the filter models them."""
    half = size / 2.0
    for cx, cz in centers:
        ax.plot([cx - half, cx + half], [cz, cz], color="crimson", lw=4,
                solid_capstyle="butt", zorder=8, alpha=0.9)
        ax.plot(cx, cz, marker="s", ms=4, color="crimson", zorder=9)


def make_figure(event_df, track_ids, title=None, sipms=None, sipm_size=6.0):
    """One X–Z figure for one event; each selected track is a coloured polyline.
    If `sipms` (list of (x, z) centres) is given, draw the SiPM bars too."""
    cmap = plt.colormaps["turbo"].resampled(max(len(track_ids), 1))
    colors = {t: cmap(i) for i, t in enumerate(track_ids)}

    fig, ax = plt.subplots(figsize=(8, 7))
    for t in track_ids:
        xs, _, zs, primary = trajectory(event_df, t)
        _plot_one(ax, xs, zs, colors[t], primary)
    if sipms:
        draw_sipms(ax, sipms, sipm_size)
    _style_xz(ax)

    # track colour key (capped so it stays readable)
    shown = track_ids[:18]
    handles = []
    for t in shown:
        _, _, _, primary = trajectory(event_df, t)
        lab = f"track {t}" + (" (primary)" if primary else "")
        handles.append(Line2D([0], [0], color=("k" if primary else colors[t]),
                              lw=(2.4 if primary else 1.5), label=lab))
    if len(track_ids) > len(shown):
        handles.append(Line2D([0], [0], color="none",
                              label=f"… +{len(track_ids) - len(shown)} more"))
    handles += [Line2D([0], [0], marker="*", color="gray", lw=0, ms=8, label="start"),
                Line2D([0], [0], marker="o", color="gray", lw=0, ms=5, label="end")]
    if sipms:
        handles.append(Line2D([0], [0], color="crimson", lw=4, label="SiPM"))
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(1.0, 0.5),
               frameon=False, fontsize=9)
    if title:
        fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig

def _default_out(file, suffix):
    return f"{os.path.splitext(file)[0]}_{suffix}.png"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", help="path to the Geant4 ntuple CSV")
    p.add_argument("--event", type=int, default=None,
                   help="EventID to plot (default: sole event, else the first)")
    p.add_argument("--tracks", default="all",
                   help="track selection: 'all', '1210', '1211-1215', '1,1210', or mixes")
    p.add_argument("--sipms", default=None,
                   help="SiPM centres to overlay: inline 'x,z;x,z;...' or a path to "
                        "a file with one 'x,z' per line")
    p.add_argument("--sipm-size", type=float, default=6.0,
                   help="SiPM length in x [mm], matching the filter (default 6)")
    p.add_argument("--separate", action="store_true",
                   help="one PNG per track instead of all on one figure")
    p.add_argument("--max-tracks", type=int, default=None,
                   help="cap how many tracks are drawn (overlaid mode)")
    p.add_argument("--out", default=None,
                   help="output path (single-figure modes; default: next to input)")
    p.add_argument("--outdir", default=None, help="directory for output PNGs")
    p.add_argument("--show", action="store_true",
                   help="open an interactive window instead of saving")
    args = p.parse_args(argv)

    df = read_g4_ntuple(args.file)
    sipms = parse_sipms(args.sipms)
    event_id = resolve_event(df, args.event)
    event_df = df[df[EID_COL] == event_id]

    selection = parse_track_spec(args.tracks, event_df[TID_COL].unique())
    if not selection:
        sys.exit(f"No matching tracks in event {event_id}.")
    if args.max_tracks is not None:
        selection = selection[:args.max_tracks]

    base = os.path.basename(args.file)

    def save(fig, path):
        if args.outdir:
            os.makedirs(args.outdir, exist_ok=True)
            path = os.path.join(args.outdir, os.path.basename(path))
        fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
        print(f"Wrote {path}")

    # ---- separate: one PNG per track
    if args.separate:
        if args.show:
            sys.exit("--show can't combine with --separate; pick a single track.")
        print(f"Rendering {len(selection)} tracks for event {event_id}...")
        for t in selection:
            title = f"{base}  event {event_id}  track {t}"
            fig = make_figure(event_df, [t], title=title,
                              sipms=sipms, sipm_size=args.sipm_size)
            save(fig, _default_out(args.file, f"event{event_id}_track{t}"))
        return

    # ---- overlaid: all selected tracks on one figure
    n = len(selection)
    title = f"{base}  event {event_id}  ({n} track{'s' if n != 1 else ''})"
    fig = make_figure(event_df, selection, title=title,
                      sipms=sipms, sipm_size=args.sipm_size)
    if args.show:
        plt.show(); return
    span = (f"tracks{selection[0]}-{selection[-1]}" if n > 1 else f"track{selection[0]}")
    suffix = f"event{event_id}_{span}"
    save(fig, args.out or _default_out(args.file, suffix))


if __name__ == "__main__":
    main()
