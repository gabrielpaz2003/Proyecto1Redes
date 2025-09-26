# MCP Server: AnimeHelper (Anime & Manga via AniList/Jikan)

Servidor MCP **local por STDIO** para consultar información de **anime y manga** usando **AniList** (por defecto) con **fallback a Jikan** (no requiere API key).
Pensado para integrarse a un *host* con **tool-calling**, ya sea invocando tools directamente (`:call`) o en **lenguaje natural**.

> **Estado actual probado en tu entorno**: `health`, `help`, `help_text`, `search_media`, `media_details`, `resolve_title`, `airing_status`, `airing_calendar` funcionan OK.  
> `trending` y `season_top` dependen de AniList y pueden devolver **500 upstream (anilist)** temporalmente — ver sección *Problemas comunes* y *Workarounds / Fallback*.

---

## ¿Qué hace?
Tools expuestas por el server:

- `ask` — **Consulta NL (ES/EN)**. Router interno que decide entre `season_top`, `trending`, `search_media`, `media_details`, `airing_status`, etc.
- `search_media` — Buscar obras por **título** (`kind: ANIME|MANGA`, `source: anilist|jikan`, `limit`, `format_in`).
- `media_details` — **Ficha** normalizada (títulos, formato/estado, episodios/capítulos, géneros, **enlaces** y **recomendaciones**).
- `trending` — Top en **tendencia** (AniList). *(Puede fallar si AniList está caído)*
- `season_top` — Top de la **temporada actual** (AniList). *(Puede fallar si AniList está caído)*
- `airing_status` — Último emitido y **próximo episodio** (ANIME) por `query` o `anilist_id`.
- `airing_calendar` — **Calendario** de próximos episodios para los próximos `days`.
- `resolve_title` — Resolver nombre a **IDs canónicos** (AniList/MAL).
- `cache_info` / `cache_clear` — Estado y limpieza del **cache GraphQL** interno.
- `health`, `help`, `help_text`, `about` — Diagnóstico y ayuda.

---

## Configuración en `mcp_config.json`
```jsonc
{
  "name": "anime-helper",
  "transport": "stdio",
  "command": "py",
  "args": ["-3.11", "-m", "anime_helper.server"],
  "cwd": ".",
  "env": {}
}
```
> Verifica que tu Python 3.11 tenga instalado el paquete que expone `anime_helper.server`.

---

## Uso desde el host (consola)
Inicia el host y lista servidores:
```bash
py -3.11 -m src.host_cli
:servers
```

Activa modo **RAW** para ver JSON crudo cuando quieras depurar:
```bash
:raw   # ON
```

---

## Smoke tests por `:call` (directo a la tool)

### 1) Salud y Ayuda
```bash
:call anime-helper health {}
:call anime-helper help {}
:call anime-helper help_text {}
```

### 2) Búsqueda por título (forzando Jikan si AniList falla)
```bash
:call anime-helper search_media {"query":"one piece","kind":"ANIME","source":"jikan","limit":3}
```
**Esperado:** una lista con `id`, `title`, `year` (o `startDate.year`) y `source`=`jikan`.

### 3) Resolver título → ficha completa
```bash
# resolver IDs
:call anime-helper resolve_title {"title":"Vinland Saga","kind":"ANIME"}
# toma el id y la fuente (de preferencia AniList) y pide la ficha
:call anime-helper media_details {"source":"anilist","id": 101348, "kind":"ANIME"}
# si AniList estuviera caído, prueba con Jikan cambiando source e id
:call anime-helper media_details {"source":"jikan","id": <ID_JIKAN>, "kind":"ANIME"}
```

### 4) Estado de emisión
```bash
:call anime-helper airing_status {"query":"One Piece"}
# o si ya tienes un anilist_id:
:call anime-helper airing_status {"anilist_id": 21}
```

### 5) Calendario (7 días por defecto)
```bash
:call anime-helper airing_calendar {"days":7,"per_page":50}
```

### 6) Trending y Top de temporada (pueden fallar por AniList)
```bash
:call anime-helper trending {"limit":10}
:call anime-helper season_top {"limit":10}
```
Si aparece:
```jsonc
{"error":{"code":"UPSTREAM_0","message":"500 upstream","source":"anilist"}}
```
sigue a la sección *Workarounds*.

---

## Lenguaje natural (tool-calling automático)
> El host expone **nombres seguros** `anime__*` para tool-calling, por lo que puedes usar prompts naturales.

Ejemplos ya listos:
- “¿En qué capítulo va **One Piece** y cuándo sale el siguiente? Muéstralo en tabla.”  
  *(usa `airing_status`)*
- “Búscame **3 animes** que se llamen **One Piece** y muéstrame **título, id y año**.”  
  *(usa `search_media`)*
- “Resuelve **‘Vinland Saga’** a sus IDs y dame la **ficha** (formato, estado, géneros, URL) en una tabla.”  
  *(usa `resolve_title` → `media_details`)*
- “Muéstrame el **calendario de emisiones** de la semana con fecha/hora.”  
  *(usa `airing_calendar`)*
- “Dame un **top 10** de animes **en tendencia**.”  
  *(intenta `trending`; si AniList falla, ver *Workarounds*)*

> Si quieres forzar Jikan en NL, dilo explícitamente en el prompt:  
> “Usa **Jikan** como fuente para la búsqueda y ordénalos por **score**.”

---

## Workarounds / Fallback cuando AniList devuelve 500

- **Plan A:** Evitar `trending`/`season_top` y usar:
  - `search_media` con `source:"jikan"` + ordenar por `score`/`members`.
  - `airing_calendar` para próximos episodios.

- **Plan B (server):** Extender el server para incluir `top_from_jikan` o permitir `source:"jikan"` en `trending`/`season_top` cuando el upstream de AniList falle (retry + fallback).

- **Plan C (host):** Detectar en la respuesta un `error.source=="anilist"` y hacer reintentos/backoff o lanzar una consulta alternativa con `search_media (source:"jikan")` y construir una tabla “top” con los campos disponibles.

---

## Consejos de uso
- Usa `:raw` para inspeccionar payloads completos; si tu host tabula con `structuredContent.result` y una tool regresa un shape distinto, verás el JSON crudo para ajustar la visualización.
- Para `media_details`, **usa el `id` acorde a la `source`** (no mezclar id de AniList con source Jikan).
- Respeta **rate limits**; si spameas `trending/season_top`, AniList puede rechazar o devolver 5xx.

---

## Problemas comunes

- **`UPSTREAM_0 / 500 upstream (anilist)`**  
  Servicio de AniList con problemas temporales. Usa *Workarounds* o fuerza `source:"jikan"` en tus consultas.

- **No aparecen tools en `:servers`**  
  Revisa `mcp_config.json` (nombre `anime-helper`, `command` y `args` correctos) y vuelve a iniciar el host.

- **`media_details` no encuentra ficha con Jikan**  
  Asegúrate de pasar el **ID de Jikan** cuando `source:"jikan"` (no el de AniList). Puedes obtenerlo con `search_media` o `resolve_title`.

---

## Suite de pruebas rápida (lista para copiar)

```bash
# 0) Estado y ayuda
:call anime-helper health {}
:call anime-helper help {}
:call anime-helper help_text {}

# 1) Buscar 3 One Piece con Jikan (título, id, año)
:raw             # (opcional para ver JSON crudo)
:call anime-helper search_media {"query":"one piece","kind":"ANIME","source":"jikan","limit":3}

# 2) Resolver título → ficha
:call anime-helper resolve_title {"title":"Vinland Saga","kind":"ANIME"}
# reemplaza <ID_ANILIST> usando la salida anterior
:call anime-helper media_details {"source":"anilist","id": <ID_ANILIST>, "kind":"ANIME"}

# 3) Estado de emisión de One Piece
:call anime-helper airing_status {"query":"One Piece"}

# 4) Calendario 7 días
:call anime-helper airing_calendar {"days":7,"per_page":50}

# 5) (Opcional) Trending y Top de temporada — pueden fallar si AniList está caído
:call anime-helper trending {"limit":10}
:call anime-helper season_top {"limit":10}
```

---

## Notas de integración con tu host
- Tu host inserta tools seguras `anime__*` en `OPENAI_TOOLS`, y en `handle_tool_call` reenvía a `clients["anime-helper"]` con el nombre remoto correcto.
- Para depurar tool-calls del LLM, conserva `:raw` **ON** y observa el último payload crudo que loguea el host.
- Si deseas, puedes añadir un **fallback automático** en el host cuando `trending/season_top` devuelvan `error.source=="anilist"`.

---

## Licencia y créditos
- Datos vía **AniList** (GraphQL) y **Jikan** (REST, wrapper de MyAnimeList). Respeta términos y rate limits correspondientes.
- Server “AnimeHelper” creado con fines educativos y de integración MCP.
