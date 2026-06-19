import argparse
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree


N = 32
QUERY_WORKERS = 1
_OPT_GRID = None
_CHECK_GRID = None
_MAXITER = 180
_Q = 36


def rectangular_grid(nx=8, ny=4):
    xs = (np.arange(nx) + 0.5) / nx
    ys = (np.arange(ny) + 0.5) / ny
    return np.array([(x, y) for y in ys for x in xs])


def staggered_grid(rows):
    pts = []
    yvals = (np.arange(len(rows)) + 0.5) / len(rows)
    for j, count in enumerate(rows):
        y = yvals[j]
        xs = (np.arange(count) + 0.5) / count
        if j % 2:
            xs = xs + 0.5 / count
            xs = np.clip(xs, 0.0, 1.0)
        pts.extend((x, y) for x in xs)
    return np.array(pts[:N])


def sample_grid(m):
    xs = np.linspace(0.0, 1.0, m)
    yy, xx = np.meshgrid(xs, xs, indexing="ij")
    return np.column_stack((xx.ravel(), yy.ravel()))


def radius_on_grid(pts, grid):
    d, _ = cKDTree(pts).query(grid, workers=QUERY_WORKERS)
    return float(d.max())


def exact_grid_radius(pts, m=501):
    return radius_on_grid(pts, sample_grid(m))


def smooth_radius(flat, grid, q=36):
    pts = flat.reshape(N, 2)
    d, _ = cKDTree(pts).query(grid, workers=QUERY_WORKERS)
    scale = max(float(d.max()), 1e-12)
    return scale * float(np.mean((d / scale) ** q) ** (1.0 / q))


def farthest_sample(pts, grid):
    d, _ = cKDTree(pts).query(grid, workers=QUERY_WORKERS)
    idx = int(np.argmax(d))
    return grid[idx], float(d[idx])


def optimize_from(start, grid, maxiter=180, q=36):
    res = minimize(
        lambda z: smooth_radius(z, grid, q=q),
        start.ravel(),
        method="L-BFGS-B",
        bounds=[(0.0, 1.0)] * (2 * N),
        options={"maxiter": maxiter, "ftol": 1e-13, "gtol": 1e-8},
    )
    return res.x.reshape(N, 2), float(res.fun), bool(res.success), str(res.message)


def init_worker(opt_grid, check_grid, maxiter, q):
    global _OPT_GRID, _CHECK_GRID, _MAXITER, _Q
    _OPT_GRID = opt_grid
    _CHECK_GRID = check_grid
    _MAXITER = maxiter
    _Q = q


def run_start(job):
    idx, name, start = job
    pts, obj, ok, message = optimize_from(start, _OPT_GRID, maxiter=_MAXITER, q=_Q)
    r_check = radius_on_grid(pts, _CHECK_GRID)
    far, far_d = farthest_sample(pts, _CHECK_GRID)
    return {
        "idx": idx,
        "name": name,
        "pts": pts,
        "obj": obj,
        "ok": ok,
        "message": message,
        "r_check": r_check,
        "far": far,
        "far_d": far_d,
    }


def build_starts(seed, jitter_count, random_count):
    rng = np.random.default_rng(seed)
    starts = [
        ("rect_8x4", rectangular_grid()),
        ("stagger_7_6_6_6_7", staggered_grid([7, 6, 6, 6, 7])),
        ("stagger_6_7_6_7_6", staggered_grid([6, 7, 6, 7, 6])),
        ("stagger_5_6_7_7_7", staggered_grid([5, 6, 7, 7, 7])),
    ]

    base = list(starts)
    for name, pts in base:
        for k in range(jitter_count):
            jitter = rng.normal(0.0, 0.025, size=pts.shape)
            starts.append((f"{name}_j{k}", np.clip(pts + jitter, 0.0, 1.0)))
    for k in range(random_count):
        starts.append((f"random_{k}", rng.random((N, 2))))
    return starts


def plot_points(pts, out_path, grid_m=801):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grid = sample_grid(grid_m)
    d, _ = cKDTree(pts).query(grid, workers=QUERY_WORKERS)
    radius = float(d.max())
    far = grid[int(np.argmax(d))]

    fig, ax = plt.subplots(figsize=(7, 7), dpi=180)
    ax.set_aspect("equal")
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xticks(np.linspace(0.0, 1.0, 6))
    ax.set_yticks(np.linspace(0.0, 1.0, 6))
    ax.grid(alpha=0.18)
    ax.add_patch(plt.Rectangle((0.0, 0.0), 1.0, 1.0, fill=False, lw=2.0, color="black"))
    for x, y in pts:
        ax.add_patch(plt.Circle((x, y), radius, fill=False, lw=0.6, alpha=0.18, color="#1f77b4"))
    ax.scatter(pts[:, 0], pts[:, 1], s=28, c="#0b4f8a", zorder=3, label="32 centers")
    ax.scatter([far[0]], [far[1]], s=42, c="#d62728", marker="x", zorder=4, label="sampled worst hole")
    ax.set_title(f"32-point unit-square covering candidate, sampled R = {radius:.6f}")
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return radius, far


def print_result(result):
    far = result["far"]
    print(
        f"{result['idx']:02d} {result['name']:24s} "
        f"obj={result['obj']:.9f} check={result['r_check']:.9f} "
        f"ok={result['ok']} far=({far[0]:.4f},{far[1]:.4f})",
        flush=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Search for 32-point minimax coverings of the unit square.")
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--opt-grid", type=int, default=70)
    parser.add_argument("--check-grid", type=int, default=701)
    parser.add_argument("--maxiter", type=int, default=180)
    parser.add_argument("--q", type=int, default=36)
    parser.add_argument("--jitter", type=int, default=1)
    parser.add_argument("--random", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260619)
    parser.add_argument("--csv-out", default="analysis/cover32_best_points.csv")
    parser.add_argument("--plot-out", default="analysis/cover32_best_points.png")
    parser.add_argument("--no-plot", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    opt_grid = sample_grid(args.opt_grid)
    check_grid = sample_grid(args.check_grid)
    starts = build_starts(args.seed, args.jitter, args.random)
    jobs = [(i, name, pts) for i, (name, pts) in enumerate(starts, 1)]
    worker_count = min(max(1, args.jobs), len(jobs))

    print(f"Rectangular 8x4 radius analytic: {math.sqrt((1/16)**2 + (1/8)**2):.9f}", flush=True)
    print(f"Rectangular 8x4 radius sampled:  {exact_grid_radius(rectangular_grid(), args.check_grid):.9f}", flush=True)
    print(f"Running {len(jobs)} starts with {worker_count} worker process(es)", flush=True)
    print(flush=True)

    best = None
    if worker_count == 1:
        init_worker(opt_grid, check_grid, args.maxiter, args.q)
        for job in jobs:
            result = run_start(job)
            print_result(result)
            if best is None or result["r_check"] < best["r_check"]:
                best = result
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            initializer=init_worker,
            initargs=(opt_grid, check_grid, args.maxiter, args.q),
        ) as executor:
            future_to_job = {executor.submit(run_start, job): job for job in jobs}
            for future in as_completed(future_to_job):
                result = future.result()
                print_result(result)
                if best is None or result["r_check"] < best["r_check"]:
                    best = result

    assert best is not None
    pts = best["pts"]
    pts = pts[np.lexsort((pts[:, 0], pts[:, 1]))]
    csv_out = Path(args.csv_out)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(csv_out, pts, delimiter=",", header="x,y", comments="", fmt="%.10f")

    print(flush=True)
    print(f"BEST {best['name']}: sampled radius {best['r_check']:.9f}", flush=True)
    print(f"Wrote {csv_out}", flush=True)

    if not args.no_plot:
        plot_radius, plot_far = plot_points(pts, Path(args.plot_out))
        print(f"Wrote {args.plot_out} with sampled plot radius {plot_radius:.9f} far=({plot_far[0]:.4f},{plot_far[1]:.4f})", flush=True)

    for x, y in pts:
        print(f"{x:.10f}, {y:.10f}", flush=True)


if __name__ == "__main__":
    main()
