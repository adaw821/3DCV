# 素描 → 3D 重建（中文说明）

从一张或多张**手绘素描**重建出可交互的 3D 场景。本项目基于论文
Talwar & Laasri《3D Reconstruction from Sketches》(arXiv:2505.14621)，并做了
三处改进。

> English version: [`README.md`](README.md)

---

## 一、这个项目是干什么的

一张素描里隐含着 3D 结构（建筑的立面、前后遮挡、透视）。我们把这种结构恢复出来，
把素描变成可以在浏览器里旋转查看的 3D 表面。整体流程：

```
素描 ─▶ [清理+增强] ─▶ [Depth Anything V2 估深度] ─▶ [(多素描融合)] ─▶ 深度 ─▶ 3D表面 + 网页查看器
```

**相对原论文的三个改进：**

1. **现代深度模型 + 清理（替代 CycleGAN 和 MegaDepth）**。原论文先用脆弱的
   CycleGAN 把素描转成照片，再用 2018 年的 MegaDepth 估深度。我们**完全去掉
   CycleGAN**，直接用 **Depth Anything V2（2024）** 基础模型估深度，再加一个
   **清理阶段**（降噪、光照归一化、CLAHE），在噪声/低对比/光照不均的素描上恢复
   深度保真度。*结果*：素描深度与对应照片深度相关性 ≈ 0.93。
2. **多素描深度空间融合**。原论文在图像空间"拼接"多张素描，真实数据上"完全失败"。
   我们改成**每张素描各自估深度**，再用稠密强度对齐 + 置信度加权融合深度图，对
   画风差异鲁棒。
3. **Three.js 交互式查看器**。把素描在浏览器里抬升成 3D 表面（旋转/缩放/调深度/线框）。

我们还做了**消融实验**：发现额外尝试的"合成阴影"步骤在用了强深度模型后**并无帮助**，
因此默认关闭。

---

## 二、环境与安装

- Python ≥ 3.9
- 依赖见 [`requirements.txt`](requirements.txt)（torch、torchvision、transformers、
  opencv-python、numpy、pillow、matplotlib）
- CUDA GPU **可选**（没有 GPU 用 CPU 也能跑，只是慢）。开发用的是 RTX 4060。

```bash
pip install -r requirements.txt
```

> 首次运行会从 HuggingFace 下载 Depth Anything V2 权重（约 100MB），需要联网一次。

> 作者机器上的解释器是 `D:/anaconda3/envs/ocr_env/python.exe`；老师在自己机器上把
> 命令里的 `python` 换成自己的解释器即可。

---

## 三、数据

项目里**已附带示例图片**，可直接运行。要用自己的图：

| 文件夹 | 放什么 | 被哪个脚本用 |
|--------|--------|--------------|
| `data/sketches/` | 建筑/场景**素描、线稿、版画**（`.png/.jpg`） | `run.py single` / `fuse` |
| `data/buildings/` | 真实建筑**照片** | `run.py pairs`、`ablation.py`、`degrade_eval.py` |
| 自建子文件夹，如 `data/myscene/` | **同一场景**的 2–3 张素描 | `run.py fuse` |

评估脚本需要真实照片，因为素描没有 3D 真值：我们从每张照片合成一张素描（Dodging），
用照片自身的深度作参考来量化对比。

---

## 四、怎么运行

在项目根目录执行（`python` 换成你的解释器）：

```bash
# 重建 data/sketches/ 里的每一张素描（各自独立）
python src/run.py single

# 把一个文件夹里的多张素描融合成一个 3D
python src/run.py fuse data/myscene 场景名

# 定量评估：照片深度 vs 素描深度  -> outputs/pair_eval.csv
python src/run.py pairs

# 消融实验（报告表1，干净素描）   -> outputs/ablation_table.tex
python src/ablation.py

# 退化鲁棒性（报告表2）           -> outputs/degrade_table.tex
python src/degrade_eval.py
```

**在浏览器里看 3D 结果：**

```bash
python -m http.server 8000 -d web
# 然后打开 http://localhost:8000   （Ctrl+C 停止）
```

查看器里：右上角下拉切换样本，拖动旋转，滚轮缩放，右键平移，滑块调深度强度/细节/线框。

> 用 PyCharm：打开本文件夹 → 解释器选 `D:\anaconda3\envs\ocr_env\python.exe` →
> 底部 Terminal（`Alt+F12`）里敲上面的命令（可直接用 `python`）。

---

## 五、文件结构

```
sketch3d/
├── README.md              英文说明
├── README_zh.md           本文件（中文）
├── requirements.txt       Python 依赖
│
├── src/                   全部流程代码
│   ├── preprocess.py      素描清理+增强（降噪、CLAHE 等）
│   ├── depth.py           Depth Anything V2 封装（单目深度估计）
│   ├── fusion.py          多素描深度空间融合（ECC对齐+加权）
│   ├── dodging.py         从照片生成素描（造配对数据/画风变体）
│   ├── run.py             主入口：single / fuse / pairs，并导出网页资源
│   ├── ablation.py        报告表1：干净素描上的预处理消融
│   └── degrade_eval.py    报告表2：退化素描上的鲁棒性（创新2的正面证据）
│
├── data/
│   ├── sketches/          输入素描（含示例图）
│   ├── buildings/         评估用真实照片
│   ├── myscene/           多素描融合示例集
│   └── pairs/             从照片自动生成的素描
│
├── web/                   Three.js 交互查看器
│   ├── index.html         页面 + 控件
│   ├── viewer.js          读取深度+纹理，构建 3D 表面
│   └── assets/            每个样本的 depth.json + texture.png + manifest.json
│                          （由 run.py 生成）
│
├── outputs/               生成的结果与指标
│   ├── <名字>/enhanced.png, depth_color.png    报告图
│   ├── pair_eval.csv, ablation.csv, degrade.csv  指标表
│   └── *_table.tex                              可直接粘贴的 LaTeX 表格行
│
└── report/                CVPR 格式报告
    ├── main.tex           报告正文（Overleaf 编译）
    ├── refs.bib           参考文献
    ├── figures/           报告用图
    └── README.md          编译步骤 + 提交前清单
```

---

## 六、输出在哪

- `web/assets/<名字>/` + `manifest.json` —— 网页查看器读取（跨多次运行累积）
- `outputs/<名字>/enhanced.png`、`depth_color.png` —— 报告图
- `outputs/pair_eval.csv`、`ablation.csv`、`degrade.csv` —— 指标表
- `outputs/ablation_table.tex`、`degrade_table.tex` —— 可直接粘贴的 LaTeX 行

> **注意 —— 这些是生成物，不纳入版本/不用提交。** `outputs/` 和 `web/assets/`
> 都被 `.gitignore` 排除：跑一次脚本就重新生成，所以**不属于交付物**。评分需要的
> 结果都已在**报告**里（PDF + `report/figures/`，这个文件夹**有**进仓库）和**演示
> 视频**里。老师验代码时照上面的命令一跑，这些文件会自动生成。
> *（可选：若想让老师没 GPU、不下模型也能打开 3D 查看器，把 `web/assets/` 文件夹
> 跟代码一起附上即可。）*

---

## 七、报告

`report/main.tex` 是 CVPR 格式正文，在 [Overleaf](https://overleaf.com) 上编译
（上传 `main.tex`、`refs.bib`、`figures/`，编译器选 pdfLaTeX）。详见
`report/README.md` 的步骤和提交前清单。

---

## 八、交付物清单

- [x] 代码（已全部跑通）
- [ ] 报告 PDF（Overleaf 编译，填好 `[[FILL]]`，约 5 页）
- [ ] 演示视频（4–4.5 分钟，每人都要出镜讲解）

> 示例里包含合成测试图（`test_street`、`test_building`）；交 final 前，把
> `data/buildings/test_building*` 删掉再重跑评估，数字更干净。
