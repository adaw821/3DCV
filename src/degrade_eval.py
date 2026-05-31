"""
degrade_eval.py  --  Robustness experiment for the report's Table 2.

The standard ablation (ablation.py) feeds *clean* Dodging sketches, so the
pre-processing's cleaning stage has nothing to fix and shows no quantitative
benefit. But real sketches are photographed/scanned: they carry sensor noise,
low contrast, and uneven page lighting. This experiment tests exactly that.

For each photo we:
  1. take the photo's depth as the reference,
  2. make a clean Dodging sketch,
  3. *degrade* it (noise + low contrast + uneven illumination) to mimic a phone
     photo of a drawing, and
  4. compare depth fidelity (corr/RMSE vs the reference) for:
        - clean sketch, no enhancement      (upper bound)
        - degraded sketch, no enhancement    (the damage)
        - degraded + cleaning+CLAHE          (our cleaning)
        - degraded + full enhancement (ours)
Each cleaning step targets a specific degradation (illumination normalization
fixes uneven light, bilateral filter fixes noise, CLAHE fixes low contrast), so
this is a fair test of what pre-processing is actually for.

Run:
    D:/anaconda3/envs/ocr_env/python.exe src/degrade_eval.py

Outputs:
    outputs/degrade.csv          per-image numbers
    outputs/degrade_table.tex    ready-to-paste LaTeX rows for Table 2
    report/figures/degrade_example.png   clean / degraded / restored triptych
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
FIG_DIR = os.path.join(ROOT, "report", "figures")


# --------------------------------------------------------------------------- #
#  Degradation: mimic a phone photo / scan of a paper sketch
# --------------------------------------------------------------------------- #
def degrade(gray: np.ndarray, seed: int = 0) -> np.ndarray:
    """Add uneven illumination + sensor noise + low contrast to a clean sketch."""
    rng = np.random.RandomState(seed)
    h, w = gray.shape
    out = gray.astype(np.float32)

    # 1) uneven illumination: smooth low-frequency multiplicative field in [0.45, 1.0]
    field = rng.rand(h // 32 + 2, w // 32 + 2).astype(np.float32)
    field = cv2.resize(field, (w, h), interpolation=cv2.INTER_CUBIC)
    field = cv2.GaussianBlur(field, (0, 0), sigmaX=max(h, w) / 12.0)
    field = cv2.normalize(field, None, 0.45, 1.0, cv2.NORM_MINMAX)
    out = out * field

    # 2) sensor noise
    out = out + rng.normal(0, 14.0, size=out.shape).astype(np.float32)

    # 3) low contrast: pull toward mid-gray
    out = out * 0.6 + 0.22 * 255.0

    return np.clip(out, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------- #
def _metrics(ref: np.ndarray, est: np.ndarray):
    a = ref.flatten().astype(np.float64)
    b = est.flatten().astype(np.float64)
    rmse = float(np.sqrt(np.mean((a - b) ** 2)))
    if a.std() < 1e-6 or b.std() < 1e-6:
        return 0.0, rmse
    corr = float(np.corrcoef(a, b)[0, 1])
    return (0.0 if np.isnan(corr) else corr), rmse


def _depth_of(gray_or_bgr):
    if gray_or_bgr.ndim == 2:
        gray_or_bgr = cv2.cvtColor(gray_or_bgr, cv2.COLOR_GRAY2BGR)
    return estimate_depth(gray_or_bgr)


SETTINGS = [
    ("clean_raw",      "Clean sketch, no enhancement (upper bound)"),
    ("degraded_raw",   "Degraded sketch, no enhancement"),
    ("degraded_clean", "Degraded + cleaning + CLAHE"),
    ("degraded_full",  "Degraded + full enhancement (ours)"),
]


def _list_photos():
    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp")
    files = []
    for e in exts:
        files += glob.glob(os.path.join(ROOT, "data", "buildings", e))
        files += glob.glob(os.path.join(ROOT, "data", "buildings", e.upper()))
    return sorted(set(files))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)
    photos = _list_photos()
    if not photos:
        raise SystemExit("No photos in data/buildings/ — add some and retry.")

    results = {k: [] for k, _ in SETTINGS}
    rows = []
    saved_fig = False

    for fp in photos:
        name = os.path.splitext(os.path.basename(fp))[0]
        photo = cv2.imread(fp)
        if photo is None:
            continue
        print(f"[degrade] {name}")

        ref = estimate_depth(photo)                       # reference depth
        clean = photo_to_sketch(photo)                    # clean sketch (gray)
        dirty = degrade(clean, seed=1)                    # degraded sketch

        variants = {
            "clean_raw":      enhance_sketch(cv2.cvtColor(clean, cv2.COLOR_GRAY2BGR),
                                             do_clean=False, do_contrast=False, do_shading=False),
            "degraded_raw":   enhance_sketch(cv2.cvtColor(dirty, cv2.COLOR_GRAY2BGR),
                                             do_clean=False, do_contrast=False, do_shading=False),
            "degraded_clean": enhance_sketch(cv2.cvtColor(dirty, cv2.COLOR_GRAY2BGR),
                                             do_clean=True, do_contrast=True, do_shading=False),
            "degraded_full":  enhance_sketch(cv2.cvtColor(dirty, cv2.COLOR_GRAY2BGR)),
        }

        for key, _label in SETTINGS:
            d = estimate_depth(variants[key])
            c, r = _metrics(ref, d)
            results[key].append((c, r))
            rows.append((name, key, c, r))
            print(f"    {key:16s} corr={c:6.3f}  rmse={r:6.4f}")

        # save one qualitative triptych: clean / degraded / restored
        if not saved_fig:
            trip = np.hstack([
                clean,
                dirty,
                cv2.cvtColor(variants["degraded_clean"], cv2.COLOR_BGR2GRAY),
            ])
            cv2.imwrite(os.path.join(FIG_DIR, "degrade_example.png"), trip)
            saved_fig = True

    # ---- aggregate ----
    print(f"\n=== Degradation robustness (mean over {len(photos)} image(s)) ===")
    print(f"{'setting':44s} {'corr':>7s} {'rmse':>8s}")
    agg = {}
    for key, label in SETTINGS:
        rs = results[key]
        mc = float(np.mean([c for c, _ in rs])) if rs else 0.0
        mr = float(np.mean([r for _, r in rs])) if rs else 0.0
        agg[key] = (mc, mr, label)
        print(f"{label:44s} {mc:7.3f} {mr:8.4f}")

    # ---- CSV ----
    with open(os.path.join(OUT_DIR, "degrade.csv"), "w") as f:
        f.write("image,setting,corr,rmse\n")
        for img, key, c, r in rows:
            f.write(f"{img},{key},{c:.4f},{r:.4f}\n")
        f.write("\n# means\nsetting,corr,rmse\n")
        for key, _l in SETTINGS:
            mc, mr, _ = agg[key]
            f.write(f"{key},{mc:.4f},{mr:.4f}\n")

    # ---- LaTeX (bold best among the three DEGRADED rows) ----
    deg_keys = ["degraded_raw", "degraded_clean", "degraded_full"]
    best_c = max(agg[k][0] for k in deg_keys)
    best_r = min(agg[k][1] for k in deg_keys)
    with open(os.path.join(OUT_DIR, "degrade_table.tex"), "w") as f:
        f.write("% Table 2 rows: degradation robustness. Bold = best among the\n")
        f.write("% degraded rows (the clean row is an upper-bound reference).\n")
        for key, label in SETTINGS:
            mc, mr, _ = agg[key]
            bc = key in deg_keys and abs(mc - best_c) < 1e-9
            br = key in deg_keys and abs(mr - best_r) < 1e-9
            cs = f"\\textbf{{{mc:.3f}}}" if bc else f"{mc:.3f}"
            rs = f"\\textbf{{{mr:.4f}}}" if br else f"{mr:.4f}"
            f.write(f"{label:44s} & {cs} & {rs} \\\\\n")

    print(f"\n[degrade] wrote {os.path.join(OUT_DIR, 'degrade.csv')}")
    print(f"[degrade] wrote {os.path.join(OUT_DIR, 'degrade_table.tex')}")
    print(f"[degrade] wrote {os.path.join(FIG_DIR, 'degrade_example.png')}")


if __name__ == "__main__":
    main()
