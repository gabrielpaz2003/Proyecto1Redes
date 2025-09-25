# src/core/openai_client.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Set
from openai import OpenAI

from .config import settings
from ..mcp.client import MCPClient  # noqa: F401 (referencia de tipos en otros módulos)

# =========================================================
# Construcción del cliente OpenAI
# =========================================================
def build_openai_client():
    cfg = settings()
    client = OpenAI(api_key=cfg.openai_api_key)
    return client, cfg.openai_model

# =========================================================
# Catálogo de tools expuestas al modelo (tool-calling)
# =========================================================

# Mapeo OpenAI -> métodos del servidor SQLScout
OPENAI_TO_MCP = {
    "sql_load": "sql.load",
    "sql_explain": "sql.explain",
    "sql_diagnose": "sql.diagnose",
    "sql_optimize": "sql.optimize",
    "sql_apply": "sql.apply",
    "sql_optimize_apply": "sql.optimize_apply",
}

# Tools de alto nivel (FS/Git amigables + SQL)
OPENAI_TOOLS: List[Dict[str, Any]] = [
    # SQL
    {"type": "function", "function": {
        "name": "sql_load",
        "description": "Carga un esquema SQL (texto completo .sql).",
        "parameters": {"type":"object","properties":{"schema":{"type":"string"}},"required":["schema"]}
    }},
    {"type": "function", "function": {
        "name": "sql_explain",
        "description": "EXPLAIN QUERY PLAN de una consulta.",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}
    }},
    {"type": "function", "function": {
        "name": "sql_diagnose",
        "description": "Diagnóstico estático de una consulta.",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}
    }},
    {"type": "function", "function": {
        "name": "sql_optimize",
        "description": "Sugerencias de índices/reescrituras.",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}
    }},
    {"type": "function", "function": {
        "name": "sql_apply",
        "description": "Aplica DDL (CREATE/DROP INDEX, ALTER...).",
        "parameters": {"type":"object","properties":{"ddl":{"type":"string"}},"required":["ddl"]}
    }},
    {"type": "function", "function": {
        "name": "sql_optimize_apply",
        "description": "Compara plan antes/después aplicando DDL temporalmente.",
        "parameters": {"type":"object","properties":{"query":{"type":"string"},"ddl":{"type":"string"}},"required":["query","ddl"]}
    }},

    # FS (wrappers con rutas relativas a WORKSPACE_ROOT)
    {"type": "function", "function": {
        "name": "fs_create_dir",
        "description": "Crea una carpeta dentro del workspace (ruta relativa).",
        "parameters": {"type":"object","properties":{"relative_path":{"type":"string"}},"required":["relative_path"]}
    }},
    {"type": "function", "function": {
        "name": "fs_write_text",
        "description": "Crea/sobrescribe archivo de texto dentro del workspace.",
        "parameters": {"type":"object","properties":{
            "relative_path":{"type":"string"},
            "content":{"type":"string"}
        },"required":["relative_path","content"]}
    }},
    {"type": "function", "function": {
        "name": "fs_read_text",
        "description": "Lee un archivo de texto del workspace.",
        "parameters": {"type":"object","properties":{"relative_path":{"type":"string"}},"required":["relative_path"]}
    }},
    {"type": "function", "function": {
        "name": "fs_list",
        "description": "Lista un directorio del workspace.",
        "parameters": {"type":"object","properties":{"relative_path":{"type":"string","default":"."}},"required":["relative_path"]}
    }},
    {"type": "function", "function": {
        "name": "fs_move",
        "description": "Mueve/renombra un archivo o carpeta dentro del workspace.",
        "parameters": {"type":"object","properties":{
            "source":{"type":"string"},
            "destination":{"type":"string"}
        },"required":["source","destination"]}
    }},
    {"type": "function", "function": {
        "name": "fs_trash_delete",
        "description": "Elimina (lógica) un archivo dentro del workspace.",
        "parameters": {"type":"object","properties":{"relative_path":{"type":"string"}},"required":["relative_path"]}
    }},

    # Git (en REPO_ROOT; nunca 'add all')
    {"type": "function", "function": {
        "name": "git_init_here",
        "description": "Inicializa un repo Git en REPO_ROOT si no existe.",
        "parameters": {"type":"object","properties":{},"required":[]}
    }},
    {"type": "function", "function": {
        "name": "git_add_files",
        "description": "Añade SOLO archivos indicados (rutas relativas al repo).",
        "parameters": {"type":"object","properties":{"files":{
            "type":"array","items":{"type":"string"}}},"required":["files"]}
    }},
    {"type": "function", "function": {
        "name": "git_commit_msg",
        "description": "git commit -m en REPO_ROOT.",
        "parameters": {"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}
    }},
    {"type": "function", "function": {
        "name": "git_status_here",
        "description": "git status en REPO_ROOT.",
        "parameters": {"type":"object","properties":{},"required":[]}
    }},
    {"type": "function", "function": {
        "name": "git_log_here",
        "description": "git log en REPO_ROOT.",
        "parameters": {"type":"object","properties":{"max_count":{"type":"integer","default":5}},"required":[]}
    }},
]

# =========================================================
# Ejecución de tools (wrappers)
# =========================================================

def _exec_sql(clients: Dict[str, MCPClient], tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if "SQLScout" not in clients:
        return {"content":[{"type":"text","text":"Servidor 'SQLScout' no está configurado."}],"isError":True}
    mcp_method = OPENAI_TO_MCP.get(tool_name)
    if not mcp_method:
        return {"content":[{"type":"text","text":f"Tool '{tool_name}' no mapeada a SQLScout."}],"isError":True}
    return clients["SQLScout"].call(mcp_method, args)

def _ws_abs(rel: str) -> str:
    import os
    cfg = settings()
    return os.path.normpath(os.path.join(cfg.workspace_root, rel))

def _repo_root() -> str:
    cfg = settings()
    return cfg.repo_root

def handle_tool_call(t_name: str, args: Dict[str, Any], clients: Dict[str, MCPClient], remote_supabase: Set[str]) -> Dict[str, Any]:
    # --- FS ---
    if t_name == "fs_create_dir":
        return clients["FS"].call("create_directory", {"path": _ws_abs(args["relative_path"])})
    if t_name == "fs_write_text":
        return clients["FS"].call("write_file", {"path": _ws_abs(args["relative_path"]), "content": args["content"]})
    if t_name == "fs_read_text":
        return clients["FS"].call("read_text_file", {"path": _ws_abs(args["relative_path"])})
    if t_name == "fs_list":
        return clients["FS"].call("list_directory", {"path": _ws_abs(args.get("relative_path","."))})
    if t_name == "fs_move":
        return clients["FS"].call("move_file", {"source": _ws_abs(args["source"]), "destination": _ws_abs(args["destination"]) })
    if t_name == "fs_trash_delete":
        # Borrado lógico: mover a .trash
        import os, time
        base = os.path.basename(args["relative_path"].replace("\\","/"))
        ts = time.strftime("%Y%m%d-%H%M%S")
        trash_dir = _ws_abs(".trash")
        clients["FS"].call("create_directory", {"path": trash_dir})
        return clients["FS"].call("move_file", {
            "source": _ws_abs(args["relative_path"]),
            "destination": os.path.join(trash_dir, f"{ts}-{base}")
        })

    # --- Git ---
    if t_name == "git_init_here":
        return clients["Git"].call("git_init", {"repo_path": _repo_root()})
    if t_name == "git_add_files":
        # Filtrado defensivo
        BLOCKLIST_PREFIXES = (".git", "_git", "__pycache__")
        BLOCKLIST_EXT = (".pyc", ".pyo", ".pyd", ".log")
        safe: List[str] = []
        for f in args.get("files", []):
            rp = (f or "").replace("\\","/").lstrip("/")
            if (not rp) or any(rp.startswith(p) for p in BLOCKLIST_PREFIXES) or rp.endswith(BLOCKLIST_EXT):
                continue
            safe.append(rp)
        if not safe:
            return {"content":[{"type":"text","text":"No hay archivos válidos para agregar."}],"isError":True}
        return clients["Git"].call("git_add", {"repo_path": _repo_root(), "files": safe})
    if t_name == "git_commit_msg":
        return clients["Git"].call("git_commit", {"repo_path": _repo_root(), "message": args["message"]})
    if t_name == "git_status_here":
        return clients["Git"].call("git_status", {"repo_path": _repo_root()})
    if t_name == "git_log_here":
        return clients["Git"].call("git_log", {"repo_path": _repo_root(), "max_count": int(args.get("max_count",5))})

    # --- Supabase (si declaraste server con tools HTTP) ---
    if t_name in remote_supabase:
        return clients["Supabase"].call(t_name, args)

    # --- SQL por defecto ---
    return _exec_sql(clients, t_name, args)
