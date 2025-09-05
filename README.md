# Proyecto 1 — Chatbot (Host) con MCP + Gemini

Implementación de un **chatbot en consola** que actúa como **anfitrión MCP** y se conecta a:
- Un **LLM gratuito** (Google **Gemini**).
- Servidores MCP **oficiales** locales: **Filesystem** y **Git**.
- Un **servidor MCP local** propio (`servers/my_local_srv.py`) con herramientas no triviales.

Cumple con los puntos 1–5 de la **Primera Parte** del enunciado.

---

## Tabla de contenido
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración (.env)](#configuración-env)
- [Servidores MCP](#servidores-mcp)
- [Ejecución](#ejecución)
- [Comandos disponibles en el chat](#comandos-disponibles-en-el-chat)
- [Demostración FS + Git](#demostración-fs--git)
- [Servidor MCP local (CFG Tools)](#servidor-mcp-local-cfg-tools)
- [Memoria y Log](#memoria-y-log)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Solución de problemas](#solución-de-problemas)

---

## Arquitectura

```
[Usuario CLI] ──> Host (app/client.py, Gemini) ── usa ──┐
                                                        ├─ MCP Filesystem (npx)
                                                        ├─ MCP Git (python -m mcp_server_git)
                                                        └─ MCP Local (servers/my_local_srv.py)
```

- El **host** mantiene **conexiones persistentes** a cada servidor MCP.
- Convierte las **tools MCP** a **function declarations** para el LLM.
- Guarda **memoria de conversación** y **logs** de llamadas MCP.

---

## Requisitos

- **Python 3.11+**
- **Git** instalado (`git --version`)
- **Node + npx** instalados (`node -v`, `npx -v`)
- Cuenta en **Google AI Studio** y **API key** de Gemini (gratis).

---

## Instalación

```bash
# Crear y activar venv (Windows PowerShell)
python -m venv .venv
.\.venv\Scriptsctivate

# Dependencias
pip install -U google-genai mcp mcp-server-git python-dotenv rich
```

---

## Configuración (.env)

Crea un archivo **`.env`** en la **raíz** del proyecto:

```
# Tu clave (elige una variable; si defines ambas, GOOGLE_API_KEY tiene prioridad)
GOOGLE_API_KEY=tu_api_key
# o
GEMINI_API_KEY=tu_api_key

# Modelo recomendado
GEMINI_MODEL=gemini-2.5-flash
```

> **No** subas `.env` al repo (está en `.gitignore`).

---

## Servidores MCP

Archivo: **`app/config_servers.json`**

```json
{
  "fs": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "./work"]
  },
  "git": {
    "command": ".\\.venv\\Scripts\\python.exe",
    "args": ["-m", "mcp_server_git", "--repository", ".\\work"]
  },
  "local": {
    "command": ".\\.venv\\Scripts\\python.exe",
    "args": ["servers/my_local_srv.py"]
  }
}
```

> Crea la carpeta de trabajo e **inicializa Git** una vez:
```bash
mkdir work  # si no existe
git init .\work
```

---

## Ejecución

```bash
# Desde la raíz del proyecto
.\.venv\Scriptsctivate
python -m app.client
```

Verás algo como:
```
Conectando 'fs' -> npx [...]
✔ Conectado 'fs'
Conectando 'git' -> python -m mcp_server_git --repository .\work
✔ Conectado 'git'
Conectando 'local' -> python servers/my_local_srv.py
✔ Conectado 'local'

Chat listo (Gemini). Comandos: /tools, /reset, /logs, /demo, quit
```

---

## Comandos disponibles en el chat

- **`/tools`** — Lista todas las herramientas detectadas (`fs:*`, `git:*`, `local:*`).
- **`/demo`** — Ejecuta un flujo ejemplo con Filesystem y Git (crear repo, README, add, commit).
- **`/reset`** — Borra la memoria de conversación.
- **`/logs`** — Muestra las últimas líneas del log MCP.

Además, puedes conversar normalmente con el LLM para verificar **conexión** y **contexto**:
```
¿Quién fue Alan Turing?
¿Y en qué fecha nació?
```

---

## Demostración FS + Git

Dentro del chat, ejecuta:
```
/demo
```

El host le pide al LLM que use herramientas MCP para:
1. **filesystem** → escribir `work/README.md` con una descripción.
2. **git** → `init` (si hace falta), `add README.md`, `commit "init"`.

Verifica:
- Archivo creado: `work/README.md`
- Repo Git en `work/.git/`
- Entradas en `logs.jsonl` con `mcp_call` y `mcp_result`.

---

## Servidor MCP local (CFG Tools)

Archivo: **`servers/my_local_srv.py`**  
Expone, por ejemplo:
- `local:eliminate_epsilon` — Elimina producciones **ε** en una gramática libre de contexto.
- `local:cyk_parse` — Aplica el algoritmo **CYK** a una oración según la gramática.

Uso sugerido (desde el chat):
```
Usa local:eliminate_epsilon con:
S -> A B | a
A -> ε | a
B -> b | A
```

o

```
Usa local:cyk_parse con la misma gramática y la oración: a b
```

> El host transforma estas peticiones en llamadas MCP y devuelve los resultados al LLM.

---

## Memoria y Log

- **Memoria de conversación**: `conversation.json` (se persiste entre ejecuciones).
- **Log MCP**: `logs.jsonl` (cada línea es un JSON con `event`, `server`, `tool`, `args`, `result`, `ts`).

Desde el chat, puedes ver un tail rápido con **`/logs`**.

---

## Estructura del proyecto

```
.
├── app/
│   ├── __init__.py
│   ├── client.py               # Host (Gemini + MCP)
│   ├── config_servers.json     # Configuración de servers MCP
│   ├── logger.py               # Log JSONL
│   └── memory.py               # Persistencia de conversación
├── servers/
│   └── my_local_srv.py         # Servidor MCP local (CFG Tools)
├── work/                       # Carpeta de trabajo para FS/Git (ignorada en git)
├── .env                        # Claves/API/vars (ignorado)
├── conversation.json           # Memoria (ignorado)
├── logs.jsonl                  # Log MCP (ignorado)
├── requirements.txt
└── .gitignore
```

---

## Solución de problemas

**1) `Connection closed` al conectar Filesystem**  
- No usar `--allow`. El FS server acepta **rutas posicionales**: `@modelcontextprotocol/server-filesystem ./work`.

**2) Git server: “not a valid Git repository”**  
- Ejecuta una vez: `git init .\work`.

**3) npx tarda o “se queda pegado” la primera vez**  
- Es la descarga inicial. Puedes “precalentar” ejecutando manualmente:
  - `npx -y @modelcontextprotocol/server-filesystem .\work` (Ctrl+C para salir)
  - `python -m mcp_server_git --repository .\work` (Ctrl+C para salir)

**4) Error de Gemini por schemas (`$schema`, `additional_properties`, etc.)**  
- El host incluye un **sanitizador** que normaliza/elimina claves no soportadas.
- Asegúrate de tener `google-genai` actualizado: `pip install -U google-genai`.

**5) Variables de entorno no detectadas**  
- Usa `.env` en la raíz o PowerShell:
  - `$env:GEMINI_API_KEY="tu_key"`
  - (opcional) `$env:GOOGLE_API_KEY="tu_key"`

**6) OneDrive agrega latencia o bloqueos en `work`**  
- Prueba con una ruta local corta (p. ej., `C:\dev\work`) y actualiza `app/config_servers.json`.

---

¡Listo! Con esto puedes clonar, configurar y correr el proyecto sin sorpresas.
