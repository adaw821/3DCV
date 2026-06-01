# 演讲逐字稿 — Sketch → 3D（4–4.5 分钟）

- **A = Wang Qiaopei**（讲幻灯片 1–4：故事 + 思路）
- **B = Peng Shiqi**（讲幻灯片 5–9：方法 + 结果 + 演示）
- 语速放稳，整场约 4 分 20 秒。下面【】里是中文提示，不用读出来。
- 每段后括号是大致用时。

---

## Slide 1 — Title 【A】(~12s)
"Hi everyone, we're Wang Qiaopei and Peng Shiqi. Our project is **Sketch to 3D**: reconstructing scenes from the era before photography, using nothing but hand-drawn sketches."

---

## Slide 2 — Motivation 【A】(~40s)
"Here's the motivation. Cameras are recent, so a huge part of our visual history survives only as drawings. A classic example is **Field Lane**, a London slum from Dickens' *Oliver Twist*. It was demolished long ago, and no photograph of it exists — only these 1840s engravings.

So the question we ask is: can we take such old sketches and rebuild a **3D street that people can actually explore**? That's the problem we tackle, building on a prior paper by Talwar and Laasri."

---

## Slide 3 — Prior work & limits 【A】(~40s)
"That prior paper proposed a pipeline: it turns a sketch into a fake photo with a CycleGAN, then estimates depth with MegaDepth, then builds a surface.

But it has three weaknesses. **One**, the CycleGAN is fragile — it's sensitive to drawing style and needs training. **Two**, MegaDepth is a 2018 model, hard to deploy and trained only on outdoor photos. And **three**, when they try to combine several sketches by matching features, it — in their own words — *completely fails* on real drawings. These three problems are exactly what we set out to fix."

---

## Slide 4 — Our approach 【A】(~32s)
"Our pipeline is simple: a sketch goes in, we estimate a depth map, and we lift it into a 3D surface.

We make three contributions. **First**, we drop the CycleGAN entirely and use a modern foundation depth model, with a cleaning stage for messy sketches. **Second**, we fuse multiple sketches in *depth space* instead of stitching images. **Third**, an interactive viewer to explore the result. Peng will now walk you through how each works."

【交接给 B】

---

## Slide 5 — Method 1: depth + cleaning 【B】(~35s)
"Thanks. Our first idea: modern depth models are good enough that we don't need the CycleGAN at all — **Depth Anything V2** reads the sketch directly.

But real sketches are photographed or scanned, so they have noise, low contrast, and uneven lighting. Our cleaning stage targets each of these — denoising, illumination normalization, and contrast equalization. You can see here: a clean sketch, the same sketch degraded, and our cleaning bringing it back."

---

## Slide 6 — Method 2: depth-space fusion 【B】(~35s)
"Second, fusion. Instead of stitching sketches in image space — which fails — we estimate a depth map for *each* sketch and combine them in **depth space**.

We align them with dense registration rather than sparse feature matching, then fuse with confidence weighting. Depth maps are smooth and comparable even when the two drawings look very different, so this is far more robust to style. On the right you can see two per-sketch depths merged into one clean fused result."

---

## Slide 7 — Results & negative result 【B】(~45s)
"How well does it work? Since drawings have no 3D ground truth, we generate sketches from real photos and compare depths. The sketch-derived depth correlates at **0.94** with the real photo's depth — with no CycleGAN — so the foundation model alone is enough.

For cleaning: on degraded sketches, correlation drops to 0.87, and our cleaning brings it back up to **0.96**. And here's an honest result — we also tried adding synthetic shading, ran an ablation, found it actually *hurt*, and removed it. We think reporting that is just as valuable."

---

## Slide 8 — Field Lane case study 【B】(~40s)
"Finally, back to Field Lane. We took two real 1840s engravings drawn by **different artists**. Even though their styles differ, our depth-space fusion aligns them and produces one coherent street — the figures in front are near, and the alley correctly recedes into the distance.

And because it's all in the browser, you can rotate and walk into this reconstruction of an early-1800s London street in real time."

【如果有录屏：此处切到查看器旋转的视频，5–8 秒】

---

## Slide 9 — Takeaways 【B】(~25s)
"To wrap up: a modern depth model removes the fragile CycleGAN step; cleaning helps on real degraded sketches; depth-space fusion succeeds where stitching failed; and our ablation honestly cut a part that didn't help. Next we'd like metric depth and filling in hidden surfaces. Thanks for watching!"

---

### 计时核对
| 段 | 讲者 | 累计 |
|----|------|------|
| S1–S4 | A | ~2:04 |
| S5–S9 | B | ~3:00 → 总计约 4:20 |

留约 10–15 秒缓冲，控制在 4.5 分钟以内。

### 录制提示
- 各自只讲自己那几页，交接句已写好（S4 末 / S5 开头），衔接自然。
- 别逐字背，理解了用自己的话说更自然；保留每页第一句和关键数字（0.94 / 0.87→0.96 / shading cut）。
- Slide 8 如果能放一段查看器旋转的屏幕录像，最加分。
