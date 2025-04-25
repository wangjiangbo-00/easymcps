from typing import Any, Dict, Optional

from app.mcp_client import MCPClient
from app.tool.base import BaseTool, ToolResult


class MCPTool(BaseTool):
    server_name:str
    mcp_client: MCPClient
    """Wrapper for MCP server tools to integrate with the agent system"""



    def __init__(self, name: str,
                 server_name: str,
                 parameters: Dict,
                 description:str,
                 mcp_client: MCPClient, /, **data: Any):
        super().__init__(description=description,  # 显式传递必填字段
        name=name,
        server_name=server_name,
        parameters=parameters,
        mcp_client=mcp_client,**data)
        self.mcp_client = mcp_client
        self.server_name = server_name

    @property
    def name(self) -> str:
        return f"{self.name}.{self.name}"

    @property
    def parameters(self) -> Dict:
        # TODO: Get actual schema from MCP server
        return {"type": "object", "properties": {}, "required": []}
    async def execute(self, **kwargs) -> Any:
        result = {"observation": "", "success": False}
        try:
            call_respone = await self.mcp_client.sessions[self.server_name].call_tool(
                self.name, kwargs or {}
            )
            result["observation"] = call_respone
            return dict(result)
        except Exception as e:
            return dict(result)

    async def run(self, input: Optional[Dict] = None) -> ToolResult:
        try:
            result = await self.mcp_client.sessions[self.server_name].call_tool(
                self.name, input or {}
            )
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
