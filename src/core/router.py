from __future__ import annotations
from typing import Dict, Tuple, Optional, Set, Any

from .ui import clear_screen, print_note, print_error, print_help

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
    'extra' puede devolver un string especial como '__RAW__<json>' si se quiere propagar.
    """
    if not user.startswith(":"):
        return False, None

    cmd = user.strip().split()[0]

    if cmd == ":help":
        print_help()
        return True, None

    if cmd == ":clear":
        clear_screen()
        # no volvemos a imprimir aquí nada más; el caller decide si repinta banner/tablas
        return True, None

    if cmd in (":servers", ":tools"):
        # El caller (host_cli) se encarga de imprimir la tabla de servidores.
        return True, None

    if cmd == ":raw":
        if raw_state is None:
            print_error("Modo :raw no disponible.")
            return True, None
        raw_state["enabled"] = not raw_state.get("enabled", False)
        print_note(f"Modo RAW {'[ON]' if raw_state['enabled'] else '[OFF]'}")
        return True, None

    # comandos no reconocidos
    if cmd.startswith(":"):
        print_error(f"Comando desconocido: {cmd}. Usa :help")
        return True, None

    return False, None
