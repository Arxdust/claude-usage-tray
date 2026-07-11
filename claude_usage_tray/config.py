"""การตั้งค่าผู้ใช้ — โหลด/บันทึกจากไฟล์ JSON ในโฮมของผู้ใช้.

ค่าเริ่มต้นออกแบบให้ปลอดภัยกับ rate limit (poll ทุก 180 วิ) และ threshold สี
ตรงกับที่ผู้ใช้เลือก: ดูจาก "token ที่เหลือ" (remaining %).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".claude-usage-tray.json"

# ค่าเริ่มต้น — ทุกค่าปรับได้ในไฟล์ config
DEFAULTS: dict[str, Any] = {
    # วินาทีต่อรอบ poll. อย่าต่ำกว่า 180 ไม่งั้นเสี่ยงโดน HTTP 429 จาก API
    "poll_seconds": 180,
    # เกณฑ์สี วัดจาก "เปอร์เซ็นต์ที่เหลือ" (remaining = 100 - utilization)
    #   remaining > green_above           -> เขียว
    #   orange_at >= remaining > red_at    -> ส้ม
    #   remaining <= red_at                -> แดง (กะพริบ)
    "green_above": 50,   # เหลือมากกว่า 50% = เขียว
    "orange_at": 50,     # เหลือ <= 50% = ส้ม
    "red_at": 20,        # เหลือ <= 20% = แดง
    # เด้ง Windows notification (balloon) เมื่อ "ข้ามเกณฑ์ลง" ครั้งแรก
    "notify": True,
    # เด้ง popup หน้าต่างเตือน (ค้างหน้าจอ) ทันทีที่เหลือต่ำกว่า 50% และ 20%
    "popup_alert": True,
    # ให้ไอคอนแดงกะพริบเมื่อใกล้หมด
    "blink_when_red": True,
    # แสดงตัวเลข % ที่เหลือทับบนไอคอน (อ่านยากที่ 16px แต่ชัดที่ DPI สูง)
    "show_percent_text": True,
    # นับ quota ไหนบ้างในการเลือกสี (ใช้ค่าที่แย่ที่สุด = เหลือน้อยสุด)
    #   five_hour = หน้าต่าง 5 ชม., seven_day = เพดานรายสัปดาห์
    "watch": ["five_hour", "seven_day"],
    # widget ลอยหน้าจอ (ธีมสว่าง)
    "widget_opacity": 0.94,     # ความโปร่งใส 0.5–1.0
    "widget_on_start": False,   # เปิด widget อัตโนมัติเมื่อเริ่มโปรแกรม
}


def load() -> dict[str, Any]:
    """โหลด config รวมกับค่า default; เขียนไฟล์ตัวอย่างให้ถ้ายังไม่มี."""
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass  # ไฟล์เสีย -> ใช้ค่า default เงียบ ๆ
    else:
        save(cfg)
    return cfg


def save(cfg: dict[str, Any]) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
