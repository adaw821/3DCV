"""
preprocess.py  --  Innovation #2: Targeted sketch pre-processing enhancement.

The original paper (Talwar & Laasri, "3D Reconstruction from Sketches") fed raw
sketches into a CycleGAN and found the depth step unstable, partly because real
sketches are noisy, low-contrast, and have inconsistent line weights.

A modern foundation depth model (Depth Anything V2) is robust to appearance, but
it still expects a photo-like, single-channel-of-shading input. A bare line
drawing on white paper gives the model very little to latch onto: most pixels are
flat white, so the predicted depth is almost constant.

Our pre-processing turns a raw sketch into a "depth-friendly" image by:
    1. Cleaning   -- denoise + normalise the page to white, lines to dark.
    2. Enhancing  -- CLAHE local contrast so faint pencil strokes survive.
    3. Shading    -- synthesise soft tonal shading from line density so flat
                     regions get a depth cue (this is the key trick).

We expose a single function `enhance_sketch(bgr) -> bgr` plus a few helpers so the
ablation in the report can turn individual stages on/off.
"""

from __future__ import annotations

import cv2
import numpy as np


# --------------------------------------------------------------------------- #
#  Stage 1: cleaning
# --------------------------------------------------------------------------- #
def to_clean_gray(bgr: np.ndarray) -> np.ndarray:
    """Grayscale + edge-preserving denoise + white-background normalisation.

    Returns a uint8 grayscale image where paper is ~white (255) and lines are
    dark, regardless of how the scan/photo was lit.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Edge-preserving denoise: keeps line strokes crisp, removes paper grain.
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

    # Flatten uneven lighting / shadows from phone photos of paper.
    # Divide by a heavily blurred version (illumination estimate), then rescale.
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=35)
    bg = np.clip(bg, 1, 255)
    norm = (gray.astype(np.float32) / bg.astype(np.float32)) * 255.0
    norm = np.clip(norm, 0, 255).astype(np.uint8)
    return norm


# --------------------------------------------------------------------------- #
#  Stage 2: contrast enhancement
# --------------------------------------------------------------------------- #
def boost_contrast(gray: np.ndarray, clip: float = 3.0, grid: int = 8) -> np.ndarray:
    """CLAHE local contrast so faint strokes become clearly visible."""
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    return clahe.apply(gray)


# --------------------------------------------------------------------------- #
#  Stage 3: synthesise tonal shading (the important bit)
# --------------------------------------------------------------------------- #
def synth_shading(gray: np.ndarray, strength: float = 0.6) -> np.ndarray:
    """Turn a flat line drawing into a softly shaded image.

    Idea: regions that are densely hatched / close to many strokes should read as
    "near" or "in shadow". We estimate local line density (how dark the
    neighbourhood is) and blend that soft field back into the image. This gives
    the depth model continuous tonal gradients to reason about instead of a sea
    of flat white.

    strength in [0,1] controls how much synthetic shading is mixed in.
    """
    inv = 255 - gray  # lines become bright on black

    # Local stroke density at several scales -> smooth tonal field.
    small = cv2.GaussianBlur(inv, (0, 0), sigmaX=4)
    large = cv2.GaussianBlur(inv, (0, 0), sigmaX=18)
    density = cv2.normalize(0.5 * small + 0.5 * large, None, 0, 255,
                            cv2.NORM_MINMAX).astype(np.float32)

    # Shaded image = original tone darkened where stroke density is high.
    shaded = gray.astype(np.float32) - strength * density
    shaded = cv2.normalize(shaded, None, 0, 255, cv2.NORM_MINMAX)
    return shaded.astype(np.uint8)


# --------------------------------------------------------------------------- #
#  Full pipeline
# --------------------------------------------------------------------------- #
def enhance_sketch(
    bgr: np.ndarray,
    do_clean: bool = True,
    do_contrast: bool = True,
    do_shading: bool = False,   # ABLATED OUT: see note below
    shading_strength: float = 0.6,
) -> np.ndarray:
    """Raw sketch (BGR) -> enhanced, depth-friendly BGR image.

    The boolean flags let the report's ablation isolate each stage.

    NOTE on synthetic shading: we originally expected it to help by giving the
    depth model tonal cues. Our ablation (see degrade_eval.py / Table 2) shows
    the opposite -- modern foundation depth models are robust enough to raw line
    art that the extra shading injects spurious depth and *reduces* fidelity. We
    therefore disable it by default. The cleaning + CLAHE stages, however, give a
    clear, measurable robustness gain on noisy/low-contrast/unevenly-lit sketches
    (which is what real photographed drawings look like).
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if not do_clean else to_clean_gray(bgr)

    if do_contrast:
        gray = boost_contrast(gray)

    if do_shading:
        gray = synth_shading(gray, strength=shading_strength)

    # Depth Anything wants a 3-channel image; replicate the enhanced gray.
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


if __name__ == "__main__":
    import sys

    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "enhanced.png"
    img = cv2.imread(src)
    if img is None:
        raise SystemExit(f"Could not read image: {src}")
    out = enhance_sketch(img)
    cv2.imwrite(dst, out)
    print(f"Wrote {dst}")
