"""ตัวหลัก — วนถาดระบบ, poll usage, เปลี่ยนสีไอคอน, แจ้งเตือน, กะพริบเมื่อแดง."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import threading
from typing import Any

import pystray

from . import autostart, config, i18n, icon as icon_mod, ui
from .api import fetch_usage, read_access_token
from .i18n import t
from .status import RED, UNKNOWN, Status, evaluate, humanize_reset


def _tr(key: str):
    """Menu text that follows the current language (re-read on update_menu)."""
    return lambda _item: t(key)


class TrayApp:
    def __init__(self) -> None:
        self.cfg: dict[str, Any] = config.load()
        self.cfg["language"] = i18n.set_language(self.cfg.get("language"))
        self.status: Status = Status(UNKNOWN, None, None, [], error=t("status.loading"))
        self._usage: dict[str, Any] | None = None  # last API response, re-evaluated on language change
        self._status_lock = threading.Lock()
        self._last_color: str | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()   # ปลุกให้ poll ทันที (Refresh)
        self._blink_on = False

        self.icon = pystray.Icon(
            "claude_usage_tray",
            icon=icon_mod.render(self.status, self.cfg),
            title=f"Claude Usage — {t('status.loading')}",
            menu=self._build_menu(),
        )

    # ---------- เมนู ----------
    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda _: self._headline(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr("menu.refresh"), self._on_refresh),
            pystray.MenuItem(_tr("menu.details"), self._on_details, default=True),
            pystray.MenuItem(_tr("menu.widget"), self._on_widget),
            pystray.MenuItem(_tr("menu.connect"), self._on_connect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                _tr("menu.autostart"),
                self._on_toggle_autostart,
                checked=lambda _: autostart.is_enabled(),
            ),
            pystray.MenuItem(
                _tr("menu.notify"),
                self._on_toggle_notify,
                checked=lambda _: self.cfg.get("notify", True),
            ),
            pystray.MenuItem(
                _tr("menu.popup"),
                self._on_toggle_popup,
                checked=lambda _: self.cfg.get("popup_alert", True),
            ),
            pystray.MenuItem(_tr("menu.language"), pystray.Menu(*[
                pystray.MenuItem(
                    name,
                    self._language_action(code),
                    checked=lambda _, c=code: i18n.get_language() == c,
                    radio=True,
                )
                for code, name in i18n.LANGUAGES.items()
            ])),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr("menu.about"), self._on_about),
            pystray.MenuItem(_tr("menu.quit"), self._on_quit),
        )

    def _headline(self) -> str:
        s = self.status
        if s.error:
            return f"⚠ {s.error}"
        if s.remaining_pct is None:
            return t("status.no_data")
        dot = {"green": "🟢", "orange": "🟠", "red": "🔴"}.get(s.color, "⚪")
        return f"{dot} {t('common.remaining_pct', pct=f'{s.remaining_pct:.0f}')}"

    def _details_text(self) -> str:
        s = self.status
        if s.error:
            return t("details.status", error=s.error)
        lines = [t("details.title") + "\n"]
        for q in s.quotas:
            mark = t("details.driver") if q.key == s.driver else ""
            lines.append(t(
                "details.line", label=q.label, remaining=f"{q.remaining_pct:.0f}",
                used=f"{q.used_pct:.0f}", reset=humanize_reset(q.resets_at),
            ) + mark)
        lines.append("\n" + t("details.legend"))
        lines.append(t("details.poll", n=self.cfg["poll_seconds"]))
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

    def _on_about(self, *_):
        ui.show_about(lambda: self.status, self.cfg)

    def _on_widget(self, *_):
        ui.show_widget(lambda: self.status, self.cfg, self._on_refresh)

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

    def _language_action(self, code: str):
        return lambda *_: self._set_language(code)

    def _set_language(self, code: str) -> None:
        self.cfg["language"] = i18n.set_language(code)
        config.save(self.cfg)
        # re-translate quota labels/errors from the last response, no extra API call
        with self._status_lock:
            if self._usage is not None:
                self.status = evaluate(self._usage, self.cfg)
            else:
                self.status = Status(UNKNOWN, None, None, [], error=t("status.loading"))
        self._apply_icon()
        self.icon.update_menu()

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
        usage = fetch_usage()
        with self._status_lock:
            self._usage = usage
            new = evaluate(usage, self.cfg)
            prev, self.status = self.status, new
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
        return "Claude Usage — " + t("tooltip.remaining", parts="  |  ".join(parts))

    def _maybe_notify(self, prev: Status, new: Status) -> None:
        order = {"unknown": 0, "green": 0, "orange": 1, "red": 2}
        # แจ้งเฉพาะตอน "แย่ลง" ข้ามระดับ (เขียว->ส้ม, ส้ม->แดง)
        if not (order.get(new.color, 0) > order.get(prev.color, 0) and new.remaining_pct is not None):
            return

        is_red = new.color == RED
        label = t("alert.red" if is_red else "alert.orange")
        left = t("common.remaining_pct", pct=f"{new.remaining_pct:.0f}")
        reset = humanize_reset(_driver_reset(new))

        # 1) notification balloon
        if self.cfg.get("notify", True):
            try:
                self.icon.notify(f"{label} {left}\n{t('common.resets', reset=reset)}", "Claude Usage")
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
                        0, f"{label} {left}", "Claude Usage", flags),
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
        elif self.cfg.get("widget_on_start"):
            ui.show_widget(lambda: self.status, self.cfg, self._on_refresh)
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
