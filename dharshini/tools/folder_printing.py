from __future__ import annotations

import os
import re
from pathlib import Path

from .printer import SUPPORTED_EXTENSIONS, default_printer, print_file

TYPE_ALIASES = {
    "pdf": {".pdf"},
    "word": {".doc", ".docx"},
    "doc": {".doc"},
    "docx": {".docx"},
    "excel": {".xls", ".xlsx"},
    "spreadsheet": {".xls", ".xlsx"},
    "spreadsheets": {".xls", ".xlsx"},
    "xls": {".xls"},
    "xlsx": {".xlsx"},
    "all": set(SUPPORTED_EXTENSIONS),
}


def extensions_for_types(file_types: str | list[str] | None) -> set[str]:
    """Translate spoken file-type descriptions into supported extensions.

    Empty input means all supported types. Examples: 'PDFs and Word files',
    'excel', '.pdf, .docx', or 'all'.
    """
    if file_types is None or (isinstance(file_types, str) and not file_types.strip()):
        return set(SUPPORTED_EXTENSIONS)

    raw = " ".join(file_types) if isinstance(file_types, list) else str(file_types)
    normalized = raw.lower().replace(".", " ")
    tokens = re.findall(
        r"\b(pdf|pdfs|word|docx|doc|excel|spreadsheet|spreadsheets|xlsx|xls|all)\b",
        normalized,
    )
    if not tokens:
        raise ValueError(
            "Unrecognized file type. Say PDF, Word, Excel, or all supported files."
        )

    if "all" in tokens:
        return set(SUPPORTED_EXTENSIONS)

    extensions: set[str] = set()
    for token in tokens:
        if token == "pdfs":
            token = "pdf"
        extensions.update(TYPE_ALIASES[token])

    return extensions


def print_folder(
    folder: str,
    printer_name: str | None = None,
    recursive: bool = True,
    file_types: str | list[str] | None = None,
) -> str:
    """Print matching supported files from a folder, including nested folders."""
    root = Path(os.path.expandvars(os.path.expanduser(folder))).resolve()
    if not root.is_dir():
        raise ValueError(f"Folder does not exist: {root}")

    extensions = extensions_for_types(file_types)
    printer = printer_name or default_printer()
    candidates = root.rglob("*") if recursive else root.iterdir()
    files = sorted(
        (path for path in candidates if path.is_file() and path.suffix.lower() in extensions),
        key=lambda path: str(path).lower(),
    )

    type_label = ", ".join(sorted(extensions))
    if not files:
        return f"No matching files ({type_label}) found in {root}."

    successes: list[str] = []
    failures: list[str] = []
    for index, path in enumerate(files, start=1):
        try:
            print(
                f"[Dharshini printer] {index}/{len(files)} printing {path}",
                flush=True,
            )
            successes.append(print_file(str(path), printer))
        except Exception as exc:
            failures.append(f"{path}: {exc}")
            print(f"[Dharshini printer] FAILED {path}: {exc}", flush=True)

    summary = (
        f"Finished folder print: {len(successes)}/{len(files)} matching file(s) "
        f"printed from {root} (types: {type_label}; "
        f"{'including subfolders' if recursive else 'top-level only'})."
    )
    if failures:
        summary += " Failures: " + " | ".join(failures)
    return summary
