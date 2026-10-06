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

TOOLS: dict[str, ToolSpec] = {
    "open_app": ToolSpec("open_app", "Open an allow-listed Windows application.", open_app),
    "open_url": ToolSpec("open_url", "Open an HTTP or HTTPS URL in the default browser.", open_url),
    "open_folder": ToolSpec("open_folder", "Open an existing local folder.", open_folder),
    "system_info": ToolSpec("system_info", "Report current CPU and memory usage.", system_info),
    "take_screenshot": ToolSpec("take_screenshot", "Capture the desktop to a local PNG file.", take_screenshot, "CONFIRM"),
}
SCHEMAS: dict[str, dict[str, Any]] = {
    "open_app": {"app": {"type": "STRING", "description": "Allow-listed application name."}},
    "open_url": {"url": {"type": "STRING", "description": "HTTP or HTTPS URL."}},
    "open_folder": {"path": {"type": "STRING", "description": "Existing local folder path."}},
    "system_info": {},
    "take_screenshot": {"path": {"type": "STRING", "description": "Optional output PNG path."}},
}
def declarations() -> list[dict[str, Any]]:
    return [{"name": s.name, "description": s.description,
             "parameters": {"type": "OBJECT", "properties": SCHEMAS[s.name],
                           "required": list(SCHEMAS[s.name])}}
            for s in TOOLS.values()]
def as_gemini_tools() -> list[dict[str, Any]]:
    return declarations()
