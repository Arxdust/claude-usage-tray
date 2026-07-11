"""หน้าต่างกราฟิก (tkinter) — รายละเอียดโควต้า, popup เตือน, และ onboarding.

ทุกหน้าต่างรันในเธรดของตัวเอง (มี Tk root + mainloop แยก) เพื่อไม่ชนกับลูปถาดระบบ
ของ pystray. ใช้เฉพาะ stdlib (tkinter) + Pillow ที่มีอยู่แล้ว จึง bundle ลง .exe ได้
"""
from __future__ import annotations

import base64
import io
import os
import threading
import tkinter as tk
from typing import Any, Callable

from . import config as config_mod, dashboard, icon as icon_mod
from .status import COLORS, GREEN, ORANGE, RED, Status, humanize_reset

# โทนสี (ธีมเข้ม)
BG = "#0b1220"
CARD = "#151f34"
CARD2 = "#1b2740"
TXT = "#e5e9f0"
SUB = "#8b98b4"
TRACK = "#243149"

FONT = "Segoe UI"

_open_windows: dict[str, bool] = {}
_lock = threading.Lock()


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _classify(remaining: float, cfg: dict) -> str:
    if remaining <= cfg["red_at"]:
        return RED
    if remaining <= cfg["orange_at"]:
        return ORANGE
    return GREEN


def _photo(pil_img, size: int) -> tk.PhotoImage:
    """PIL image -> tk.PhotoImage (ผ่าน PNG+base64, ไม่ต้องพึ่ง ImageTk)."""
    im = pil_img.resize((size, size))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def _center(win: tk.Tk, w: int, h: int) -> None:
    win.update_idletasks()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 3
    win.geometry(f"{w}x{h}+{x}+{y}")


def _round_pill(cv: tk.Canvas, x: int, y: int, w: int, h: int, fill: str) -> None:
    r = h // 2
    if w < h:
        w = h
    cv.create_oval(x, y, x + h, y + h, fill=fill, outline=fill)
    cv.create_oval(x + w - h, y, x + w, y + h, fill=fill, outline=fill)
    cv.create_rectangle(x + r, y, x + w - r, y + h, fill=fill, outline=fill)


def _progress(parent, frac: float, color: str, width: int = 300, h: int = 16) -> tk.Canvas:
    cv = tk.Canvas(parent, width=width, height=h, bg=CARD, highlightthickness=0)
    _round_pill(cv, 0, 0, width, h, TRACK)
    fw = max(h, int(width * max(0.0, min(1.0, frac))))
    _round_pill(cv, 0, 0, fw, h, color)
    return cv


def _once(key: str) -> bool:
    """คืน True ถ้ายังไม่มีหน้าต่างชนิดนี้เปิดอยู่ (กันเปิดซ้อน)."""
    with _lock:
        if _open_windows.get(key):
            return False
        _open_windows[key] = True
        return True


def _done(key: str) -> None:
    with _lock:
        _open_windows[key] = False


def _pil_photo(pil_img) -> tk.PhotoImage:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def _in_rect(x, y, rect) -> bool:
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


# ---------- หน้า Dashboard สวย (สไตล์ AC app) ----------
def show_details(get_status: Callable[[], Status], cfg: dict, on_refresh: Callable[[], None]) -> None:
    if not _once("details"):
        return
    threading.Thread(target=_dashboard_window, args=(get_status, cfg, on_refresh), daemon=True).start()


def _dashboard_window(get_status, cfg, on_refresh) -> None:
    try:
        root = tk.Tk()
        root.overrideredirect(True)          # frameless = ลุคพรีเมียม
        root.configure(bg=dashboard.BG_BOT and "#0b0f1c")
        _center(root, dashboard.W, dashboard.H)

        st = {"sel": None, "photo": None, "regions": {}, "press": None}
        lbl = tk.Label(root, bd=0, bg="#0b0f1c")
        lbl.pack()

        def redraw():
            s = get_status()
            pil, regions = dashboard.render(s, cfg, st["sel"])
            st["photo"] = _pil_photo(pil)      # กัน GC
            st["regions"] = regions
            lbl.config(image=st["photo"])

        def hit(x, y):
            r = st["regions"]
            if _in_rect(x, y, r.get("close", (0, 0, 0, 0))):
                root.destroy(); return
            if _in_rect(x, y, r.get("settings", (0, 0, 0, 0))):
                try:
                    os.startfile(config_mod.CONFIG_PATH)  # เปิดไฟล์ตั้งค่า
                except Exception:  # noqa: BLE001
                    pass
                return
            rf = r.get("refresh")
            if rf and _in_rect(x, y, rf):
                on_refresh(); root.after(1500, redraw); return
            for key, rect in r.get("cards", []):
                if _in_rect(x, y, rect):
                    st["sel"] = key; redraw(); return

        def on_press(e):
            st["press"] = (e.x_root, e.y_root, root.winfo_x(), root.winfo_y())

        def on_drag(e):
            if not st["press"]:
                return
            px, py, wx, wy = st["press"]
            root.geometry(f"+{wx + e.x_root - px}+{wy + e.y_root - py}")

        def on_release(e):
            if not st["press"]:
                return
            px, py, _, _ = st["press"]
            if abs(e.x_root - px) < 5 and abs(e.y_root - py) < 5:  # คลิก (ไม่ใช่ลาก)
                hit(e.x, e.y)

        lbl.bind("<Button-1>", on_press)
        lbl.bind("<B1-Motion>", on_drag)
        lbl.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", lambda _e: root.destroy())

        redraw()
        root.attributes("-topmost", True)
        root.after(200, root.focus_force)
        root.after(500, lambda: root.attributes("-topmost", False))
        root.mainloop()
    except Exception:  # noqa: BLE001 — ถ้า dashboard พัง ใช้หน้าตารางเดิม
        _details_window(get_status, cfg, on_refresh)
        return
    finally:
        _done("details")


def _details_window(get_status, cfg, on_refresh) -> None:
    root = tk.Tk()
    root.title("Claude Usage")
    root.configure(bg=BG)
    root.resizable(False, False)
    W, H = 480, 470
    _center(root, W, H)

    try:
        root.iconphoto(True, _photo(icon_mod.render(get_status(), cfg), 64))
    except Exception:  # noqa: BLE001
        pass

    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=18, pady=16)

    def rebuild():
        for wdg in body.winfo_children():
            wdg.destroy()
        s = get_status()

        # header
        head = tk.Frame(body, bg=BG)
        head.pack(fill="x", pady=(0, 12))
        try:
            img = _photo(icon_mod.render(s, cfg), 52)
            lbl = tk.Label(head, image=img, bg=BG)
            lbl.image = img  # กัน GC
            lbl.pack(side="left")
        except Exception:  # noqa: BLE001
            pass
        htxt = tk.Frame(head, bg=BG)
        htxt.pack(side="left", padx=12)
        tk.Label(htxt, text="Claude Usage", bg=BG, fg=TXT,
                 font=(FONT, 16, "bold")).pack(anchor="w")
        if s.error:
            tk.Label(htxt, text=s.error, bg=BG, fg=_hex(COLORS[ORANGE]),
                     font=(FONT, 10)).pack(anchor="w")
        elif s.remaining_pct is not None:
            tk.Label(htxt, text=f"เหลือรวมต่ำสุด {s.remaining_pct:.0f}%", bg=BG,
                     fg=_hex(COLORS[s.color]), font=(FONT, 11, "bold")).pack(anchor="w")

        # การ์ดต่อ quota
        if not s.error:
            for q in s.quotas:
                col = _hex(COLORS[_classify(q.remaining_pct, cfg)])
                card = tk.Frame(body, bg=CARD)
                card.pack(fill="x", pady=5, ipady=10, ipadx=12)
                top = tk.Frame(card, bg=CARD)
                top.pack(fill="x", padx=12, pady=(4, 6))
                tk.Label(top, text=q.label, bg=CARD, fg=TXT,
                         font=(FONT, 11, "bold")).pack(side="left")
                tk.Label(top, text=f"{q.remaining_pct:.0f}%", bg=CARD, fg=col,
                         font=(FONT, 18, "bold")).pack(side="right")
                tk.Label(top, text="เหลือ ", bg=CARD, fg=SUB,
                         font=(FONT, 9)).pack(side="right")
                bar = tk.Frame(card, bg=CARD)
                bar.pack(fill="x", padx=12)
                _progress(bar, q.used_pct / 100.0, col, width=W - 84).pack(side="left")
                tk.Label(card, text=f"ใช้ไป {q.used_pct:.0f}%  ·  รีเซ็ต {humanize_reset(q.resets_at)}",
                         bg=CARD, fg=SUB, font=(FONT, 9)).pack(anchor="w", padx=12, pady=(6, 0))

        # legend
        leg = tk.Frame(body, bg=BG)
        leg.pack(fill="x", pady=(10, 4))
        for c, t in ((GREEN, ">50%"), (ORANGE, "≤50%"), (RED, "≤20%")):
            chip = tk.Frame(leg, bg=BG)
            chip.pack(side="left", padx=(0, 14))
            tk.Canvas(chip, width=12, height=12, bg=BG, highlightthickness=0).pack(side="left")
            dot = chip.winfo_children()[-1]
            dot.create_oval(1, 1, 11, 11, fill=_hex(COLORS[c]), outline="")
            tk.Label(chip, text=t, bg=BG, fg=SUB, font=(FONT, 9)).pack(side="left", padx=4)

        # ปุ่ม
        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(8, 0))

        def do_refresh():
            on_refresh()
            root.after(1500, rebuild)

        tk.Button(btns, text="⟳ รีเฟรช", command=do_refresh, bg=CARD2, fg=TXT,
                  activebackground=TRACK, activeforeground=TXT, relief="flat",
                  font=(FONT, 10, "bold"), padx=16, pady=6, cursor="hand2").pack(side="left")
        tk.Button(btns, text="ปิด", command=root.destroy, bg=CARD, fg=SUB,
                  activebackground=TRACK, activeforeground=TXT, relief="flat",
                  font=(FONT, 10), padx=16, pady=6, cursor="hand2").pack(side="right")

    rebuild()
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    try:
        root.mainloop()
    finally:
        _done("details")


# ---------- popup เตือนแบบกราฟิก ----------
def show_alert(status: Status, cfg: dict, is_red: bool, reset_text: str) -> None:
    threading.Thread(target=_alert_window, args=(status, cfg, is_red, reset_text), daemon=True).start()


def _alert_window(status: Status, cfg: dict, is_red: bool, reset_text: str) -> None:
    color = COLORS[RED if is_red else ORANGE]
    root = tk.Tk()
    root.title("Claude Usage — เตือนโควต้า")
    root.configure(bg=BG)
    root.resizable(False, False)
    W, H = 420, 300
    _center(root, W, H)

    # แถบสีหัว
    band = tk.Frame(root, bg=_hex(color), height=8)
    band.pack(fill="x")

    wrap = tk.Frame(root, bg=BG)
    wrap.pack(fill="both", expand=True, padx=22, pady=18)

    try:
        img = _photo(icon_mod.render(status, cfg), 72)
        l = tk.Label(wrap, image=img, bg=BG)
        l.image = img
        l.pack(pady=(4, 6))
    except Exception:  # noqa: BLE001
        pass

    title = "⛔ โควต้าใกล้หมด!" if is_red else "⚠ โควต้าเริ่มเหลือน้อย"
    tk.Label(wrap, text=title, bg=BG, fg=_hex(color), font=(FONT, 15, "bold")).pack()

    rem = status.remaining_pct if status.remaining_pct is not None else 0
    tk.Label(wrap, text=f"เหลือ {rem:.0f}%", bg=BG, fg=TXT, font=(FONT, 26, "bold")).pack(pady=(2, 2))
    tk.Label(wrap, text=f"จะรีเซ็ต {reset_text}", bg=BG, fg=SUB, font=(FONT, 10)).pack()
    msg = ("ใช้ต่อได้อีกไม่มาก โปรดวางแผนการใช้งาน" if is_red
           else "ใช้ไปเกินครึ่งแล้ว เริ่มระวังการใช้งาน")
    tk.Label(wrap, text=msg, bg=BG, fg=SUB, font=(FONT, 10)).pack(pady=(6, 10))

    tk.Button(wrap, text="รับทราบ", command=root.destroy, bg=_hex(color), fg="#0b1220",
              activebackground=_hex(color), relief="flat", font=(FONT, 11, "bold"),
              padx=28, pady=7, cursor="hand2").pack()

    root.attributes("-topmost", True)
    root.bell()
    try:
        root.mainloop()
    except Exception:  # noqa: BLE001
        pass


# ---------- onboarding / เชื่อมต่อบัญชี ----------
def show_onboarding(recheck: Callable[[], bool], open_login: Callable[[], None],
                    has_cli: Callable[[], bool]) -> None:
    if not _once("onboard"):
        return
    threading.Thread(target=_onboard_window, args=(recheck, open_login, has_cli), daemon=True).start()


def _onboard_window(recheck, open_login, has_cli) -> None:
    root = tk.Tk()
    root.title("Claude Usage — เชื่อมต่อบัญชี")
    root.configure(bg=BG)
    root.resizable(False, False)
    W, H = 480, 420
    _center(root, W, H)

    tk.Frame(root, bg=_hex(COLORS[GREEN]), height=8).pack(fill="x")
    wrap = tk.Frame(root, bg=BG)
    wrap.pack(fill="both", expand=True, padx=26, pady=20)

    tk.Label(wrap, text="เชื่อมต่อบัญชี Claude ของคุณ", bg=BG, fg=TXT,
             font=(FONT, 16, "bold")).pack(anchor="w")
    tk.Label(wrap, text="แอปนี้อ่านสถานะโควต้าจากบัญชีที่ล็อกอินไว้ใน Claude Code\n"
                        "(อ่านอย่างเดียว ไม่เก็บ ไม่ส่ง token ไปที่ไหน)",
             bg=BG, fg=SUB, font=(FONT, 10), justify="left").pack(anchor="w", pady=(4, 14))

    steps = tk.Frame(wrap, bg=CARD)
    steps.pack(fill="x", ipady=10)
    txt = ("ขั้นตอน:\n"
           "1) ติดตั้ง Claude Code  (npm i -g @anthropic-ai/claude-code)\n"
           "2) เปิด terminal พิมพ์  claude  แล้วสั่ง  /login\n"
           "3) ล็อกอินด้วยบัญชี Claude (Pro/Max/Team) ในเบราว์เซอร์\n"
           "4) กลับมากดปุ่ม \"ตรวจสอบอีกครั้ง\" ด้านล่าง")
    tk.Label(steps, text=txt, bg=CARD, fg=TXT, font=(FONT, 10),
             justify="left").pack(anchor="w", padx=14, pady=6)

    status_lbl = tk.Label(wrap, text="", bg=BG, fg=SUB, font=(FONT, 10, "bold"))
    status_lbl.pack(anchor="w", pady=(12, 8))

    def do_recheck():
        if recheck():
            status_lbl.config(text="✅ เชื่อมต่อสำเร็จ! ปิดหน้าต่างนี้ได้เลย",
                              fg=_hex(COLORS[GREEN]))
            root.after(1500, root.destroy)
        else:
            status_lbl.config(text="❌ ยังไม่พบการล็อกอิน — ทำตามขั้นตอนแล้วลองใหม่",
                              fg=_hex(COLORS[RED]))

    def do_login():
        open_login()
        status_lbl.config(text="กำลังเปิด terminal สำหรับ login… เสร็จแล้วกด \"ตรวจสอบอีกครั้ง\"",
                          fg=SUB)

    btns = tk.Frame(wrap, bg=BG)
    btns.pack(fill="x", pady=(4, 0))
    if has_cli():
        tk.Button(btns, text="เปิด Login ผ่าน Claude Code", command=do_login,
                  bg=_hex(COLORS[GREEN]), fg="#0b1220", relief="flat",
                  font=(FONT, 10, "bold"), padx=16, pady=7, cursor="hand2").pack(side="left")
    else:
        tk.Label(btns, text="⚠ ไม่พบคำสั่ง claude — ติดตั้ง Claude Code ก่อน",
                 bg=BG, fg=_hex(COLORS[ORANGE]), font=(FONT, 9)).pack(side="left")
    tk.Button(btns, text="ตรวจสอบอีกครั้ง", command=do_recheck, bg=CARD2, fg=TXT,
              relief="flat", font=(FONT, 10, "bold"), padx=16, pady=7,
              cursor="hand2").pack(side="right")

    root.attributes("-topmost", True)
    root.after(400, lambda: root.attributes("-topmost", False))
    try:
        root.mainloop()
    finally:
        _done("onboard")
