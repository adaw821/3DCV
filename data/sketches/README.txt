把你下载的建筑/场景素描图片放这里 (png/jpg)。

然后在终端(PowerShell, 在 sketch3d 文件夹里打开)运行:
   D:/anaconda3/envs/ocr_env/python.exe src/run.py single

多张同一场景的素描 -> 放进一个子文件夹做融合:
   D:/anaconda3/envs/ocr_env/python.exe src/run.py fuse data/你的文件夹 场景名
