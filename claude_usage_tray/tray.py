"""ตัวหลัก — วนถาดระบบ, poll usage, เปลี่ยนสีไอคอน, แจ้งเตือน, กะพริบเมื่อแดง."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import threading
from typing import Any

import pystray

from . import autostart, config, icon as icon_mod, ui
from .api import fetch_usage, read_access_token
from .status import RED, Status, evaluate, humanize_reset


class TrayApp:
    def __init__(self) -> None:
        self.cfg: dict[str, Any] = config.load()
        self.status: Status = Status("unknown", None, None, [], error="กำลังโหลด…")
        self._last_color: str | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()   # ปลุกให้ poll ทันที (Refresh)
        self._blink_on = False

        self.icon = pystray.Icon(
            "claude_usage_tray",
            icon=icon_mod.render(self.status, self.cfg),
            title="Claude Usage — กำลังโหลด…",
            menu=self._build_menu(),
        )

    # ---------- เมนู ----------
    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda _: self._headline(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("รีเฟรชเดี๋ยวนี้", self._on_refresh),
            pystray.MenuItem("ดูรายละเอียด…", self._on_details, default=True),
            pystray.MenuItem("เชื่อมต่อบัญชี Claude…", self._on_connect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "เริ่มพร้อม Windows",
                self._on_toggle_autostart,
                checked=lambda _: autostart.is_enabled(),
            ),
            pystray.MenuItem(
                "แจ้งเตือน (balloon)",
                self._on_toggle_notify,
                checked=lambda _: self.cfg.get("notify", True),
            ),
            pystray.MenuItem(
                "Popup เตือนเมื่อต่ำกว่า 50%/20%",
                self._on_toggle_popup,
                checked=lambda _: self.cfg.get("popup_alert", True),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("ออก", self._on_quit),
        )

    def _headline(self) -> str:
        s = self.status
        if s.error:
            return f"⚠ {s.error}"
        if s.remaining_pct is None:
            return "ไม่มีข้อมูล"
        dot = {"green": "🟢", "orange": "🟠", "red": "🔴"}.get(s.color, "⚪")
        return f"{dot} เหลือ {s.remaining_pct:.0f}%"

    def _details_text(self) -> str:
        s = self.status
        if s.error:
            return f"สถานะ: {s.error}"
        lines = ["โควต้าคงเหลือ (Claude Code)\n"]
        for q in s.quotas:
            mark = "  ← กำหนดสี" if q.key == s.driver else ""
            lines.append(
                f"• {q.label}: เหลือ {q.remaining_pct:.0f}%  "
                f"(ใช้ไป {q.used_pct:.0f}%, รีเซ็ต {humanize_reset(q.resets_at)}){mark}"
            )
        lines.append("\nเกณฑ์สี: เขียว >50%  |  ส้ม ≤50%  |  แดง ≤20%")
        lines.append(f"อัปเดตทุก {self.cfg['poll_seconds']} วินาที")
        return "\n".join(lines)

    # ---------- callbacks ----------
    def _on_refresh(self, *_):
        self._wake.set()

    def _on_details(self, *_):
        try:
            ui.show_details(lambda: self.status, self.cfg, self._on_refresh)
        except Exception:  # noqa: BLE001 — fallback เป็น MessageBox ถ้า tkinter มีปัญหา
            threading.Thread(
                target=lambda: ctypes.windll.user32.MessageBoxW(0, self._details_text(), "Claude Usage", 0x40),
                daemon=True,
            ).start()

    def _on_connect(self, *_):
        ui.show_onboarding(self._recheck_token, self._open_login, self._has_cli)

    @staticmethod
    def _has_cli() -> bool:
        return shutil.which("claude") is not None

    def _recheck_token(self) -> bool:
        if read_access_token():
            self._wake.set()  # เจอ token แล้ว -> poll ทันที
            return True
        return False

    @staticmethod
    def _open_login() -> None:
        """เปิด terminal ให้ผู้ใช้ login ผ่าน Claude Code อย่างเป็นทางการ."""
        try:
            if os.name == "nt":
                subprocess.Popen(
                    'start "Claude Login" cmd /k claude',
                    shell=True,
                )
            else:
                subprocess.Popen(["claude"])
        except Exception:  # noqa: BLE001
            pass

    def _on_toggle_autostart(self, *_):
        autostart.toggle()

    def _on_toggle_notify(self, *_):
        self.cfg["notify"] = not self.cfg.get("notify", True)
        config.save(self.cfg)

    def _on_toggle_popup(self, *_):
        self.cfg["popup_alert"] = not self.cfg.get("popup_alert", True)
        config.save(self.cfg)

    def _on_quit(self, *_):
        self._stop.set()
        self._wake.set()
        self.icon.stop()

    # ---------- ลูปทำงาน ----------
    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            self._refresh_once()
            # รอจนถึงรอบถัดไป หรือถูกปลุก (Refresh/Quit)
            self._wake.wait(timeout=self.cfg["poll_seconds"])
            self._wake.clear()

    def _refresh_once(self) -> None:
        new = evaluate(fetch_usage(), self.cfg)
        prev = self.status
        self.status = new
        self._apply_icon()
        self._maybe_notify(prev, new)

    def _apply_icon(self) -> None:
        self.icon.icon = icon_mod.render(self.status, self.cfg)
        self.icon.title = self._tooltip()
        self._last_color = self.status.color

    def _tooltip(self) -> str:
        s = self.status
        if s.error:
            return f"Claude Usage — {s.error}"
        if s.remaining_pct is None:
            return "Claude Usage"
        parts = [f"{q.label}: {q.remaining_pct:.0f}%" for q in s.quotas[:3]]
        return "Claude Usage — เหลือ " + "  |  ".join(parts)

    def _maybe_notify(self, prev: Status, new: Status) -> None:
        order = {"unknown": 0, "green": 0, "orange": 1, "red": 2}
        # แจ้งเฉพาะตอน "แย่ลง" ข้ามระดับ (เขียว->ส้ม, ส้ม->แดง)
        if not (order.get(new.color, 0) > order.get(prev.color, 0) and new.remaining_pct is not None):
            return

        is_red = new.color == RED
        label = "โควต้าใกล้หมด!" if is_red else "โควต้าเริ่มเหลือน้อย"
        reset = humanize_reset(_driver_reset(new))

        # 1) notification balloon
        if self.cfg.get("notify", True):
            try:
                self.icon.notify(f"{label} เหลือ {new.remaining_pct:.0f}%\nรีเซ็ต {reset}", "Claude Usage")
            except Exception:  # noqa: BLE001
                pass

        # 2) popup หน้าต่างเตือนแบบกราฟิก (เด้งค้างหน้าจอ) เมื่อข้ามลงต่ำกว่า 50%/20%
        if self.cfg.get("popup_alert", True):
            try:
                ui.show_alert(new, self.cfg, is_red, reset)
            except Exception:  # noqa: BLE001 — fallback MessageBox
                flags = (0x10 if is_red else 0x30) | 0x40000
                threading.Thread(
                    target=lambda: ctypes.windll.user32.MessageBoxW(
                        0, f"{label} เหลือ {new.remaining_pct:.0f}%", "Claude Usage", flags),
                    daemon=True,
                ).start()

    def _blink_loop(self) -> None:
        while not self._stop.is_set():
            if icon_mod.should_blink(self.status, self.cfg):
                self._blink_on = not self._blink_on
                try:
                    self.icon.icon = icon_mod.render(self.status, self.cfg, dim=self._blink_on)
                except Exception:  # noqa: BLE001
                    pass
                self._stop.wait(0.6)
            else:
                if self._blink_on:  # เพิ่งเลิกกะพริบ -> คืนไอคอนเต็ม
                    self._blink_on = False
                    self._apply_icon()
                self._stop.wait(0.5)

    def run(self) -> None:
        # ครั้งแรกยังไม่ login -> เปิดหน้า onboarding ช่วยเชื่อมต่อบัญชี
        if not read_access_token():
            ui.show_onboarding(self._recheck_token, self._open_login, self._has_cli)
        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._blink_loop, daemon=True).start()
        self.icon.run()


def _driver_reset(s: Status) -> str | None:
    for q in s.quotas:
        if q.key == s.driver:
            return q.resets_at
    return None


def main() -> None:
    TrayApp().run()
