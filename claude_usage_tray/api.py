"""API client — อ่าน OAuth token ของ Claude Code แล้วถาม usage endpoint.

โมดูลนี้เป็น "ที่เดียว" ที่แตะ credential. คุยกับ api.anthropic.com เท่านั้น และ
ใช้ token ในเฮดเดอร์ Authorization เท่านั้น (ไม่เขียนลงดิสก์ ไม่ส่งไปที่อื่น).

Token จะถูก Claude Code หมุน (refresh) ให้เองในไฟล์ .credentials.json เราจึงแค่
อ่านไฟล์ใหม่ทุกรอบ ไม่ต้อง refresh เอง.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

API_URL_USAGE = "https://api.anthropic.com/api/oauth/usage"

CLAUDE_CONFIG_DIR = (
    Path(os.environ["CLAUDE_CONFIG_DIR"])
    if os.environ.get("CLAUDE_CONFIG_DIR")
    else Path.home() / ".claude"
)
CLAUDE_CREDENTIALS = CLAUDE_CONFIG_DIR / ".credentials.json"

# ถ้าหา version ของ claude CLI ไม่เจอ ใช้ค่านี้แทน (ต้องมี User-Agent claude-code/*
# ไม่งั้นจะโดน bucket ที่ rate-limit หนักและ 429 ตลอด)
_FALLBACK_UA = "claude-code/2.1.204"
_cached_ua: str | None = None


def read_access_token() -> str | None:
    """อ่าน accessToken ปัจจุบันจากไฟล์ credential."""
    if not CLAUDE_CREDENTIALS.exists():
        return None
    try:
        creds = json.loads(CLAUDE_CREDENTIALS.read_text(encoding="utf-8"))
        return creds.get("claudeAiOauth", {}).get("accessToken") or None
    except (OSError, ValueError, KeyError):
        # OSError ครอบเคสอ่านชนกับตอน Claude Code เขียนไฟล์ทับ (หมุน token) ด้วย
        return None


def read_plan() -> str | None:
    """อ่านชื่อแพ็กเกจสำหรับ badge (เช่น 'Max (20×)' / 'Pro') จาก credential."""
    if not CLAUDE_CREDENTIALS.exists():
        return None
    try:
        o = json.loads(CLAUDE_CREDENTIALS.read_text(encoding="utf-8")).get("claudeAiOauth", {})
    except (OSError, ValueError):
        return None
    sub = o.get("subscriptionType")
    tier = o.get("rateLimitTier") or ""
    name = sub.capitalize() if isinstance(sub, str) and sub else None
    m = re.search(r"(\d+)\s*x", str(tier), re.I)
    if name and m:
        return f"{name} ({m.group(1)}×)"
    return name


def _user_agent() -> str:
    global _cached_ua
    if _cached_ua:
        return _cached_ua
    ver = None
    try:
        out = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=5,
            shell=os.name == "nt",  # บน Windows claude เป็น .cmd ต้องผ่าน shell
        )
        m = re.search(r"(\d+\.\d+\.\d+)", out.stdout or "")
        if m:
            ver = m.group(1)
    except Exception:
        pass
    _cached_ua = f"claude-code/{ver}" if ver else _FALLBACK_UA
    return _cached_ua


def _headers() -> dict[str, str] | None:
    token = read_access_token()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": _user_agent(),
        "anthropic-beta": "oauth-2025-04-20",
    }


def fetch_usage() -> dict[str, Any]:
    """ดึงข้อมูล usage. คืน dict เสมอ; ถ้า error จะมีคีย์ 'error'.

    รูปแบบสำเร็จ (คีย์สำคัญ):
        {
          "five_hour": {"utilization": 33.0, "resets_at": "..."},
          "seven_day": {"utilization": 13.0, "resets_at": "..."},
          "seven_day_opus": null | {...},
          ...
        }
    utilization = % ที่ "ใช้ไปแล้ว" (0-100).
    Error text shown to the user comes from locales (error.<code>); 'message'
    only carries technical detail for codes without a translation.
    """
    headers = _headers()
    if not headers:
        return {"error": "no_token"}
    try:
        resp = requests.get(API_URL_USAGE, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"error": "connection"}
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code == 401:
            return {"error": "auth"}
        if code == 429:
            return {"error": "rate_limited"}
        return {"error": "http", "message": f"HTTP {code or '?'}"}
    except Exception as e:  # noqa: BLE001
        return {"error": "unknown", "message": str(e)[:80]}
