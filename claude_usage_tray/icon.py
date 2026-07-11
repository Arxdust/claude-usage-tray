"""วาดไอคอนถาดระบบ — ดาว/ประกาย Claude ระบายสีตามสถานะ + วงแหวนวัดระดับ.

สีของดาว = สัญญาณหลัก (เขียว/ส้ม/แดง). วงแหวนรอบนอก = สัดส่วนที่ "ใช้ไปแล้ว".
ตัวเลข % ที่เหลือ (option) วางมุมล่างขวา.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .status import COLORS, RED, Status

_SIZE = 256          # วาดใหญ่แล้วให้ pystray ย่อ = คมกว่า
_N_RAYS = 11         # จำนวนแฉกของประกาย Claude
_BG = (0, 0, 0, 0)   # โปร่งใส


def _petal(color: tuple[int, int, int], inner: float, outer: float, width: float) -> Image.Image:
    """สร้างภาพแฉกเดี่ยว (แนวตั้ง ชี้ขึ้น) แบบปลายมน เพื่อเอาไปหมุนรอบจุดศูนย์กลาง."""
    layer = Image.new("RGBA", (_SIZE, _SIZE), _BG)
    d = ImageDraw.Draw(layer)
    cx = _SIZE / 2
    top = cx - outer
    bottom = cx - inner
    half = width / 2
    # แคปซูลแนวตั้ง = สี่เหลี่ยม + วงกลมสองปลาย (ปลายมน)
    d.rounded_rectangle(
        [cx - half, top, cx + half, bottom],
        radius=half,
        fill=color + (255,),
    )
    return layer


def _starburst(color: tuple[int, int, int], alpha: int = 255) -> Image.Image:
    """ประกอบแฉกทั้งหมดเป็นดาวประกายแบบโลโก้ Claude (เต็มเฟรม)."""
    burst = Image.new("RGBA", (_SIZE, _SIZE), _BG)
    # แฉกยาวเกือบชนขอบ + กว้างขึ้น = กราฟิกใหญ่เต็มไอคอน
    petal = _petal(color, inner=_SIZE * 0.05, outer=_SIZE * 0.485, width=_SIZE * 0.135)
    for i in range(_N_RAYS):
        angle = i * (360 / _N_RAYS)
        burst.alpha_composite(petal.rotate(angle, resample=Image.BICUBIC, center=(_SIZE / 2, _SIZE / 2)))
    if alpha < 255:
        band = burst.split()[3].point(lambda a: int(a * alpha / 255))
        burst.putalpha(band)
    return burst


def _ring(draw: ImageDraw.ImageDraw, used_pct: float, color: tuple[int, int, int]) -> None:
    """วงแหวนวัดระดับรอบนอก: เต็มวง = ใช้ไป 100%."""
    pad = _SIZE * 0.03
    box = [pad, pad, _SIZE - pad, _SIZE - pad]
    w = int(_SIZE * 0.07)
    # รางจาง
    draw.arc(box, 0, 360, fill=color + (55,), width=w)
    # ส่วนที่ใช้ไป เริ่มจากบนสุด (-90°) ตามเข็ม
    sweep = max(0.0, min(100.0, used_pct)) / 100 * 360
    if sweep > 0:
        draw.arc(box, -90, -90 + sweep, fill=color + (255,), width=w)


def _best_font(px: int):
    for name in ("segoeuib.ttf", "arialbd.ttf", "segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_center_number(img: Image.Image, remaining: float, color: tuple[int, int, int]) -> None:
    """ตัวเลข % ที่เหลือ 'ใหญ่เต็มกลางไอคอน' บนแผ่นกลมทึบ อ่านง่ายแม้ไอคอนเล็ก."""
    d = ImageDraw.Draw(img)
    txt = f"{int(round(remaining))}"

    # แผ่นรองกลมทึบตรงกลาง ให้ตัวเลขเด่นเหนือประกาย
    r = int(_SIZE * 0.375)
    cx = cy = _SIZE // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 23, 42, 245))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (255,), width=int(_SIZE * 0.03))

    # เลือกขนาดฟอนต์ใหญ่สุดที่ยังพอในแผ่น (1-3 หลัก)
    max_w = int(r * 1.55)
    px = int(_SIZE * (0.62 if len(txt) == 1 else 0.50 if len(txt) == 2 else 0.38))
    while px > 8:
        font = _best_font(px)
        bb = d.textbbox((0, 0), txt, font=font)
        if bb[2] - bb[0] <= max_w:
            break
        px -= 6
    bb = d.textbbox((0, 0), txt, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), txt, font=font, fill=color + (255,))


def render(status: Status, cfg: dict, dim: bool = False) -> Image.Image:
    """สร้างภาพไอคอนจากสถานะ. dim=True ใช้ตอนกะพริบ (เฟรมจาง)."""
    color = COLORS[status.color]
    img = Image.new("RGBA", (_SIZE, _SIZE), _BG)
    d = ImageDraw.Draw(img)

    used = 100.0 - (status.remaining_pct if status.remaining_pct is not None else 100.0)
    show_num = cfg.get("show_percent_text") and status.remaining_pct is not None
    _ring(d, used, color)
    # ถ้าโชว์ตัวเลข ให้ประกายจางลงเป็นฉากหลัง เพื่อให้เลขเด่น
    img.alpha_composite(_starburst(color, alpha=150 if show_num else 255))

    if show_num:
        _draw_center_number(img, status.remaining_pct, color)

    if dim:
        # เฟรมจางสำหรับกะพริบ (ลด alpha ทั้งภาพ)
        alpha = img.split()[3].point(lambda a: int(a * 0.35))
        img.putalpha(alpha)

    return img


def should_blink(status: Status, cfg: dict) -> bool:
    return bool(cfg.get("blink_when_red")) and status.color == RED
