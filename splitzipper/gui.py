import json
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from splitzipper import join_and_unzip, split_zip
from splitzipper.localization import TEXTS

HISTORY_FILE = Path.home() / ".splitzipper_history.json"
SETTINGS_FILE = Path.home() / ".splitzipper_settings.json"


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {
        "chunk_size_mb": 16,
        "language": "en",
        "extension": "b64",
    }


def _(key, settings):
    return TEXTS[settings["language"]][key]


class Application(ttk.Frame):
    PAD = 8

    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=self.PAD)
        self.settings = load_settings()
        self.history = self._load_history()
        self._setup_style()

        self.master.title("SplitZipper")
        self.master.geometry("650x490")
        self.master.resizable(False, False)
        self.pack(fill=tk.BOTH, expand=True)

        self._build_widgets()
        self.progress_lock = threading.Lock()

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        default_font = ("Segoe UI", 10)
        style.configure(".", font=default_font)
        style.configure(
            "Accent.TButton", foreground="white", background="#0078D7", padding=6
        )
        style.map("Accent.TButton", background=[("active", "#005A9E")])
        style.configure("LabeledProgressbar", text="", anchor="center")

    def _build_widgets(self):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=self.PAD, pady=(0, self.PAD))
        self.header_label = ttk.Label(
            header_frame,
            text=_("app_title", self.settings),
            font=("Segoe UI", 16, "bold"),
        )
        self.header_label.pack(side=tk.LEFT)
        settings_btn = ttk.Button(
            header_frame, text="⚙️", width=3, command=self._open_settings
        )
        settings_btn.pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=self.PAD, pady=self.PAD)

        self.tab_archive = ttk.Frame(self.notebook, padding=self.PAD)
        self.notebook.add(
            self.tab_archive,
            text=_("tab_archive", self.settings).replace(
                ".EXT", f".{self.settings['extension']}"
            ),
        )
        self._build_archive_tab()

        self.tab_restore = ttk.Frame(self.notebook, padding=self.PAD)
        self.notebook.add(
            self.tab_restore,
            text=_("tab_restore", self.settings).replace(
                ".EXT", f".{self.settings['extension']}"
            ),
        )
        self._build_restore_tab()

        self.tab_history = ttk.Frame(self.notebook, padding=self.PAD)
        self.notebook.add(self.tab_history, text=_("history_label", self.settings))
        self._build_history_tab()

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=self.PAD, pady=(0, self.PAD))

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(
            bottom_frame, orient="horizontal", variable=self.progress_var, maximum=100
        )
        self.progress.pack(fill=tk.X)

        self.status_var = tk.StringVar(value=_("ready", self.settings))
        ttk.Label(bottom_frame, textvariable=self.status_var, anchor="w").pack(
            fill=tk.X, pady=(5, 0)
        )

    def _build_archive_tab(self):
        for widget in self.tab_archive.winfo_children():
            widget.destroy()
        self.src_entry = self._folder_entry(
            self.tab_archive, _("source_folder", self.settings)
        )
        self.dst_entry = self._folder_entry(
            self.tab_archive, _("dest_parts", self.settings)
        )
        run_btn = ttk.Button(
            self.tab_archive,
            text=_("run", self.settings),
            style="Accent.TButton",
            command=self._on_archive,
        )
        run_btn.pack(pady=(10, 0))

    def _build_restore_tab(self):
        for widget in self.tab_restore.winfo_children():
            widget.destroy()
        self.enc_entry = self._folder_entry(
            self.tab_restore,
            _("encoded_folder", self.settings).replace(
                ".EXT", f".{self.settings['extension']}"
            ),
        )
        self.out_entry = self._folder_entry(
            self.tab_restore, _("extract_to", self.settings)
        )
        run_btn = ttk.Button(
            self.tab_restore,
            text=_("run", self.settings),
            style="Accent.TButton",
            command=self._on_restore,
        )
        run_btn.pack(pady=(10, 0))

    def _build_history_tab(self):
        for widget in self.tab_history.winfo_children():
            widget.destroy()
        cols = ("timestamp", "operation", "src", "dst", "status")
        tree = ttk.Treeview(self.tab_history, columns=cols, show="headings", height=15)
        tree.heading("timestamp", text="Timestamp")
        tree.heading("operation", text="Operation")
        tree.heading("src", text="Source")
        tree.heading("dst", text="Destination")
        tree.heading("status", text="Status")
        tree.column("timestamp", width=140)
        tree.column("operation", width=80)
        tree.column("src", width=180)
        tree.column("dst", width=180)
        tree.column("status", width=60)
        tree.pack(fill=tk.BOTH, expand=True)

        for entry in self.history:
            tree.insert(
                "",
                tk.END,
                values=(
                    entry["timestamp"],
                    entry["operation"],
                    entry["src"],
                    entry["dst"],
                    entry["status"],
                ),
            )

    def _folder_entry(self, parent: ttk.Frame, label: str) -> tk.StringVar:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 8))

        lbl = ttk.Label(frame, text=label)
        lbl.grid(row=0, column=0, sticky="w")

        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var, width=50)
        entry.grid(row=0, column=1, padx=(10, 0), sticky="we")

        btn = ttk.Button(
            frame,
            text="📁",
            width=3,
            command=lambda: var.set(filedialog.askdirectory(title=label) or var.get()),
        )
        btn.grid(row=0, column=2, padx=(10, 0))

        frame.columnconfigure(1, weight=1)
        return var

    def _open_settings(self):
        settings_win = tk.Toplevel(self.master)
        settings_win.title(_("settings", self.settings))
        settings_win.resizable(False, False)
        settings_win.grab_set()

        pad = 10
        frame = ttk.Frame(settings_win, padding=pad)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=_("chunk_size_label", self.settings)).grid(
            row=0, column=0, sticky="w"
        )
        chunk_var = tk.IntVar(value=self.settings["chunk_size_mb"])
        chunk_spin = ttk.Spinbox(
            frame, from_=1, to=1024, textvariable=chunk_var, width=5
        )
        chunk_spin.grid(row=0, column=1, padx=(10, 0), sticky="w")

        ttk.Label(frame, text=_("language_label", self.settings)).grid(
            row=1, column=0, sticky="w"
        )
        lang_var = tk.StringVar(value=self.settings["language"])
        lang_combo = ttk.Combobox(
            frame, values=["en", "ru"], state="readonly", width=5, textvariable=lang_var
        )
        lang_combo.grid(row=1, column=1, padx=(10, 0), sticky="w")

        ttk.Label(frame, text=_("extension_label", self.settings)).grid(
            row=2, column=0, sticky="w"
        )
        ext_var = tk.StringVar(value=self.settings["extension"])
        ext_entry = ttk.Entry(frame, textvariable=ext_var, width=5)
        ext_entry.grid(row=2, column=1, padx=(10, 0), sticky="w")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(pad, 0))
        apply_btn = ttk.Button(
            btn_frame,
            text=_("apply", self.settings),
            command=lambda: self._apply_settings(
                settings_win, chunk_var, lang_var, ext_var
            ),
        )
        apply_btn.pack(side=tk.LEFT, padx=(0, pad))
        cancel_btn = ttk.Button(
            btn_frame, text=_("cancel", self.settings), command=settings_win.destroy
        )
        cancel_btn.pack(side=tk.LEFT)

    def _apply_settings(self, window, chunk_var, lang_var, ext_var):
        self.settings["chunk_size_mb"] = chunk_var.get()
        self.settings["language"] = lang_var.get()
        self.settings["extension"] = ext_var.get().strip()
        try:
            SETTINGS_FILE.write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2)
            )
        except Exception:
            pass

        self._refresh_ui_texts()
        self.progress.update()
        self.status_var.set(_("ready", self.settings))
        window.destroy()

    def _refresh_ui_texts(self):
        self.master.title(_("app_title", self.settings))
        self.header_label.config(text=_("app_title", self.settings))

        for idx, tab in enumerate(
            [
                ("tab_archive", f".{self.settings['extension']}"),
                ("tab_restore", f".{self.settings['extension']}"),
                ("history_label", ""),
            ]
        ):
            key, suf = tab
            text = _(key, self.settings)
            text = text.replace(".EXT", suf)
            self.notebook.tab(idx, text=text)

        self._build_archive_tab()
        self._build_restore_tab()
        self._build_history_tab()

        self.status_var.set(_("ready", self.settings))

    def _on_archive(self):
        src = self.src_entry.get().strip()
        dst = self.dst_entry.get().strip() or ""
        if not src:
            messagebox.showwarning(
                _("app_title", self.settings),
                _("missing_source", self.settings).replace(
                    ".EXT", f".{self.settings['extension']}"
                ),
            )
            return
        threading.Thread(
            target=self._run_archive,
            args=(Path(src), Path(dst) or Path(src).parent),
            daemon=True,
        ).start()

    def _on_restore(self):
        enc = self.enc_entry.get().strip()
        out = self.out_entry.get().strip() or ""
        if not enc:
            messagebox.showwarning(
                _("app_title", self.settings),
                _("missing_encoded", self.settings).replace(
                    ".EXT", f".{self.settings['extension']}"
                ),
            )
            return
        threading.Thread(
            target=self._run_restore,
            args=(Path(enc), Path(out) or Path(enc).parent),
            daemon=True,
        ).start()

    def _run_archive(self, src: Path, dst: Path):
        try:
            chunk_bytes = self.settings["chunk_size_mb"] * 1024 * 1024
            parts = split_zip(
                src,
                dst,
                chunk_size=chunk_bytes,
                ext=self.settings["extension"],
                progress_cb=self._progress,
            )
            save_path = parts[0].parent
            msg = _("done_parts", self.settings).format(
                count=len(parts), path=str(save_path)
            )
            self._status(msg, reset=True)
            self._add_history("archive", str(src), str(save_path), "OK")
        except Exception as e:
            self._status(_("error", self.settings).format(msg=str(e)))
            self._add_history("archive", str(src), str(dst), f"Error: {e}")
            messagebox.showerror(_("app_title", self.settings), str(e))

    def _run_restore(self, enc: Path, out: Path):
        try:
            result_dir = join_and_unzip(
                enc, out, ext=self.settings["extension"], progress_cb=self._progress
            )
            msg = _("extracted_to", self.settings).format(path=str(result_dir))
            self._status(msg, reset=True)
            self._add_history("restore", str(enc), str(result_dir), "OK")
        except Exception as e:
            self._status(_("error", self.settings).format(msg=str(e)))
            self._add_history("restore", str(enc), str(out), f"Error: {e}")
            messagebox.showerror(_("app_title", self.settings), str(e))

    def _progress(self, phase: str, current: int, total: int):
        with self.progress_lock:
            pct = 0 if total == 0 else (current / total) * 100
            self.progress_var.set(pct)
            phase_text = _(phase, self.settings)
            self.status_var.set(f"{phase_text} {current}/{total}")

    def _status(self, text: str, *, reset: bool = False):
        self.status_var.set(text)
        if reset:
            self.progress_var.set(0)

    def _load_history(self):
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text())
            except Exception:
                return []
        return []

    def _add_history(self, operation: str, src: str, dst: str, status: str):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operation": operation,
            "src": src,
            "dst": dst,
            "status": status,
        }
        self.history.insert(0, entry)
        self.history = self.history[:50]
        try:
            HISTORY_FILE.write_text(
                json.dumps(self.history, indent=2, ensure_ascii=False)
            )
        except Exception:
            pass
        self._build_history_tab()


def main():
    root = tk.Tk()
    Application(root)
    root.mainloop()
