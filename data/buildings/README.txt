把你额外下载的真实建筑照片放这里 (png/jpg)。

在终端(PowerShell, 在 sketch3d 文件夹里打开)运行:
   D:/anaconda3/envs/ocr_env/python.exe src/run.py pairs

会自动用Dodging生成素描, 并对比"照片深度 vs 素描深度",
输出 outputs/pair_eval.csv (报告里的定量评估表)。
