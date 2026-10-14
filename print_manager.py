from __future__ import annotations

import builtins
import json
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
        local_app_data = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        self.history_path = local_app_data / "Dharshini" / "PrintManager" / "job_state.json"
        self.file_statuses: dict[str, str] = {}
        self._load_job_state()
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
        self.resume_button = ttk.Button(bottom, text="Resume pending", command=self._start_print)
        self.resume_button.pack(side="left", padx=(8, 0))
        self.reset_button = ttk.Button(bottom, text="Reset selected", command=self._reset_selected)
        self.reset_button.pack(side="left", padx=(8, 0))
        self.cancel_button = ttk.Button(bottom, text="Stop after current file", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))
        ttk.Label(outer, textvariable=self.status_var, wraplength=850).pack(anchor="w", pady=(10, 0))

    def _load_job_state(self) -> None:
        try:
            if self.history_path.is_file():
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                statuses = data.get("statuses", {})
                if isinstance(statuses, dict):
                    self.file_statuses = {
                        str(path): ("NEEDS VERIFICATION" if state == "IN PROGRESS" else str(state))
                        for path, state in statuses.items()
                    }
        except (OSError, ValueError, TypeError):
            self.file_statuses = {}

    def _save_job_state(self) -> None:
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.history_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"statuses": self.file_statuses}, indent=2), encoding="utf-8")
            temporary.replace(self.history_path)
        except OSError as exc:
            self.status_var.set(f"Warning: could not save print history: {exc}")

    def _set_file_status(self, path: Path, status: str) -> None:
        self.file_statuses[str(path.resolve())] = status
        self._save_job_state()

    def _refresh_file_row(self, index: int, path: Path) -> None:
        if index < 0 or index >= self.file_list.size():
            return
        state = self.file_statuses.get(str(path.resolve()), "PENDING")
        root_path = Path(self.path_var.get().strip().strip('"'))
        try:
            display_path = str(path.relative_to(root_path))
        except ValueError:
            display_path = str(path)
        self.file_list.delete(index)
        self.file_list.insert(index, f"[{state}] {display_path}")
        color = "#16733c" if state == "SUBMITTED - VERIFY OUTPUT" else (
            "#b42318" if state == "NEEDS VERIFICATION" else (
                "#996515" if state == "IN PROGRESS" else "#333333"
            )
        )
        self.file_list.itemconfig(index, foreground=color)

    def _reset_selected(self) -> None:
        selection = self.file_list.curselection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select a file first.")
            return
        index = selection[0]
        if index >= len(self.files):
            return
        path = self.files[index]
        current = self.file_statuses.get(str(path.resolve()), "PENDING")
        if current not in {"NEEDS VERIFICATION", "SUBMITTED - VERIFY OUTPUT", "FAILED"}:
            messagebox.showinfo(APP_TITLE, "Only a file requiring verification or retry can be reset.")
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Check the physical pages and Windows print queue for:\\n{path.name}\\n\\nOnly choose Yes if you have confirmed it is safe to print this file again.",
        ):
            return
        self._set_file_status(path, "PENDING")
        self._refresh_file_row(index, path)
        self.status_var.set(f"{path.name} reset to pending.")

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
            self.files = []
            self.file_list.delete(0, tk.END)
            self.count_var.set("0 matching file(s)")
            messagebox.showerror(APP_TITLE, "Please enter a valid folder path or use Browse.")
            return
        extensions = self._selected_extensions()
        if not extensions:
            self.files = []
            self.file_list.delete(0, tk.END)
            self.count_var.set("0 matching file(s)")
            messagebox.showwarning(APP_TITLE, "Select at least one file type.")
            return
        try:
            candidates = root.rglob("*") if self.recursive_var.get() else root.iterdir()
            self.files = sorted((p for p in candidates if p.is_file() and p.suffix.lower() in extensions), key=lambda p: str(p).lower())
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not read folder:\n{exc}")
            return
        self.file_list.delete(0, tk.END)
        for index, path in enumerate(self.files):
            self.file_list.insert(tk.END, "")
            self._refresh_file_row(index, path)
        pending = sum(
            self.file_statuses.get(str(path.resolve()), "PENDING") == "PENDING"
            for path in self.files
        )
        self.count_var.set(f"{len(self.files)} matching file(s); {pending} pending")
        self.status_var.set("Preview ready. Submitted files are not automatically retried." if self.files else "No matching files found.")

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
        pending = [
            path for path in self.files
            if self.file_statuses.get(str(path.resolve()), "PENDING") == "PENDING"
        ]
        if not pending:
            messagebox.showinfo(APP_TITLE, "There are no pending files. Use Reset selected only after checking the printer output and queue.")
            return
        printer_name = self.printer_var.get().strip()
        if not printer_name:
            messagebox.showerror(APP_TITLE, "Select an installed printer first.")
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Submit {len(pending)} pending file(s) to {printer_name}?\\n\\n"
            "Previously submitted or uncertain files will not be automatically retried. "
            "If a file fails, the batch will pause so you can check the printer before resuming.",
        ):
            return
        self.busy = True
        self.cancel_requested = False
        self.print_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.reset_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(maximum=len(pending), value=0)
        threading.Thread(target=self._print_worker, args=(pending, printer_name), daemon=True).start()

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
        paused_on_error = False
        try:
            for index, path in enumerate(files, start=1):
                if self.cancel_requested:
                    break
                self.events.put(("status", index, len(files), str(path), f"Printing {path.name}…"))
                try:
                    result = printer_engine.print_file(str(path), printer_name)
                    successes += 1
                    self.events.put(("file", index, len(files), str(path), "SUBMITTED - VERIFY OUTPUT", f"{path.name} — submitted; verify the physical output"))
                except Exception as exc:
                    # The spooler may have accepted some or all of this file.
                    # Never retry it automatically and pause the batch at once.
                    failures.append(f"{path.name}: {exc}")
                    self.events.put(("file", index, len(files), str(path), "NEEDS VERIFICATION", f"{path.name} — status uncertain; check printer output and queue: {exc}"))
                    paused_on_error = True
                    break
        finally:
            builtins.input = original_input
            self.events.put(("done", successes, len(files), failures, self.cancel_requested, paused_on_error))

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
                    _, index, total, path_text, message = event
                    path = Path(path_text)
                    self._set_file_status(path, "IN PROGRESS")
                    row = next((i for i, item in enumerate(self.files) if str(item.resolve()) == str(path.resolve())), -1)
                    self._refresh_file_row(row, path)
                    self.progress.configure(maximum=total, value=index - 1)
                    self.status_var.set(f"{index}/{total}: {message}")
                elif event[0] == "file":
                    _, index, total, path_text, state, message = event
                    path = Path(path_text)
                    self._set_file_status(path, state)
                    row = next((i for i, item in enumerate(self.files) if str(item.resolve()) == str(path.resolve())), -1)
                    self._refresh_file_row(row, path)
                    if row >= 0:
                        self.file_list.selection_clear(0, tk.END)
                        self.file_list.selection_set(row)
                        self.file_list.see(row)
                    self.progress.configure(maximum=total, value=index)
                    self.status_var.set(message)
                elif event[0] == "done":
                    _, successes, total, failures, cancelled, paused_on_error = event
                    self.busy = False
                    self.print_button.configure(state="normal")
                    self.resume_button.configure(state="normal")
                    self.reset_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    summary = f"Submitted {successes}/{total} file(s) in this batch."
                    if cancelled:
                        summary += " Stopped after the current file; remaining files are pending."
                    if failures:
                        summary += " Batch paused after an error. The uncertain file was not retried; check the physical output and Windows print queue."
                    elif paused_on_error:
                        summary += " Batch paused for printer recovery."
                    if not failures and not cancelled:
                        self.progress.configure(value=total)
                    self.status_var.set(summary)
                    if failures:
                        messagebox.showwarning(APP_TITLE, summary + "\\n\\n" + "\\n".join(failures[:10]))
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
