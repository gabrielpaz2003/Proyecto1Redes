#src/core/router.py
from __future__ import annotations
from typing import Dict, Tuple, Optional, Any
import json

from .ui import (
    clear_screen, print_note, print_error, print_help, print_json
)
from ..utils.jsonfmt import table_from_result


def _print_tool_response(resp: Dict[str, Any], raw_state: Optional[dict]) -> Optional[str]:
    """
    Imprime una respuesta de tool. Si :raw está ON, devolvemos un string especial
    '__RAW__<json>' para que el caller lo recuerde como 'último payload crudo'.
    """
    if raw_state and raw_state.get("enabled"):
        return "__RAW__" + json.dumps(resp, ensure_ascii=False, indent=2)

    # Normalizamos contenido “tabulable”
    payload = resp.get("result", resp) if isinstance(resp, dict) else resp
    try:
        text = table_from_result(payload.get("result", payload))
        # table_from_result devuelve texto tipo tabla (str) o una cadena vacía
        # Si no es tabulable, caemos a JSON bonito
        if text.strip():
            print_note(text)
        else:
            print_json(payload)
    except Exception:
        print_json(payload)
    return None


def handle_colon_commands(
    user: str,
    clients: Dict[str, Any],
    default_server: str,
    openai_tools: Optional[list] = None,
    raw_state: Optional[dict] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Procesa comandos enviados con prefijo ':'.
    Devuelve (handled, extra). Si handled=True, el caller no envía el prompt al LLM.
    'extra' puede devolver '__RAW__<json>' si queremos propagar el último payload crudo.
    """
    if not user.startswith(":"):
        return False, None

    # --- comandos simples ---
    cmd = user.strip().split()[0]

    if cmd == ":help":
        print_help()
        return True, None

    if cmd == ":clear":
        clear_screen()
        return True, None

    if cmd in (":servers", ":tools"):
        # El caller (host_cli) repinta la tabla de servidores.
        return True, None

    if cmd == ":raw":
        if raw_state is None:
            print_error("Modo :raw no disponible.")
            return True, None
        raw_state["enabled"] = not raw_state.get("enabled", False)
        print_note(f"Modo RAW {'[ON]' if raw_state['enabled'] else '[OFF]'}")
        return True, None

    # --- :call <Server> <tool> <json_args?>
    if cmd == ":call":
        parts = user.strip().split(maxsplit=3)
        if len(parts) < 3:
            print_error("Uso: :call <Servidor> <tool> {JSON_opcional}")
            return True, None

        server = parts[1]
        tool = parts[2]
        arg_str = parts[3] if len(parts) > 3 else "{}"

        if server not in clients:
            print_error(f"Servidor '{server}' no está disponible. Usa :servers.")
            return True, None

        try:
            args = json.loads(arg_str) if arg_str else {}
            if not isinstance(args, dict):
                raise ValueError("Los argumentos deben ser un objeto JSON.")
        except Exception as e:
            print_error(f"JSON inválido: {e}")
            return True, None

        try:
            resp = clients[server].call(tool, args)
        except Exception as e:
            print_error(f"Error llamando {server}.{tool}: {e}")
            return True, None

        extra = _print_tool_response(resp, raw_state)
        return True, extra

    # --- no reconocido ---
    print_error(f"Comando desconocido: {cmd}. Usa :help")
    return True, None
