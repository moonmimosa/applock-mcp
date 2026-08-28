import os
import requests
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
import uvicorn

mcp = FastMCP("applock")

EDGE_URL = "https://akhfjfiznrpzlyciuemr.supabase.co/functions/v1/control"

@mcp.tool()
def control_app_lock(app: str, on: bool) -> str:
    """
    远程控制应用锁，锁定或解锁指定App。
    """
    try:
        url = f"{EDGE_URL}?app={app}&on={str(on).lower()}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get("ok"):
            return f"{'🔒 已锁定' if on else '🔓 已解锁'} {app}！"
        return f"操作失败：{data.get('error')}"
    except Exception as e:
        return f"出错：{str(e)}"

sse = SseServerTransport("/messages")

async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request.send
    ) as (read_stream, write_stream):
        await mcp._server.run(
            read_stream, write_stream, mcp._server.create_initialization_options()
        )

app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
