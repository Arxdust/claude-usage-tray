"""เรนเดอร์ widget ลอยหน้าจอ ธีมสว่าง (สไตล์ /usage ของ Claude).

แถบ usage แนวนอนบอก % ที่ "ใช้ไป" ของแต่ละหน้าต่างโควต้า + badge แพ็กเกจ + ปุ่ม
รีเฟรช/ปักหมุด/ปิด. ใช้ฟอนต์ Sarabun (ไทย) + Inter (ละติน) + Material Icons Round
จาก assets/fonts. คืน (image, regions) โดย regions เป็นพิกัด display สำหรับ hit-test.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import icon as icon_mod
from .i18n import get_language, t
from .status import COLORS, GREEN, ORANGE, RED, Status, humanize_reset

W, H = 320, 224
SS = 2

# ---- โทนสว่าง ----
BG = (250, 250, 252)
BORDER = (228, 230, 236)
TXT = (26, 28, 36)
SUB = (139, 146, 159)
TRACK = (233, 235, 240)
BADGE_BG = (238, 240, 245)
BADGE_TX = (92, 98, 112)
BTN_BG = (240, 242, 246)

# Material icon codepoints
MI = {"refresh": 0xE5D5, "close": 0xE5CD, "pin": 0xF10D, "monitor": 0xEF5B,
      "dot": 0xE061, "schedule": 0xE8B5}

_cache: dict[str, Any] = {}

# window color key: the OS makes pixels of exactly this color fully transparent
KEY = (255, 0, 255)


def _fpath(name: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = os.path.join(base, "assets", "fonts", name)
        if os.path.exists(p):
            return p
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "assets", "fonts", name)


def _sarabun(px, weight="Regular"):
    key = f"sara{weight}{px}"
    if key not in _cache:
        try:
            _cache[key] = ImageFont.truetype(_fpath(f"Sarabun-{weight}.ttf"), int(px))
        except OSError:
            _cache[key] = ImageFont.load_default()
    return _cache[key]


def _inter(px, weight="Regular"):
    key = f"inter{weight}{px}"
    if key not in _cache:
        try:
            f = ImageFont.truetype(_fpath("Inter-Variable.ttf"), int(px))
            try:
                f.set_variation_by_name(weight)
            except Exception:  # noqa: BLE001
                pass
            _cache[key] = f
        except OSError:
            _cache[key] = _sarabun(px, "SemiBold" if "Bold" in weight else "Regular")
    return _cache[key]


def _text(px, weight="Regular"):
    """Font for translated text: Sarabun has no Cyrillic, so non-Thai languages use Inter."""
    return _sarabun(px, weight) if get_language() == "th" else _inter(px, weight)


def _mi(px):
    key = f"mi{px}"
    if key not in _cache:
        try:
            _cache[key] = ImageFont.truetype(_fpath("MaterialIconsRound-Regular.otf"), int(px))
        except OSError:
            _cache[key] = ImageFont.load_default()
    return _cache[key]


def _classify(remaining, cfg):
    if remaining <= cfg["red_at"]:
        return RED
    if remaining <= cfg["orange_at"]:
        return ORANGE
    return GREEN


def _rt(d, x, y, s, f, fill, anchor="la"):
    d.text((x, y), s, font=f, fill=fill, anchor=anchor)


def _pill(d, box, r, fill):
    d.rounded_rectangle(box, radius=r, fill=fill)


def color_keyed(img: Image.Image) -> Image.Image:
    """Flatten an RGBA render for a color-keyed window, which has no per-pixel alpha:
    the corners and soft shadow become KEY, the card is made opaque (its anti-aliased
    edge blended onto the card color)."""
    opaque = img.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    card = Image.new("RGBA", img.size, BG + (255,))
    card.alpha_composite(img)
    out = Image.new("RGB", img.size, KEY)
    out.paste(card.convert("RGB"), mask=opaque)
    return out


def _wrap(d, text, font, width) -> list[str]:
    """Greedy word wrap to the given pixel width."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and d.textlength(trial, font=font) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def render(status: Status, cfg: dict, plan: str | None, updated: str) -> tuple[Image.Image, dict]:
    S = SS
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # เงานุ่ม + การ์ดโค้ง
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [8 * S, 10 * S, (W - 8) * S, (H - 6) * S], 22 * S, fill=(20, 24, 40, 60))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(9 * S)))
    d = ImageDraw.Draw(img)
    _pill(d, [6 * S, 6 * S, (W - 6) * S, (H - 8) * S], 22 * S, BG + (255,))
    d.rounded_rectangle([6 * S, 6 * S, (W - 6) * S, (H - 8) * S], 22 * S,
                        outline=BORDER + (255,), width=int(1.5 * S))

    regions: dict[str, Any] = {}
    pad = 22

    # ----- header -----
    ico = icon_mod.render(status, cfg).resize((26 * S, 26 * S), Image.LANCZOS)
    img.paste(ico, (pad * S, 18 * S), ico)
    d = ImageDraw.Draw(img)
    _rt(d, (pad + 34) * S, 22 * S, "Claude Usage", _inter(15 * S, "SemiBold"), TXT)

    # close (มุมขวาบน)
    cxr = W - pad - 4
    _rt(d, cxr * S, 24 * S, chr(MI["close"]), _mi(18 * S), SUB, anchor="mm")
    regions["close"] = (cxr - 13, 12, cxr + 13, 38)

    # badge แพ็กเกจ (ซ้ายของ close)
    if plan:
        bf = _inter(11 * S, "Medium")
        bb = d.textbbox((0, 0), plan, font=bf)
        bw = (bb[2] - bb[0]) / S + 18
        bx1 = cxr - 26 - bw
        _pill(d, [bx1 * S, 16 * S, (bx1 + bw) * S, 34 * S], 9 * S, BADGE_BG + (255,))
        _rt(d, (bx1 + bw / 2) * S, 25 * S, plan, bf, BADGE_TX, anchor="mm")

    # ----- sections (แถบ usage) -----
    quotas = [q for q in status.quotas if q.key in ("five_hour", "seven_day")][:2] or status.quotas[:2]
    y = 58
    for q in quotas:
        col = COLORS[_classify(q.remaining_pct, cfg)]
        label = t(f"widget.{q.key}", default=q.label)
        _rt(d, pad * S, y * S, label, _text(13.5 * S, "SemiBold"), TXT)
        _rt(d, (W - pad) * S, y * S, t("widget.used", pct=f"{q.used_pct:.0f}"),
            _text(12 * S, "Medium"), SUB, anchor="ra")
        # แถบ
        by = y + 22
        _pill(d, [pad * S, by * S, (W - pad) * S, (by + 8) * S], 4 * S, TRACK + (255,))
        fw = max(8, (W - pad * 2) * min(1.0, q.used_pct / 100.0))
        _pill(d, [pad * S, by * S, (pad + fw) * S, (by + 8) * S], 4 * S, col + (255,))
        _rt(d, pad * S, (by + 12) * S, t("common.resets", reset=humanize_reset(q.resets_at)),
            _text(11 * S, "Regular"), SUB)
        y += 56

    # ----- footer -----
    fy = H - 32
    # divider = BORDER at alpha 120 over the card, pre-blended and drawn opaque:
    # a translucent outline would overwrite the card's alpha and leave a see-through line
    div = tuple(int(b + (c - b) * 120 / 255) for b, c in zip(BG, BORDER))
    d.rounded_rectangle([pad * S, (fy - 8) * S, (W - pad) * S, (fy - 8) * S], 0,
                        outline=div + (255,), width=int(1 * S))
    _rt(d, pad * S, fy * S, chr(MI["dot"]), _mi(11 * S), COLORS[GREEN], anchor="lm")
    _rt(d, (pad + 16) * S, fy * S, t("widget.footer", time=updated, n=cfg["poll_seconds"] // 60),
        _text(10.5 * S, "Regular"), SUB, anchor="lm")

    # ปุ่มปักหมุด + รีเฟรช (มุมขวาล่าง)
    pinned = bool(_cache.get("_pinned", True))
    pin_x = W - pad - 12
    _rt(d, pin_x * S, fy * S, chr(MI["pin"]), _mi(16 * S),
        COLORS[GREEN] if pinned else SUB, anchor="mm")
    regions["pin"] = (pin_x - 13, fy - 13, pin_x + 13, fy + 13)

    rf_w = 30
    rf_x = pin_x - 16 - rf_w
    _pill(d, [rf_x * S, (fy - 12) * S, (rf_x + rf_w) * S, (fy + 12) * S], 11 * S, BTN_BG + (255,))
    _rt(d, (rf_x + rf_w / 2) * S, fy * S, chr(MI["refresh"]), _mi(16 * S), BADGE_TX, anchor="mm")
    regions["refresh"] = (rf_x, fy - 12, rf_x + rf_w, fy + 12)

    if status.error:
        # in the empty body of the card: outside the card the window is transparent
        ef = _text(11 * S)
        lines = _wrap(d, status.error, ef, (W - pad * 2) * S)
        ey = 112 - (len(lines) - 1) * 8
        for i, line in enumerate(lines):
            _rt(d, (W / 2) * S, (ey + i * 16) * S, line, ef, COLORS[ORANGE], anchor="mm")

    return img.resize((W, H), Image.LANCZOS), regions
