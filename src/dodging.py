"""
dodging.py  --  Generate pencil-sketch look-alikes from real photos.

This reproduces the "Dodging" technique the original paper used to build its
image<->sketch dataset from the Zurich Building Database. We use it for two
things:
  1. Make paired (photo, sketch) data from any building photos you download, so
     the report can do a *quantitative* evaluation (the photo's depth is a
     reference for the sketch's depth).
  2. Provide extra, style-varied sketches to test multi-sketch fusion.

Reference: M. Beyeler, "How to create a pencil sketch with OpenCV+Python".
"""

from __future__ import annotations

import cv2
import numpy as np


def photo_to_sketch(bgr: np.ndarray, blur_sigma: float = 21.0,
                    high_pass: bool = True) -> np.ndarray:
    """Real photo (BGR) -> grayscale pencil sketch (single channel uint8).

    Steps follow the paper:
      gray -> invert -> blur -> color-dodge blend (divide) -> (optional) high-pass
    `blur_sigma` controls line thickness/softness; vary it to synthesise
    different drawing "styles" for the same building.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    inv = 255 - gray
    blur = cv2.GaussianBlur(inv, (0, 0), sigmaX=blur_sigma)

    # Color-dodge: sketch = gray * 256 / (256 - blur)
    denom = 256.0 - blur.astype(np.float32)
    denom = np.clip(denom, 1.0, None)
    sketch = np.clip(gray.astype(np.float32) * 256.0 / denom, 0, 255).astype(np.uint8)

    if high_pass:
        # The paper notes online sketches are noisier; a high-pass + negative
        # pushes the look closer to a hand drawing.
        lp = cv2.GaussianBlur(sketch, (0, 0), sigmaX=3)
        hp = cv2.subtract(sketch, lp)
        sketch = 255 - cv2.normalize(hp, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    return sketch


def make_style_variants(bgr: np.ndarray, sigmas=(12.0, 21.0, 32.0)):
    """Return several sketch 'styles' of one photo for fusion experiments."""
    return [photo_to_sketch(bgr, blur_sigma=s) for s in sigmas]


if __name__ == "__main__":
    import sys

    img = cv2.imread(sys.argv[1])
    if img is None:
        raise SystemExit(f"Could not read {sys.argv[1]}")
    out = sys.argv[2] if len(sys.argv) > 2 else "sketch.png"
    cv2.imwrite(out, photo_to_sketch(img))
    print(f"Wrote {out}")
