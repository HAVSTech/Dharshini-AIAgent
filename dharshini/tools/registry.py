from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .windows import open_app, open_folder, open_url, system_info, take_screenshot

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., str]
    risk: str = "SAFE"

TOOLS = {
    "open_app": ToolSpec("open_app", "Open an allow-listed Windows application.", open_app, "SAFE"),
    "open_url": ToolSpec("open_url", "Open an HTTP or HTTPS URL in the default browser.", open_url, "SAFE"),
    "open_folder": ToolSpec("open_folder", "Open an existing Windows folder.", open_folder, "SAFE"),
    "system_info": ToolSpec("system_info", "Get current CPU and memory usage.", system_info, "SAFE"),
    "take_screenshot": ToolSpec("take_screenshot", "Take a screenshot of the desktop.", take_screenshot, "CONFIRM"),
}

def as_gemini_tools() -> list[dict[str, Any]]:
    declarations = []
    for spec in TOOLS.values():
        declarations.append({
            "name": spec.name,
            "description": spec.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "app": {"type": "STRING", "description": "Application name for open_app."},
                    "url": {"type": "STRING", "description": "HTTP/HTTPS URL for open_url."},
                    "path": {"type": "STRING", "description": "Local path for open_folder or screenshot."},
                },
            },
        })
    return declarations
