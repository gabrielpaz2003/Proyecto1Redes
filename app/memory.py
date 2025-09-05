import json, os, time
from typing import List, Dict, Any

MEM_PATH = "conversation.json"

class ConversationMemory:
    def __init__(self, path: str = MEM_PATH):
        self.path = path
        self.messages: List[Dict[str, Any]] = []
        if os.path.exists(self.path):
            try:
                self.messages = json.load(open(self.path, "r", encoding="utf-8"))
            except Exception:
                self.messages = []

    def add(self, role: str, content):
        self.messages.append({"role": role, "content": content, "ts": time.time()})
        self._persist()

    def clear(self):
        self.messages = []
        self._persist()

    def _persist(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)
