from __future__ import annotations

import builtins
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from dharshini.tools import printer as printer_engine

APP_TITLE = "Dharshini Print Manager"
TYPE_EXTENSIONS = {
    "PDF": {".pdf"},
    "Word": {".doc", ".docx"},
    "Excel": {".xls", ".xlsx"},
}


class PrintManagerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("900x680")
        self.root.minsize(760, 560)
        self.events: queue.Queue[tuple] = queue.Queue()
        self.busy = False
        self.cancel_requested = False
        self.files: list[Path] = []
        self.type_vars = {name: tk.BooleanVar(value=True) for name in TYPE_EXTENSIONS}
        self.recursive_var = tk.BooleanVar(value=True)
        self.path_var = tk.StringVar()
        self.printer_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.count_var = tk.StringVar(value="Choose a folder and click Preview.")
        self._detect_sumatra()
        self._build_ui()
        self._load_printers()
        self.root.after(100, self._process_events)

    @staticmethod
    def _detect_sumatra() -> None:
        if os.getenv("DHARSHINI_SUMATRA_PATH", "").strip():
            return
        local_app_data = os.getenv("LOCALAPPDATA", "")
        candidates = [
            Path(local_app_data) / "SumatraPDF" / "SumatraPDF.exe" if local_app_data else None,
            Path(os.getenv("PROGRAMFILES", r"C:\Program Files")) / "SumatraPDF" / "SumatraPDF.exe",
            Path(os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "SumatraPDF" / "SumatraPDF.exe",
        ]
        for candidate in candidates:
            if candidate and candidate.is_file():
                os.environ["DHARSHINI_SUMATRA_PATH"] = str(candidate)
                return

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x", pady=(0, 14))
        ttk.Label(heading, text="Dharshini Print Manager", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(heading, text="Print PDF, Word and Excel files locally — no Gemini account or API key required.").pack(anchor="w", pady=(3, 0))

        path_frame = ttk.LabelFrame(outer, text="Folder path", padding=10)
        path_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(path_frame, textvariable=self.path_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(path_frame, text="Browse…", command=self._browse).pack(side="left")
        ttk.Button(path_frame, text="Preview files", command=self._preview).pack(side="left", padx=(8, 0))

        options = ttk.LabelFrame(outer, text="Print options", padding=10)
        options.pack(fill="x", pady=(0, 10))
        type_row = ttk.Frame(options)
        type_row.pack(fill="x")
        ttk.Label(type_row, text="File types:").pack(side="left", padx=(0, 10))
        labels = {"PDF": "PDF (.pdf)", "Word": "Word (.doc, .docx)", "Excel": "Excel (.xls, .xlsx)"}
        for name in TYPE_EXTENSIONS:
            ttk.Checkbutton(type_row, text=labels[name], variable=self.type_vars[name], command=self._preview_if_path).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(options, text="Include subfolders", variable=self.recursive_var, command=self._preview_if_path).pack(anchor="w", pady=(8, 0))

        printer_frame = ttk.LabelFrame(outer, text="Printer", padding=10)
        printer_frame.pack(fill="x", pady=(0, 10))
        self.printer_combo = ttk.Combobox(printer_frame, textvariable=self.printer_var, state="readonly")
        self.printer_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(printer_frame, text="Refresh printers", command=self._load_printers).pack(side="left", padx=(8, 0))

        files_frame = ttk.LabelFrame(outer, text="Files to print", padding=8)
        files_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.file_list = tk.Listbox(files_frame, selectmode="browse", font=("Consolas", 9), height=12)
        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.count_var).pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=12)
        self.print_button = ttk.Button(bottom, text="Print All", command=self._start_print)
        self.print_button.pack(side="left")
        self.cancel_button = ttk.Button(bottom, text="Stop after current file", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))
        ttk.Label(outer, textvariable=self.status_var, wraplength=850).pack(anchor="w", pady=(10, 0))

    def _browse(self) -> None:
        folder = filedialog.askdirectory(title="Choose folder to print")
        if folder:
            self.path_var.set(folder)
            self._preview()

    def _selected_extensions(self) -> set[str]:
        return set().union(*(exts for name, exts in TYPE_EXTENSIONS.items() if self.type_vars[name].get()))

    def _preview_if_path(self) -> None:
        if self.path_var.get().strip():
            self._preview()

    def _preview(self) -> None:
        if self.busy:
            return
        raw_path = os.path.expandvars(os.path.expanduser(self.path_var.get().strip().strip('"')))
        root = Path(raw_path)
        if not root.is_dir():
            messagebox.showerror(APP_TITLE, "Please enter a valid folder path or use Browse.")
            return
        extensions = self._selected_extensions()
        if not extensions:
            messagebox.showwarning(APP_TITLE, "Select at least one file type.")
            return
        try:
            candidates = root.rglob("*") if self.recursive_var.get() else root.iterdir()
            self.files = sorted((p for p in candidates if p.is_file() and p.suffix.lower() in extensions), key=lambda p: str(p).lower())
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not read folder:\n{exc}")
            return
        self.file_list.delete(0, tk.END)
        for path in self.files:
            self.file_list.insert(tk.END, str(path.relative_to(root)))
        self.count_var.set(f"{len(self.files)} matching file(s)")
        self.status_var.set("Preview ready." if self.files else "No matching files found.")

    def _load_printers(self) -> None:
        try:
            names = printer_engine.list_printers()
            self.printer_combo["values"] = names
            current = self.printer_var.get()
            if current in names:
                return
            try:
                default = printer_engine.default_printer()
            except Exception:
                default = ""
            self.printer_var.set(default if default in names else (names[0] if names else ""))
            if not names:
                self.status_var.set("No Windows printers found. Connect/install a printer and refresh.")
        except Exception as exc:
            self.status_var.set(f"Could not load printers: {exc}")

    def _start_print(self) -> None:
        if self.busy:
            return
        self._preview()
        if not self.files:
            return
        printer_name = self.printer_var.get().strip()
        if not printer_name:
            messagebox.showerror(APP_TITLE, "Select an installed printer first.")
            return
        if not messagebox.askyesno(APP_TITLE, f"Submit {len(self.files)} file(s) to {printer_name}?\n\nWord and Excel print single-sided. PDF duplex follows the existing rules. Check the printer queue before retrying any uncertain job."):
            return
        self.busy = True
        self.cancel_requested = False
        self.print_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(maximum=len(self.files), value=0)
        threading.Thread(target=self._print_worker, args=(list(self.files), printer_name), daemon=True).start()

    def _paper_prompt(self) -> None:
        answer = threading.Event()
        outcome = {"ok": False}
        def show_prompt() -> None:
            outcome["ok"] = messagebox.askokcancel(APP_TITLE, "The printer reports that paper is out or unavailable.\n\nRefill the tray and clear the printer's panel warning, then choose OK. The existing job will not be resubmitted.")
            answer.set()
        self.root.after(0, show_prompt)
        answer.wait()
        if not outcome["ok"]:
            raise EOFError("Paper-out recovery cancelled by user.")

    def _print_worker(self, files: list[Path], printer_name: str) -> None:
        original_input = builtins.input
        builtins.input = lambda prompt="": self._paper_prompt()
        successes = 0
        failures: list[str] = []
        try:
            for index, path in enumerate(files, start=1):
                if self.cancel_requested:
                    break
                self.events.put(("status", index, len(files), f"Printing {path.name}…"))
                try:
                    result = printer_engine.print_file(str(path), printer_name)
                    successes += 1
                    self.events.put(("file", index, "OK", f"{path.name} — {result}"))
                except Exception as exc:
                    failures.append(f"{path.name}: {exc}")
                    self.events.put(("file", index, "FAILED", f"{path.name} — {exc}"))
        finally:
            builtins.input = original_input
            self.events.put(("done", successes, len(files), failures, self.cancel_requested))

    def _cancel(self) -> None:
        if self.busy:
            self.cancel_requested = True
            self.cancel_button.configure(state="disabled")
            self.status_var.set("Stop requested; the current file will be allowed to finish.")

    def _process_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "status":
                    _, index, total, message = event
                    self.progress.configure(maximum=total, value=index - 1)
                    self.status_var.set(f"{index}/{total}: {message}")
                elif event[0] == "file":
                    _, index, state, message = event
                    self.file_list.selection_clear(0, tk.END)
                    if index - 1 < self.file_list.size():
                        self.file_list.selection_set(index - 1)
                        self.file_list.see(index - 1)
                    self.file_list.itemconfig(index - 1, foreground="#16733c" if state == "OK" else "#b42318")
                    self.status_var.set(message)
                elif event[0] == "done":
                    _, successes, total, failures, cancelled = event
                    self.busy = False
                    self.print_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    if not cancelled:
                        self.progress.configure(value=total)
                    summary = f"Finished: {successes}/{total} file(s) submitted."
                    if cancelled:
                        summary += " Stopped after current file."
                    if failures:
                        summary += f" {len(failures)} file(s) failed."
                    self.status_var.set(summary)
                    if failures:
                        messagebox.showwarning(APP_TITLE, summary + "\n\n" + "\n".join(failures[:10]))
                    else:
                        messagebox.showinfo(APP_TITLE, summary)
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    PrintManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
