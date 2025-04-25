import json
import os
import subprocess
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Dict, List, Optional

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from mcp.types import ListToolsResult
from app.logger import logger

class MCPClient:
    def __init__(self, config_path: str = "config/test_mcp_settings.json"):
        self.config_path = Path(config_path)
        self.servers: Dict[str, subprocess.Popen] = {}
        self.tools: Dict[str, List[Tool]] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.states: Dict[str, bool] = {}
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.load_config()

    def load_config(self) -> Dict:
        """Load MCP server configurations"""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def start_server(self, server_name: str, server_config: Dict) -> bool:
        """Start an MCP server"""

        if server_config.get("disabled", False):
            return False

        try:
            # Parse args and env from JSON strings if needed
            args = server_config.get("args", None)
            if args and isinstance(args, str):
                args = json.loads(args)

            env = server_config.get("env", {})
            if env and isinstance(env, str):
                env = json.loads(env)

            cmd = server_config.get("cmd")
            if cmd == "python":
                cmd = sys.executable
            else:
                if getattr(sys, "frozen", False):
                    base_path = sys._MEIPASS  # 打包后的临时资源目录:
                else:
                    base_path = os.path.dirname(__file__)
                if "app" in base_path:
                    cmd = os.path.join(base_path, "nodejs", "node.exe")
                else:
                    cmd = os.path.join(base_path, "app", "nodejs", "node.exe")
                print("base_path=" + base_path)
                parent_dir = os.path.dirname(base_path)
                for i in range(len(args)):
                    args[i] = os.path.join(parent_dir,"servers", args[i])
                    logger.info("args=" + args[i])
            logger.info("cmd=" + cmd)
            # cmd = sys.executable

            server_params = StdioServerParameters(
                command=cmd,
                args=args if args else None,
                env=env if env else {},
            )
            print("args=" + args[i])

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.sessions[server_name] = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.sessions[server_name].initialize()

            response = await self.sessions[server_name].list_tools()
            tools = response.tools

            self.tools[server_name] = tools
            self.states[server_name] = True
            return True

        except Exception as e:
            print(f"Failed to start server {server_name}: {e}")
            self.states[server_name] = False
            return False

    def stop_server(self, server_name: str) -> bool:
        """Stop an MCP server"""

        try:
            self.states[server_name] = False

            return True
        except Exception as e:
            print(f"Failed to stop server {server_name}: {e}")
            return False

    def get_server_status(self, server_name: str) -> bool:
        """Get server status and tools"""
        return self.states[server_name] if server_name in self.states else False

    async def refresh_all_servers(self):
        """Refresh all servers based on config"""
        config = self.load_config()
        for server_name in config.get("mcpServers", {}):
            if not config["mcpServers"][server_name].get("disabled", False):
                await self.start_server(server_name)
            else:
                self.stop_server(server_name)
