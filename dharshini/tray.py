from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

from dharshini.startup import install_startup, uninstall_startup, startup_enabled


class DharshiniTray:
    def __init__(self):
        self.voice_process: subprocess.Popen | None = None
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
        if self.voice_process and self.voice_process.poll() is None:
            return

        self.voice_process = subprocess.Popen(
            [sys.executable, "-m", "dharshini.main", "--voice"],
            cwd=str(Path.cwd()),
        )

    def _stop_voice(self, icon, item):
        if self.voice_process and self.voice_process.poll() is None:
            self.voice_process.terminate()
            try:
                self.voice_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.voice_process.kill()
        self.voice_process = None

    def _toggle_startup(self, icon, item):
        if startup_enabled():
            uninstall_startup()
        else:
            install_startup()

    def _exit(self, icon, item):
        self._stop_voice(icon, item)
        icon.stop()

    def run(self):
        self.icon.run()


def run_tray():
    DharshiniTray().run()
