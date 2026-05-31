# Report — how to compile & finish

The report is `main.tex` (CVPR-style two-column). No LaTeX install on this
machine, so compile on **Overleaf** (free, in-browser):

1. [overleaf.com](https://overleaf.com) → **New Project → Blank Project**.
2. Delete the default `main.tex`, then **upload** `main.tex`, `refs.bib`, and
   the whole `figures/` folder (drag the folder in).
3. Top-left **Menu → Compiler → pdfLaTeX**. Click **Recompile**.

The numbers in Table 1 and Table 2 are already filled in from our current
run. The text reflects the honest finding: the foundation model is strong on
its own, **cleaning + CLAHE** helps on degraded sketches, and **synthetic
shading does not help** (we disabled it). Re-run on your final data to refresh
the numbers.

## Before submitting — fill in every `[[FILL]]`

Search the file for `[[FILL` and replace:

- [ ] Author names, course, emails (top of `main.tex`).
- [ ] **Refresh the two tables on your final data.** First delete the
      synthetic test images from `data/buildings/` (`test_building*`), add your
      real photos, then run both:
      - `python src/ablation.py`  → clean-sketch ablation → **Table 1**
        (paste from `outputs/ablation_table.tex`).
      - `python src/degrade_eval.py` → degradation robustness → **Table 2**
        (paste from `outputs/degrade_table.tex`).
      The `[[FILL\ 0.93]]` markers in the abstract/§4 should match Table 1's
      raw-sketch corr.
- [ ] **Figures** are already generated from a real sketch
      (`depth_example.png`, `recon_3d.png`, `degrade_example.png`,
      `sketch_input.png`, `enhanced_example.png`). Regenerate if you want a
      different example (same filenames = no tex edits).
      - **Add `figures/viewer.png`**: a screenshot of the Three.js viewer
        (`python -m http.server 8000 -d web`), referenced in Fig. 3's caption.
      - Optional `figures/fusion.png` for the multi-sketch fusion result.
- [ ] **Individual Contributions** section — split the work between you two.

## Length
Target ~5 pages excluding references. If it runs long, the rubric rewards
concise writing — trim Related Work first.
