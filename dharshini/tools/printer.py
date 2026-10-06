from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}

STANDARD_PAPERS_MM = {
    "a5": (148, 210),
    "a4": (210, 297),
    "a3": (297, 420),
    "letter": (216, 279),
    "legal": (216, 356),
    "ledger": (279, 432),
}

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
class PaperInfo:
    name: str
    code: int | None
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class PrintAnalysis:
    path: str
    extension: str
    pages: int
    orientation: str
    duplex: str
    paper: str = "auto"
    paper_size_mm: tuple[float, float] | None = None
    mixed_paper: bool = False

    @property
    def summary(self) -> str:
        mode = "simplex" if self.duplex == "simplex" else f"duplex {self.duplex}"
        paper = self.paper
        if self.paper_size_mm:
            paper = f"{paper} ({self.paper_size_mm[0]:.0f}x{self.paper_size_mm[1]:.0f} mm)"
        mixed = ", mixed paper" if self.mixed_paper else ""
        return (
            f"{Path(self.path).name}: {self.pages} page(s), "
            f"{self.orientation}, {mode}, paper={paper}{mixed}"
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


def _printer_info(printer_name: str) -> dict:
    handle = win32print.OpenPrinter(printer_name)
    try:
        return win32print.GetPrinter(handle, 2)
    finally:
        win32print.ClosePrinter(handle)


def printer_status(printer_name: str | None = None) -> str:
    printer = printer_name or default_printer()
    info = _printer_info(printer)
    status = info.get("Status", 0)
    jobs = info.get("cJobs", 0)
    flags = _status_flags(status)
    state = ", ".join(flags) if flags else "ready"
    return f"Printer {printer}: {state}; queued jobs={jobs}."


def _status_flags(status: int) -> list[str]:
    if win32print is None:
        return []

    names = [
        "PRINTER_STATUS_PAUSED",
        "PRINTER_STATUS_ERROR",
        "PRINTER_STATUS_PENDING_DELETION",
        "PRINTER_STATUS_PAPER_JAM",
        "PRINTER_STATUS_PAPER_OUT",
        "PRINTER_STATUS_MANUAL_FEED",
        "PRINTER_STATUS_PAPER_PROBLEM",
        "PRINTER_STATUS_OFFLINE",
        "PRINTER_STATUS_IO_ACTIVE",
        "PRINTER_STATUS_BUSY",
        "PRINTER_STATUS_PRINTING",
        "PRINTER_STATUS_OUTPUT_BIN_FULL",
        "PRINTER_STATUS_NOT_AVAILABLE",
        "PRINTER_STATUS_WAITING",
        "PRINTER_STATUS_PROCESSING",
        "PRINTER_STATUS_TONER_LOW",
        "PRINTER_STATUS_NO_TONER",
        "PRINTER_STATUS_DOOR_OPEN",
        "PRINTER_STATUS_USER_INTERVENTION",
    ]
    return [
        name.removeprefix("PRINTER_STATUS_").lower().replace("_", " ")
        for name in names
        if status & getattr(win32print, name, 0)
    ]


def _blocking_printer_flags(status: int) -> list[str]:
    flags = set(_status_flags(status))
    return sorted(
        flags
        & {
            "error",
            "paper jam",
            "paper out",
            "paper problem",
            "offline",
            "not available",
            "no toner",
            "door open",
            "user intervention",
            "pending deletion",
        }
    )


def _ensure_printer_ready(printer_name: str) -> None:
    info = _printer_info(printer_name)
    blocking = _blocking_printer_flags(info.get("Status", 0))
    if blocking:
        raise RuntimeError(
            f"Printer '{printer_name}' is not ready: {', '.join(blocking)}."
        )


def _pdf_pages(path: Path) -> list[tuple[float, float]]:
    if PdfReader is None:
        raise RuntimeError("pypdf is required for PDF analysis.")

    reader = PdfReader(str(path))
    if not reader.pages:
        raise ValueError(f"PDF has no printable pages: {path}")

    sizes: list[tuple[float, float]] = []
    for page in reader.pages:
        box = page.mediabox
        width_pt = float(box.width)
        height_pt = float(box.height)
        sizes.append((width_pt * 25.4 / 72.0, height_pt * 25.4 / 72.0))
    return sizes


def _dominant_orientation(sizes: list[tuple[float, float]]) -> str:
    landscape = sum(width > height for width, height in sizes)
    return "landscape" if landscape > len(sizes) / 2 else "portrait"


def _nearest_standard_paper(size_mm: tuple[float, float]) -> str:
    width, height = size_mm
    candidates = [
        (name, dims)
        for name, dims in STANDARD_PAPERS_MM.items()
    ]

    def distance(dims):
        a, b = dims
        direct = abs(width - a) + abs(height - b)
        rotated = abs(width - b) + abs(height - a)
        return min(direct, rotated)

    name, dims = min(candidates, key=lambda item: distance(item[1]))
    return name if distance(dims) <= 8 else "custom"


def _office_to_pdf(path: Path) -> Path:
    """Export Word/Excel to a temporary PDF so rendered pages can be analyzed."""
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
            document = word.Documents.Open(
                str(path), ReadOnly=True, AddToRecentFiles=False
            )
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


def _paper_capabilities(printer_name: str) -> list[PaperInfo]:
    _require_win32()
    info = _printer_info(printer_name)
    port = info.get("pPortName")
    driver = info.get("pDriverName")

    paper_codes = win32print.DeviceCapabilities(
        printer_name, port, win32con.DC_PAPERS, None, None
    )
    paper_names = win32print.DeviceCapabilities(
        printer_name, port, win32con.DC_PAPERNAMES, None, None
    )
    paper_sizes = win32print.DeviceCapabilities(
        printer_name, port, win32con.DC_PAPERSIZE, None, None
    )

    result: list[PaperInfo] = []
    for index, code in enumerate(paper_codes or []):
        name = (
            paper_names[index].strip()
            if index < len(paper_names)
            else f"paper-{code}"
        )
        size = paper_sizes[index] if index < len(paper_sizes) else (0, 0)
        result.append(
            PaperInfo(
                name=name,
                code=int(code),
                width_mm=float(size[0]) / 10.0,
                height_mm=float(size[1]) / 10.0,
            )
        )
    return result


def printer_capabilities(printer_name: str | None = None) -> str:
    printer = printer_name or default_printer()
    papers = _paper_capabilities(printer)
    if not papers:
        return f"{printer}: no paper forms were reported by the driver."

    formatted = ", ".join(
        f"{p.name} ({p.width_mm:.0f}x{p.height_mm:.0f} mm)"
        for p in papers
    )
    duplex = bool(
        win32print.DeviceCapabilities(
            printer,
            _printer_info(printer).get("pPortName"),
            win32con.DC_DUPLEX,
            None,
            None,
        )
    )
    return f"{printer}: duplex={'yes' if duplex else 'no'}; papers: {formatted}"


def _select_supported_paper(
    printer_name: str,
    size_mm: tuple[float, float],
) -> PaperInfo:
    papers = _paper_capabilities(printer_name)
    if not papers:
        raise RuntimeError("Printer driver reported no supported paper forms.")

    width, height = size_mm

    def distance(paper: PaperInfo) -> float:
        direct = abs(width - paper.width_mm) + abs(height - paper.height_mm)
        rotated = abs(width - paper.height_mm) + abs(height - paper.width_mm)
        return min(direct, rotated)

    selected = min(papers, key=distance)
    if distance(selected) > 12:
        raise RuntimeError(
            f"Document requires approximately {width:.0f}x{height:.0f} mm, "
            f"but the printer driver did not report a close supported paper size."
        )
    return selected


def analyze_file(path: str, printer_name: str | None = None) -> PrintAnalysis:
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
            temp_pdf = file_path
        else:
            temp_pdf = _office_to_pdf(file_path)

        sizes = _pdf_pages(temp_pdf)
        orientation = _dominant_orientation(sizes)
        dominant = max(set(sizes), key=sizes.count)
        paper_name = _nearest_standard_paper(dominant)
        mixed = len(set(sizes)) > 1

        if len(sizes) == 1:
            duplex = "simplex"
        elif orientation == "portrait":
            duplex = "long-edge"
        else:
            duplex = "short-edge"

        selected_paper = None
        if printer_name:
            selected_paper = _select_supported_paper(printer_name, dominant)

        return PrintAnalysis(
            path=str(file_path),
            extension=extension,
            pages=len(sizes),
            orientation=orientation,
            duplex=duplex,
            paper=selected_paper.name if selected_paper else paper_name,
            paper_size_mm=(
                (selected_paper.width_mm, selected_paper.height_mm)
                if selected_paper
                else dominant
            ),
            mixed_paper=mixed,
        )
    finally:
        if temp_pdf and temp_pdf != file_path:
            shutil.rmtree(temp_pdf.parent, ignore_errors=True)


def _get_modified_devmode(
    printer_name: str,
    orientation: str,
    duplex: str,
    paper: PaperInfo | None,
):
    _require_win32()
    handle = win32print.OpenPrinter(printer_name)
    try:
        size = win32print.DocumentProperties(0, handle, printer_name, None, None, 0)
        if size <= 0:
            raise RuntimeError("Could not obtain printer DEVMODE.")

        driver_extra = size - pywintypes.DEVMODEType().Size
        dm = pywintypes.DEVMODEType(driver_extra)

        win32print.DocumentProperties(
            0, handle, printer_name, dm, None, win32con.DM_OUT_BUFFER
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

        if paper and (dm.Fields & win32con.DM_PAPERSIZE):
            dm.Fields |= win32con.DM_PAPERSIZE
            dm.PaperSize = paper.code
        elif paper and (dm.Fields & win32con.DM_PAPERWIDTH):
            dm.Fields |= win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH
            dm.PaperWidth = int(round(paper.width_mm * 10))
            dm.PaperLength = int(round(paper.height_mm * 10))

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
        {"DesiredAccess": win32print.PRINTER_ACCESS_USE},
    )
    try:
        win32print.SetPrinter(handle, 9, {"pDevMode": dm}, 0)
    finally:
        win32print.ClosePrinter(handle)


def _snapshot_job_ids(printer_name: str) -> set[int]:
    handle = win32print.OpenPrinter(printer_name)
    try:
        return {job["JobId"] for job in win32print.EnumJobs(handle, 0, -1, 1)}
    finally:
        win32print.ClosePrinter(handle)


def _wait_for_spool(
    printer_name: str,
    before_ids: set[int],
    timeout: int = 180,
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = _printer_info(printer_name)
        blocking = _blocking_printer_flags(info.get("Status", 0))
        if blocking:
            raise RuntimeError(
                f"Printer error while processing job: {', '.join(blocking)}."
            )

        handle = win32print.OpenPrinter(printer_name)
        try:
            jobs = win32print.EnumJobs(handle, 0, -1, 1)
        finally:
            win32print.ClosePrinter(handle)

        new_jobs = [job for job in jobs if job["JobId"] not in before_ids]
        if not new_jobs:
            return

        job_errors = [
            job for job in new_jobs
            if job.get("Status", 0) & getattr(win32print, "JOB_STATUS_ERROR", 0)
        ]
        if job_errors:
            raise RuntimeError("Windows reported a printer job error.")

        time.sleep(1)

    raise TimeoutError(
        f"Timed out waiting for the printer queue after {timeout} seconds."
    )


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
    subprocess.run(
        [
            str(sumatra),
            "-silent",
            "-print-to",
            printer_name,
            "-print-settings",
            settings,
            analysis.path,
        ],
        check=True,
        timeout=120,
    )
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
    printer = printer_name or default_printer()
    if printer not in list_printers():
        raise ValueError(f"Printer not found: {printer}")

    _ensure_printer_ready(printer)
    analysis = analyze_file(path, printer)

    paper = _select_supported_paper(
        printer,
        analysis.paper_size_mm or (210, 297),
    )

    dm = _get_modified_devmode(
        printer,
        analysis.orientation,
        analysis.duplex,
        paper,
    )
    _set_user_devmode(printer, dm)

    last_error = None
    for attempt in range(1, 4):
        try:
            _ensure_printer_ready(printer)
            if analysis.extension == ".pdf":
                _print_pdf(analysis, printer)
            else:
                _print_office(analysis, printer)
            return f"Printed on {printer}: {analysis.summary}"
        except Exception as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(2 * attempt)

    raise RuntimeError(
        f"Printing failed after 3 attempts for {Path(path).name}: {last_error}"
    )


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
    failures = []
    for index, path in enumerate(files, start=1):
        try:
            analysis = analyze_file(str(path), printer)
            print(
                f"[Dharshini printer] {index}/{len(files)} {analysis.summary}",
                flush=True,
            )
            results.append(print_file(str(path), printer))
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            print(
                f"[Dharshini printer] FAILED {path.name}: {exc}",
                flush=True,
            )

    summary = f"Completed {len(results)}/{len(files)} file(s) on {printer}."
    if failures:
        summary += " Failures: " + " | ".join(failures)
    return summary
