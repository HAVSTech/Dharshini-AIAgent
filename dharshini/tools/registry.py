from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .printer import (
    default_printer,
    list_printers,
    print_file,
    print_folder,
    printer_capabilities,
    printer_status,
)
from .windows import open_app, open_folder, open_url, system_info, take_screenshot


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., str]
    risk: str = "SAFE"


TOOLS: dict[str, ToolSpec] = {
    "open_app": ToolSpec(
        "open_app", "Open an allow-listed Windows application.", open_app
    ),
    "open_url": ToolSpec(
        "open_url",
        "Open an HTTP or HTTPS URL in the default browser.",
        open_url,
    ),
    "open_folder": ToolSpec(
        "open_folder", "Open an existing local folder.", open_folder
    ),
    "system_info": ToolSpec(
        "system_info", "Report current CPU and memory usage.", system_info
    ),
    "take_screenshot": ToolSpec(
        "take_screenshot",
        "Capture the desktop to a local PNG file.",
        take_screenshot,
        "CONFIRM",
    ),
    "printer_status": ToolSpec(
        "printer_status",
        "Report the Windows printer status and queued job count.",
        printer_status,
    ),
    "printer_capabilities": ToolSpec(
        "printer_capabilities",
        "Report supported paper forms and duplex capability for a Windows printer.",
        printer_capabilities,
    ),
    "list_printers": ToolSpec(
        "list_printers",
        "List installed Windows printers.",
        lambda: ", ".join(list_printers()) or "No printers found.",
    ),
    "default_printer": ToolSpec(
        "default_printer",
        "Report the current Windows default printer.",
        default_printer,
    ),
    "print_file": ToolSpec(
        "print_file",
        "Analyze and print one PDF, Word, or Excel file with automatic paper size, orientation, and duplex selection.",
        print_file,
        "CONFIRM",
    ),
    "print_folder": ToolSpec(
        "print_folder",
        "Analyze and sequentially print supported PDF, Word, and Excel files with automatic paper size, orientation, and duplex selection.",
        print_folder,
        "CONFIRM",
    ),
}


SCHEMAS: dict[str, dict[str, Any]] = {
    "open_app": {
        "app": {"type": "STRING", "description": "Allow-listed application name."}
    },
    "open_url": {
        "url": {"type": "STRING", "description": "HTTP or HTTPS URL."}
    },
    "open_folder": {
        "path": {"type": "STRING", "description": "Existing local folder path."}
    },
    "system_info": {},
    "take_screenshot": {
        "path": {"type": "STRING", "description": "Optional output PNG path."}
    },
    "printer_status": {
        "printer_name": {
            "type": "STRING",
            "description": "Optional Windows printer name.",
        }
    },
    "printer_capabilities": {
        "printer_name": {
            "type": "STRING",
            "description": "Optional Windows printer name.",
        }
    },
    "list_printers": {},
    "default_printer": {},
    "print_file": {
        "path": {
            "type": "STRING",
            "description": "PDF, Word, or Excel file to print.",
        },
        "printer_name": {
            "type": "STRING",
            "description": "Optional Windows printer name. Uses the default printer when omitted.",
        },
    },
    "print_folder": {
        "folder": {
            "type": "STRING",
            "description": "Folder containing files to print.",
        },
        "printer_name": {
            "type": "STRING",
            "description": "Optional Windows printer name. Uses the default printer when omitted.",
        },
        "recursive": {
            "type": "BOOLEAN",
            "description": "Whether to include files in subfolders. Defaults to true.",
        },
    },
}


REQUIRED: dict[str, list[str]] = {
    "open_app": ["app"],
    "open_url": ["url"],
    "open_folder": ["path"],
    "system_info": [],
    "take_screenshot": [],
    "printer_status": [],
    "printer_capabilities": [],
    "list_printers": [],
    "default_printer": [],
    "print_file": ["path"],
    "print_folder": ["folder"],
}


def declarations() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "behavior": "BLOCKING",
            "parameters": {
                "type": "OBJECT",
                "properties": SCHEMAS[spec.name],
                "required": REQUIRED[spec.name],
            },
        }
        for spec in TOOLS.values()
    ]


def as_gemini_tools() -> list[dict[str, Any]]:
    return declarations()
