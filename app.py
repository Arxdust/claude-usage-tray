"""Entry point สำหรับ PyInstaller (import แบบ absolute).

โหมด dev ใช้ `python -m claude_usage_tray` ได้เหมือนเดิม; ไฟล์นี้มีไว้ให้ตัว build
ชี้เข้ามาโดยไม่ติดปัญหา relative import ตอนถูกรันเป็นสคริปต์ top-level.
"""
from claude_usage_tray.tray import main

if __name__ == "__main__":
    main()
