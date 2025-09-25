# src/services/fs.py
from __future__ import annotations

import os
import time
from typing import Any, Dict

from ..core.config import settings

def _abs(rel: str) -> str:
    cfg = settings()
    rel = (rel or "").lstrip("/\\")
    return os.path.normpath(os.path.join(cfg.workspace_root, rel))

def exec_fs_create_dir(clients, relative_path: str) -> Dict[str, Any]:
    path = _abs(relative_path)
    return clients["FS"].call("create_directory", {"path": path})

def exec_fs_write_text(clients, relative_path: str, content: str) -> Dict[str, Any]:
    path = _abs(relative_path)
    return clients["FS"].call("write_file", {"path": path, "content": content})

def exec_fs_list(clients, relative_path: str = ".") -> Dict[str, Any]:
    path = _abs(relative_path)
    return clients["FS"].call("list_directory", {"path": path})

def exec_fs_read_text(clients, relative_path: str) -> Dict[str, Any]:
    path = _abs(relative_path)
    return clients["FS"].call("read_text_file", {"path": path})

def exec_fs_move(clients, source_rel: str, dest_rel: str) -> Dict[str, Any]:
    src = _abs(source_rel)
    dst = _abs(dest_rel)
    return clients["FS"].call("move_file", {"source": src, "destination": dst})

def exec_fs_trash_delete(clients, relative_path: str) -> Dict[str, Any]:
    """
    'Borrado' seguro: mover a .trash/<timestamp>-<nombre>
    """
    cfg = settings()
    trash_dir = os.path.join(cfg.workspace_root, ".trash")
    clients["FS"].call("create_directory", {"path": trash_dir})
    base = os.path.basename(relative_path.replace("\\","/"))
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(trash_dir, f"{ts}-{base}")
    return clients["FS"].call("move_file", {"source": _abs(relative_path), "destination": dest})
