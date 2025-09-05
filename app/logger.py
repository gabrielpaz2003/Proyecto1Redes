import json, time

LOG_PATH = "logs.jsonl"

def log(event: str, **payload):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "event": event, **payload}, ensure_ascii=False) + "\n")
