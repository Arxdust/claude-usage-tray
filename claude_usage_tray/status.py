"""แปลง usage response -> สถานะสี + ตัวเลขสรุปสำหรับ tooltip/popup."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .i18n import t

# ระดับสถานะ เรียงจากดี -> แย่
GREEN = "green"
ORANGE = "orange"
RED = "red"
UNKNOWN = "unknown"

# สี RGB สำหรับวาดไอคอน
COLORS = {
    GREEN: (34, 197, 94),    # #22C55E
    ORANGE: (245, 158, 11),  # #F59E0B
    RED: (239, 68, 68),      # #EF4444
    UNKNOWN: (148, 163, 184),  # เทา #94A3B8
}

# usage keys that are real quota windows: five_hour, seven_day, seven_day_opus, ...
QUOTA_PREFIXES = ("five_hour", "seven_day")


def quota_label(key: str) -> str:
    """Localized quota name (locales: quota.<key>); unknown quotas show their key."""
    return t(f"quota.{key}", default=key)


@dataclass
class Quota:
    key: str
    label: str
    used_pct: float       # % ที่ใช้ไป (utilization)
    remaining_pct: float  # % ที่เหลือ
    resets_at: str | None


@dataclass
class Status:
    color: str                 # GREEN/ORANGE/RED/UNKNOWN
    remaining_pct: float | None  # remaining ของ quota ที่แย่ที่สุด
    driver: str | None         # key ของ quota ที่เป็นตัวกำหนดสี
    quotas: list[Quota]        # ทุก quota ที่อ่านได้ (ไว้โชว์ใน popup)
    error: str | None = None


def _classify(remaining: float, cfg: dict[str, Any]) -> str:
    if remaining <= cfg["red_at"]:
        return RED
    if remaining <= cfg["orange_at"]:
        return ORANGE
    return GREEN


def evaluate(usage: dict[str, Any], cfg: dict[str, Any]) -> Status:
    """คำนวณสถานะจาก response ของ fetch_usage()."""
    if usage.get("error"):
        code = usage["error"]
        return Status(UNKNOWN, None, None, [], error=t(f"error.{code}", default=usage.get("message") or code))

    quotas: list[Quota] = []
    for key, val in usage.items():
        # only plan rate-limit windows; the endpoint also returns codename entries
        # (e.g. "iguana_necktie" = a dollar credit budget) that are not quotas
        if not isinstance(val, dict) or not key.startswith(QUOTA_PREFIXES):
            continue
        util = val.get("utilization")
        if util is None:
            continue  # quota ที่ยังไม่เริ่มใช้ (เช่น seven_day_opus = null)
        used = float(util)
        quotas.append(
            Quota(
                key=key,
                label=quota_label(key),
                used_pct=used,
                remaining_pct=max(0.0, 100.0 - used),
                resets_at=val.get("resets_at"),
            )
        )

    if not quotas:
        return Status(UNKNOWN, None, None, [], error=t("error.no_quota"))

    # เลือกสีจาก quota ที่ผู้ใช้สั่งให้เฝ้า (watch) และเหลือน้อยที่สุด = แย่สุด
    watched = [q for q in quotas if q.key in cfg["watch"]] or quotas
    worst = min(watched, key=lambda q: q.remaining_pct)
    color = _classify(worst.remaining_pct, cfg)

    quotas.sort(key=lambda q: q.remaining_pct)  # แย่สุดขึ้นก่อนใน popup
    return Status(color, worst.remaining_pct, worst.key, quotas)


def humanize_reset(resets_at: str | None) -> str:
    """แปลง ISO timestamp -> 'อีก 2ชม 14น' (โดยประมาณ)."""
    if not resets_at:
        return "-"
    try:
        dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    delta = dt - datetime.now(timezone.utc)
    secs = int(delta.total_seconds())
    if secs <= 0:
        return t("reset.soon")
    h, rem = divmod(secs, 3600)
    m = rem // 60
    if h >= 24:
        d, hh = divmod(h, 24)
        return t("reset.days", d=d, h=hh)
    if h:
        return t("reset.hours", h=h, m=m)
    return t("reset.minutes", m=m)
