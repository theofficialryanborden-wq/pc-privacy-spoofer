"""Graphical interface for PC Privacy Spoofer."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, Callable

from privacy_spoofer import __version__
from privacy_spoofer.admin import AdminRequiredError, is_admin, request_elevation
from privacy_spoofer import operations


class PrivacySpooferApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PC Privacy Spoofer")
        self.minsize(760, 560)
        self.geometry("900x640")

        self._work_queue: queue.Queue[tuple[Callable[[], Any], str]] = queue.Queue()
        self._admin = is_admin()

        self._build_styles()
        self._build_ui()
        self._poll_queue()
        self.after(100, self.refresh_status)

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9))
        style.configure("AdminOk.TLabel", foreground="#1a7f37")
        style.configure("AdminWarn.TLabel", foreground="#b54708")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(16, 12, 16, 8))
        header.pack(fill="x")

        title_row = ttk.Frame(header)
        title_row.pack(fill="x")

        ttk.Label(title_row, text="PC Privacy Spoofer", style="Title.TLabel").pack(side="left")
        ttk.Label(title_row, text=f"v{__version__}", style="Subtitle.TLabel").pack(side="left", padx=(10, 0))

        admin_style = "AdminOk.TLabel" if self._admin else "AdminWarn.TLabel"
        admin_text = "Administrator" if self._admin else "Not elevated — spoof/restore disabled"
        self._admin_label = ttk.Label(title_row, text=admin_text, style=admin_style)
        self._admin_label.pack(side="right")

        ttk.Label(
            header,
            text="email theofficialryanborden@gmail.com for issues or help",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        ttk.Label(
            header,
            text="Rotate common Windows identifiers for privacy. Original values are backed up before changes.",
            style="Subtitle.TLabel",
            wraplength=860,
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=16, pady=8)

        status_frame = ttk.Labelframe(body, text="Current identifiers", style="Section.TLabelframe", padding=8)
        actions_frame = ttk.Labelframe(body, text="Actions", style="Section.TLabelframe", padding=12)
        body.add(status_frame, weight=3)
        body.add(actions_frame, weight=2)

        self._status_text = scrolledtext.ScrolledText(
            status_frame,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
            height=20,
        )
        self._status_text.pack(fill="both", expand=True)

        refresh_btn = ttk.Button(status_frame, text="Refresh status", command=self.refresh_status)
        refresh_btn.pack(anchor="e", pady=(8, 0))

        self._var_mac = tk.BooleanVar(value=True)
        self._var_registry = tk.BooleanVar(value=True)
        self._var_computer_name = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            actions_frame,
            text="MAC addresses (network adapters)",
            variable=self._var_mac,
        ).pack(anchor="w", pady=4)
        ttk.Checkbutton(
            actions_frame,
            text="Registry IDs (MachineGuid, ProductId, etc.)",
            variable=self._var_registry,
        ).pack(anchor="w", pady=4)
        ttk.Checkbutton(
            actions_frame,
            text="Computer name (requires reboot)",
            variable=self._var_computer_name,
        ).pack(anchor="w", pady=4)

        btn_frame = ttk.Frame(actions_frame)
        btn_frame.pack(fill="x", pady=(16, 8))

        self._spoof_btn = ttk.Button(btn_frame, text="Spoof selected", command=self.spoof_selected)
        self._spoof_btn.pack(fill="x", pady=4)

        self._spoof_all_btn = ttk.Button(btn_frame, text="Spoof everything", command=self.spoof_all)
        self._spoof_all_btn.pack(fill="x", pady=4)

        self._restore_btn = ttk.Button(btn_frame, text="Restore from backup", command=self.restore_backup)
        self._restore_btn.pack(fill="x", pady=4)

        if not self._admin:
            elevate_btn = ttk.Button(btn_frame, text="Restart as Administrator", command=self._elevate)
            elevate_btn.pack(fill="x", pady=(12, 4))
            for widget in (self._spoof_btn, self._spoof_all_btn, self._restore_btn):
                widget.state(["disabled"])

        ttk.Separator(actions_frame, orient="horizontal").pack(fill="x", pady=12)
        ttk.Label(
            actions_frame,
            text="Backups are saved to:\n%USERPROFILE%\\.pc-privacy-spoofer\\backups\\latest.json",
            style="Subtitle.TLabel",
            wraplength=280,
            justify="left",
        ).pack(anchor="w")

        log_frame = ttk.Labelframe(self, text="Activity log", style="Section.TLabelframe", padding=8)
        log_frame.pack(fill="both", expand=False, padx=16, pady=(0, 16))

        self._log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
            height=8,
        )
        self._log_text.pack(fill="both", expand=True)

    def _elevate(self) -> None:
        if request_elevation():
            self.destroy()
        else:
            messagebox.showerror("Elevation failed", "Could not restart with administrator privileges.")

    def _log(self, message: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _set_status_display(self, text: str) -> None:
        self._status_text.configure(state="normal")
        self._status_text.delete("1.0", "end")
        self._status_text.insert("1.0", text)
        self._status_text.configure(state="disabled")

    def _run_async(self, fn: Callable[[], Any], label: str) -> None:
        self._log(f"Starting: {label}…")

        def worker() -> None:
            try:
                result = fn()
                self._work_queue.put((lambda: self._on_success(label, result), "success"))
            except AdminRequiredError as exc:
                self._work_queue.put((lambda: self._on_error(label, str(exc)), "error"))
            except FileNotFoundError as exc:
                self._work_queue.put((lambda: self._on_error(label, str(exc)), "error"))
            except Exception as exc:
                self._work_queue.put((lambda: self._on_error(label, str(exc)), "error"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, label: str, result: Any) -> None:
        self._log(f"Finished: {label}")
        if isinstance(result, operations.SpoofResult):
            self._log(f"Backup saved to: {result.backup_path}")
            self._log(json.dumps({"results": result.results}, indent=2))
            if result.reboot_recommended:
                messagebox.showwarning(
                    "Reboot recommended",
                    "Computer name was changed. Reboot Windows for the change to fully apply.",
                )
        elif isinstance(result, operations.RestoreResult):
            self._log(json.dumps({"results": result.results}, indent=2))
            if result.reboot_recommended:
                messagebox.showwarning(
                    "Reboot recommended",
                    "Computer name was restored. Reboot Windows for the change to fully apply.",
                )
        elif isinstance(result, dict):
            self._set_status_display(self._format_status(result))
        elif label not in ("Refresh status",):
            self.refresh_status()

    def _on_error(self, label: str, message: str) -> None:
        self._log(f"Failed: {label}")
        self._log(message)
        messagebox.showerror(label, message)

    def _poll_queue(self) -> None:
        try:
            while True:
                callback, _ = self._work_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _format_status(self, status: dict[str, Any]) -> str:
        lines: list[str] = []
        lines.append(f"Computer name: {status.get('computer_name', 'unknown')}")
        lines.append("")
        lines.append("Registry identifiers:")
        registry = status.get("registry") or {}
        if registry:
            for name, value in registry.items():
                lines.append(f"  {name}: {value}")
        else:
            lines.append("  (none found)")

        lines.append("")
        lines.append("Network adapters:")
        adapters = status.get("network_adapters") or []
        if adapters:
            for adapter in adapters:
                lines.append(f"  [{adapter.get('key')}] {adapter.get('description')}")
                lines.append(f"    MAC: {adapter.get('mac') or 'unknown'}")
                if adapter.get("spoofed_mac"):
                    lines.append(f"    Registry override: {adapter['spoofed_mac']}")
        else:
            lines.append("  (none found)")

        volumes = status.get("volumes") or []
        if volumes:
            lines.append("")
            lines.append("Volumes (read-only):")
            for volume in volumes:
                lines.append(
                    f"  {volume.get('drive')} {volume.get('label')}: {volume.get('unique_id')}"
                )

        return "\n".join(lines)

    def refresh_status(self) -> None:
        self._run_async(operations.get_status, "Refresh status")

    def spoof_selected(self) -> None:
        if not any((self._var_mac.get(), self._var_registry.get(), self._var_computer_name.get())):
            messagebox.showwarning("Nothing selected", "Select at least one identifier type to spoof.")
            return

        if self._var_computer_name.get() and not messagebox.askyesno(
            "Computer name",
            "Changing the computer name requires a reboot. Continue?",
        ):
            return

        if not messagebox.askyesno(
            "Confirm spoof",
            "This will change the selected identifiers and save a backup of the originals. Continue?",
        ):
            return

        def action() -> operations.SpoofResult:
            return operations.run_spoof(
                spoof_mac=self._var_mac.get(),
                spoof_registry=self._var_registry.get(),
                spoof_computer_name=self._var_computer_name.get(),
            )

        self._run_async(action, "Spoof selected")

    def spoof_all(self) -> None:
        if not messagebox.askyesno(
            "Confirm spoof all",
            "This will spoof MAC addresses, registry IDs, and the computer name.\n"
            "A reboot will be required for the computer name change.\n\nContinue?",
        ):
            return

        self._run_async(lambda: operations.run_spoof(spoof_all=True), "Spoof everything")

    def restore_backup(self) -> None:
        if not messagebox.askyesno(
            "Confirm restore",
            "Restore all identifiers from the latest backup?",
        ):
            return

        self._run_async(lambda: operations.run_restore(), "Restore from backup")


def main() -> None:
    app = PrivacySpooferApp()
    app.mainloop()


if __name__ == "__main__":
    main()
