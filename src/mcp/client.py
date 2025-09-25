import json, subprocess, uuid, os, requests
from typing import Any, Dict

class MCPConfigError(Exception): ...

class MCPClient:
    def __init__(self, config_path: str = "mcp_config.json", server_name: str = "SQLScout"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        servers = cfg.get("servers", [])
        match = next((s for s in servers if s.get("name") == server_name), None)
        if not match:
            raise MCPConfigError(f"Server '{server_name}' no encontrado en {config_path}")

        self.server_name = server_name
        self.transport = match.get("transport", "stdio")
        self.proc = None
        if self.transport == "stdio":
            self._init_stdio(match)
        elif self.transport == "http":
            self._init_http(match)
        else:
            raise MCPConfigError(f"Transporte '{self.transport}' no soportado")

    def _id(self) -> str:
        return str(uuid.uuid4())

    # ---- stdio ----
    def _init_stdio(self, config: Dict[str, Any]):
        cmd = [config["command"]] + config.get("args", [])
        cwd = config.get("cwd", ".")
        env = os.environ.copy()
        env.update(config.get("env", {}))
        env["PYTHONIOENCODING"] = "utf-8"; env["PYTHONUTF8"] = "1"

        self.proc = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1
        )

        self._send_stdio({
            "jsonrpc": "2.0", "id": self._id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "host-cli", "version": "1.0"},
                "capabilities": {}
            }
        })
        self._read_stdio()
        self._send_stdio({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def _send_stdio(self, obj: Dict[str, Any]):
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _read_stdio(self) -> Dict[str, Any]:
        assert self.proc and self.proc.stdout
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"Sin respuesta del servidor.\nSTDERR:\n{err}")
        return json.loads(line)

    # ---- http ----
    def _init_http(self, config: Dict[str, Any]):
        self.base_url = config.get("url", "").rstrip("/")
        self.endpoint = config.get("endpoint", "/mcp")
        self.timeout = config.get("timeout", 30)
        self.headers = {"Content-Type": "application/json"}
        if not self.base_url:
            raise MCPConfigError("URL es requerida para transporte HTTP")

        self._send_http({
            "jsonrpc": "2.0", "id": self._id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "host-cli", "version": "1.0"},
                "capabilities": {}
            }
        })
        try:
            self._send_http({"jsonrpc": "2.0","method":"notifications/initialized","params":{}})
        except: pass

    def _send_http(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        url = f"{self.base_url}{self.endpoint}"
        r = requests.post(url, json=obj, headers=self.headers, timeout=self.timeout)
        if r.status_code == 204:
            return {"result": "notification sent"}
        r.raise_for_status()
        return r.json()

    # ---- API ----
    def list_tools(self) -> Dict[str, Any]:
        req = {"jsonrpc": "2.0","id": self._id(),"method":"tools/list","params":{}}
        if self.transport == "stdio":
            self._send_stdio(req); return self._read_stdio()
        return self._send_http(req)

    def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        req = {"jsonrpc":"2.0","id": self._id(),"method":"tools/call","params":{"name":name,"arguments":arguments}}
        if self.transport == "stdio":
            self._send_stdio(req); return self._read_stdio()
        return self._send_http(req)

    def close(self):
        if self.transport == "stdio" and self.proc:
            try: self.proc.terminate()
            except: pass
