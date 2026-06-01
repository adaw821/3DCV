// Build the 9-slide deck for the sketch->3D project.
const pptxgen = require("pptxgenjs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "report", "figures");
const OUT = path.join(ROOT, "outputs");
const DATA = path.join(ROOT, "data");

const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";

// palette (amber/purple echo the inferno depth maps)
const DARK = "1A1D29", INK = "20242E", WHITE = "FFFFFF";
const AMBER = "E8820E", PURPLE = "7C5CD3", MUTE = "6B7280", LINE = "E4E6EC";
const HF = "Georgia", BF = "Calibri";

const W = 13.333, H = 7.5;

// ---- helpers ----------------------------------------------------------
function titleBar(s, t, kicker) {
  if (kicker)
    s.addText(kicker.toUpperCase(), { x: 0.6, y: 0.42, w: 12, h: 0.3,
      fontFace: BF, fontSize: 12, bold: true, color: AMBER, charSpacing: 2 });
  s.addText(t, { x: 0.6, y: 0.68, w: 12.1, h: 0.8, fontFace: HF, fontSize: 30,
    bold: true, color: INK });
}
function bullets(s, items, x, y, w, opts = {}) {
  s.addText(
    items.map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 18 },
      breakLine: true } })),
    { x, y, w, h: opts.h || 3.6, fontFace: BF, fontSize: opts.fs || 16,
      color: opts.color || "33384A", lineSpacingMultiple: 1.15, valign: "top",
      paraSpaceAfter: opts.sp != null ? opts.sp : 10 });
}
function img(s, file, x, y, w, h) {
  s.addImage({ path: file, x, y, w, h, sizing: { type: "contain", w, h } });
}
function caption(s, t, x, y, w) {
  s.addText(t, { x, y, w, h: 0.3, fontFace: BF, fontSize: 11, italic: true,
    color: MUTE, align: "center" });
}

// ============================ Slide 1 — Title (dark) ===================
let s = p.addSlide(); s.background = { color: DARK };
img(s, path.join(FIG, "depth_example.png"), 7.7, 0, 5.633, 7.5);
s.addShape("rect", { x: 7.7, y: 0, w: 5.633, h: 7.5, fill: { color: DARK,
  transparency: 35 } });
s.addText("Sketch → 3D", { x: 0.7, y: 2.2, w: 7.2, h: 1.1, fontFace: HF,
  fontSize: 50, bold: true, color: WHITE });
s.addText("Reconstructing pre-photograph scenes from hand-drawn sketches",
  { x: 0.72, y: 3.35, w: 6.9, h: 0.8, fontFace: BF, fontSize: 18, color: "C7CBD6" });
s.addText([{ text: "Wang Qiaopei", options: {} },
           { text: "    ·    ", options: { color: AMBER } },
           { text: "Peng Shiqi", options: {} }],
  { x: 0.72, y: 4.4, w: 7, h: 0.4, fontFace: BF, fontSize: 16, color: "E9EBF0" });
s.addText("Building on Talwar & Laasri, 3D Reconstruction from Sketches (arXiv:2505.14621)",
  { x: 0.72, y: 6.7, w: 7, h: 0.3, fontFace: BF, fontSize: 11, italic: true,
    color: "8A90A0" });

// ============================ Slide 2 — Motivation =====================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Why reconstruct 3D from drawings?", "Motivation");
bullets(s, [
  "Cameras are recent — countless streets and buildings survive only as drawings.",
  "Field Lane: a London slum in Dickens’ Oliver Twist, long demolished. No photos exist — only 1800s engravings.",
  "Goal: turn such sketches into a 3D street you can explore.",
], 0.6, 1.9, 6.5, { fs: 18, sp: 16 });
img(s, path.join(DATA, "fieldlane",
  "field-lane-holborn-london-in-the-1840s-vividly-described-by-dickens-in-oliver-twist-this-engraving-has-the-names-of-fagin-and-scrooge-above-shop-fronts-2C84JE2.jpg"),
  7.5, 1.8, 5.2, 4.7);
caption(s, "Field Lane engraving, 1840s (Holborn, London)", 7.5, 6.55, 5.2);

// ============================ Slide 3 — Prior work =====================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Prior work & its limits", "Background");
s.addText("Base pipeline (Talwar & Laasri):  sketch → CycleGAN → MegaDepth → 3D surface",
  { x: 0.6, y: 1.75, w: 12, h: 0.4, fontFace: BF, fontSize: 16, bold: true,
    color: INK });
const lims = [
  ["CycleGAN is fragile", "Sketch→photo style transfer is sensitive to drawing style and needs training."],
  ["MegaDepth is dated", "The 2018 depth model is hard to deploy and trained only on outdoor photos."],
  ["Stitching fails", "Combining multiple sketches by feature matching “completely fails” on real drawings."],
];
let cx = 0.6;
lims.forEach(([h1, b], i) => {
  s.addShape("roundRect", { x: cx, y: 2.5, w: 3.9, h: 3.4, rectRadius: 0.08,
    fill: { color: "F7F8FB" }, line: { color: LINE, width: 1 } });
  s.addText((i + 1).toString(), { x: cx + 0.25, y: 2.75, w: 0.7, h: 0.7,
    fontFace: HF, fontSize: 26, bold: true, color: WHITE, align: "center",
    valign: "middle", fill: { color: AMBER }, shape: "ellipse" });
  s.addText(h1, { x: cx + 0.25, y: 3.65, w: 3.4, h: 0.5, fontFace: BF,
    fontSize: 18, bold: true, color: INK });
  s.addText(b, { x: cx + 0.25, y: 4.2, w: 3.45, h: 1.5, fontFace: BF,
    fontSize: 14, color: "4B5163", lineSpacingMultiple: 1.1, valign: "top" });
  cx += 4.07;
});

// ============================ Slide 4 — Our approach ===================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Our approach: three contributions", "Overview");
// pipeline strip
const strip = [["sketch_input.png", "sketch"], ["depth_example.png", "depth"],
  ["recon_3d.png", "3D surface"]];
let px = 0.9;
strip.forEach(([f, lab], i) => {
  img(s, f.includes("recon") ? path.join(FIG, f) : path.join(FIG, f), px, 1.8, 2.7, 2.0);
  caption(s, lab, px, 3.82, 2.7);
  if (i < 2) s.addText("→", { x: px + 2.7, y: 1.8, w: 0.7, h: 2.0,
    fontFace: BF, fontSize: 30, bold: true, color: AMBER, align: "center",
    valign: "middle" });
  px += 3.4;
});
const contribs = [
  ["1", "Foundation depth + cleaning", "Drop CycleGAN; run Depth Anything V2 on the sketch, with a cleaning stage for real noisy drawings."],
  ["2", "Depth-space fusion", "Fuse multiple sketches in depth space (not image stitching) — robust to style."],
  ["3", "Interactive viewer", "A Three.js viewer lifts the sketch into an explorable 3D surface."],
];
let yy = 4.35;
contribs.forEach(([n, h1, b]) => {
  s.addText(n, { x: 0.6, y: yy, w: 0.55, h: 0.55, fontFace: HF, fontSize: 20,
    bold: true, color: WHITE, align: "center", valign: "middle",
    fill: { color: PURPLE }, shape: "ellipse" });
  s.addText([{ text: h1 + "   ", options: { bold: true, color: INK } },
             { text: b, options: { color: "5A6072" } }],
    { x: 1.3, y: yy - 0.02, w: 11.4, h: 0.62, fontFace: BF, fontSize: 15,
      valign: "middle", lineSpacingMultiple: 1.0 });
  yy += 0.78;
});

// ============================ Slide 5 — Method 1 =======================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Foundation depth + targeted cleaning", "Method · 1");
img(s, path.join(FIG, "degrade_example.png"), 0.6, 1.95, 7.4, 3.9);
caption(s, "clean sketch  →  realistic degradation  →  after our cleaning", 0.6, 5.9, 7.4);
bullets(s, [
  "Depth Anything V2 (2024) reads the sketch directly — no CycleGAN needed.",
  "Cleaning targets real-world damage: denoise, illumination normalization, CLAHE.",
  "Each step undoes a specific corruption (noise / uneven light / low contrast).",
], 8.3, 2.1, 4.5, { fs: 15, sp: 14 });

// ============================ Slide 6 — Method 2 =======================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Multi-sketch depth-space fusion", "Method · 2");
img(s, path.join(OUT, "fusion_compare.png"), 0.6, 2.5, 8.2, 2.9);
caption(s, "per-sketch depth (left, middle)  →  fused depth (right)", 0.6, 5.45, 8.2);
bullets(s, [
  "Image-space stitching fails on real sketches.",
  "We align in depth space with dense ECC registration (not sparse features).",
  "Fuse confidence-weighted — tolerant of style differences, suppresses noise.",
], 9.05, 2.4, 3.75, { fs: 15, sp: 14 });

// ============================ Slide 7 — Results ========================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Results & a useful negative result", "Evaluation");
const stats = [
  ["r = 0.94", "sketch depth vs. real-photo depth (no CycleGAN)"],
  ["0.87 → 0.96", "cleaning recovers degraded sketches (corr.)"],
  ["shading: cut", "ablation showed synthetic shading hurts — we removed it"],
];
let sx = 0.6;
stats.forEach(([big, lab]) => {
  s.addShape("roundRect", { x: sx, y: 2.0, w: 3.9, h: 2.0, rectRadius: 0.08,
    fill: { color: "FBF4EA" }, line: { color: "F0DEC2", width: 1 } });
  s.addText(big, { x: sx + 0.2, y: 2.2, w: 3.5, h: 0.9, fontFace: HF,
    fontSize: 30, bold: true, color: AMBER, align: "center" });
  s.addText(lab, { x: sx + 0.3, y: 3.15, w: 3.3, h: 0.7, fontFace: BF,
    fontSize: 13, color: "5A6072", align: "center", valign: "top",
    lineSpacingMultiple: 1.05 });
  sx += 4.07;
});
bullets(s, [
  "Metric: no 3D ground truth for drawings, so we compare to the real photo’s depth via paired (photo, sketch) data.",
  "Key insight: a strong foundation model is enough — the fragile style-transfer step is unnecessary.",
  "We honestly ablated our own idea (shading) and dropped it when it didn’t help.",
], 0.6, 4.4, 12.1, { fs: 15, sp: 9, h: 2.6 });

// ============================ Slide 8 — Field Lane =====================
s = p.addSlide(); s.background = { color: WHITE };
titleBar(s, "Field Lane: the original scene, rebuilt", "Case study");
img(s, path.join(FIG, "fieldlane.png"), 0.6, 1.9, 7.8, 5.0);
bullets(s, [
  "Two 1840s engravings by different artists.",
  "Despite different line styles, dense alignment + depth fusion give one coherent street.",
  "Foreground figures are near; the alley recedes into depth.",
  "Explore it live in the Three.js viewer.",
], 8.7, 2.2, 4.1, { fs: 15, sp: 14 });

// ============================ Slide 9 — Takeaways (dark) ===============
s = p.addSlide(); s.background = { color: DARK };
s.addText("Takeaways", { x: 0.7, y: 0.7, w: 12, h: 0.9, fontFace: HF,
  fontSize: 34, bold: true, color: WHITE });
bullets(s, [
  "A 2024 foundation depth model removes the fragile CycleGAN step (r = 0.94 vs. photo depth).",
  "Cleaning measurably restores fidelity on degraded, real-world sketches.",
  "Fusing in depth space succeeds where image stitching fails — shown on real Field Lane engravings.",
  "An honest ablation removed a component (synthetic shading) that did not help.",
  "An interactive viewer lets anyone explore the reconstructed 3D street.",
], 0.7, 1.9, 12.0, { fs: 17, sp: 14, color: "D7DAE4" });
s.addText("Future work:  metric depth  ·  occlusion completion  ·  optional ControlNet for highly stylized drawings",
  { x: 0.7, y: 6.35, w: 12, h: 0.5, fontFace: BF, fontSize: 14, italic: true,
    color: AMBER });

p.writeFile({ fileName: path.join(__dirname, "sketch3d_slides.pptx") })
  .then((f) => console.log("saved", f));
