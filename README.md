# Wingosy Launcher

![Wingosy Example](@Wingosy_example.png)

A Windows port of the original [Argosy Launcher for Android](https://github.com/rommapp/argosy-launcher).

**Wingosy** is a lightweight, portable Windows game launcher designed to bridge the gap between your local emulators and a **RomM** server. It features automated cloud save syncing, portable emulator management, and a unified library interface.

## Key Features

- **Cloud Save Syncing**: Automatically pulls your latest saves from RomM before you play and pushes changes back to the cloud as soon as you close the emulator.
- **Universal PLAY Button**: One-click to sync, launch, and track your games across PCSX2, Dolphin, Yuzu/Eden, RetroArch, and more.
- **Portable Emulator Management**: Download and manage the latest versions of your favorite emulators directly through the app. Supports "Portable Mode" automatically.
- **BIOS / Firmware Rescue**: Search and download required BIOS files directly from your RomM library or firmware index.
- **Library Search & Filtering**: Instantly find games by name or console platform.

## Getting Started

1.  **Download**: Grab the latest `Wingosy.exe` from the [Releases](https://github.com/abduznik/Wingosy-Launcher/releases) page.
2.  **Setup**: On the first run, enter your RomM host URL and credentials.
3.  **Configure Paths**:
    -   Go to the **Emulators** tab.
    -   Set your **ROM Path** (where your games are stored).
    -   Set your **Emu Path** (where you want emulators to be installed).
4.  **Sync & Play**: Click on any game in your library and hit **▶ PLAY**. Wingosy v0.4.0 handles the rest!

## Supported Emulators

Note: PlayStation 2, Nintendo Switch, and GameCube/Wii have been fully tested and verified as stable.

- **PlayStation 2**: PCSX2 (Qt) - Tested
- **Nintendo Switch**: Yuzu / Eden / Ryujinx - Tested
- **GameCube / Wii**: Dolphin - Tested
- **Multi-system**: RetroArch - Tested
- **And more...** (easily extensible via `config.json`)

## Roadmap

### Current Status (v0.4.0)
- ✅ Tested and Stable: PlayStation 2 (PCSX2), Nintendo Switch (Yuzu/Eden), Dolphin, RetroArch
- ✅ Auto-updating: downloads and replaces Wingosy.exe in place, no browser needed
- ✅ Save conflict resolution: choose between cloud, local, or keep both
- ✅ RetroArch core auto-download for missing cores
- ✅ System tray notifications for sync events
- ✅ Download queue panel with progress and cancel
- ✅ Game state indicators on library cards (local ROM, cloud save)
- ✅ Emulator health indicators (green/red/grey dot per emulator)
- ✅ Library refresh button and F5 shortcut
- ✅ First-run welcome screen
- ✅ Connection test in Settings
- ✅ Window size and position remembered between sessions
- ✅ Keyboard shortcuts (Ctrl+F to search, F5 to refresh)
- ✅ About dialog

### Planned for v0.5.0
- RPCS3 (PS3) and Citra (3DS) save path resolution
- RetroArch intelligence: auto-select core based on RomM platform metadata
- Detailed game view with screenshots and metadata from RomM
- Custom emulator profiles via UI
- System Tray: minimize to tray on close option

## Building from Source

If you want to run or build Wingosy manually:

```powershell
# Install dependencies
pip install PySide6 psutil requests py7zr Pillow

# Run the app
python main.py

# Build .exe with icon
pip install pyinstaller
pyinstaller --noconsole --onefile --name Wingosy --icon "icon.png" --add-data "icon.png;." --hidden-import sqlite3 --hidden-import src.ui --hidden-import src.ui.main_window --hidden-import src.ui.dialogs --hidden-import src.ui.threads --hidden-import src.ui.widgets --hidden-import src.ui.tabs --hidden-import src.ui.tabs.library --hidden-import src.ui.tabs.emulators main.py
```

## Changelog

### v0.4.0
- Auto-updating exe with in-place replacement and restart prompt
- Save conflict resolution dialog (Use Cloud / Keep Local / Keep Both)
- RetroArch core auto-download from libretro buildbot when core is missing
- RetroArch fallback for platforms without a dedicated emulator (N64, PSX, SNES, GBA, etc.)
- System tray notifications for sync success, failure, and cloud save applied
- Download queue panel showing active downloads with progress and cancel buttons
- Game state indicators on library cards: green dot for local ROM, blue dot for cloud save
- Emulator health indicators: green/red/grey status per emulator row
- Library refresh button and F5 keyboard shortcut
- Ctrl+F keyboard shortcut to focus search
- First-run welcome dialog explaining setup steps
- Connection test button in Settings
- Window geometry saved and restored between sessions
- About dialog in Settings
- Logout confirmation dialog
- URL validation in setup dialog
- UI refactored from single 1000+ line file into maintainable package structure
- Save temp files now go to ~/.wingosy/tmp/ instead of current working directory
- Fixed: simultaneous game launches no longer corrupt each other's temp files
- Fixed: image fetch queue properly cancels on library filter change
- Fixed: track_session no longer blocks the UI thread on PLAY
- Fixed: Switch title ID resolution via SQLite cache, XCI header, and recency scan

### v0.3.1
- Fixed Switch save path resolution for Eden and Yuzu
- Dynamic title ID resolution replacing hardcoded dictionary
- Multi-method fallback: SQLite cache, XCI header, recency scan, regex
- Expanded search roots for yuzu, eden, sudachi, torzu

### v0.3.0
- Initial Windows release
- Cloud save sync with RomM
- Portable emulator management
- BIOS/firmware download
- Process-specific game tracking

## License

GNU General Public License v3.0. See `LICENSE` for details.
