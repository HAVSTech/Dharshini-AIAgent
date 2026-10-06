from __future__ import annotations
import os
import subprocess
import webbrowser
from pathlib import Path
import psutil
from PIL import ImageGrab

SAFE_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "code": "code",
}

def open_app(app: str) -> str:
    key = app.strip().lower()
    command = SAFE_APPS.get(key)
    if not command:
        raise ValueError(f"Application '{app}' is not allow-listed.")
    subprocess.Popen(command, shell=False)
    return f"Opened {key}."

def open_url(url: str) -> str:
    value = url.strip()
    if not value.startswith(("http://", "https://")):
        raise ValueError("Only http:// and https:// URLs are allowed.")
    webbrowser.open(value)
    return f"Opened {value}."

def open_folder(path: str) -> str:
    folder = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder does not exist: {folder}")
    os.startfile(str(folder))
    return f"Opened {folder}."

def system_info() -> str:
    cpu = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    return f"CPU usage {cpu:.0f} percent. Memory usage {memory.percent:.0f} percent ({memory.used / (1024**3):.1f} GB of {memory.total / (1024**3):.1f} GB)."

def take_screenshot(path: str = "dharshini_screenshot.png") -> str:
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab().save(output)
    return f"Screenshot saved to {output}."
