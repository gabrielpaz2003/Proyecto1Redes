import json
from typing import Any, Dict, List

def table_from_result(result: Dict[str, Any]) -> str:
    """Convierte respuestas de tools a tabla Markdown simple cuando se pueda."""
    sc = result.get("structuredContent", {})
    if sc and "result" in sc:
        data = sc["result"]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            headers = list(data[0].keys())
            head = "| " + " | ".join(headers) + " |"
            sep  = "| " + " | ".join("---" for _ in headers) + " |"
            rows = ["| " + " | ".join(str(r.get(h, "")) for h in headers) + " |" for r in data]
            return "\n".join([head, sep] + rows)
        return json.dumps(data, ensure_ascii=False, indent=2)

    parts = result.get("content", [])
    if isinstance(parts, list):
        texts = [p.get("text","") for p in parts if isinstance(p, dict) and p.get("type")=="text"]
        if texts:
            return "\n".join(texts)

    # fallback
    return json.dumps(result, ensure_ascii=False, indent=2)
