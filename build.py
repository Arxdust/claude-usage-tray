"""Build เป็นไฟล์ .exe เดียว ด้วย PyInstaller.

    pip install pyinstaller
    python build.py

ได้ผลลัพธ์ที่ dist/ClaudeUsageTray.exe (รันได้เลย ไม่ต้องมี Python)
"""
import subprocess
import sys

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "assets", "app.ico")

ARGS = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile",
    "--windowed",              # ไม่มีหน้าต่าง console
    "--name", "ClaudeUsageTray",
    "--collect-submodules", "pystray",
    "--collect-submodules", "PIL",
]
if os.path.exists(ICON):
    ARGS += ["--icon", ICON]
ARGS.append(os.path.join(HERE, "app.py"))

if __name__ == "__main__":
    raise SystemExit(subprocess.call(ARGS))
