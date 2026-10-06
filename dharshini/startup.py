from __future__ import annotations

import os
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DharshiniAI"


def _command() -> str:
    python = Path(sys.executable).resolve()
    return f'"{python}" -m dharshini.main --tray'


def install_startup() -> str:
    if os.name != "nt":
        raise RuntimeError("Windows startup integration requires Windows.")

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())

    return "Dharshini will start with Windows."


def uninstall_startup() -> str:
    if os.name != "nt":
        raise RuntimeError("Windows startup integration requires Windows.")

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass

    return "Dharshini startup has been disabled."


def startup_enabled() -> bool:
    if os.name != "nt":
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
