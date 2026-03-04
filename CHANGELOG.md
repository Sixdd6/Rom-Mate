# Wingosy Launcher Changelog

All notable changes to this project will be documented here.

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
