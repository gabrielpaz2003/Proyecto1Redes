from typing import Dict, Any, Set, List
from ..mcp.client import MCPClient

def import_remote_tools(clients: Dict[str, MCPClient], openai_tools: List[dict]) -> Set[str]:
    names: Set[str] = set()
    if "Supabase" in clients:
        try:
            res = clients["Supabase"].list_tools()
            tools = res.get("result", {}).get("tools", [])
            for t in tools:
                # Añade como tool OpenAI tal cual
                openai_tools.append({"type":"function","function":t})
                n = t.get("name")
                if isinstance(n, str):
                    names.add(n)
        except Exception:
            pass
    return names

def exec_supabase_or_none(clients: Dict[str, MCPClient], tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    return clients["Supabase"].call(tool_name, args)
