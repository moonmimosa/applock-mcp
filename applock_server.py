import os
import json
import requests
import asyncio
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EDGE_URL = "https://akhfjfiznrpzlyciuemr.supabase.co/functions/v1/control"
API_KEY = "sb_publishable_LvNP1g3Y7kXp1CL-x3jdGQ_1y_hnlWb"

queues = {}

@app.get("/sse")
async def sse():
    session_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    queues[session_id] = queue

    async def event_stream():
        yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {msg}\n\n"
            except asyncio.TimeoutError:
                yield ": ping\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/messages")
async def messages(request: Request):
    session_id = request.query_params.get("session_id")
    data = await request.json()
    asyncio.create_task(process_message(session_id, data))
    return JSONResponse(content={"status": "ok"}, status_code=202)

async def process_message(session_id, data):
    try:
        method = data.get("method")
        req_id = data.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "applock", "version": "1.0.0"}
                }
            }
        elif method == "initialized":
            return
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [{
                        "name": "control_app_lock",
                        "description": "远程控制应用锁，锁定或解锁指定App。参数：app(应用名如抖音), on(true锁定/false解锁)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "app": {"type": "string", "description": "应用名称，如抖音、小红书"},
                                "on": {"type": "boolean", "description": "true表示锁定，false表示解锁"}
                            },
                            "required": ["app", "on"]
                        }
                    }]
                }
            }
        elif method == "tools/call":
            params = data.get("params", {})
            arguments = params.get("arguments", {})
            app = arguments.get("app", "")
            on = arguments.get("on", False)

            try:
                url = f"{EDGE_URL}?app={app}&on={str(on).lower()}"
                headers = {
                    "apikey": API_KEY,
                    "Authorization": f"Bearer {API_KEY}"
                }
                r = requests.get(url, headers=headers, timeout=10)
                result_data = r.json()
                if result_data.get("ok"):
                    result_text = f"{'🔒 已锁定' if on else '🔓 已解锁'} {app}！"
                else:
                    result_text = f"操作失败：{result_data.get('error')}"
            except Exception as e:
                result_text = f"出错：{str(e)}"

            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False
                }
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"}
            }

        if session_id in queues:
            await queues[session_id].put(json.dumps(response))
    except Exception as e:
        print(f"Error: {e}")
        if session_id in queues:
            error_response = {
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {"code": -32603, "message": str(e)}
            }
            await queues[session_id].put(json.dumps(error_response))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
