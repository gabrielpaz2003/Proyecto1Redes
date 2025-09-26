# MCP Server: Filesystem (oficial Anthropic)

Servidor MCP oficial para operaciones de **sistema de archivos** dentro de rutas permitidas.

## ¿Qué hace?
- Crear directorios y archivos, leer archivos de texto y binarios, mover, listar, buscar.
- El host usa estos métodos como **FS** (p. ej., `create_directory`, `write_file`, `list_directory`, etc.).

## Configuración en `mcp_config.json`
```json
{
  "name": "FS",
  "transport": "stdio",
  "command": "C:/Program Files/nodejs/npx.cmd",
  "args": ["-y","@modelcontextprotocol/server-filesystem","C:/UVG/PROYECTO1/MCP_Local"],
  "cwd": ".",
  "env": {}
}
```
> Cambia la ruta al directorio raíz permitido si lo deseas.

## Smoke tests
### Atajos `:call`
```
:servers
:call FS list_allowed_directories {}
:call FS create_directory {"path":"C:/UVG/PROYECTO1/MCP_Local/demo"}
:call FS write_file {"path":"C:/UVG/PROYECTO1/MCP_Local/demo/README.txt","content":"hola FS"}
:call FS read_text_file {"path":"C:/UVG/PROYECTO1/MCP_Local/demo/README.txt"}
:call FS move_file {"source":"C:/UVG/PROYECTO1/MCP_Local/demo/README.txt","destination":"C:/UVG/PROYECTO1/MCP_Local/demo/README.moved.txt"}
:call FS list_directory {"path":"C:/UVG/PROYECTO1/MCP_Local/demo"}
```

### Lenguaje natural
- “Crea una carpeta `demo` en el root permitido y guarda un archivo `README.txt` con el texto ‘hola FS’; después muévelo y muéstrame el listado.”

## Problemas comunes
- **Acceso fuera de root**: debes usar rutas dentro de la raíz configurada en los args del servidor.
