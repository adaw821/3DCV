# Sketch → 3D Reconstruction

Reconstruct an explorable 3D scene from one or more hand-drawn **sketches**.
This project builds on Talwar & Laasri, *"3D Reconstruction from Sketches"*
(arXiv:2505.14621) and improves it in three ways.

---

## 1. What this project does

A sketch contains implicit 3D structure (a building's facades, depth ordering,
perspective). We recover that structure and turn the drawing into a 3D surface
you can rotate in a browser. The pipeline is:

```
sketch ─▶ [clean & enhance] ─▶ [Depth Anything V2] ─▶ [(fuse multi-sketch)] ─▶ depth ─▶ 3D surface + web viewer
```

**Our contributions over the base paper:**

1. **Modern depth + cleaning (replaces CycleGAN & MegaDepth).** The base paper
   converts a sketch to a photo with a fragile CycleGAN, then runs MegaDepth
   (2018). We drop CycleGAN entirely and use the **Depth Anything V2 (2024)**
   foundation model directly on the sketch, plus a **cleaning stage** (denoise,
   illumination normalization, CLAHE) that restores depth fidelity on noisy /
   low-contrast / unevenly-lit sketches. *Result:* sketch-depth correlates
   ≈ 0.93 with the corresponding photo's depth.
2. **Multi-sketch depth-space fusion.** The base paper stitches multiple
   sketches in image space and reports it "completely fails" on real drawings.
   We instead estimate depth **per sketch** and fuse the depth maps after dense
   intensity-based alignment + confidence weighting — robust to style
   differences.
3. **Interactive Three.js viewer.** Lifts the sketch into a 3D surface in the
   browser (rotate / zoom / depth-scale / wireframe).

We also report an **ablation** showing that an extra "synthetic shading" step we
tried does **not** help once a strong depth model is used (disabled by default).

---

## 2. Requirements & setup

- Python ≥ 3.9
- Packages in [`requirements.txt`](requirements.txt) (torch, torchvision,
  transformers, opencv-python, numpy, pillow, matplotlib)
- A CUDA GPU is **optional** (CPU works, just slower). Developed on an RTX 4060.

```bash
pip install -r requirements.txt
```

> First run downloads the Depth Anything V2 weights (~100 MB) from HuggingFace,
> so an internet connection is needed once.

*(On the authors' machine the interpreter is
`D:/anaconda3/envs/ocr_env/python.exe`; substitute your own `python`.)*

---

## 3. Data

Sample images are already included so you can run immediately. To use your own:

| Folder | Put here | Used by |
|--------|----------|---------|
| `data/sketches/` | building/scene **sketches, line art, engravings** (`.png/.jpg`) | `run.py single` / `fuse` |
| `data/buildings/` | real building **photos** | `run.py pairs`, `ablation.py`, `degrade_eval.py` |
| a subfolder you make, e.g. `data/myscene/` | 2–3 sketches of the **same** scene | `run.py fuse` |

The evaluation scripts need real photos because there is no 3D ground truth for
drawings: we synthesize a sketch from each photo (Dodging) and use the photo's
own depth as a reference.

---

## 4. How to run

From the project root (replace `python` with your interpreter if needed):

```bash
# Reconstruct every sketch in data/sketches/ (each on its own)
python src/run.py single

# Fuse multiple sketches of one scene into a single 3D model
python src/run.py fuse data/myscene my_scene

# Quantitative eval: photo-depth vs sketch-depth  -> outputs/pair_eval.csv
python src/run.py pairs

# Ablation (Table 1, clean sketches)              -> outputs/ablation_table.tex
python src/ablation.py

# Degradation robustness (Table 2)                -> outputs/degrade_table.tex
python src/degrade_eval.py
```

**View the 3D results in a browser:**

```bash
python -m http.server 8000 -d web
# then open http://localhost:8000   (Ctrl+C to stop)
```

In the viewer: pick a sample from the dropdown, drag to rotate, scroll to zoom,
right-drag to pan, and use the sliders for depth scale / detail / wireframe.

---

## 5. File structure

```
sketch3d/
├── README.md              this file (English)
├── requirements.txt       Python dependencies
│
├── src/                   all pipeline code
│   ├── preprocess.py      Sketch cleaning + enhancement (denoise, CLAHE, ...)
│   ├── depth.py           Depth Anything V2 wrapper (monocular depth)
│   ├── fusion.py          Multi-sketch depth-space fusion (ECC align + weight)
│   ├── dodging.py         Make sketches from photos (paired data / variants)
│   ├── run.py             Main entry: single / fuse / pairs  + web export
│   ├── ablation.py        Table 1: preprocessing ablation on clean sketches
│   └── degrade_eval.py    Table 2: robustness on degraded sketches
│
├── data/
│   ├── sketches/          input sketches  (sample images included)
│   ├── buildings/         real photos for evaluation
│   ├── myscene/           example multi-sketch fusion set
│   └── pairs/             auto-generated sketches from photos
│
├── web/                   interactive Three.js viewer
│   ├── index.html         page + controls
│   ├── viewer.js          loads depth + texture, builds the 3D surface
│   └── assets/            per-sample depth.json + texture.png + manifest.json
│                          (generated by run.py)
│
├── outputs/               generated results & metrics
│   ├── <name>/enhanced.png, depth_color.png    figures
│   ├── pair_eval.csv, ablation.csv, degrade.csv  metric tables
│   └── *_table.tex                              ready-to-paste LaTeX rows
│
└── report/                CVPR-format write-up
    ├── main.tex           the report (compile on Overleaf)
    ├── refs.bib           references
    ├── figures/           figures used in the report
    └── README.md          how to compile + finishing checklist
```

---

## 6. Outputs

- `web/assets/<name>/` + `manifest.json` — consumed by the viewer (accumulates
  across runs).
- `outputs/<name>/enhanced.png`, `depth_color.png` — report figures.
- `outputs/pair_eval.csv`, `ablation.csv`, `degrade.csv` — metric tables.
- `outputs/ablation_table.tex`, `degrade_table.tex` — paste-ready LaTeX rows.

---
