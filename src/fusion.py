"""
fusion.py  --  Innovation #1: multi-sketch depth fusion.

The original paper tried to combine multiple sketches of the same scene by
*stitching the images* (ORB features + homography). They report this "completely
fails" on real drawings, because two artists' line work is too different for
feature matching.

Our key idea: don't fuse in image space, fuse in DEPTH space.
  1. Estimate a depth map for each sketch independently (robust per-sketch).
  2. Align the depth maps to a reference using intensity-based alignment (ECC),
     which is far more forgiving of style differences than sparse feature
     matching, with an ORB-homography fallback.
  3. Fuse the aligned depths with a robust, confidence-weighted combination
     (per-pixel median / weighted mean), so outliers from any single noisy
     sketch are suppressed.

This directly targets the paper's stated failure mode and is the project's main
methodological contribution.
"""

from __future__ import annotations

import cv2
import numpy as np


# --------------------------------------------------------------------------- #
#  Alignment
# --------------------------------------------------------------------------- #
def _align_ecc(ref_gray: np.ndarray, mov_gray: np.ndarray):
    """Dense intensity alignment (ECC). Returns 2x3 warp or None on failure."""
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5)
    try:
        _, warp = cv2.findTransformECC(
            ref_gray.astype(np.float32) / 255.0,
            mov_gray.astype(np.float32) / 255.0,
            warp, cv2.MOTION_AFFINE, crit, None, 5,
        )
        return warp
    except cv2.error:
        return None


def _align_orb(ref_gray: np.ndarray, mov_gray: np.ndarray):
    """Sparse ORB + homography fallback. Returns 3x3 H or None."""
    orb = cv2.ORB_create(2000)
    k1, d1 = orb.detectAndCompute(ref_gray, None)
    k2, d2 = orb.detectAndCompute(mov_gray, None)
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(d2, d1)
    if len(matches) < 12:
        return None
    matches = sorted(matches, key=lambda m: m.distance)[:80]
    src = np.float32([k2[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([k1[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    H, _ = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return H


def align_to_reference(ref_gray, mov_gray, mov_depth):
    """Warp `mov_depth` into the reference frame.

    Returns (aligned_depth, valid_mask, method_str). `valid_mask` marks pixels
    that actually came from the moving image (so padding doesn't pollute fusion).
    """
    h, w = ref_gray.shape[:2]
    ones = np.ones_like(mov_depth, dtype=np.float32)

    warp = _align_ecc(ref_gray, mov_gray)
    if warp is not None:
        aligned = cv2.warpAffine(mov_depth, warp, (w, h),
                                 flags=cv2.INTER_LINEAR, borderValue=0)
        mask = cv2.warpAffine(ones, warp, (w, h),
                              flags=cv2.INTER_NEAREST, borderValue=0) > 0.5
        return aligned, mask, "ecc"

    H = _align_orb(ref_gray, mov_gray)
    if H is not None:
        aligned = cv2.warpPerspective(mov_depth, H, (w, h),
                                      flags=cv2.INTER_LINEAR, borderValue=0)
        mask = cv2.warpPerspective(ones, H, (w, h),
                                   flags=cv2.INTER_NEAREST, borderValue=0) > 0.5
        return aligned, mask, "orb"

    # No alignment possible: assume already roughly registered.
    return mov_depth.copy(), ones > 0.5, "identity"


# --------------------------------------------------------------------------- #
#  Per-sketch confidence
# --------------------------------------------------------------------------- #
def depth_confidence(gray: np.ndarray) -> np.ndarray:
    """Heuristic per-pixel confidence in [0,1].

    Depth is most trustworthy near actual strokes / structure. We use local
    gradient energy (edge strength) as a proxy and smooth it into a soft field.
    """
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    energy = cv2.magnitude(gx, gy)
    energy = cv2.GaussianBlur(energy, (0, 0), sigmaX=9)
    conf = cv2.normalize(energy, None, 0.15, 1.0, cv2.NORM_MINMAX)
    return conf.astype(np.float32)


# --------------------------------------------------------------------------- #
#  Fusion
# --------------------------------------------------------------------------- #
def _match_scale(ref_depth, depth, mask):
    """Align a depth map's scale/offset to the reference over the overlap.

    Per-sketch relative depths live on arbitrary scales; least-squares fit
    depth -> a*depth + b on overlapping valid pixels before combining.
    """
    m = mask & np.isfinite(depth)
    if m.sum() < 50:
        return depth
    x = depth[m].astype(np.float64)
    y = ref_depth[m].astype(np.float64)
    a, b = np.polyfit(x, y, 1)
    return (a * depth + b).astype(np.float32)


def fuse_depths(grays, depths, method: str = "weighted"):
    """Fuse a list of (aligned-to-same-size) depth maps.

    Parameters
    ----------
    grays  : list of enhanced grayscale images (used for alignment + confidence)
    depths : list of per-sketch float depth maps in [0,1]
    method : "weighted" (confidence-weighted mean) or "median" (robust)

    Returns
    -------
    fused depth map float32 [0,1], and a dict of debug info.
    """
    assert len(grays) == len(depths) and len(grays) >= 1
    ref_gray = grays[0]
    ref_depth = depths[0]
    h, w = ref_gray.shape[:2]

    aligned_depths = [ref_depth]
    masks = [np.ones((h, w), bool)]
    confs = [depth_confidence(ref_gray)]
    methods = ["reference"]

    for g, d in zip(grays[1:], depths[1:]):
        ad, mask, how = align_to_reference(ref_gray, g, d)
        ad = _match_scale(ref_depth, ad, mask)
        # warp the gray too, for confidence in the reference frame
        ag, _, _ = align_to_reference(ref_gray, g, g.astype(np.float32))
        aligned_depths.append(ad)
        masks.append(mask)
        confs.append(depth_confidence(ag.astype(np.uint8)) * mask)
        methods.append(how)

    D = np.stack(aligned_depths, 0)          # (N,H,W)
    M = np.stack(masks, 0).astype(np.float32)
    C = np.stack(confs, 0) * M               # zero confidence where invalid

    if method == "median":
        Dm = np.where(M > 0.5, D, np.nan)
        fused = np.nanmedian(Dm, axis=0)
        fused = np.nan_to_num(fused, nan=float(np.nanmean(Dm)))
    else:  # confidence-weighted mean
        wsum = C.sum(0)
        wsum_safe = np.where(wsum > 1e-6, wsum, 1.0)
        fused = (D * C).sum(0) / wsum_safe
        # fall back to reference where nothing overlapped
        fused = np.where(wsum > 1e-6, fused, ref_depth)

    fused = cv2.normalize(fused, None, 0, 1, cv2.NORM_MINMAX).astype(np.float32)
    info = {"methods": methods, "n": len(depths)}
    return fused, info


if __name__ == "__main__":
    print("fusion.py is a library; import fuse_depths / align_to_reference.")
