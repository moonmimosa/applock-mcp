import requests
from mcp.server.fastmcp import FastMCP

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

if __name__ == "__main__":
    mcp.run(transport="sse")
