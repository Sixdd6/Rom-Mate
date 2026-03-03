import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from src.config import ConfigManager
from src.api import RomMClient
from src.watcher import WingosyWatcher
from src.ui import WingosyMainWindow, SetupDialog

VERSION = "0.2.1"

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # For system tray
    app.setStyle("Fusion")
    
    config = ConfigManager()
    
    # Check if we need to do first-time setup or re-auth
    if not config.get("token") or not config.get("password"):
        setup = SetupDialog(config)
        if setup.exec() == SetupDialog.Accepted:
            data = setup.get_data()
            config.set("host", data["host"])
            config.set("username", data["username"])
            config.set("password", data["password"])
        else:
            sys.exit(0)

    client = RomMClient(config.get("host"))
    
    # Attempt Login
    success, result = client.login(config.get("username"), config.get("password"))
    if success:
        config.set("token", result)
    else:
        QMessageBox.critical(None, "Login Failed", result)
        # Clear token to force setup next time
        config.set("token", None)
        sys.exit(1)

    window = WingosyMainWindow(config, client, WingosyWatcher, VERSION)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
