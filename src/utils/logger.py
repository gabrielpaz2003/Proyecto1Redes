# src/utils/logger.py
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from ..core.config import settings

class JSONLLogger:
    def __init__(self, path: str | None = None):
        cfg = settings()
        self.path = path or cfg.log_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def log(self, event: Dict[str, Any]):
        event = {"ts": time.time(), **event}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
