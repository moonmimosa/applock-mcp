import os
import requests
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn

# 创建底层 MCP Server（比 FastMCP 更稳定）
server = Server("applock")

EDGE_URL = "https://akhfjfiznrpzlyciuemr.supabase.co/functions/v1/control"

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="control_app_lock",
            description="远程控制应用锁，锁定或解锁指定App",
            inputSchema={
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "应用名称，如抖音、小红书"},
                    "on": {"type": "boolean", "description": "true=锁定, false=解锁"}
                },
                "required": ["app", "on"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "control_app_lock":
        return [TextContent(type="text", text=f"未知工具: {name}")]
    
    app = arguments.get("app", "")
    on = arguments.get("on", False)
    
    try:
        url = f"{EDGE_URL}?app={app}&on={str(on).lower()}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("ok"):
            result = f"{'🔒 已锁定' if on else '🔓 已解锁'} {app}！"
        else:
            result = f"操作失败：{data.get('error')}"
    except Exception as e:
        result = f"出错：{str(e)}"
    
    return [TextContent(type="text", text=result)]

# SSE 路由
sse = SseServerTransport("/messages")

async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request.send
    ) as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)

app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
