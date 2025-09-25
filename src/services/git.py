from typing import Dict, Any, List
from ..core.config import settings
from ..mcp.client import MCPClient

BLOCKLIST_PREFIXES = (".git", "_git", "__pycache__")
BLOCKLIST_EXT = (".pyc", ".pyo", ".pyd", ".log")

def _repo() -> str: return settings().repo_root

def git_init_here(clients: Dict[str, MCPClient]) -> Dict[str, Any]:
    return clients["Git"].call("git_init", {"repo_path": _repo()})

def git_add_files(clients: Dict[str, MCPClient], files: List[str]) -> Dict[str, Any]:
    safe = []
    for f in files:
        rp = (f or "").replace("\\","/").lstrip("/")
        if (not rp) or any(rp.startswith(p) for p in BLOCKLIST_PREFIXES) or rp.endswith(BLOCKLIST_EXT):
            continue
        safe.append(rp)
    if not safe:
        return {"content":[{"type":"text","text":"No hay archivos válidos para agregar."}],"isError":True}
    return clients["Git"].call("git_add", {"repo_path": _repo(), "files": safe})

def git_commit_msg(clients: Dict[str, MCPClient], message: str) -> Dict[str, Any]:
    return clients["Git"].call("git_commit", {"repo_path": _repo(), "message": message})

def git_status_here(clients: Dict[str, MCPClient]) -> Dict[str, Any]:
    return clients["Git"].call("git_status", {"repo_path": _repo()})

def git_log_here(clients: Dict[str, MCPClient], max_count: int = 5) -> Dict[str, Any]:
    return clients["Git"].call("git_log", {"repo_path": _repo(), "max_count": max_count})
