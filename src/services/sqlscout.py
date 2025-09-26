#src/services/sqlscout.py
from typing import Dict, Any
from ..mcp.client import MCPClient

def exec_sql(clients: Dict[str, MCPClient], mcp_method: str, args: Dict[str, Any]) -> Dict[str, Any]:
    return clients["SQLScout"].call(mcp_method, args)
