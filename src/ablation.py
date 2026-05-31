"""
ablation.py  --  Automated ablation for the report's Table 1.

For every real photo in data/buildings/ we:
  1. take the photo's depth as the reference,
  2. synthesise a sketch from it (Dodging),
  3. run our sketch->depth pipeline under THREE pre-processing settings, and
  4. measure agreement (Pearson corr, RMSE) with the reference depth.

This fills the three rows of Table 1 with one command:

    D:/anaconda3/envs/ocr_env/python.exe src/ablation.py

Outputs:
    outputs/ablation.csv         raw per-image numbers
    outputs/ablation_table.tex   ready-to-paste LaTeX rows for Table 1
and prints the aggregate table to the console.
"""

from __future__ import annotations

import os
import sys
import glob

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import enhance_sketch        # noqa: E402
from depth import estimate_depth             # noqa: E402
from dodging import photo_to_sketch          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outputs")

# The three ablation settings (name -> enhance_sketch kwargs + tex label).
SETTINGS = [
    ("raw",       dict(do_clean=False, do_contrast=False, do_shading=False),
     "Raw sketch (no enhancement)"),
    ("clean_clahe", dict(do_clean=True, do_contrast=True, do_shading=False),
     "+ cleaning + CLAHE"),
    ("full",      dict(do_clean=True, do_contrast=True, do_shading=True),
     "+ synthetic shading (full, ours)"),
]


def _metrics(ref: np.ndarray, est: np.ndarray):
    """Pearson correlation and RMSE between two normalized depth maps."""
    a = ref.flatten().astype(np.float64)
    b = est.flatten().astype(np.float64)
    rmse = float(np.sqrt(np.mean((a - b) ** 2)))
    # guard against constant maps (raw sketches can be near-flat)
    if a.std() < 1e-6 or b.std() < 1e-6:
        corr = 0.0
    else:
        corr = float(np.corrcoef(a, b)[0, 1])
        if np.isnan(corr):
            corr = 0.0
    return corr, rmse


def _list_photos():
    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp")
    files = []
    for e in exts:
        files += glob.glob(os.path.join(ROOT, "data", "buildings", e))
        files += glob.glob(os.path.join(ROOT, "data", "buildings", e.upper()))
    return sorted(set(files))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    photos = _list_photos()
    if not photos:
        raise SystemExit("No photos in data/buildings/ — add some and retry.")

    # results[setting] = list of (corr, rmse)
    results = {name: [] for name, _, _ in SETTINGS}
    per_image_rows = []  # (image, setting, corr, rmse)

    for fp in photos:
        name = os.path.splitext(os.path.basename(fp))[0]
        photo = cv2.imread(fp)
        if photo is None:
            print(f"  !! could not read {fp}")
            continue
        print(f"[ablation] {name}")

        ref_depth = estimate_depth(photo)              # reference
        sketch = photo_to_sketch(photo)                # synth sketch
        sketch_bgr = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

        for sname, kwargs, _label in SETTINGS:
            enhanced = enhance_sketch(sketch_bgr, **kwargs)
            depth = estimate_depth(enhanced)
            corr, rmse = _metrics(ref_depth, depth)
            results[sname].append((corr, rmse))
            per_image_rows.append((name, sname, corr, rmse))
            print(f"    {sname:14s} corr={corr:6.3f}  rmse={rmse:6.4f}")

    # ---- aggregate ----
    print("\n=== Ablation (mean over {} image(s)) ===".format(len(photos)))
    print(f"{'setting':34s} {'corr':>7s} {'rmse':>8s}")
    agg = {}
    for sname, _kwargs, label in SETTINGS:
        rows = results[sname]
        mc = float(np.mean([c for c, _ in rows])) if rows else 0.0
        mr = float(np.mean([r for _, r in rows])) if rows else 0.0
        agg[sname] = (mc, mr, label)
        print(f"{label:34s} {mc:7.3f} {mr:8.4f}")

    # ---- write CSV ----
    csv_path = os.path.join(OUT_DIR, "ablation.csv")
    with open(csv_path, "w") as f:
        f.write("image,setting,corr,rmse\n")
        for img, sname, c, r in per_image_rows:
            f.write(f"{img},{sname},{c:.4f},{r:.4f}\n")
        f.write("\n# means\nsetting,corr,rmse\n")
        for sname, _k, _l in SETTINGS:
            mc, mr, _ = agg[sname]
            f.write(f"{sname},{mc:.4f},{mr:.4f}\n")

    # ---- write LaTeX rows for Table 1 (paste over the [[FILL]] rows) ----
    # Bold the ACTUAL best cell in each column (best corr = max, best rmse = min),
    # not a fixed row -- so the table reflects what really won.
    best_corr = max(agg[s][0] for s, _, _ in SETTINGS)
    best_rmse = min(agg[s][1] for s, _, _ in SETTINGS)
    tex_path = os.path.join(OUT_DIR, "ablation_table.tex")
    with open(tex_path, "w") as f:
        f.write("% Paste these three rows into Table 1 of main.tex,\n")
        f.write("% replacing the [[FILL]] rows. Bold = best in that column.\n")
        for sname, _k, label in SETTINGS:
            mc, mr, _ = agg[sname]
            c = f"\\textbf{{{mc:.3f}}}" if abs(mc - best_corr) < 1e-9 else f"{mc:.3f}"
            r = f"\\textbf{{{mr:.4f}}}" if abs(mr - best_rmse) < 1e-9 else f"{mr:.4f}"
            f.write(f"{label:34s} & {c} & {r} \\\\\n")

    print(f"\n[ablation] wrote {csv_path}")
    print(f"[ablation] wrote {tex_path}  (paste into Table 1)")


if __name__ == "__main__":
    main()
