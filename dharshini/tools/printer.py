from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}

try:
    import win32con
    import win32print
    import pywintypes
except ImportError:  # pragma: no cover - Windows-only dependency
    win32con = None
    win32print = None
    pywintypes = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


@dataclass(frozen=True)
class PrintAnalysis:
    path: str
    extension: str
    pages: int
    orientation: str
    duplex: str
    paper: str = "auto"

    @property
    def summary(self) -> str:
        mode = "simplex" if self.duplex == "simplex" else f"duplex {self.duplex}"
        return (
            f"{Path(self.path).name}: {self.pages} page(s), "
            f"{self.orientation}, {mode}, paper={self.paper}"
        )


def _windows_only() -> None:
    if os.name != "nt":
        raise RuntimeError("Dharshini printer controls require Windows.")


def _require_win32() -> None:
    _windows_only()
    if win32print is None:
        raise RuntimeError(
            "pywin32 is required for printer control. Run: pip install pywin32"
        )


def default_printer() -> str:
    _require_win32()
    return win32print.GetDefaultPrinter()


def list_printers() -> list[str]:
    _require_win32()
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [item[2] for item in win32print.EnumPrinters(flags, None, 2)]


def _pdf_analysis(path: Path) -> tuple[int, str]:
    if PdfReader is None:
        raise RuntimeError("pypdf is required for PDF analysis.")

    reader = PdfReader(str(path))
    pages = len(reader.pages)
    if pages < 1:
        raise ValueError(f"PDF has no printable pages: {path}")

    portrait = 0
    landscape = 0
    for page in reader.pages:
        box = page.mediabox
        width = float(box.width)
        height = float(box.height)
        if width > height:
            landscape += 1
        else:
            portrait += 1

    orientation = "landscape" if landscape > portrait else "portrait"
    return pages, orientation


def _office_to_pdf(path: Path) -> Path:
    """Export Word/Excel to a temporary PDF so page count/orientation are known."""
    _windows_only()
    suffix = path.suffix.lower()
    temp_dir = Path(tempfile.mkdtemp(prefix="dharshini-print-"))
    pdf_path = temp_dir / f"{path.stem}.pdf"

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(
            "pywin32 is required for Word/Excel printing. Run: pip install pywin32"
        ) from exc

    if suffix in {".docx", ".doc"}:
        word = win32com.client.DispatchEx("Word.Application")
        document = None
        try:
            word.Visible = False
            document = word.Documents.Open(str(path), ReadOnly=True, AddToRecentFiles=False)
            # 17 = wdExportFormatPDF
            document.ExportAsFixedFormat(
                OutputFileName=str(pdf_path),
                ExportFormat=17,
                OpenAfterExport=False,
                OptimizeFor=0,
                Range=0,
                Item=0,
                IncludeDocProps=True,
                KeepIRM=True,
                CreateBookmarks=0,
                DocStructureTags=True,
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        finally:
            if document is not None:
                document.Close(False)
            word.Quit()

    elif suffix in {".xlsx", ".xls"}:
        excel = win32com.client.DispatchEx("Excel.Application")
        workbook = None
        try:
            excel.Visible = False
            excel.DisplayAlerts = False
            workbook = excel.Workbooks.Open(
                str(path), ReadOnly=True, UpdateLinks=False, AddToMru=False
            )
            # 0 = xlTypePDF
            workbook.ExportAsFixedFormat(0, str(pdf_path))
        finally:
            if workbook is not None:
                workbook.Close(False)
            excel.Quit()
    else:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValueError(f"Unsupported office file: {path.suffix}")

    if not pdf_path.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Could not create analysis PDF for {path.name}.")

    return pdf_path


def analyze_file(path: str) -> PrintAnalysis:
    _require_win32()
    file_path = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    if not file_path.is_file():
        raise ValueError(f"File does not exist: {file_path}")

    extension = file_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported print file type: {extension}")

    temp_pdf: Path | None = None
    try:
        if extension == ".pdf":
            pages, orientation = _pdf_analysis(file_path)
        else:
            temp_pdf = _office_to_pdf(file_path)
            pages, orientation = _pdf_analysis(temp_pdf)

        if pages == 1:
            duplex = "simplex"
        elif orientation == "portrait":
            duplex = "long-edge"
        else:
            duplex = "short-edge"

        return PrintAnalysis(
            path=str(file_path),
            extension=extension,
            pages=pages,
            orientation=orientation,
            duplex=duplex,
        )
    finally:
        if temp_pdf:
            shutil.rmtree(temp_pdf.parent, ignore_errors=True)


def _get_modified_devmode(printer_name: str, orientation: str, duplex: str):
    _require_win32()
    handle = win32print.OpenPrinter(printer_name)
    try:
        size = win32print.DocumentProperties(
            0, handle, printer_name, None, None, 0
        )
        if size <= 0:
            raise RuntimeError("Could not obtain printer DEVMODE.")

        driver_extra = size - pywintypes.DEVMODEType().Size
        dm = pywintypes.DEVMODEType(driver_extra)

        win32print.DocumentProperties(
            0,
            handle,
            printer_name,
            dm,
            None,
            win32con.DM_OUT_BUFFER,
        )

        if not (dm.Fields & win32con.DM_ORIENTATION):
            raise RuntimeError("Printer driver does not expose orientation settings.")

        dm.Fields |= win32con.DM_ORIENTATION
        dm.Orientation = (
            win32con.DMORIENT_LANDSCAPE
            if orientation == "landscape"
            else win32con.DMORIENT_PORTRAIT
        )

        if duplex != "simplex":
            if not (dm.Fields & win32con.DM_DUPLEX):
                raise RuntimeError("Printer driver does not expose duplex settings.")
            dm.Fields |= win32con.DM_DUPLEX
            dm.Duplex = (
                win32con.DMDUP_HORIZONTAL
                if duplex == "short-edge"
                else win32con.DMDUP_VERTICAL
            )
        elif dm.Fields & win32con.DM_DUPLEX:
            dm.Fields |= win32con.DM_DUPLEX
            dm.Duplex = win32con.DMDUP_SIMPLEX

        result = win32print.DocumentProperties(
            0,
            handle,
            printer_name,
            dm,
            dm,
            win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
        )
        if result != win32con.IDOK:
            raise RuntimeError("Printer driver rejected the requested settings.")

        return dm
    finally:
        win32print.ClosePrinter(handle)


def _set_user_devmode(printer_name: str, dm) -> None:
    _require_win32()
    handle = win32print.OpenPrinter(
        printer_name,
        {
            "DesiredAccess": win32print.PRINTER_ACCESS_USE,
        },
    )
    try:
        win32print.SetPrinter(
            handle,
            9,
            {"pDevMode": dm},
            0,
        )
    finally:
        win32print.ClosePrinter(handle)


def _wait_for_spool(printer_name: str, before_ids: set[int], timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        handle = win32print.OpenPrinter(printer_name)
        try:
            jobs = win32print.EnumJobs(handle, 0, -1, 1)
        finally:
            win32print.ClosePrinter(handle)

        new_jobs = [job for job in jobs if job["JobId"] not in before_ids]
        if not new_jobs:
            return

        time.sleep(1)

    raise TimeoutError(
        f"Timed out waiting for the printer queue after {timeout} seconds."
    )


def _snapshot_job_ids(printer_name: str) -> set[int]:
    handle = win32print.OpenPrinter(printer_name)
    try:
        return {
            job["JobId"]
            for job in win32print.EnumJobs(handle, 0, -1, 1)
        }
    finally:
        win32print.ClosePrinter(handle)


def _sumatra_path() -> Path | None:
    configured = os.getenv("DHARSHINI_SUMATRA_PATH", "").strip()
    candidates = [
        Path(configured) if configured else None,
        Path(r"C:\Program Files\SumatraPDF\SumatraPDF.exe"),
        Path(r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe"),
        Path(r"C:\Tools\SumatraPDF\SumatraPDF.exe"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    return None


def _print_pdf(analysis: PrintAnalysis, printer_name: str) -> None:
    sumatra = _sumatra_path()
    if sumatra is None:
        raise RuntimeError(
            "SumatraPDF was not found. Install it manually and set "
            "DHARSHINI_SUMATRA_PATH to SumatraPDF.exe."
        )

    settings = "simplex"
    if analysis.duplex == "long-edge":
        settings = "duplexlong"
    elif analysis.duplex == "short-edge":
        settings = "duplexshort"

    before = _snapshot_job_ids(printer_name)
    args = [
        str(sumatra),
        "-silent",
        "-print-to",
        printer_name,
        "-print-settings",
        settings,
        analysis.path,
    ]
    subprocess.run(args, check=True, timeout=120)
    _wait_for_spool(printer_name, before)


def _print_office(analysis: PrintAnalysis, printer_name: str) -> None:
    import win32com.client  # type: ignore

    path = Path(analysis.path)
    before = _snapshot_job_ids(printer_name)

    if analysis.extension in {".docx", ".doc"}:
        app = win32com.client.DispatchEx("Word.Application")
        document = None
        try:
            app.Visible = False
            document = app.Documents.Open(
                str(path), ReadOnly=True, AddToRecentFiles=False
            )
            document.PrintOut(
                Background=False,
                Copies=1,
                ActivePrinter=printer_name,
            )
        finally:
            if document is not None:
                document.Close(False)
            app.Quit()

    elif analysis.extension in {".xlsx", ".xls"}:
        app = win32com.client.DispatchEx("Excel.Application")
        workbook = None
        try:
            app.Visible = False
            app.DisplayAlerts = False
            workbook = app.Workbooks.Open(
                str(path), ReadOnly=True, UpdateLinks=False, AddToMru=False
            )
            workbook.PrintOut(Copies=1, ActivePrinter=printer_name)
        finally:
            if workbook is not None:
                workbook.Close(False)
            app.Quit()
    else:
        raise ValueError(f"Unsupported Office file: {analysis.extension}")

    _wait_for_spool(printer_name, before)


def print_file(path: str, printer_name: str | None = None) -> str:
    analysis = analyze_file(path)
    printer = printer_name or default_printer()

    if printer not in list_printers():
        raise ValueError(f"Printer not found: {printer}")

    dm = _get_modified_devmode(
        printer,
        analysis.orientation,
        analysis.duplex,
    )
    _set_user_devmode(printer, dm)

    if analysis.extension == ".pdf":
        _print_pdf(analysis, printer)
    else:
        _print_office(analysis, printer)

    return f"Printed on {printer}: {analysis.summary}"


def print_folder(
    folder: str,
    printer_name: str | None = None,
    recursive: bool = True,
) -> str:
    root = Path(os.path.expandvars(os.path.expanduser(folder))).resolve()
    if not root.is_dir():
        raise ValueError(f"Folder does not exist: {root}")

    printer = printer_name or default_printer()
    files = (
        [p for p in root.rglob("*") if p.is_file()]
        if recursive
        else [p for p in root.iterdir() if p.is_file()]
    )
    files = sorted(
        [p for p in files if p.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: str(p).lower(),
    )

    if not files:
        return f"No supported print files found in {root}."

    results = []
    for index, path in enumerate(files, start=1):
        analysis = analyze_file(str(path))
        print(f"[Dharshini printer] {index}/{len(files)} {analysis.summary}", flush=True)
        results.append(print_file(str(path), printer))

    return f"Completed {len(results)} file(s) on {printer}. " + " | ".join(results)


def printer_status(printer_name: str | None = None) -> str:
    printer = printer_name or default_printer()
    handle = win32print.OpenPrinter(printer)
    try:
        info = win32print.GetPrinter(handle, 2)
    finally:
        win32print.ClosePrinter(handle)

    status = info.get("Status", 0)
    jobs = info.get("cJobs", 0)
    return f"Printer {printer}: status={status}, queued jobs={jobs}."
