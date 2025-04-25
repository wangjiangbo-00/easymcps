import json
import time
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP("TimeServer")

# 使用装饰器定义获取当前时间的工具函数
@mcp.tool()
def get_current_time():
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {"current_time": current_time}

# 运行 MCP 服务器
if __name__ == "__main__":
    mcp.run()
