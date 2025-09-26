# MCP Server: SiteLens (Auditoría de HTML estático)

Servidor MCP **local por STDIO** para auditar carpetas de HTML estático sin salir a la red.

## ¿Qué hace?
Tools disponibles:
- `aa.allowed_roots` — Lista de roots permitidas.
- `aa.sitemap` — Árbol de archivos (opciones `includeHtmlOnly`, `maxDepth`).
- `aa.link_check` — Valida **links internos** (externos `status:"skipped"`).
- `aa.asset_budget` — Resumen de assets (totales, top pesados, sobre presupuesto).
- `aa.scan_accessibility` — Reglas WCAG-lite: alt text, labels, landmarks, headings order, contraste inline simple.
- `aa.report` — Consolida lo anterior (ranking 0–100 y quick wins).

## Configuración en `mcp_config.json`
```json
{
  "name": "SiteLens",
  "transport": "stdio",
  "command": "node",
  "args": [
    "C:/UVG/PROYECTO1/MCP_Local/sitelens/dist/server.js",
    "--roots",
    "C:/UVG/PROYECTO1/MCP_Local/test/site"
  ]
}
```
> Asegúrate de que `--roots` incluya la carpeta que deseas auditar.

## Carpeta de prueba
En tu caso: `C:/UVG/PROYECTO1/MCP_Local/test/site` con archivos como:
- `index.html`, `about.html`, `contact.html`, `page2.html`, `assets/styles.css`, `images/logo.png` (faltante a propósito).

## Smoke tests
### Atajos `:call`
```
:servers
:call SiteLens aa.allowed_roots {}
:call SiteLens aa.sitemap {"path":"C:/UVG/PROYECTO1/MCP_Local/test/site","includeHtmlOnly":true,"maxDepth":3}
:call SiteLens aa.scan_accessibility {"path":"C:/UVG/PROYECTO1/MCP_Local/test/site"}
:call SiteLens aa.link_check {"path":"C:/UVG/PROYECTO1/MCP_Local/test/site"}
:call SiteLens aa.asset_budget {"path":"C:/UVG/PROYECTO1/MCP_Local/test/site","budgetKB":200}
:call SiteLens aa.report {"path":"C:/UVG/PROYECTO1/MCP_Local/test/site","top":10}
```

### Lenguaje natural (ejemplos que ya funcionaron)
- “Muéstrame la lista de rutas permitidas (allowed roots) que ve SiteLens.”
- “Con SiteLens, genera un sitemap de `C:/UVG/PROYECTO1/MCP_Local/test/site` incluyendo solo HTML y con profundidad máxima 3; preséntalo en tabla.”
- “Ejecuta una auditoría de accesibilidad con SiteLens sobre `C:/UVG/PROYECTO1/MCP_Local/test/site` y muéstrame la tabla de archivos con el conteo por severidad.”
- “Pasa el verificador de links internos de SiteLens en `C:/UVG/PROYECTO1/MCP_Local/test/site` y resúmeme los enlaces rotos en una tabla (archivo, link, estado).”
- “Calcula el presupuesto de assets del sitio en `C:/UVG/PROYECTO1/MCP_Local/test/site` usando un límite de 200 KB; dame el total por tipo, los más pesados y los que superan el presupuesto.”
- “Genera un reporte consolidado con SiteLens para `C:/UVG/PROYECTO1/MCP_Local/test/site` y muéstrame el ranking top 10 y quick wins.”
- “Usa SiteLens para: 1) sitemap (profundidad 3), 2) accesibilidad, 3) links, 4) assets 200 KB, 5) reporte top 10; presenta cada resultado en su tabla.”

## Consejos de uso
- Si el modelo “responde de memoria”, recuerda que el host ya inyecta tools **sitelens__*** para guiar el tool-calling; pregunta en una sola oración y con el **path** explícito para forzar la intención.
- Habilita `:raw` si quieres ver los payloads JSON crudos que el host recibe del servidor.

## Problemas comunes
- **Acceso fuera de roots (-32000)**: ajusta `--roots` o usa una ruta incluida ahí.
- **No muestra tools**: revisa `mcp_config.json` y reinicia el host.
