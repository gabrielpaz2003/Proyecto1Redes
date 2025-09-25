# src/host_cli.py
from __future__ import annotations

import json, uuid, typer
from typing import Any, Dict, List, Set

from .core.config import APP_TITLE, APP_VERSION, DEFAULT_SERVERS, settings
from .core.openai_client import build_openai_client, OPENAI_TOOLS, handle_tool_call
from .core.router import handle_colon_commands
from .core.ui import (
    banner, print_help, print_servers_table, prompt_user,
    print_error, print_note, chat_user, chat_assistant,
    start_thinking, stop_thinking
)
from .mcp.client import MCPClient
from .utils.memory import Memory
from .utils.logger import JSONLLogger
from .utils.jsonfmt import table_from_result
from .services.supabase import import_remote_tools

app = typer.Typer(help="Host CLI con UI mejorada (Rich) + tool-calling hacia MCP")
RAW_MODE = {"enabled": False}  # :raw alterna salida cruda del último tool

@app.callback(invoke_without_command=True)
def chat(server: str = typer.Option("SQLScout", help="Server MCP por defecto para atajos")):
    client, model = build_openai_client()
    memory = Memory()
    logger = JSONLLogger()

    # Conectar a servidores MCP declarados
    clients: Dict[str, MCPClient] = {}
    ok, fail = [], []
    for name in DEFAULT_SERVERS:
        try:
            clients[name] = MCPClient(server_name=name)
            ok.append(name)
        except Exception as e:
            fail.append(f"{name} → {e}")

    banner(APP_TITLE, APP_VERSION, model, logger.path)
    print_help()
    print_servers_table(clients, ok, fail)

    # Importar tools remotas desde Supabase (si está)
    remote_supabase: Set[str] = import_remote_tools(clients, OPENAI_TOOLS)

    # Prompt de sistema
    system_prompt = (
        "Eres un asistente con acceso a FS, Git y SQL (SQLScout). "
        "Usa SIEMPRE herramientas cuando el usuario pida acciones.\n"
        "FS: fs_create_dir, fs_write_text, fs_move, fs_list, fs_read_text, fs_trash_delete "
        "(rutas relativas a WORKSPACE_ROOT). "
        "Git: git_init_here, git_add_files, git_commit_msg, git_status_here, git_log_here "
        "(en REPO_ROOT, nunca 'add all'). "
        "SQL: sql_load, sql_explain, sql_diagnose, sql_optimize, sql_apply, sql_optimize_apply.\n"
        "Supabase: usa tools remotas si están disponibles (create_user, send_magic_link, etc.).\n"
        "Encadena herramientas cuando haga falta (crear archivo + commit, etc.)."
    )
    memory.add("system", system_prompt)

    print_note("Escribe tu mensaje o un comando (:help).")
    last_tool_raw: str | None = None  # para :raw

    while True:
        user = prompt_user().strip()
        if not user:
            continue
        if user == ":quit":
            break

        # Comandos de consola (no mostramos burbuja de chat)
        handled, extra = handle_colon_commands(
            user=user,
            clients=clients,
            default_server=server,
            openai_tools=OPENAI_TOOLS,
            raw_state=RAW_MODE,
        )
        if handled:
            logger.log({"event":"colon_cmd","cmd":user})
            if isinstance(extra, str) and extra.startswith("__RAW__"):
                last_tool_raw = extra.removeprefix("__RAW__")
            if user in (":servers", ":tools"):
                print_servers_table(clients, ok, fail)
            continue

        # Mostrar tu mensaje como "burbuja"
        chat_user(user)

        # === Chat + Tool Calling ===
        messages: List[Dict[str, Any]] = memory.dump() + [{"role":"user","content":user}]
        start_thinking("Pensando…")
        try:
            reply = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=600
            )
        except Exception as e:
            stop_thinking()
            print_error(str(e))
            continue

        msg = reply.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            tool_results_msgs = []
            for tc in tool_calls:
                t_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}

                try:
                    mcp_resp = handle_tool_call(t_name, args, clients, remote_supabase)
                    raw_payload = json.dumps(mcp_resp, ensure_ascii=False, indent=2)
                    last_tool_raw = raw_payload

                    content = raw_payload if RAW_MODE["enabled"] else table_from_result(
                        mcp_resp.get("result", mcp_resp)
                    )
                    tool_results_msgs.append({
                        "role": "tool",
                        "tool_call_id": getattr(tc, "id", str(uuid.uuid4())),
                        "content": content
                    })
                except Exception as e:
                    tool_results_msgs.append({
                        "role": "tool",
                        "tool_call_id": getattr(tc, "id", str(uuid.uuid4())),
                        "content": f"ERROR ejecutando {t_name}: {e}"
                    })

            # Segunda pasada con resultados de tools
            try:
                follow = client.chat.completions.create(
                    model=model,
                    messages=messages + [
                        {"role":"assistant","content":msg.content or "", "tool_calls":[tc.__dict__ for tc in tool_calls]}
                    ] + tool_results_msgs,
                    temperature=0.2,
                    max_tokens=600
                )
                final_text = follow.choices[0].message.content or ""
            finally:
                stop_thinking()

            chat_assistant(final_text)
            memory.add("user", user)
            memory.add("assistant", final_text)
            logger.log({"event":"chat+tools","user":user,"assistant":final_text,"raw":bool(RAW_MODE["enabled"])})
        else:
            stop_thinking()
            text = msg.content or ""
            chat_assistant(text)
            memory.add("user", user)
            memory.add("assistant", text)
            logger.log({"event":"chat","user":user,"assistant":text})

    for c in clients.values():
        try: c.close()
        except: pass

    print_note("Chat finalizado.")

if __name__ == "__main__":
    app()
