# app/client.py  (Gemini + MCP, conexiones persistentes, debug y schema sanitizado)
import os, sys, json, asyncio
from typing import Dict, Any, List, Tuple
from contextlib import AsyncExitStack
from dotenv import load_dotenv

from app.memory import ConversationMemory
from app.logger import log

# Gemini SDK
from google import genai
from google.genai import types as gtypes

# MCP client (stdio)
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")   # usa el modelo más reciente
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Falta GEMINI_API_KEY en .env"); sys.exit(1)

SERVERS_CONFIG_PATH = os.getenv("MCP_SERVERS_CONFIG", "app/config_servers.json")
CONNECT_TIMEOUT = float(os.getenv("MCP_CONNECT_TIMEOUT", "60"))  # segundos

def _sanitize_schema_for_gemini(schema):
    """Elimina claves no soportadas por Gemini (ej. '$schema') y garantiza un objeto JSON Schema mínimo."""
    if not isinstance(schema, dict):
        return {"type": "object"}
    def strip_keys(x):
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                if isinstance(k, str) and k.startswith("$"):
                    continue
                out[k] = strip_keys(v)
            return out
        if isinstance(x, list):
            return [strip_keys(i) for i in x]
        return x
    cleaned = strip_keys(schema)
    if "type" not in cleaned:
        cleaned["type"] = "object"
    return cleaned

class HostChatGemini:
    def __init__(self):
        self.mem = ConversationMemory()
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()  # mantiene vivos los transports/sessions
        self.tool_index: Dict[str, Tuple[str, str]] = {}  # "ns:tool" -> (ns, tool)
        self.gemini_tools: List[gtypes.Tool] = []
        self.client = genai.Client(api_key=API_KEY)

    async def connect_from_config(self):
        print("CONFIG PATH:", SERVERS_CONFIG_PATH)
        try:
            cfg_text = open(SERVERS_CONFIG_PATH, "r", encoding="utf-8").read()
            print("CONFIG CONTENT:\n", cfg_text)
            cfg = json.loads(cfg_text)
        except Exception as e:
            print("[ERROR] No se pudo leer config_servers.json:", e)
            raise

        for name, spec in cfg.items():
            cmd, args = spec["command"], spec.get("args", [])
            print(f"Conectando '{name}' -> {cmd} {args}")
            await self._connect_one(name, cmd, args)
            print(f"✔ Conectado '{name}'")
        log("mcp_connect", servers=list(self.sessions.keys()), tools=list(self.tool_index.keys()))

    async def _connect_one(self, name: str, command: str, args: List[str]):
        transport = await self.exit_stack.enter_async_context(
            stdio_client(StdioServerParameters(command=command, args=args))
        )
        read, write = transport
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await asyncio.wait_for(session.initialize(), timeout=CONNECT_TIMEOUT)

        self.sessions[name] = session

        tools = (await session.list_tools()).tools
        print(f"[{name}] tools:", [t.name for t in tools])

        fdecls = []
        for t in tools:
            namespaced = f"{name}:{t.name}"
            self.tool_index[namespaced] = (name, t.name)

            raw_schema = t.inputSchema or {"type": "object"}
            params = _sanitize_schema_for_gemini(raw_schema)

            try:
                fdecls.append(gtypes.FunctionDeclaration(
                    name=namespaced,
                    description=t.description or "",
                    parameters=params
                ))
            except Exception as e:
                print(f"[WARN] Schema no soportado en {namespaced}: {e}. Usando {{'type':'object'}}.")
                fdecls.append(gtypes.FunctionDeclaration(
                    name=namespaced,
                    description=t.description or "",
                    parameters={"type": "object"}
                ))

        if fdecls:
            self.gemini_tools.append(gtypes.Tool(function_declarations=fdecls))

    async def close(self):
        await self.exit_stack.aclose()

    def _messages_for_gemini(self) -> List[gtypes.Content]:
        """Convierte nuestra memoria a la estructura de Gemini usando Part.from_text(...)."""
        contents: List[gtypes.Content] = []
        for m in self.mem.messages:
            role = m["role"]
            text = str(m["content"])
            part = gtypes.Part.from_text(text=text)
            if role == "user":
                contents.append(gtypes.Content(role="user", parts=[part]))
            elif role == "assistant":
                contents.append(gtypes.Content(role="model", parts=[part]))
        return contents

    async def _call_mcp_tool(self, ns_tool: str, args: Dict[str, Any]):
        ns, tool = ns_tool.split(":", 1)
        session = self.sessions[ns]
        log("mcp_call", server=ns, tool=tool, args=args)
        result = await session.call_tool(tool, arguments=args)
        payload = result.structuredContent or result.content
        log("mcp_result", server=ns, tool=tool, result=payload)
        return payload

    async def chat_once(self, user_text: str):
        # Comandos de utilidad
        if user_text.strip() == "/reset":
            self.mem.clear(); print(">> Memoria borrada."); return
        if user_text.strip() == "/tools":
            print(">> Tools:", list(self.tool_index.keys())); return
        if user_text.strip() == "/logs":
            try:
                with open("logs.jsonl","r",encoding="utf-8") as f:
                    print("".join(f.readlines()[-30:]))
            except FileNotFoundError:
                print("No hay logs aún.")
            return
        if user_text.strip() == "/demo":
            user_text = (
                "Usa herramientas MCP para crear un repo en ./work: "
                "1) filesystem escribe README.md con una descripción; "
                "2) git init; 3) git add README.md; 4) git commit 'init'. "
                "Explica cada paso y muestra los resultados."
            )

        self.mem.add("user", user_text)

        # 1) Primera pasada: Gemini decide si llamar funciones (tools via config)
        contents = self._messages_for_gemini()
        resp = self.client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=gtypes.GenerateContentConfig(
                tools=self.gemini_tools
            ),
        )

        output_chunks: List[str] = []
        pending_calls: List[Tuple[str, Dict[str, Any]]] = []
        function_call_contents: List[gtypes.Content] = []

        # Extraer texto y llamadas a funciones
        for cand in resp.candidates or []:
            function_call_contents.append(cand.content)  # conservar el bloque del modelo
            for part in cand.content.parts:
                if getattr(part, "text", None):
                    output_chunks.append(part.text)
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    pending_calls.append((fc.name, dict(fc.args or {})))

        # También soportar la API convenience: response.function_calls (si existe)
        for fc in getattr(resp, "function_calls", []) or []:
            pending_calls.append((fc.name, dict(getattr(fc.function_call, "args", {}) or {})))

        if not pending_calls:
            final = "\n".join(output_chunks).strip()
            if final:
                print("\n", final)
                self.mem.add("assistant", final)
            return

        # 2) Ejecutar herramientas MCP y construir function responses
        tool_outputs: List[gtypes.Content] = []
        for ns_tool, args in pending_calls:
            payload = await self._call_mcp_tool(ns_tool, args)
            fr_part = gtypes.Part.from_function_response(
                name=ns_tool,
                response={"content": payload}
            )
            tool_outputs.append(gtypes.Content(role="tool", parts=[fr_part]))

        # 3) Segunda pasada: modelo ve respuestas de tools y cierra
        contents2 = contents + function_call_contents + tool_outputs
        resp2 = self.client.models.generate_content(
            model=MODEL,
            contents=contents2,
            config=gtypes.GenerateContentConfig(
                tools=self.gemini_tools
            ),
        )

        for cand in resp2.candidates or []:
            for part in cand.content.parts:
                if getattr(part, "text", None):
                    output_chunks.append(part.text)

        final = "\n".join(output_chunks).strip()
        if final:
            print("\n", final)
            self.mem.add("assistant", final)

    async def run_cli(self):
        try:
            await self.connect_from_config()
        except Exception as e:
            print(f"[Fallo conectando servidores MCP] {e}")
            await self.close()
            return

        print("\nChat listo (Gemini). Comandos: /tools, /reset, /logs, /demo, quit\n")
        while True:
            try:
                q = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in ("quit", "exit"): break
            try:
                await self.chat_once(q)
            except Exception as e:
                log("error", message=str(e))
                print("[Error]", e)
        await self.close()

if __name__ == "__main__":
    asyncio.run(HostChatGemini().run_cli())
