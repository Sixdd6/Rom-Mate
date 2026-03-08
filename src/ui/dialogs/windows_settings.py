import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QDialogButtonBox, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QTimer
from src import windows_saves

EXCLUDED_EXES = [
    "unins000.exe", "uninstall.exe", "setup.exe",
    "vcredist", "directx", "dxsetup.exe",
    "vc_redist", "crashpad_handler.exe",
    "notification_helper.exe", "UnityCrashHandler",
    "dotnet", "netfx", "oalinst.exe",
    "DXSETUP.exe", "installscript",
    "dx_setup", "redist"
]

class WindowsGameSettingsDialog(QDialog):
    def __init__(self, game, config, main_window, parent=None):
        super().__init__(parent)
        self.game = game
        self.config = config
        self.main_window = main_window
        self.setWindowTitle(f"Game Settings — {game.get('name')}")
        self.resize(550, 500)
        
        saved = windows_saves.get_windows_save(game['id']) or {"name": game.get('name')}
        self.default_exe = saved.get("default_exe")
        self.save_dir = saved.get("save_dir")
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Default Executable</h3><p>Choose which .exe to launch by default.</p>"))
        
        self.exe_status = QLabel()
        self.exe_status.setStyleSheet("color: #aaa;")
        layout.addWidget(self.exe_status)
        
        eb = QHBoxLayout()
        ab = QPushButton("🔍 Auto-detect")
        ab.clicked.connect(self.auto_detect_exe)
        eb.addWidget(ab)
        bb = QPushButton("📁 Browse")
        bb.clicked.connect(self.browse_exe)
        eb.addWidget(bb)
        layout.addLayout(eb)
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("<h3>Save Directory</h3><p>Where does this game store its saves?</p>"))
        self.save_status = QLabel()
        self.save_status.setStyleSheet("color: #aaa;")
        layout.addWidget(self.save_status)
        
        sb = QHBoxLayout()
        wb = QPushButton("🌐 PCGamingWiki Suggestions")
        wb.setVisible(self.config.get("pcgamingwiki_enabled", True))
        wb.clicked.connect(self.get_wiki_suggestions)
        sb.addWidget(wb)
        mb = QPushButton("📁 Browse Manually")
        mb.clicked.connect(self.browse_save_dir)
        sb.addWidget(mb)
        layout.addLayout(sb)
        
        self.sync_status = QLabel()
        self.sync_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.sync_status)
        layout.addStretch()
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.accepted.connect(self.save_and_close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.update_ui()
        
    def update_ui(self):
        if self.default_exe:
            self.exe_status.setText(f"<b>{os.path.basename(self.default_exe)}</b><br><small>{self.default_exe}</small>")
        else:
            self.exe_status.setText("No default set")
            
        self.save_status.setText(self.save_dir or "Not configured")
        
        if self.save_dir and os.path.exists(self.save_dir):
            self.sync_status.setText("<span style='color: #4caf50;'>✅ Cloud sync active</span>")
        elif self.save_dir:
            self.sync_status.setText("<span style='color: #ff5252;'>⚠️ Folder does not exist</span>")
        else:
            self.sync_status.setText("")
            
    def auto_detect_exe(self):
        rom = self.game.get('fs_name')
        win_dir = self.config.get("windows_games_dir")
        if not rom or not win_dir:
            return
            
        folder = Path(win_dir) / Path(rom).stem
        if not folder.exists():
            return
            
        exes = [str(p) for p in folder.rglob("*.exe") if not any(ex.lower() in str(p).lower() for e in EXCLUDED_EXES)]
        if not exes:
            QMessageBox.information(self, "No EXEs", "None found.")
            return
            
        if len(exes) == 1:
            self.default_exe = exes[0]
            self.update_ui()
        else:
            from src.ui.dialogs.emulator_editor import ExePickerDialog
            p = ExePickerDialog(exes, self.game.get("name"), self)
            if p.exec() == QDialog.Accepted:
                self.default_exe = p.selected_exe
                self.update_ui()
                
    def browse_exe(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Executable", "", "Executables (*.exe)")
        if p:
            self.default_exe = p
            self.update_ui()
            
    def get_wiki_suggestions(self):
        self.loading_dlg = QMessageBox(self)
        self.loading_dlg.setWindowTitle("Fetching")
        self.loading_dlg.setText("Querying PCGamingWiki...")
        self.loading_dlg.show()
        
        from src.ui.dialogs.save_sync import WikiFetchWorker
        self.wiki_worker = WikiFetchWorker(self.game.get("name"), self.config.get("windows_games_dir", ""))
        self.wiki_worker.results_ready.connect(self.on_wiki_results)
        self.wiki_worker.failed.connect(lambda: (self.loading_dlg.close(), QMessageBox.warning(self, "Error", "Failed.")))
        
        self.wiki_timeout = QTimer()
        self.wiki_timeout.setSingleShot(True)
        self.wiki_timeout.timeout.connect(lambda: (self.wiki_worker.terminate(), self.loading_dlg.close()))
        self.wiki_timeout.start(3000)
        self.wiki_worker.start()
        
    def on_wiki_results(self, res):
        if self.wiki_timeout: self.wiki_timeout.stop()
        self.loading_dlg.close()
        
        if not res:
            QMessageBox.information(self, "No Suggestions", "None found.")
            return
            
        from src.ui.dialogs.save_sync import WikiSuggestionsDialog
        d = WikiSuggestionsDialog(res, self.game.get("name"), self)
        if d.exec() == QDialog.Accepted:
            self.save_dir = d.selected_path
            self.update_ui()
            
    def browse_save_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if directory:
            self.save_dir = directory
            self.update_ui()
            
    def save_and_close(self):
        windows_saves.set_windows_save(self.game['id'], self.game['name'], self.save_dir, self.default_exe)
        self.accept()
