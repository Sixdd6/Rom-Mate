import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from src.ui.widgets import format_size

class ExePickerDialog(QDialog):
    def __init__(self, exes, game_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Choose Executable — {game_name}")
        self.setMinimumSize(600, 450)
        self.selected_exe = None
        self.setStyleSheet("QDialog { background-color: #1e1e1e; color: #ffffff; }")
        
        layout = QVBoxLayout(self)
        header = QLabel("Multiple executables found. Select one to launch:")
        header.setStyleSheet("font-size: 12pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #2b2b2b; color: #ffffff; border: 1px solid #555; font-size: 10pt; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #3a3a3a; }
            QListWidget::item:selected { background-color: #0d6efd; color: #ffffff; }
            QListWidget::item:hover { background-color: #3a3a3a; }
        """)
        
        for path in exes:
            try:
                size_str = format_size(os.path.getsize(path))
            except:
                size_str = "Unknown"
            item = QListWidgetItem(f"{os.path.basename(path)}\n({size_str}) — {path}")
            item.setData(Qt.UserRole, path)
            self.list_widget.addItem(item)
            
        layout.addWidget(self.list_widget)
        
        btns = QHBoxLayout()
        launch_btn = QPushButton("▶ Launch Selected")
        launch_btn.setStyleSheet("background: #2e7d32; color: white; font-weight: bold; padding: 10px; font-size: 11pt;")
        launch_btn.clicked.connect(self.accept_selection)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: #444; color: #eee; padding: 10px;")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(launch_btn)
        layout.addLayout(btns)
        
    def accept_selection(self):
        if self.list_widget.currentItem():
            self.selected_exe = self.list_widget.currentItem().data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select an executable.")
