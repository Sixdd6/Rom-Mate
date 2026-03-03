import requests
import os
import time
import json
from pathlib import Path

class RomMClient:
    def __init__(self, host):
        self.host = host.rstrip('/')
        self.token = None
        self.user_games = []

    def login(self, username, password):
        try:
            url = f"{self.host}/api/token"
            data = {"username": username, "password": password}
            r = requests.post(url, data=data, timeout=10)
            if r.status_code == 200:
                self.token = r.json()["access_token"]
                return True, self.token
            return False, r.json().get("detail", "Login failed")
        except Exception as e:
            return False, str(e)

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def fetch_library(self):
        try:
            url = f"{self.host}/api/roms"
            params = {"page": 1, "page_size": 5000}
            r = requests.get(url, headers=self.get_headers(), params=params, timeout=15)
            if r.status_code == 200:
                self.user_games = r.json().get("items", [])
                return self.user_games
            return []
        except:
            return []

    def get_cover_url(self, game):
        # RomM usually serves covers at /api/raw/covers/{id}
        return f"{self.host}/api/raw/covers/{game['id']}"

    def download_rom(self, rom_id, file_name, target_path, progress_cb=None, is_cancelled=None):
        try:
            url = f"{self.host}/api/roms/{rom_id}/download"
            r = requests.get(url, headers=self.get_headers(), stream=True, timeout=30)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            start = time.time()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(1024*1024):
                    if is_cancelled and is_cancelled[0]:
                        f.close()
                        os.remove(target_path)
                        return False
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb:
                            elapsed = time.time() - start
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            progress_cb(downloaded, total, speed)
            return True
        except:
            return False

    def get_latest_save(self, rom_id):
        try:
            url = f"{self.host}/api/roms/{rom_id}/saves"
            r = requests.get(url, headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                saves = r.json()
                if saves:
                    # Sort by created_at descending
                    saves.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                    return saves[0]
            return None
        except:
            return None

    def download_save(self, save_item, target_path):
        try:
            url = f"{self.host}/api/raw/assets/{save_item['path']}"
            r = requests.get(url, headers=self.get_headers(), stream=True, timeout=30)
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except:
            return False

    def upload_save(self, rom_id, emulator, file_path):
        try:
            url = f"{self.host}/api/roms/saves/upload"
            files = {'file': open(file_path, 'rb')}
            params = {"rom_id": rom_id, "emulator": emulator, "slot": "wingosy-windows"}
            r = requests.post(url, headers=self.get_headers(), files=files, data=params, timeout=60)
            if r.status_code in [200, 201]:
                return True, "Success"
            return False, r.json().get("detail", "Upload failed")
        except Exception as e:
            return False, str(e)

    def get_firmware(self):
        try:
            url = f"{self.host}/api/firmwares"
            r = requests.get(url, headers=self.get_headers(), timeout=15)
            if r.status_code == 200:
                return r.json()
            return []
        except:
            return []

    def download_firmware(self, fw_item, target_path, progress_cb=None):
        try:
            # Firmwares are stored in assets
            url = f"{self.host}/api/raw/assets/{fw_item['path']}"
            r = requests.get(url, headers=self.get_headers(), stream=True, timeout=30)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            start = time.time()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(1024*1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb:
                            elapsed = time.time() - start
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            progress_cb(downloaded, total, speed)
            return True
        except:
            return False
