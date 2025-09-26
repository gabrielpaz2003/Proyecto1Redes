# src/services/sitelens.py
from __future__ import annotations

from typing import Dict, List, Set, Tuple, Any

def _safe_name(remote_name: str) -> str:
    """
    Convierte 'aa.sitemap' -> 'sitelens__aa_sitemap'
    (OpenAI no acepta puntos en function.name)
    """
    return "sitelens__" + remote_name.replace(".", "_")

def import_remote_tools(
    clients: Dict[str, Any],
    openai_tools: List[Dict[str, Any]],
) -> Tuple[Set[str], Dict[str, str]]:
    """
    Lee tools del servidor 'SiteLens' y las añade al catálogo OPENAI_TOOLS
    usando nombres seguros. Devuelve:
      - safe_names: set con los nombres seguros añadidos
      - name_map:   { safe_name -> remote_name }
    """
    safe_names: Set[str] = set()
    name_map: Dict[str, str] = {}

    if "SiteLens" not in clients:
        return safe_names, name_map

    try:
        res = clients["SiteLens"].list_tools()
        tools = res.get("result", {}).get("tools", [])
    except Exception:
        return safe_names, name_map

    for t in tools:
        if not isinstance(t, dict):
            continue
        remote_name = t.get("name")
        if not remote_name or not isinstance(remote_name, str):
            continue

        safe = _safe_name(remote_name)
        name_map[safe] = remote_name
        safe_names.add(safe)

        # Tomamos el inputSchema remoto si existe; si no, uno vacío
        params = t.get("inputSchema") or {"type": "object", "properties": {}, "required": []}

        # Evitamos duplicados si se re-ejecuta el host
        if any(isinstance(x, dict) and x.get("function", {}).get("name") == safe for x in openai_tools):
            continue

        openai_tools.append({
            "type": "function",
            "function": {
                "name": safe,
                "description": f"[SiteLens] {t.get('description','')}",
                "parameters": params,
            }
        })

    return safe_names, name_map
