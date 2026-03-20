import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PySide6.QtCore import Qt, Signal, QTimer
from src.platforms import RETROARCH_PLATFORMS, RETROARCH_CORES, platform_matches
from src import download_registry

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = Path(__file__).resolve().parents[2]
    return os.fspath(Path(base_path) / relative_path)

def format_speed(bps):
    if bps <= 0:
        return ""
    if bps >= 1024 * 1024 * 1024:
        return f"{bps/(1024**3):.1f} GB/s"
    if bps >= 1024 * 1024:
        return f"{bps/(1024**2):.1f} MB/s"
    if bps >= 1024:
        return f"{bps/1024:.1f} KB/s"
    return f"{bps:.0f} B/s"

def format_size(bytes_count):
    if bytes_count > 1024*1024*1024:
        return f"{bytes_count/(1024*1024*1024):.2f} GB"
    return f"{bytes_count/(1024*1024):.1f} MB"

def elide_text(text, max_chars=24):
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + "…"

_CANCELLED_AUTO_REMOVE_MS = 7000

class DownloadRow(QWidget):
    def __init__(self, rom_id, rom_name, thread, row_type, parent_queue):
        super().__init__()
        self.rom_id = str(rom_id)
        self.rom_name = rom_name
        self.thread = thread
        self.row_type = row_type # "download" | "extraction"
        self.parent_queue = parent_queue
        self._pending_registry_update = None
        self._smoothed_speed = 0.0
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(100)
        self._flush_timer.timeout.connect(self._flush_pending_update)
        
        self.setStyleSheet("""
            DownloadRow {
                background: #242424;
                border: 1px solid #333;
                border-radius: 6px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(6)

        # Top row: Name and Status Badge
        top_layout = QHBoxLayout()
        self.name_label = QLabel(rom_name)
        self.name_label.setStyleSheet("font-weight: bold; color: white; border: none;")
        top_layout.addWidget(self.name_label, 1)

        status_text = "Extracting" if row_type == "extraction" else row_type.capitalize() + "ing"
        self.status_badge = QLabel(status_text)
        self.status_badge.setContentsMargins(8, 2, 8, 2)
        self._update_badge_style("progress")
        top_layout.addWidget(self.status_badge)
        main_layout.addLayout(top_layout)

        # Progress row
        progress_layout = QHBoxLayout()
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        pbar_chunk_color = "#e65100" if row_type == "extraction" else "#0d6efd"
        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background: #2d2d2d;
                height: 6px;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background: {pbar_chunk_color};
            }}
        """)
        progress_layout.addWidget(self.pbar, 1)

        self.pct_label = QLabel("0%")
        self.pct_label.setFixedWidth(35)
        self.pct_label.setStyleSheet("color: #aaa; font-size: 11px; border: none;")
        progress_layout.addWidget(self.pct_label)

        self.size_label = QLabel("0 / 0 MB")
        self.size_label.setFixedWidth(120)
        self.size_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.size_label.setStyleSheet("color: #aaa; font-size: 11px; border: none;")
        progress_layout.addWidget(self.size_label)
        main_layout.addLayout(progress_layout)

        # Bottom row: Speed and Cancel Button
        bottom_layout = QHBoxLayout()
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #0d6efd; font-size: 10px; font-weight: bold; border: none;")
        bottom_layout.addWidget(self.speed_label)
        
        bottom_layout.addStretch()
        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setFixedWidth(80)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #f44336;
                border: 1px solid #f44336;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #f44336;
                color: white;
            }
        """)
        self.cancel_btn.clicked.connect(self.request_cancel)
        bottom_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(bottom_layout)

        # Connect to registry for updates
        download_registry.add_listener(self.rom_id, self.on_registry_update)

    def reset_for_new_thread(self, thread, row_type):
        self.thread = thread
        self.row_type = row_type
        self._pending_registry_update = None
        self._smoothed_speed = 0.0
        if self._flush_timer.isActive():
            self._flush_timer.stop()
        self.status_badge.setText("Extracting" if row_type == "extraction" else "Downloading")
        self._update_badge_style("progress")
        self.cancel_btn.show()
        self.speed_label.setText("")
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self.pct_label.setText("0%")
        self.size_label.setText("0 / 0 MB")

    def _update_badge_style(self, status):
        colors = {
            "progress": "#1565c0" if self.row_type == "download" else "#e65100",
            "done": "#2e7d32",
            "cancelled": "#555555",
            "error": "#b71c1c"
        }
        color = colors.get(status, "#555")
        self.status_badge.setStyleSheet(f"""
            background: {color};
            color: white;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
        """)

    def on_registry_update(self, rom_id, rtype, current, total, speed=0):
        if rtype in ("done", "cancelled"):
            if self._flush_timer.isActive():
                self._flush_timer.stop()
            self._pending_registry_update = None
            self._apply_registry_update(rom_id, rtype, current, total, speed)
            return

        self._pending_registry_update = (rom_id, rtype, current, total, speed)
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush_pending_update(self):
        if not self._pending_registry_update:
            self._flush_timer.stop()
            return
        rom_id, rtype, current, total, speed = self._pending_registry_update
        self._pending_registry_update = None
        self._apply_registry_update(rom_id, rtype, current, total, speed)

    def _apply_registry_update(self, rom_id, rtype, current, total, speed=0):
        if rtype == "extraction":
            if self.status_badge.text() != "Extracting":
                self.status_badge.setText("Extracting")
                self.row_type = "extraction"
                self._update_badge_style("progress")
                # Update progress bar color for extraction
                self.pbar.setStyleSheet(self.pbar.styleSheet().replace("#0d6efd", "#e65100"))
            self._on_extraction_progress(current, total)
            return

        # Normal download progress/update (also covers the initial update after a restart)
        if rtype == "download":
            if self.status_badge.text() != "Downloading":
                self.status_badge.setText("Downloading")
                self.row_type = "download"
                self._update_badge_style("progress")
                self.cancel_btn.show()

        if total > 0:
            pct = int(current / total * 100)
            self.pbar.setValue(pct)
            self.pct_label.setText(f"{pct}%")
            self.size_label.setText(f"{format_size(current)} / {format_size(total)}")

        if speed > 0:
            alpha = 0.2
            if self._smoothed_speed <= 0:
                self._smoothed_speed = float(speed)
            else:
                self._smoothed_speed = (alpha * float(speed)) + ((1.0 - alpha) * self._smoothed_speed)
        if self._smoothed_speed > 0 and self.row_type == "download":
            self.speed_label.setText(format_speed(self._smoothed_speed))
        
        if rtype == "done":
            self.status_badge.setText("Done")
            self._update_badge_style("done")
            self.cancel_btn.hide()
            self.speed_label.setText("")
            QTimer.singleShot(5000, lambda: self.parent_queue.remove_download(self.thread))
        elif rtype == "cancelled":
            self.status_badge.setText("Cancelled")
            self._update_badge_style("cancelled")
            self.cancel_btn.hide()
            self.speed_label.setText("")
            QTimer.singleShot(_CANCELLED_AUTO_REMOVE_MS, lambda: self.parent_queue.remove_download(self.thread))

    def _on_extraction_progress(self, done, total):
        if total == 0 and done == 0:
            self.pbar.setRange(0, 0)
            self.size_label.setText("Extracting...")
            return
        
        self.pbar.setRange(0, 100)
        if total == 100: # 7z percentage mode
            self.pbar.setValue(done)
            self.pct_label.setText(f"{done}%")
            self.size_label.setText(f"{done}%")
        else: # zip file count mode
            pct = int(done / total * 100) if total > 0 else 0
            self.pbar.setValue(pct)
            self.pct_label.setText(f"{pct}%")
            self.size_label.setText(f"{done} / {total} files")

    def request_cancel(self):
        # Immediately cancel without prompting (save/discard/cancel is not supported)
        self.thread.cancel()

        # Update status in registry (thread will handle unregistering)
        download_registry.update_status(self.rom_id, "cancelled")

        self.status_badge.setText("Cancelled")
        self._update_badge_style("cancelled")
        self.cancel_btn.hide()
        self.speed_label.setText("")

    def closeEvent(self, event):
        download_registry.remove_listener(self.rom_id, self.on_registry_update)
        super().closeEvent(event)

class DownloadQueueWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignTop)
        self._rows_by_thread = {} # thread: row_widget
        self._rows_by_rom_id = {} # rom_id: row_widget

    def refresh_from_registry(self):
        for rom_id, entry in download_registry.all().items():
            if str(rom_id) not in self._rows_by_rom_id:
                self.add_download(entry["rom_name"], entry["thread"], entry["type"], rom_id)

    def add_download(self, name, thread, row_type="download", rom_id=None):
        rom_id_str = str(rom_id) if rom_id is not None else None

        if rom_id_str and rom_id_str in self._rows_by_rom_id:
            row = self._rows_by_rom_id[rom_id_str]
            old_thread = getattr(row, "thread", None)

            # If a cancelled row is already present for this rom, clear it immediately and
            # create a fresh row so the UI doesn't stay stuck in the cancelled state.
            if getattr(row, "status_badge", None) and row.status_badge.text() == "Cancelled":
                if old_thread is not None:
                    self.remove_download(old_thread)
                # Proceed as a normal new row
                rom_id_str = str(rom_id) if rom_id is not None else None
            else:
                if old_thread in self._rows_by_thread:
                    del self._rows_by_thread[old_thread]

                row.reset_for_new_thread(thread, row_type)
                self._rows_by_thread[thread] = row

                entry = download_registry.get(rom_id_str)
                if entry:
                    current, total = entry.get("progress", (0, 0))
                    try:
                        row.on_registry_update(rom_id_str, entry.get("type", row_type), current, total, 0)
                    except TypeError:
                        row.on_registry_update(rom_id_str, entry.get("type", row_type), current, total)
                return

        if thread in self._rows_by_thread:
            return

        row = DownloadRow(rom_id, name, thread, row_type, self)
        self.layout.addWidget(row)
        self._rows_by_thread[thread] = row
        if rom_id_str:
            self._rows_by_rom_id[rom_id_str] = row

    def remove_download(self, thread):
        if thread in self._rows_by_thread:
            row_widget = self._rows_by_thread[thread]
            self.layout.removeWidget(row_widget)
            row_widget.deleteLater()
            del self._rows_by_thread[thread]
            rom_id_str = getattr(row_widget, "rom_id", None)
            if rom_id_str and self._rows_by_rom_id.get(str(rom_id_str)) is row_widget:
                del self._rows_by_rom_id[str(rom_id_str)]
