# src/core/ui.py
from __future__ import annotations

from typing import Dict, List, Optional, Union
import json
import contextlib

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.align import Align
from rich.prompt import Prompt
from rich.status import Status

# ---------- Consola y tema ----------
_theme = Theme(
    {
        "title": "bold cyan",
        "subtitle": "cyan",
        "ok": "bold green",
        "warn": "yellow",
        "error": "bold red",
        "note": "bright_black",
        "user": "bold bright_green",
        "assistant": "bold bright_cyan",
        "dim": "bright_black",
        "box": "cyan",
        "kbd": "bold white on #444444",
    }
)
console = Console(theme=_theme)

# ---------- Estado global del spinner ----------
_ACTIVE_STATUS: Optional[Status] = None

# ---------- Utilidades visuales ----------
def _panel(title: str, body: str) -> Panel:
    return Panel(body, border_style="box", title=title, title_align="center")

def clear_screen() -> None:
    console.clear()

def print_error(msg: str) -> None:
    console.print(_panel("Error", f"[error]{msg}[/error]"))

def print_note(msg: str) -> None:
    console.print(_panel("Nota", f"[note]{msg}[/note]"))

def print_json(data: Union[dict, list, str]) -> None:
    """Imprime JSON bonito (lo usa :raw y algunos comandos)."""
    if isinstance(data, (dict, list)):
        console.print_json(data=data, indent=2, sort_keys=False)
    else:
        # data ya es string (posiblemente JSON)
        try:
            console.print_json(data, indent=2, sort_keys=False)
        except Exception:
            console.print(str(data))

# ---------- Cabecera y ayuda ----------
def banner(app_title: str, app_version: str, model: str, log_path: str) -> None:
    header = Table.grid(expand=True)
    header.add_column(justify="center")
    header.add_row(
        f"[title]{app_title}[/title]\n"
        f"[subtitle]Modelo: [bold]{model}[/bold]   log: [dim]{log_path}[/dim][/subtitle]"
    )
    console.print(Panel(header, border_style="box"))

def print_help() -> None:
    body = (
        "[b]:help[/b] — esta ayuda\n"
        "[b]:servers[/b] — servidores conectados y tools\n"
        "[b]:tools[/b] — alias de :servers\n"
        "[b]:raw[/b] — alterna mostrar JSON crudo del último resultado de tool\n"
        "[b]:clear[/b] — limpia la pantalla\n"
        "[b]:quit[/b] — salir"
    )
    console.print(_panel("Ayuda", body))

# ---------- Servidores ----------
def print_servers_table(clients: Dict[str, object], ok: List[str], fail: List[str]) -> None:
    table = Table(title="Servidores MCP", title_style="subtitle", expand=True, show_lines=True)
    table.add_column("Servidor", style="title", no_wrap=True)
    table.add_column("Tools", style="dim")

    # Conectados (ok)
    for name in ok:
        try:
            resp = clients[name].list_tools()  # type: ignore[attr-defined]
            tools = resp.get("result", {}).get("tools", [])
            names = ", ".join(sorted(t.get("name") for t in tools if isinstance(t, dict)))
            table.add_row(f"[ok]{name}[/ok]", names or "-")
        except Exception as e:
            table.add_row(f"[warn]{name}[/warn]", f"[warn]Error listando tools: {e}[/warn]")

    # Fallidos
    for entry in fail:
        if "→" in entry:
            server, err = entry.split("→", 1)
            table.add_row(f"[error]{server.strip()}[/error]", f"[error]{err.strip()}[/error]")
        else:
            table.add_row(f"[error]{entry}[/error]", "-")

    console.print(table)

# ---------- Entrada / Chat ----------
def prompt_user() -> str:
    # Prompt minimalista (lo que se muestra arriba del chat es la burbuja de usuario)
    return Prompt.ask("[dim]>>[/dim]")

def chat_user(text: str) -> None:
    console.print(
        Panel(
            Align.left(text),
            title="[user]Tú[/user]",
            border_style="green",
        )
    )

def chat_assistant(text: str) -> None:
    console.print(
        Panel(
            Align.left(text),
            title="[assistant]Asistente[/assistant]",
            border_style="cyan",
        )
    )

# ---------- Spinner “Pensando...” ----------
@contextlib.contextmanager
def thinking_spinner(text: str = "Pensando..."):
    """
    Uso:
        with thinking_spinner():
            ... llamada a la API ...
    """
    with console.status(f"[dim]{text}[/dim]", spinner="dots"):
        yield

def start_thinking(text: str = "Pensando...") -> None:
    """
    API imperativa (compat con host_cli.py):
      start_thinking("Analizando...")
      ... trabajo ...
      stop_thinking()
    """
    global _ACTIVE_STATUS
    # Si ya hay uno activo, primero lo detenemos
    if _ACTIVE_STATUS is not None:
        try:
            _ACTIVE_STATUS.stop()
        except Exception:
            pass
        _ACTIVE_STATUS = None

    _ACTIVE_STATUS = console.status(f"[dim]{text}[/dim]", spinner="dots")
    # Status es un context manager; para usarlo imperativamente, llamamos .start()
    _ACTIVE_STATUS.start()

def stop_thinking() -> None:
    global _ACTIVE_STATUS
    if _ACTIVE_STATUS is not None:
        try:
            _ACTIVE_STATUS.stop()
        except Exception:
            pass
        _ACTIVE_STATUS = None

# ---------- Alias para importar limpio ----------
__all__ = [
    "banner",
    "print_help",
    "print_servers_table",
    "prompt_user",
    "print_error",
    "print_note",
    "chat_user",
    "chat_assistant",
    "clear_screen",
    "print_json",
    "thinking_spinner",
    "start_thinking",
    "stop_thinking",
]
