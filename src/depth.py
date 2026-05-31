"""
depth.py  --  Monocular depth estimation.

The original paper used MegaDepth (2018), which is awkward to install and was
trained only on outdoor internet photos. We replace it with Depth Anything V2
(2024), a foundation depth model that is far more robust to appearance and ships
through HuggingFace `transformers` (already installed in this env). It runs on
the local RTX 4060 GPU.

The model is loaded once and cached. We return a float32 depth map normalised to
[0, 1] where larger = nearer (Depth Anything outputs relative inverse depth, i.e.
big values are close), which is convenient for surface display.
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import pipeline

# Small model = fast, plenty for sketches. Swap to *-Base-hf for slightly nicer
# results if you have time/VRAM.
_MODEL_NAME = "depth-anything/Depth-Anything-V2-Small-hf"

_pipe = None


def _get_pipe():
    """Lazily build the HF depth-estimation pipeline on GPU if available."""
    global _pipe
    if _pipe is None:
        device = 0 if torch.cuda.is_available() else -1
        print(f"[depth] loading {_MODEL_NAME} on "
              f"{'GPU' if device == 0 else 'CPU'} ...")
        _pipe = pipeline("depth-estimation", model=_MODEL_NAME, device=device)
        print("[depth] model ready.")
    return _pipe


def estimate_depth(bgr: np.ndarray) -> np.ndarray:
    """BGR uint8 image -> float32 depth map in [0,1] (1 = nearest).

    Output has the SAME height/width as the input image.
    """
    pipe = _get_pipe()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)

    out = pipe(pil)
    depth = np.asarray(out["depth"], dtype=np.float32)

    # Resize back to input size (pipeline may rescale internally).
    h, w = bgr.shape[:2]
    if depth.shape != (h, w):
        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)

    # Normalise to [0,1].
    d = depth - depth.min()
    rng = d.max()
    if rng > 1e-6:
        d /= rng
    return d.astype(np.float32)


def colorize_depth(depth: np.ndarray) -> np.ndarray:
    """float32 [0,1] depth -> BGR colormap image for visualisation/report."""
    d8 = (np.clip(depth, 0, 1) * 255).astype(np.uint8)
    return cv2.applyColorMap(d8, cv2.COLORMAP_INFERNO)


if __name__ == "__main__":
    import sys

    img = cv2.imread(sys.argv[1])
    if img is None:
        raise SystemExit(f"Could not read {sys.argv[1]}")
    d = estimate_depth(img)
    cv2.imwrite("depth_vis.png", colorize_depth(d))
    print("Wrote depth_vis.png  (min/max:", float(d.min()), float(d.max()), ")")
