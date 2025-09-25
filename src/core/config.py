# src/core/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

APP_TITLE = "MCP Host • Consola"
APP_VERSION = "1.0.0"
DEFAULT_SERVERS = ["SQLScout", "FS", "Git", "Supabase"]

@dataclass
class AppSettings:
    workspace_root: str
    repo_root: str
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    log_path: str = "history/chat_log.jsonl"

def settings() -> AppSettings:
    """
    Carga variables desde .env y devuelve un objeto con atributos.
    Evita tuplas para que otros módulos (logger, openai_client, etc.) puedan
    acceder a .log_path, .openai_model, etc.
    """
    load_dotenv()

    ws = os.getenv("WORKSPACE_ROOT")
    rp = os.getenv("REPO_ROOT")
    if not ws or not rp:
        raise RuntimeError("Faltan WORKSPACE_ROOT y/o REPO_ROOT en .env")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY en .env")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    log_path = os.getenv("HOST_LOG_PATH", "history/chat_log.jsonl")

    return AppSettings(
        workspace_root=ws.rstrip("/\\"),
        repo_root=rp.rstrip("/\\"),
        openai_api_key=api_key,
        openai_model=model,
        log_path=log_path,
    )
