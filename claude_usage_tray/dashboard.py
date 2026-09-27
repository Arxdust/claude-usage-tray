"""เรนเดอร์หน้า Dashboard สวย ๆ ด้วย Pillow (สไตล์ AC control app).

ให้ภาพการ์ดโทนน้ำเงินเข้ม + เกจวงกลมเรืองแสงโชว์ % โควต้าที่เหลือ + การ์ด quota
เลือกได้ + ปุ่มกลม. คืน (image, regions) โดย regions เป็นพิกัด (display space)
สำหรับ hit-test คลิกในหน้าต่าง tkinter.
"""
from __future__ import annotations

import math
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .i18n import get_language, t
from .status import COLORS, GREEN, ORANGE, RED, Status, humanize_reset

# ขนาดหน้าจอแสดงผล (display) และ supersample เพื่อความคม
W, H = 360, 640
SS = 2  # วาดที่ 2x แล้วย่อ = ขอบเนียน

# โทนสี
BG_TOP = (11, 15, 28)
BG_BOT = (20, 27, 49)
TXT = (235, 239, 248)
SUB = (128, 141, 170)
CARD = (25, 33, 56)
CARD_SEL_TXT = (10, 15, 28)
TRACK = (38, 48, 74)
ACCENT = (74, 158, 255)  # ฟ้าปุ่ม

GAUGE_START = 150.0   # องศาเริ่ม (ล่างซ้าย) — PIL: 0=ขวา, เพิ่มตามเข็ม (y ชี้ลง)
GAUGE_SWEEP = 240.0   # กวาด 240° เปิดช่องล่าง 120°

# ป้ายย่อของแต่ละ quota — model names stay as-is; the rest come from locales (tag.<key>)
TAGS = {
    "seven_day_opus": "Opus",
    "seven_day_sonnet": "Sonnet",
    "seven_day_cowork": "Cowork",
}


def _font(px: int, weight: str = "regular"):
    # ใช้ Leelawadee UI / Tahoma ที่มี glyph ภาษาไทยครบ (Segoe UI ไม่มี -> เป็นกล่อง)
    # Leelawadee has no Cyrillic, so other languages use Segoe UI
    if get_language() == "th":
        names = {
            "regular": ("LeelawUI.ttf", "leelawui.ttf", "tahoma.ttf", "arial.ttf"),
            "semibold": ("LeelaUIb.ttf", "leelauib.ttf", "tahomabd.ttf", "arialbd.ttf"),
            "bold": ("LeelaUIb.ttf", "leelauib.ttf", "tahomabd.ttf", "arialbd.ttf"),
        }[weight]
    else:
        names = {
            "regular": ("segoeui.ttf", "tahoma.ttf", "arial.ttf"),
            "semibold": ("seguisb.ttf", "segoeuib.ttf", "tahomabd.ttf", "arialbd.ttf"),
            "bold": ("segoeuib.ttf", "tahomabd.ttf", "arialbd.ttf"),
        }[weight]
    for n in names:
        try:
            return ImageFont.truetype(n, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _font_num(px: int):
    """ฟอนต์บางสำหรับตัวเลขใหญ่ (ตัวเลข/สัญลักษณ์ล้วน ไม่ต้องมีไทย)."""
    for n in ("segoeuil.ttf", "segoeui.ttf", "tahoma.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(n, px)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------- ไอคอน vector (เลี่ยง unicode ที่ฟอนต์อาจไม่มี) ----------
def _ico_chevron_left(d, cx, cy, s, color, w):
    d.line([(cx + s * 0.3, cy - s * 0.5), (cx - s * 0.35, cy), (cx + s * 0.3, cy + s * 0.5)],
           fill=color, width=int(w), joint="curve")


def _ico_chevron_down(d, cx, cy, s, color, w):
    d.line([(cx - s, cy - s * 0.4), (cx, cy + s * 0.4), (cx + s, cy - s * 0.4)],
           fill=color, width=int(w), joint="curve")


def _ico_settings(d, cx, cy, s, color, w):
    # ไอคอน "สไลเดอร์" = 2 เส้นนอนกับปุ่มกลม
    for i, y in enumerate((cy - s * 0.45, cy + s * 0.45)):
        d.line([(cx - s, y), (cx + s, y)], fill=color, width=int(w))
        kx = cx + (s * 0.4 if i == 0 else -s * 0.4)
        r = s * 0.32
        d.ellipse([kx - r, y - r, kx + r, y + r], fill=color)


def _ico_refresh(d, cx, cy, r, color, w):
    # วงกลมเปิดช่อง + หัวลูกศร (circular arrow)
    box = [cx - r, cy - r, cx + r, cy + r]
    d.arc(box, 60, 360, fill=color, width=int(w))
    # หัวลูกศรที่ปลายบน (มุม ~60°)
    a = math.radians(60)
    ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
    ah = w * 1.9
    d.polygon([(ex - ah, ey - ah * 0.2), (ex + ah * 0.5, ey - ah * 1.2),
               (ex + ah * 1.1, ey + ah * 0.4)], fill=color)


def _classify(remaining: float, cfg: dict) -> str:
    if remaining <= cfg["red_at"]:
        return RED
    if remaining <= cfg["orange_at"]:
        return ORANGE
    return GREEN


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def _vgradient(w, h, top, bot):
    base = Image.new("RGB", (w, h), top)
    px = base.load()
    for y in range(h):
        c = _lerp(top, bot, y / max(1, h - 1))
        for x in range(w):
            px[x, y] = c
    return base.convert("RGBA")


def _text_center(d, cx, y, text, font, fill):
    bb = d.textbbox((0, 0), text, font=font)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], y), text, font=font, fill=fill)


def _rrect(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)


def _arc_dots(layer, cx, cy, radius, a0, a1, thick, color_fn):
    """วาดส่วนโค้งด้วยจุดวงกลมต่อเนื่อง = ปลายมน + ไล่สีได้."""
    d = ImageDraw.Draw(layer)
    steps = max(2, int(abs(a1 - a0) * 2))
    rr = thick / 2
    for i in range(steps + 1):
        t = i / steps
        ang = math.radians(a0 + (a1 - a0) * t)
        x = cx + radius * math.cos(ang)
        y = cy + radius * math.sin(ang)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=color_fn(t))


def render(status: Status, cfg: dict, selected_key: str | None) -> tuple[Image.Image, dict[str, Any]]:
    S = SS
    img = _vgradient(W * S, H * S, BG_TOP, BG_BOT)
    d = ImageDraw.Draw(img)

    quotas = status.quotas
    # เลือก quota ที่จะโชว์บนเกจ (ค่าที่เลือก หรือ ตัวที่แย่สุด)
    sel = next((q for q in quotas if q.key == selected_key), None)
    if sel is None:
        sel = next((q for q in quotas if q.key == status.driver), None) or (quotas[0] if quotas else None)

    # ----- header -----
    _text_center(d, W * S / 2, 28 * S, "Claude Usage", _font(19 * S, "bold"), TXT)
    ws = t("dash.subtitle")
    wf = _font(11 * S)
    wbb = d.textbbox((0, 0), ws, font=wf)
    wtot = (wbb[2] - wbb[0]) + 14 * S
    wx = W * S / 2 - wtot / 2
    d.text((wx, 58 * S), ws, font=wf, fill=SUB)
    _ico_chevron_down(d, wx + (wbb[2] - wbb[0]) + 8 * S, 66 * S, 4 * S, SUB, 2 * S)

    # ปุ่มมุมซ้าย (ปิด/ย้อนกลับ) / มุมขวา (ตั้งค่า)
    _rrect(d, [11 * S, 20 * S, 45 * S, 54 * S], 12 * S, fill=CARD)
    _ico_chevron_left(d, 28 * S, 37 * S, 7 * S, SUB, 3 * S)
    _rrect(d, [(W - 45) * S, 20 * S, (W - 11) * S, 54 * S], 12 * S, fill=CARD)
    _ico_settings(d, (W - 28) * S, 37 * S, 7 * S, SUB, 2.4 * S)

    # ----- เกจวงกลม -----
    cx, cy, R, TH = W / 2, 250, 112, 15
    color = COLORS[_classify(sel.remaining_pct, cfg)] if sel else COLORS[GREEN]

    # แสงเรืองด้านหลังเกจ (radial glow)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([(cx - 90) * S, (cy - 90) * S, (cx + 90) * S, (cy + 90) * S],
               fill=color + (60,))
    glow = glow.filter(ImageFilter.GaussianBlur(40 * S))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)

    # ราง
    _arc_dots(img, cx * S, cy * S, R * S, GAUGE_START, GAUGE_START + GAUGE_SWEEP,
              TH * S, lambda t: TRACK + (255,))

    frac = max(0.0, min(1.0, (sel.remaining_pct if sel else 0) / 100.0))
    end_ang = GAUGE_START + GAUGE_SWEEP * frac
    dark = _lerp(color, BG_TOP, 0.35)

    # เงาเรืองของเส้น progress
    prog_glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    _arc_dots(prog_glow, cx * S, cy * S, R * S, GAUGE_START, end_ang,
              (TH + 8) * S, lambda t: color + (120,))
    img.alpha_composite(prog_glow.filter(ImageFilter.GaussianBlur(8 * S)))
    # เส้น progress ไล่สี
    _arc_dots(img, cx * S, cy * S, R * S, GAUGE_START, end_ang, TH * S,
              lambda t: _lerp(dark, color, t) + (255,))
    d = ImageDraw.Draw(img)

    # หมุดปลายเกจ (จุดขาวเรืองแสง)
    ha = math.radians(end_ang)
    hx, hy = cx + R * math.cos(ha), cy + R * math.sin(ha)
    hglow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(hglow).ellipse(
        [(hx - 16) * S, (hy - 16) * S, (hx + 16) * S, (hy + 16) * S], fill=color + (200,))
    img.alpha_composite(hglow.filter(ImageFilter.GaussianBlur(6 * S)))
    d = ImageDraw.Draw(img)
    d.ellipse([(hx - 11) * S, (hy - 11) * S, (hx + 11) * S, (hy + 11) * S], fill=(255, 255, 255, 255))
    d.ellipse([(hx - 5) * S, (hy - 5) * S, (hx + 5) * S, (hy + 5) * S], fill=color + (255,))

    # ปลายรางซ้าย/ขวา label 0/100
    _text_center(d, (cx - R * 0.86) * S, (cy + R * 0.66) * S, "0%", _font(10 * S), SUB)
    _text_center(d, (cx + R * 0.86) * S, (cy + R * 0.66) * S, "100%", _font(10 * S), SUB)

    # ตัวเลขตรงกลาง
    num = f"{sel.remaining_pct:.0f}" if sel else "--"
    nf = _font_num(64 * S)
    bb = d.textbbox((0, 0), num, font=nf)
    nx = cx * S - (bb[2] - bb[0]) / 2 - bb[0]
    d.text((nx, (cy - 52) * S), num, font=nf, fill=TXT)
    d.text((nx + (bb[2] - bb[0]) + 4 * S, (cy - 44) * S), "%", font=_font(20 * S, "regular"), fill=color)
    _text_center(d, cx * S, (cy + 20) * S, t("dash.tokens_left"), _font(12 * S), SUB)
    if sel:
        _text_center(d, cx * S, (cy + 38) * S, t("common.resets", reset=humanize_reset(sel.resets_at)),
                     _font(10 * S), SUB)

    # ----- โหมด/สถานะ -----
    st = _classify(sel.remaining_pct, cfg) if sel else GREEN
    _text_center(d, W * S / 2, 388 * S, t("dash.status"), _font(10 * S), SUB)
    _text_center(d, W * S / 2, 404 * S, t(f"state.{st}"), _font(20 * S, "bold"), COLORS[st])

    # ----- การ์ด quota (เลือกได้) -----
    show = quotas[:3]
    regions: dict[str, Any] = {"cards": [], "close": (11, 20, 45, 54),
                               "settings": (W - 45, 20, W - 11, 54)}
    if show:
        gap, pad = 12, 20
        cw = (W - pad * 2 - gap * (len(show) - 1)) / len(show)
        ch, cyc = 92, 452
        for i, q in enumerate(show):
            x0 = pad + i * (cw + gap)
            qcolor = COLORS[_classify(q.remaining_pct, cfg)]
            is_sel = q.key == (sel.key if sel else None)
            box = [x0 * S, cyc * S, (x0 + cw) * S, (cyc + ch) * S]
            if is_sel:
                # การ์ดถูกเลือก: เรืองแสง + พื้นสีสถานะ
                gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(gl).rounded_rectangle(box, 18 * S, fill=qcolor + (90,))
                img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(10 * S)))
                d = ImageDraw.Draw(img)
                _rrect(d, box, 18 * S, fill=_lerp(qcolor, BG_BOT, 0.15) + (255,))
                tcol, lcol = CARD_SEL_TXT, _lerp(CARD_SEL_TXT, qcolor, 0.0)
            else:
                _rrect(d, box, 18 * S, fill=CARD + (255,))
                tcol, lcol = TXT, SUB
            # emblem จุดสี
            ex = (x0 + cw / 2)
            d.ellipse([(ex - 9) * S, (cyc + 16) * S, (ex + 9) * S, (cyc + 34) * S],
                      fill=(qcolor if not is_sel else CARD_SEL_TXT) + (255,))
            tag = TAGS.get(q.key) or t(f"tag.{q.key}", default=q.label)
            _text_center(d, ex * S, (cyc + 44) * S, tag, _font(11 * S, "semibold"), tcol)
            _text_center(d, ex * S, (cyc + 62) * S, f"{q.remaining_pct:.0f}%", _font(15 * S, "bold"), tcol)
            regions["cards"].append((q.key, (x0, cyc, x0 + cw, cyc + ch)))

    # ----- ปุ่มกลม (รีเฟรช) -----
    bx, by, br = W / 2, 588, 30
    bglow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(bglow).ellipse([(bx - br) * S, (by - br) * S, (bx + br) * S, (by + br) * S],
                                  fill=ACCENT + (150,))
    img.alpha_composite(bglow.filter(ImageFilter.GaussianBlur(14 * S)))
    d = ImageDraw.Draw(img)
    d.ellipse([(bx - br) * S, (by - br) * S, (bx + br) * S, (by + br) * S], fill=ACCENT + (255,))
    _ico_refresh(d, bx * S, by * S, 13 * S, (255, 255, 255, 255), 3 * S)
    regions["refresh"] = (bx - br, by - br, bx + br, by + br)

    if status.error:
        _text_center(d, W * S / 2, (H - 16) * S, status.error, _font(10 * S), COLORS[ORANGE])

    return img.resize((W, H), Image.LANCZOS), regions
