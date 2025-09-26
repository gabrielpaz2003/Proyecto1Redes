# MCP Server: Git (Python)

Servidor MCP que expone comandos **Git** sobre un repo local.

## ¿Qué hace?
Comandos expuestos (entre otros): `git_init`, `git_status`, `git_add`, `git_commit`, `git_log`, `git_checkout`, etc.

## Configuración en `mcp_config.json`
```json
{
  "name": "Git",
  "transport": "stdio",
  "command": "py",
  "args": ["-3.11","-m","mcp_server_git","--repository","C:/UVG/PROYECTO1/MCP_Local"],
  "cwd": "."
}
```
> Ajusta `--repository` a la carpeta que deseas usar como repo.

## Smoke tests
### Atajos `:call`
```
:servers
:call Git git_init {}
:call Git git_status {}
:call Git git_add {"files":["README.md"]}
:call Git git_commit {"message":"chore: initial commit"}
:call Git git_log {"max_count":5}
```

### Lenguaje natural
- “Inicializa un repo en la carpeta configurada, crea un README y haz el primer commit.”
- “Muéstrame el estado y los últimos 3 commits.”

## Problemas comunes
- **No hay repo**: corre `git_init` primero.
- **No agrega archivos**: el host filtra rutas inseguras; pasa rutas relativas válidas.
