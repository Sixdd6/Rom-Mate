"""
Save Strategy Pattern for Wingosy.

To add a new save mode:
1. Create a class inheriting SaveStrategy
2. Set mode_id = "your_mode_name"
3. Implement get_save_files() and restore_save_files()
4. Register it in STRATEGY_REGISTRY

That's it — no other files need changing.
"""

import os
import logging
import shutil
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class SaveStrategy(ABC):
    """
    Base class for all save strategies.
    Each strategy knows how to:
    - Find local save files for a ROM
    - Restore downloaded saves to the correct location
    """
    
    # Override in subclass
    mode_id: str = ""
    
    def __init__(self, config: dict, emulator: dict):
        self.config   = config
        self.emulator = emulator
    
    @abstractmethod
    def get_save_files(self, rom: dict) -> list[Path]:
        """
        Return list of local save file Paths for this ROM.
        Empty list = no saves.
        """
        ...
    
    @abstractmethod
    def restore_save_files(self, rom: dict, save_data: bytes, filename: str) -> bool:
        """
        Write save_data to the correct local path.
        Return True on success.
        """
        ...
    
    def get_save_dir(self, rom: dict) -> Optional[Path]:
        """
        Optional: return the save directory for this ROM if applicable.
        Override if needed.
        """
        return None
    
    def _get_retroarch_save_dir(self) -> Optional[Path]:
        """Helper for RetroArch strategies."""
        # Use config_path from emulator if present
        ra_cfg = self.emulator.get("config_path", "")
        if not ra_cfg:
            # Fallback to config manager's path if we had it
            ra_cfg = self.config.get("retroarch_config", "")
            
        if not ra_cfg or not Path(ra_cfg).exists():
            return None
        try:
            with open(ra_cfg, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("savefile_directory"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            d = parts[1].strip().strip('"')
                            if d and d != "default":
                                return Path(d)
        except Exception as e:
            logging.warning(f"[Strategy] RA cfg read error: {e}")
        return None


class RetroArchStrategy(SaveStrategy):
    """
    Handles RetroArch .srm save files.
    Looks in the RetroArch savefile_directory from retroarch.cfg,
    falling back to the ROM directory.
    """
    mode_id = "retroarch"
    
    def get_save_files(self, rom: dict) -> list[Path]:
        save_dir = self._get_retroarch_save_dir()
        rom_name = Path(rom.get("fs_name") or rom.get("file_name", "")).stem
        
        if not rom_name:
            return []
        
        candidates = []
        
        # Priority 1: RetroArch configured save dir
        if save_dir and save_dir.exists():
            # Check for subfolders (RA often uses core-named subfolders)
            # This logic might need more nuance based on core, but starting simple
            for p in save_dir.rglob(f"{rom_name}.srm"):
                candidates.append(p)
            for p in save_dir.rglob(f"{rom_name}.sav"):
                candidates.append(p)
            for p in save_dir.rglob(f"{rom_name}.state*"):
                candidates.append(p)
        
        # Priority 2: Alongside ROM (fallback)
        if not candidates:
            # We don't necessarily know ROM dir here easily without more context,
            # but usually RA uses its saves folder.
            pass
            
        return candidates
    
    def restore_save_files(self, rom: dict, save_data: bytes, filename: str) -> bool:
        save_dir = self._get_retroarch_save_dir()
        rom_name = Path(rom.get("fs_name") or rom.get("file_name", "")).stem
        
        if not rom_name:
            return False
        
        dest_dir = save_dir
        if not dest_dir:
            # Last resort fallback if no RA dir found
            return False
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Use server filename if valid, else derive from ROM name
        dest_name = filename if filename.endswith((".srm", ".sav")) else f"{rom_name}.srm"
        
        # If it's a state, keep original filename
        if ".state" in filename:
            dest_name = filename

        dest = dest_dir / dest_name
        try:
            dest.write_bytes(save_data)
            logging.info(f"[RetroArchStrategy] Restored: {dest}")
            return True
        except Exception as e:
            logging.error(f"[RetroArchStrategy] Write failed: {e}")
            return False
    
    def get_save_dir(self, rom: dict) -> Optional[Path]:
        return self._get_retroarch_save_dir()


class FolderStrategy(SaveStrategy):
    """
    Handles emulators that store saves in a dedicated folder per game
    or per emulator (e.g. Dolphin, RPCS3, Yuzu-style).
    
    Save dir is taken from emulator["save_resolution"]["path"] or ["save_dir"]
    """
    mode_id = "folder"
    
    def _base_dir(self, rom: dict) -> Optional[Path]:
        res = self.emulator.get("save_resolution", {})
        save_dir = res.get("path") or res.get("save_dir") or res.get("srm_dir")
        if not save_dir:
            return None
        return Path(save_dir)
    
    def get_save_files(self, rom: dict) -> list[Path]:
        base = self._base_dir(rom)
        if not base or not base.exists():
            return []
        
        # Collect all files recursively
        return [p for p in base.rglob("*") if p.is_file()]
    
    def restore_save_files(self, rom: dict, save_data: bytes, filename: str) -> bool:
        base = self._base_dir(rom)
        if not base:
            return False
        
        base.mkdir(parents=True, exist_ok=True)
        dest = base / filename
        try:
            dest.write_bytes(save_data)
            logging.info(f"[FolderStrategy] Restored: {dest}")
            return True
        except Exception as e:
            logging.error(f"[FolderStrategy] Write failed: {e}")
            return False
    
    def get_save_dir(self, rom: dict) -> Optional[Path]:
        return self._base_dir(rom)


class FileStrategy(SaveStrategy):
    """
    Handles emulators that use a single save file per ROM, 
    stored alongside the ROM file or in a configured path.
    """
    mode_id = "file"
    mode_id_alt = "direct_file" # Alias for older configs
    
    def _save_path(self, rom: dict) -> Optional[Path]:
        res = self.emulator.get("save_resolution", {})
        save_dir = res.get("path") or res.get("save_dir") or res.get("srm_dir")
        
        rom_name = Path(rom.get("fs_name") or rom.get("file_name", "")).stem
        if not rom_name:
            return None
        
        if save_dir:
            base = Path(save_dir)
        else:
            # Fallback: same dir as ROM if we had it
            return None
        
        # Try common save extensions or specific one from emulator
        target_ext = res.get("extension")
        if target_ext:
            if not target_ext.startswith("."): target_ext = "." + target_ext
            p = base / f"{rom_name}{target_ext}"
            return p

        for ext in (".sav", ".srm", ".save", ".dat"):
            p = base / f"{rom_name}{ext}"
            if p.exists():
                return p
        
        # Default to .sav
        return base / f"{rom_name}.sav"
    
    def get_save_files(self, rom: dict) -> list[Path]:
        p = self._save_path(rom)
        if p and p.exists():
            return [p]
        return []
    
    def restore_save_files(self, rom: dict, save_data: bytes, filename: str) -> bool:
        p = self._save_path(rom)
        if not p:
            return False
        
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.write_bytes(save_data)
            logging.info(f"[FileStrategy] Restored: {p}")
            return True
        except Exception as e:
            logging.error(f"[FileStrategy] Write failed: {e}")
            return False
    
    def get_save_dir(self, rom: dict) -> Optional[Path]:
        p = self._save_path(rom)
        return p.parent if p else None


class WindowsNativeStrategy(SaveStrategy):
    """
    Handles Windows native games.
    """
    mode_id = "windows"
    
    def get_save_files(self, rom: dict) -> list[Path]:
        from src import windows_saves
        save_dir = windows_saves.get_save_dir(rom.get("id"))
        if not save_dir:
            return []
        p = Path(save_dir)
        if not p.exists():
            return []
        return [f for f in p.rglob("*") if f.is_file()]
    
    def restore_save_files(self, rom: dict, save_data: bytes, filename: str) -> bool:
        from src import windows_saves
        save_dir = windows_saves.get_save_dir(rom.get("id"))
        if not save_dir:
            return False
        dest = Path(save_dir) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_bytes(save_data)
            return True
        except Exception as e:
            logging.error(f"[WindowsStrategy] Write failed: {e}")
            return False
    
    def get_save_dir(self, rom: dict) -> Optional[Path]:
        from src import windows_saves
        d = windows_saves.get_save_dir(rom.get("id"))
        return Path(d) if d else None


# ── Registry ─────────────────────────────

STRATEGY_REGISTRY: dict[str, type[SaveStrategy]] = {
    "retroarch": RetroArchStrategy,
    "folder": FolderStrategy,
    "file": FileStrategy,
    "direct_file": FileStrategy, # Alias
    "windows": WindowsNativeStrategy,
}

def get_strategy(config: dict, emulator: dict) -> SaveStrategy:
    """
    Return the correct SaveStrategy for an emulator.
    """
    mode = emulator.get("save_resolution", {}).get("mode", "retroarch")
    
    if emulator.get("id") == "windows_native" or emulator.get("is_native"):
        mode = "windows"
    
    cls = STRATEGY_REGISTRY.get(mode, RetroArchStrategy)
    return cls(config, emulator)
