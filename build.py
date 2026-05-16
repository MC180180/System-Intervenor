import os
import subprocess
import sys

print("正在准备打包系统干预器为独立 EXE 文件...")
print("这个过程可能需要耗费几十秒，请耐心等待。")
print("如果遇到杀毒软件拦截，请允许放行。\n")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "-y",
    "--noconsole",
    "--onefile",
    "--name", "系统干预器",
    "main.py"
]

try:
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n打包成功！")
        print("您的可执行文件已经生成在当前目录的 dist 文件夹中。")
        os.startfile("dist")
    else:
        print("\n打包过程遇到错误，请检查相关输出。")
except Exception as e:
    print("\n发生异常:", e)

os.system("pause")
