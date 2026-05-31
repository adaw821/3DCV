"""
run.py  --  End-to-end pipeline orchestrator.

Sketch(es) --> [enhance #2] --> [Depth Anything V2] --> [fuse #1] --> web assets (#5)

Usage (run with the project's GPU env):
    D:/anaconda3/envs/ocr_env/python.exe src/run.py single
        Reconstruct every image in data/sketches/ on its own.

    D:/anaconda3/envs/ocr_env/python.exe src/run.py fuse <folder> [name]
        Fuse all sketches in <folder> into ONE reconstruction (innovation #1).

    D:/anaconda3/envs/ocr_env/python.exe src/run.py pairs
        For each photo in data/buildings/: make a Dodging sketch, reconstruct
        both, and report depth agreement (quantitative eval for the report).

Outputs:
    outputs/<name>/         full-res enhanced sketch, depth colormap (for report)
    web/assets/<name>/      texture.png + depth.json  (consumed by the viewer)
    web/assets/manifest.json
"""

from __future__ import annotations

import json
import os
import sys
import glob

import cv2
import numpy as np

# allow `python src/run.py` from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import enhance_sketch                      # noqa: E402
from depth import estimate_depth, colorize_depth           # noqa: E402
from fusion import fuse_depths                              # noqa: E402
from dodging import photo_to_sketch                         # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outputs")
WEB_ASSETS = os.path.join(ROOT, "web", "assets")
GRID_W = 200  # depth grid width exported to the web viewer


# --------------------------------------------------------------------------- #
#  Web asset export
# --------------------------------------------------------------------------- #
def _downsample_depth(depth: np.ndarray):
    """Return a small (gw x gh) nested list of depth values in [0,1]."""
    h, w = depth.shape
    gw = GRID_W
    gh = max(1, int(round(gw * h / w)))
    small = cv2.resize(depth, (gw, gh), interpolation=cv2.INTER_AREA)
    small = np.clip(small, 0, 1)
    return small, gw, gh


def export_sample(name: str, texture_bgr: np.ndarray, depth: np.ndarray,
                  manifest: list):
    """Write texture.png + depth.json for the viewer and append to manifest."""
    adir = os.path.join(WEB_ASSETS, name)
    os.makedirs(adir, exist_ok=True)

    # Texture the viewer drapes over the surface (use the original drawing).
    cv2.imwrite(os.path.join(adir, "texture.png"), texture_bgr)

    small, gw, gh = _downsample_depth(depth)
    with open(os.path.join(adir, "depth.json"), "w") as f:
        json.dump({"w": gw, "h": gh, "data": small.round(4).tolist()}, f)

    manifest.append({
        "name": name,
        "texture": f"assets/{name}/texture.png",
        "depth": f"assets/{name}/depth.json",
    })


def write_manifest(manifest: list):
    """Merge new samples into any existing manifest (keyed by name) so results
    accumulate across separate `single` / `fuse` / `pairs` runs."""
    os.makedirs(WEB_ASSETS, exist_ok=True)
    path = os.path.join(WEB_ASSETS, "manifest.json")
    existing = {}
    if os.path.exists(path):
        try:
            for s in json.load(open(path)).get("samples", []):
                existing[s["name"]] = s
        except (ValueError, KeyError):
            pass
    for s in manifest:
        existing[s["name"]] = s
    merged = list(existing.values())
    with open(path, "w") as f:
        json.dump({"samples": merged}, f, indent=2)
    print(f"[web] manifest now has {len(merged)} sample(s) "
          f"(+{len(manifest)} this run).")


def save_report_images(name: str, enhanced_bgr, depth):
    odir = os.path.join(OUT_DIR, name)
    os.makedirs(odir, exist_ok=True)
    cv2.imwrite(os.path.join(odir, "enhanced.png"), enhanced_bgr)
    cv2.imwrite(os.path.join(odir, "depth_color.png"), colorize_depth(depth))


# --------------------------------------------------------------------------- #
#  Core: one sketch -> (enhanced_gray, depth)
# --------------------------------------------------------------------------- #
def reconstruct_one(bgr: np.ndarray):
    enhanced = enhance_sketch(bgr)
    depth = estimate_depth(enhanced)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    return enhanced, gray, depth


# --------------------------------------------------------------------------- #
#  Modes
# --------------------------------------------------------------------------- #
def _list_images(folder):
    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp")
    files = []
    for e in exts:
        files += glob.glob(os.path.join(folder, e))
        files += glob.glob(os.path.join(folder, e.upper()))
    return sorted(set(files))


def mode_single(manifest):
    folder = os.path.join(ROOT, "data", "sketches")
    files = _list_images(folder)
    if not files:
        print(f"[single] no images in {folder} — drop some sketches there.")
        return
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        print(f"[single] {name}")
        bgr = cv2.imread(fp)
        if bgr is None:
            print(f"  !! could not read {fp}, skipping")
            continue
        enhanced, _gray, depth = reconstruct_one(bgr)
        save_report_images(name, enhanced, depth)
        export_sample(name, bgr, depth, manifest)  # drape ORIGINAL sketch


def mode_fuse(manifest, folder, name=None):
    files = _list_images(folder)
    if len(files) < 2:
        print(f"[fuse] need >=2 images in {folder}")
        return
    name = name or f"fused_{os.path.basename(os.path.normpath(folder))}"
    print(f"[fuse] {name}  <-  {len(files)} sketches")

    grays, depths, first_bgr = [], [], None
    ref_shape = None
    for i, fp in enumerate(files):
        bgr = cv2.imread(fp)
        if bgr is None:
            continue
        if ref_shape is None:
            ref_shape = bgr.shape[:2][::-1]  # (w,h)
            first_bgr = bgr
        else:
            bgr = cv2.resize(bgr, ref_shape)  # common canvas for fusion
        enhanced, gray, depth = reconstruct_one(bgr)
        grays.append(gray)
        depths.append(depth)
        print(f"  - {os.path.basename(fp)} done")

    fused, info = fuse_depths(grays, depths, method="weighted")
    print(f"  alignment methods: {info['methods']}")
    save_report_images(name, cv2.cvtColor(grays[0], cv2.COLOR_GRAY2BGR), fused)
    export_sample(name, first_bgr, fused, manifest)


def mode_pairs(manifest):
    """Quantitative eval: photo vs its Dodging-sketch reconstruction."""
    folder = os.path.join(ROOT, "data", "buildings")
    files = _list_images(folder)
    if not files:
        print(f"[pairs] no photos in {folder} — drop building photos there.")
        return
    rows = []
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        photo = cv2.imread(fp)
        if photo is None:
            continue
        print(f"[pairs] {name}")

        # Reference: depth of the real photo directly.
        photo_depth = estimate_depth(photo)

        # Make a sketch from it, run our full sketch pipeline.
        sketch = photo_to_sketch(photo)
        sketch_bgr = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(os.path.join(ROOT, "data", "pairs", f"{name}_sketch.png"), sketch)
        _enh, _g, sketch_depth = reconstruct_one(sketch_bgr)

        # Agreement metrics between photo-depth and sketch-depth.
        a = photo_depth.flatten()
        b = sketch_depth.flatten()
        rmse = float(np.sqrt(np.mean((a - b) ** 2)))
        corr = float(np.corrcoef(a, b)[0, 1])
        rows.append((name, rmse, corr))
        print(f"   RMSE={rmse:.4f}  corr={corr:.3f}")

        save_report_images(f"{name}_sketch", sketch_bgr, sketch_depth)
        export_sample(f"{name}_sketch", sketch_bgr, sketch_depth, manifest)

    if rows:
        print("\n=== Pair evaluation (photo-depth vs sketch-depth) ===")
        print(f"{'sample':24s} {'RMSE':>8s} {'corr':>8s}")
        for n, r, c in rows:
            print(f"{n:24s} {r:8.4f} {c:8.3f}")
        mr = np.mean([r for _, r, _ in rows])
        mc = np.mean([c for _, _, c in rows])
        print(f"{'MEAN':24s} {mr:8.4f} {mc:8.3f}")
        with open(os.path.join(OUT_DIR, "pair_eval.csv"), "w") as f:
            f.write("sample,rmse,corr\n")
            for n, r, c in rows:
                f.write(f"{n},{r:.4f},{c:.4f}\n")
        print(f"[pairs] wrote {os.path.join(OUT_DIR, 'pair_eval.csv')}")


# --------------------------------------------------------------------------- #
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(WEB_ASSETS, exist_ok=True)

    args = sys.argv[1:]
    mode = args[0] if args else "single"
    manifest = []

    if mode == "single":
        mode_single(manifest)
    elif mode == "fuse":
        if len(args) < 2:
            raise SystemExit("usage: run.py fuse <folder> [name]")
        mode_fuse(manifest, args[1], args[2] if len(args) > 2 else None)
    elif mode == "pairs":
        mode_pairs(manifest)
    elif mode == "all":
        mode_single(manifest)
        mode_pairs(manifest)
    else:
        raise SystemExit(f"unknown mode: {mode}")

    if manifest:
        write_manifest(manifest)
        print("\nDone. Start the viewer with:")
        print("  D:/anaconda3/envs/ocr_env/python.exe -m http.server 8000 -d web")
        print("  then open http://localhost:8000")


if __name__ == "__main__":
    main()
