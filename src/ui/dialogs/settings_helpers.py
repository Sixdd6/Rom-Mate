import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox)
from PySide6.QtCore import Qt

class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Wingosy Launcher")
        self.resize(500, 350)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<h1>Welcome to Wingosy!</h1>"))
        info = QLabel("<p style='font-size: 12pt;'>Your setup is almost complete. Follow the tabs to get started.</p>")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        
        btn = QPushButton("Get Started")
        btn.setStyleSheet("background: #1e88e5; color: white; padding: 10px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class SetupDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wingosy Setup")
        self.config = config_manager
        self.resize(400, 200)
        layout = QFormLayout(self)
        
        self.host_input = QLineEdit(self.config.get("host"))
        self.user_input = QLineEdit(self.config.get("username"))
        self.pass_input = QLineEdit("")
        self.pass_input.setEchoMode(QLineEdit.Password)
        
        layout.addRow("RomM Host:", self.host_input)
        layout.addRow("Username:", self.user_input)
        layout.addRow("Password:", self.pass_input)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)
        
    def validate_and_accept(self):
        if not re.match(r'^https?://.+', self.host_input.text().strip()):
            QMessageBox.warning(self, "Invalid Host", "Enter a valid URL.")
            return
        self.accept()
        
    def get_data(self):
        return {
            "host": self.host_input.text().strip().rstrip('/'),
            "username": self.user_input.text().strip(),
            "password": self.pass_input.text()
        }
