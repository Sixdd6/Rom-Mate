import logging

# Key: rom_id (str)
# Value: {
#   "type": "download" | "extraction",
#   "thread": QThread,
#   "rom_name": str,
#   "progress": (current, total),
#   "status": "downloading"|"extracting"|"done"|"cancelled",
#   "listeners": []  # callbacks for UI updates
# }
_registry = {}

def register_download(rom_id, rom_name, thread):
    rom_id = str(rom_id)
    if rom_id in _registry:
        old_entry = _registry[rom_id]
        old_thread = old_entry.get("thread")
        old_listeners = list(old_entry.get("listeners", []))
        was_running = False
        try:
            was_running = bool(old_thread and hasattr(old_thread, "isRunning") and old_thread.isRunning())
        except Exception:
            was_running = False
        if old_thread:
            try:
                old_thread.quit()
                old_thread.wait(500)
            except Exception:
                pass
        if was_running:
            for cb in old_listeners:
                try:
                    cb(rom_id, "cancelled", old_entry["progress"][0], old_entry["progress"][1])
                except Exception:
                    pass
        _registry.pop(rom_id)

    _registry[rom_id] = {
        "type": "download",
        "thread": thread,
        "rom_name": rom_name,
        "progress": (0, 0),
        "status": "downloading",
        "listeners": old_listeners if 'old_listeners' in locals() else []
    }
    logging.debug(f"[Registry] Registered download for {rom_name} ({rom_id})")

def register_extraction(rom_id, rom_name, thread):
    rom_id = str(rom_id)
    if rom_id in _registry:
        old_entry = _registry[rom_id]
        old_thread = old_entry.get("thread")
        old_listeners = list(old_entry.get("listeners", []))
        was_running = False
        try:
            was_running = bool(old_thread and hasattr(old_thread, "isRunning") and old_thread.isRunning())
        except Exception:
            was_running = False
        if old_thread:
            try:
                old_thread.quit()
                old_thread.wait(500)
            except Exception:
                pass
        if was_running:
            for cb in old_listeners:
                try:
                    cb(rom_id, "cancelled", old_entry["progress"][0], old_entry["progress"][1])
                except Exception:
                    pass
        _registry.pop(rom_id)

    _registry[rom_id] = {
        "type": "extraction",
        "thread": thread,
        "rom_name": rom_name,
        "progress": (0, 0),
        "status": "extracting",
        "listeners": old_listeners if 'old_listeners' in locals() else []
    }
    logging.debug(f"[Registry] Registered extraction for {rom_name} ({rom_id})")

def get(rom_id):
    return _registry.get(str(rom_id))

def all():
    return _registry

def unregister(rom_id):
    rom_id = str(rom_id)
    entry = _registry.get(rom_id)
    if not entry:
        return
    # Use "cancelled" if that was the last status, otherwise "done"
    final_status = "cancelled" if entry.get("status") == "cancelled" else "done"
    entry["status"] = final_status
    # Notify BEFORE removing
    for cb in list(entry["listeners"]):
        try:
            cb(rom_id, final_status, entry["progress"][0], entry["progress"][1])
        except Exception:
            pass
    _registry.pop(rom_id, None)
    logging.debug(f"[Registry] Unregistered {rom_id} (status: {final_status})")

def add_listener(rom_id, callback):
    rom_id = str(rom_id)
    entry = _registry.get(rom_id)
    if entry:
        if callback not in entry["listeners"]:
            entry["listeners"].append(callback)
            # Initial update
            try:
                callback(rom_id, entry["type"], entry["progress"][0], entry["progress"][1])
            except Exception:
                pass

def remove_listener(rom_id, callback):
    rom_id = str(rom_id)
    entry = _registry.get(rom_id)
    if entry and callback in entry["listeners"]:
        entry["listeners"].remove(callback)

def update_progress(rom_id, current, total, speed=0):
    rom_id = str(rom_id)
    entry = _registry.get(rom_id)
    if entry:
        entry["progress"] = (current, total)
        for cb in entry["listeners"]:
            try:
                # Some listeners might expect 4 args, some 5 if we include speed
                # Let's keep it simple: always pass (rom_id, type, current, total, speed)
                cb(rom_id, entry["type"], current, total, speed)
            except Exception:
                # Fallback for old listeners
                try:
                    cb(rom_id, entry["type"], current, total)
                except Exception:
                    pass

def update_status(rom_id, status):
    rom_id = str(rom_id)
    entry = _registry.get(rom_id)
    if entry:
        entry["status"] = status
        if status == "cancelled":
            for cb in entry["listeners"]:
                try:
                    cb(rom_id, "cancelled", entry["progress"][0], entry["progress"][1])
                except Exception:
                    pass
