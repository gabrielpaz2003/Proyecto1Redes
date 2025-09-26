# src/services/remotemcp.py
from __future__ import annotations
from typing import Dict, List, Set, Tuple, Any

SAFE_PREFIX = "remote__"

SCHEMAS: Dict[str, Dict[str, Any]] = {
    "remote.ping": {"type": "object", "properties": {}, "required": []},
    "remote.time": {"type": "object", "properties": {}, "required": []},
    "remote.echo": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
}

DESCS: Dict[str, str] = {
    "remote.ping": "Ping remoto — responde {ok:true, message:'pong'}.",
    "remote.time": "Hora del servidor — responde ISO en {now}.",
    "remote.echo": "Eco remoto — responde {echo:<text>}.",
}

def _safe(remote_name: str) -> str:
    # remote.ping -> remote__remote_ping (sustituimos '.' por '_')
    return SAFE_PREFIX + remote_name.replace(".", "_")

def import_remote_tools(clients: Dict[str, Any], openai_tools: List[Dict[str, Any]]) -> Tuple[Set[str], Dict[str, str]]:
    safe_names: Set[str] = set()
    mapping: Dict[str, str] = {}

    if "RemoteMCP" not in clients:
        return safe_names, mapping

    try:
        res = clients["RemoteMCP"].list_tools()
        tools = res.get("result", {}).get("tools", [])
    except Exception:
        return safe_names, mapping

    for t in tools:
        if not isinstance(t, dict):
            continue
        remote_name = t.get("name")
        if not remote_name or not isinstance(remote_name, str):
            continue

        sname = _safe(remote_name)
        if any(isinstance(x, dict) and x.get("function", {}).get("name") == sname for x in openai_tools):
            continue

        safe_names.add(sname)
        mapping[sname] = remote_name

        params = SCHEMAS.get(remote_name, {"type": "object", "properties": {}, "required": []})
        desc = DESCS.get(remote_name, f"[RemoteMCP] Tool remota '{remote_name}'.")

        openai_tools.append({
            "type": "function",
            "function": {
                "name": sname,
                "description": desc,
                "parameters": params,
            }
        })

    return safe_names, mapping
