# MCP Server: SQLScout (SQLite helper)

Este servidor MCP expone utilidades para **diagnóstico y optimización de SQL** (SQLite) desde el host `ChatBot_Host`.

## ¿Qué hace?
- `sql.load` — Carga un esquema SQL completo (texto .sql).
- `sql.explain` — Ejecuta **EXPLAIN QUERY PLAN** sobre una consulta.
- `sql.diagnose` — Revisión estática de una consulta.
- `sql.optimize` — Sugerencias de índices y reescrituras.
- `sql.apply` — Aplica DDL (CREATE/DROP INDEX, ALTER…).
- `sql.optimize_apply` — Compara plan antes/después aplicando DDL temporalmente.

## Configuración en `mcp_config.json`
```json
{
  "name": "SQLScout",
  "transport": "stdio",
  "command": "python",
  "args": ["-B", "-m", "src.server_mcp"],
  "cwd": "C:/UVG/PROYECTO1/MCP_Local/SQL_MCP",
  "env": {}
}
```

> Ajusta `cwd` a la ruta real del repo de tu server SQL.

## Smoke tests (desde el host)
En el CLI del host (`py -3.11 -m src.host_cli`):

### Atajos `:call`
```
:servers
:call SQLScout sql.load {"schema":"CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT); CREATE INDEX ix_users_name ON users(name);"}
:call SQLScout sql.explain {"query":"SELECT * FROM users WHERE name='Ana';"}
:call SQLScout sql.diagnose {"query":"SELECT * FROM users WHERE name='Ana';"}
:call SQLScout sql.optimize {"query":"SELECT * FROM users WHERE name='Ana';"}
:call SQLScout sql.apply {"ddl":"DROP INDEX IF EXISTS ix_users_name;"}
```

### Lenguaje natural
- “Carga este esquema de ejemplo con una tabla `users` y un índice por `name`; luego explícame el plan de la query `SELECT * FROM users WHERE name='Ana';`”  
- “Diagnostica y proponme optimizaciones para la consulta anterior, y si hay DDL seguro, aplícalo.”

## Problemas comunes
- **No se ve el servidor**: revisa `mcp_config.json` y reinicia el host.
- **Error de permisos**: verifica que `cwd` apunte a la carpeta del servidor y dependencias instaladas.
