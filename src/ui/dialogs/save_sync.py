import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QScrollArea, QWidget, QFileDialog)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFontMetrics

class ConflictDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Save Conflict: {title}")
        self.resize(450, 200)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Conflict found for <b>{title}</b>. Which save would you like to use?"))
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.result_mode = None
        
        for mode, text in [("cloud", "☁️ Use Cloud"), ("local", "💾 Keep Local"), ("both", "📁 Keep Both")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, m=mode: self.finish(m))
            btn_layout.addWidget(btn)
            
        layout.addLayout(btn_layout)
        
    def finish(self, mode):
        self.result_mode = mode
        self.accept()

class WikiSuggestionsDialog(QDialog):
    def __init__(self, suggestions, game_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Save Location Suggestions — {game_name}")
        self.setFixedSize(680, 350)
        self.selected_path = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        layout.addWidget(QLabel(f"<b>Found {len(suggestions)} possible save locations from PCGamingWiki:</b>"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: #1a1a1a; border: 1px solid #333;")
        
        container = QWidget()
        list_layout = QVBoxLayout(container)
        list_layout.setContentsMargins(2, 2, 2, 2)
        list_layout.setSpacing(2)
        list_layout.setAlignment(Qt.AlignTop)
        
        metrics = QFontMetrics(self.font())
        
        for item in suggestions:
            row = QWidget()
            row.setFixedHeight(36)
            row.setStyleSheet("background: #252525; border-radius: 3px;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(4, 0, 4, 0)
            rl.setSpacing(4)
            
            badge = QLabel(item["path_type"])
            color = "#2e7d32" if item["exists"] else "#555"
            badge.setFixedWidth(130)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(f"background: {color}; color: white; border-radius: 2px; font-size: 10px; font-weight: bold; padding: 2px;")
            rl.addWidget(badge)
            
            p_val = item['expanded_path']
            elided = metrics.elidedText(p_val, Qt.ElideMiddle, 380)
            lbl = QLabel(elided)
            lbl.setToolTip(p_val)
            lbl.setStyleSheet("font-size: 10px; color: #ddd;")
            rl.addWidget(lbl, 1)
            
            btn = QPushButton("📁 Browse Here")
            btn.setFixedWidth(100)
            btn.setStyleSheet("font-size: 10px; padding: 4px 8px; background: #444;")
            btn.clicked.connect(lambda checked, p=p_val: self.browse_and_confirm(p))
            rl.addWidget(btn)
            
            list_layout.addWidget(row)
            
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet("padding: 6px;")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)
        
    def browse_and_confirm(self, start_path):
        p = Path(start_path)
        while not p.exists() and p.parent != p:
            p = p.parent
        directory = QFileDialog.getExistingDirectory(self, "Select Save Folder", str(p))
        if directory:
            if QMessageBox.question(self, "Confirm", f"Use this folder?\n{directory}") == QMessageBox.Yes:
                self.selected_path = directory
                self.accept()

class WikiFetchWorker(QThread):
    results_ready = Signal(list)
    failed = Signal()
    
    def __init__(self, game_title, windows_games_dir):
        super().__init__()
        self.game_title = game_title
        self.windows_games_dir = windows_games_dir
        
    def run(self):
        try:
            from src.pcgamingwiki import fetch_save_locations
            self.results_ready.emit(fetch_save_locations(self.game_title, self.windows_games_dir))
        except Exception:
            self.failed.emit()

class SaveSyncSetupDialog(QDialog):
    def __init__(self, game_name, config, main_window, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Up Save Sync")
        self.game_name = game_name
        self.config = config
        self.main_window = main_window
        self.selected_path = None
        self.setFixedSize(450, 250)
        
        layout = QVBoxLayout(self)
        msg = QLabel(f"Where does <b>{game_name}</b> save its files?<br><br>Setting this up enables automatic cloud backup.")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)
        layout.addStretch()
        
        self.btn_wiki = QPushButton("🌐 Get PCGamingWiki Suggestions")
        self.btn_wiki.setStyleSheet("padding: 10px; background: #1565c0; color: white; font-weight: bold;")
        self.btn_wiki.setVisible(self.config.get("pcgamingwiki_enabled", True))
        self.btn_wiki.clicked.connect(self.get_suggestions)
        layout.addWidget(self.btn_wiki)
        
        btn_man = QPushButton("📁 Browse Manually")
        btn_man.clicked.connect(self.browse_manually)
        layout.addWidget(btn_man)
        
        btn_skip = QPushButton("▶ Skip for Now")
        btn_skip.clicked.connect(self.reject)
        layout.addWidget(btn_skip)
        
    def get_suggestions(self):
        self.loading_dlg = QMessageBox(self)
        self.loading_dlg.setWindowTitle("Fetching")
        self.loading_dlg.setText("Querying PCGamingWiki...")
        self.loading_dlg.show()
        
        self.btn_wiki.setEnabled(False)
        self.wiki_worker = WikiFetchWorker(self.game_name, self.config.get("windows_games_dir", ""))
        self.wiki_worker.results_ready.connect(self.on_wiki_results)
        self.wiki_worker.failed.connect(self.on_wiki_failed)
        
        self.wiki_timeout = QTimer()
        self.wiki_timeout.setSingleShot(True)
        self.wiki_timeout.timeout.connect(self.on_wiki_timeout)
        self.wiki_timeout.start(3000)
        self.wiki_worker.start()
        
    def on_wiki_timeout(self):
        if self.wiki_worker and self.wiki_worker.isRunning():
            self.wiki_worker.terminate()
            self.on_wiki_failed()
            
    def on_wiki_results(self, res):
        if self.wiki_timeout: self.wiki_timeout.stop()
        self.loading_dlg.close()
        self.btn_wiki.setEnabled(True)
        
        if not res:
            QMessageBox.information(self, "No Suggestions", "None found. Browse manually.")
            self.browse_manually()
            return
            
        QTimer.singleShot(100, lambda: self._show_suggestions(res))
        
    def _show_suggestions(self, res):
        d = WikiSuggestionsDialog(res, self.game_name, self)
        if d.exec() == QDialog.Accepted:
            self.selected_path = d.selected_path
            self.accept()
            
    def on_wiki_failed(self):
        if self.wiki_timeout: self.wiki_timeout.stop()
        self.loading_dlg.close()
        self.btn_wiki.setEnabled(True)
        QMessageBox.warning(self, "Error", "Failed to reach wiki.")
        
    def browse_manually(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if directory:
            self.selected_path = directory
            self.accept()
