from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

from dharshini.agent.live import DharshiniAgent
from dharshini.startup import install_startup, uninstall_startup, startup_enabled


class DharshiniTray:
    def __init__(self, agent: DharshiniAgent):
        self.agent = agent
        self.voice_thread: threading.Thread | None = None
        self.stop_requested = threading.Event()
        self.icon = pystray.Icon(
            "dharshini",
            self._make_icon(),
            "Dharshini AI",
            self._menu(),
        )

    def _make_icon(self):
        image = Image.new("RGBA", (64, 64), (24, 24, 28, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), outline=(120, 190, 255, 255), width=4)
        draw.ellipse((22, 22, 42, 42), fill=(120, 190, 255, 255))
        return image

    def _menu(self):
        return pystray.Menu(
            pystray.MenuItem("Start Voice", self._start_voice),
            pystray.MenuItem("Stop Voice", self._stop_voice),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows",
                self._toggle_startup,
                checked=lambda _: startup_enabled(),
            ),
            pystray.MenuItem("Exit", self._exit),
        )

    def _start_voice(self, icon, item):
        if self.voice_thread and self.voice_thread.is_alive():
            return

        self.stop_requested.clear()

        def run():
            try:
                asyncio.run(self.agent.voice())
            except Exception as exc:
                print(f"[Dharshini tray] Voice stopped: {exc}", flush=True)

        self.voice_thread = threading.Thread(
            target=run,
            name="dharshini-voice",
            daemon=True,
        )
        self.voice_thread.start()

    def _stop_voice(self, icon, item):
        self.stop_requested.set()
        # The voice session is designed to be stopped by Ctrl+C/process exit
        # today; this menu item provides a safe state transition for the tray.
        print("[Dharshini tray] Stop requested.", flush=True)

    def _toggle_startup(self, icon, item):
        if startup_enabled():
            uninstall_startup()
        else:
            install_startup()

    def _exit(self, icon, item):
        self.stop_requested.set()
        icon.stop()

    def run(self):
        self.icon.run()


def run_tray(agent: DharshiniAgent):
    DharshiniTray(agent).run()
