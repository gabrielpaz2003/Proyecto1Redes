# src/services/anime_helper.py
from __future__ import annotations
from typing import Dict, List, Set, Tuple, Any
import re

from ..mcp.client import MCPClient

SAFE_PREFIX = "anime__"

# Esquemas (ligeros) para las tools más usadas
def _param(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "object", **obj}

SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ask": _param({
        "properties": {
            "text": {"type": "string", "description": "Pregunta en lenguaje natural (ES/EN)"},
            "default_kind": {"type": "string", "enum": ["ANIME", "MANGA"], "default": "ANIME"},
            "default_limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 5}
        },
        "required": ["text"]
    }),
    "search_media": _param({
        "properties": {
            "query": {"type": "string"},
            "kind": {"type": "string", "enum": ["ANIME", "MANGA"], "default": "ANIME"},
            "source": {"type": "string", "enum": ["anilist", "jikan"], "default": "anilist"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 5},
            "format_in": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["query"]
    }),
    "media_details": _param({
        "properties": {
            "source": {"type": "string", "enum": ["anilist", "jikan"]},
            "id": {"type": "integer"},
            "kind": {"type": "string", "enum": ["ANIME", "MANGA"], "default": "ANIME"}
        },
        "required": ["source", "id"]
    }),
    "trending": _param({
        "properties": {
            "kind": {"type": "string", "enum": ["ANIME", "MANGA"], "default": "ANIME"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            "format_in": {"type": "array", "items": {"type": "string"}}
        },
        "required": []
    }),
    "season_top": _param({
        "properties": {
            "kind": {"type": "string", "enum": ["ANIME", "MANGA"], "default": "ANIME"},
            "season": {"type": "string"},
            "year": {"type": "integer"},
            "sort": {"type": "string", "default": "TRENDING_DESC"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            "format_in": {"type": "array", "items": {"type": "string"}}
        },
        "required": []
    }),
    "airing_status": _param({
        "properties": {
            "anilist_id": {"type": "integer"},
            "query": {"type": "string"}
        },
        "required": []
    }),
    "airing_calendar": _param({
        "properties": {
            "days": {"type": "integer", "minimum": 1, "maximum": 30, "default": 7},
            "per_page": {"type": "integer", "minimum": 1, "maximum": 50, "default": 50}
        },
        "required": []
    }),
    "resolve_title": _param({
        "properties": {
            "title": {"type": "string"},
            "kind": {"type": "string", "enum": ["ANIME", "MANGA"], "default": "ANIME"},
            "prefer_format": {"type": "string"}
        },
        "required": ["title"]
    }),
    "cache_info": _param({"properties": {}, "required": []}),
    "cache_clear": _param({"properties": {}, "required": []}),
    "health": _param({"properties": {}, "required": []}),
    "help": _param({"properties": {}, "required": []}),
    "help_text": _param({"properties": {}, "required": []}),
    "about": _param({"properties": {}, "required": []}),
}

# Descripciones cortas
DESC = {
    "ask": "Consulta NL (ES/EN) sobre anime/manga. Router interno a trending/season_top/details/etc.",
    "search_media": "Buscar ANIME/MANGA por título (AniList por defecto; Jikan fallback).",
    "media_details": "Ficha normalizada (títulos, formato/estado, episodios/capítulos, géneros, sinopsis, enlaces, recomendaciones).",
    "trending": "Top en tendencia (AniList).",
    "season_top": "Top de la temporada actual (AniList) — ANIME; para MANGA usa trending.",
    "airing_status": "Último emitido y próximo episodio (ANIME).",
    "airing_calendar": "Calendario de próximos episodios (ANIME).",
    "resolve_title": "Resolver título a IDs canónicos (AniList/MAL).",
    "cache_info": "Estadísticas internas del cache GraphQL.",
    "cache_clear": "Limpia el cache interno GraphQL.",
    "health": "Ping/estado del server.",
    "help": "Ayuda estructurada del server.",
    "help_text": "Ayuda en texto plano.",
    "about": "Metadatos del server y versiones.",
}

# Mapear tool real -> nombre seguro
def _safe_name(remote: str) -> str:
    # remote llega como p.ej. "search_media" o "help_text"
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", remote)
    return SAFE_PREFIX + cleaned

def import_remote_tools(clients: Dict[str, MCPClient], openai_tools: List[Dict[str, Any]]) -> Tuple[Set[str], Dict[str, str]]:
    """
    - Descubre las tools de 'anime-helper'
    - Inserta definiciones en openai_tools con nombres seguros 'anime__...'
    - Devuelve (safe_names, map_safe_to_remote)
    """
    if "anime-helper" not in clients:
        return set(), {}

    client = clients["anime-helper"]
    listed = client.list_tools()  # {"tools":[{"name":"search_media", ...}, ...]}
    names = [t.get("name") for t in (listed.get("tools") or []) if isinstance(t, dict)]

    safe_names: Set[str] = set()
    mapping: Dict[str, str] = {}

    for remote_name in names:
        sname = _safe_name(remote_name)
        safe_names.add(sname)
        mapping[sname] = remote_name

        schema = SCHEMAS.get(remote_name, _param({"properties": {}, "required": []}))
        desc = DESC.get(remote_name, f"Tool remota '{remote_name}' del servidor anime-helper.")

        openai_tools.append({
            "type": "function",
            "function": {
                "name": sname,
                "description": desc,
                "parameters": schema
            }
        })

    return safe_names, mapping
