"""GUI installer bootstrap so end users never need terminal commands."""

from __future__ import annotations

import platform
import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    # Package import path (normal module execution).
    from .resolver import resolve_target
    from .service import download_installer, run_installer
except ImportError:
    # Script/frozen execution path (e.g. PyInstaller entrypoint from file path).
    from smartscreen_bootstrap.resolver import resolve_target
    from smartscreen_bootstrap.service import download_installer, run_installer


class InstallerWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SmartScreen Installer")
        self.root.geometry("620x420")
        self.root.minsize(620, 420)

        self.repo_var = tk.StringVar(value="devodan69/smartscreen")
        self.version_var = tk.StringVar(value="latest")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0.0)

        target = resolve_target(platform.system(), platform.machine())
        self.target_text = f"Detected platform: {target.os_name}/{target.arch}"

        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.root.after(120, self._drain_queue)

    def _build_ui(self) -> None:
        self.root.configure(bg="#0F172A")

        frame = tk.Frame(self.root, bg="#0F172A")
        frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        header = tk.Label(
            frame,
            text="SmartScreen Installer",
            font=("Segoe UI", 22, "bold"),
            bg="#0F172A",
            fg="#E5F0FF",
        )
        header.pack(anchor="w")

        subtitle = tk.Label(
            frame,
            text="Install SmartScreen with a native installer UI",
            font=("Segoe UI", 11),
            bg="#0F172A",
            fg="#A7B8D6",
        )
        subtitle.pack(anchor="w", pady=(0, 14))

        target_lbl = tk.Label(frame, text=self.target_text, font=("Segoe UI", 10), bg="#0F172A", fg="#8CFFB5")
        target_lbl.pack(anchor="w", pady=(0, 12))

        form = tk.Frame(frame, bg="#0F172A")
        form.pack(fill=tk.X)

        tk.Label(form, text="GitHub Repo", bg="#0F172A", fg="#D7E5FF", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=6
        )
        tk.Entry(form, textvariable=self.repo_var, width=44).grid(row=0, column=1, sticky="ew", pady=6)

        tk.Label(form, text="Version", bg="#0F172A", fg="#D7E5FF", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=6
        )
        tk.Entry(form, textvariable=self.version_var, width=44).grid(row=1, column=1, sticky="ew", pady=6)

        form.columnconfigure(1, weight=1)

        actions = tk.Frame(frame, bg="#0F172A")
        actions.pack(fill=tk.X, pady=(16, 10))

        self.install_btn = tk.Button(
            actions,
            text="Install Now",
            command=lambda: self._start_worker(install=True),
            bg="#2CCEF6",
            fg="#061528",
            activebackground="#4ED7FF",
            relief=tk.FLAT,
            padx=14,
            pady=8,
        )
        self.install_btn.pack(side=tk.LEFT)

        self.download_btn = tk.Button(
            actions,
            text="Download Only",
            command=lambda: self._start_worker(install=False),
            bg="#23304D",
            fg="#DCE7FF",
            activebackground="#334A76",
            relief=tk.FLAT,
            padx=14,
            pady=8,
        )
        self.download_btn.pack(side=tk.LEFT, padx=8)

        self.quit_btn = tk.Button(
            actions,
            text="Quit",
            command=self.root.destroy,
            bg="#1D2438",
            fg="#DCE7FF",
            relief=tk.FLAT,
            padx=14,
            pady=8,
        )
        self.quit_btn.pack(side=tk.RIGHT)

        bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100)
        bar.pack(fill=tk.X, pady=(6, 8))

        status = tk.Label(frame, textvariable=self.status_var, bg="#0F172A", fg="#A7B8D6", font=("Segoe UI", 10))
        status.pack(anchor="w")

        self.log_text = tk.Text(
            frame,
            height=11,
            bg="#0A1224",
            fg="#BFD2F8",
            insertbackground="#BFD2F8",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#263A63",
            font=("Consolas", 9),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self._log("Ready")

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.install_btn.configure(state=state)
        self.download_btn.configure(state=state)
        if not busy:
            self.progress_var.set(0.0)

    def _log(self, msg: str) -> None:
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def _start_worker(self, install: bool) -> None:
        if self._worker and self._worker.is_alive():
            return

        repo = self.repo_var.get().strip() or "dgeprojects/smartscreen"
        version = self.version_var.get().strip() or "latest"
        self._set_busy(True)
        self.status_var.set("Working")
        self.progress_var.set(10.0)

        def worker() -> None:
            try:
                with tempfile.TemporaryDirectory(prefix="smartscreen-installer-ui-") as tmp:
                    tmp_path = Path(tmp)
                    self._queue.put(("log", f"Resolving {repo}@{version}"))

                    def progress(msg: str) -> None:
                        self._queue.put(("progress", msg))

                    result = download_installer(repo=repo, version=version, destination_dir=tmp_path, progress=progress)
                    self._queue.put(("log", f"Downloaded: {result.installer_path.name}"))

                    if install:
                        self._queue.put(("log", "Launching installer"))
                        code = run_installer(result.installer_path, silent=False)
                        if code != 0:
                            raise RuntimeError(f"Installer exited with code {code}")
                        self._queue.put(("done", "Install finished"))
                    else:
                        self._queue.put(("done", f"Download complete: {result.installer_path}"))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "progress":
                    self._log(payload)
                    self.status_var.set(payload)
                    self.progress_var.set(min(95.0, self.progress_var.get() + 16.0))
                elif kind == "done":
                    self._log(payload)
                    self.status_var.set(payload)
                    self.progress_var.set(100.0)
                    self._set_busy(False)
                    messagebox.showinfo("SmartScreen Installer", payload)
                elif kind == "error":
                    self._log("ERROR: " + payload)
                    self.status_var.set("Failed")
                    self._set_busy(False)
                    messagebox.showerror("SmartScreen Installer", payload)
        except queue.Empty:
            pass

        self.root.after(120, self._drain_queue)


def main() -> int:
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    InstallerWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
