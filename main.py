import asyncio
import json
import os

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from starlette.requests import Request

from mock_data import ACCOUNTS, ORDERS
from system_prompt import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, dispatch_tool

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime-2"

NO_CACHE = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

app = FastAPI(title="Snapdeal Voice Bot")


@app.get("/")
async def root():
    return FileResponse("static/index.html", headers=NO_CACHE)


@app.get("/app")
async def app_fresh():
    return FileResponse("static/index.html", headers=NO_CACHE)


@app.get("/static/app.js")
async def serve_app_js():
    return FileResponse("static/app.js", media_type="application/javascript", headers=NO_CACHE)


@app.get("/static/style.css")
async def serve_style_css():
    return FileResponse("static/style.css", media_type="text/css", headers=NO_CACHE)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/mock-data")
async def mock_data_endpoint():
    return {"orders": ORDERS, "accounts": ACCOUNTS}


@app.websocket("/ws")
async def websocket_proxy(client_ws: WebSocket):
    await client_ws.accept()

    api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)
    if not api_key:
        await client_ws.send_text(json.dumps({"type": "error", "message": "OPENAI_API_KEY is not configured on the server."}))
        await client_ws.close()
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        async with websockets.connect(REALTIME_URL, extra_headers=headers) as openai_ws:
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "instructions": SYSTEM_PROMPT,
                    "tools": TOOL_SCHEMAS,
                    "tool_choice": "auto",
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcm", "rate": 24000},
                            "transcription": {"model": "whisper-1"},
                            "turn_detection": None,
                        },
                        "output": {
                            "format": {"type": "audio/pcm", "rate": 24000},
                            "voice": "marin",
                        },
                    },
                },
            }))

            async def client_to_openai():
                try:
                    while True:
                        data = await client_ws.receive_text()
                        await openai_ws.send(data)
                except (WebSocketDisconnect, Exception):
                    pass

            async def openai_to_client():
                try:
                    async for raw in openai_ws:
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        event_type = event.get("type", "")

                        if event_type == "response.function_call_arguments.done":
                            name = event.get("name", "")
                            args = json.loads(event.get("arguments", "{}"))
                            result = dispatch_tool(name, args)

                            if name == "connect_to_agent":
                                await client_ws.send_text(json.dumps({
                                    "type": "agent_connect",
                                    "data": result,
                                }))

                            await openai_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": event.get("call_id", ""),
                                    "output": json.dumps(result),
                                },
                            }))
                            await openai_ws.send(json.dumps({"type": "response.create"}))
                        elif event_type != "response.function_call_arguments.delta":
                            await client_ws.send_text(json.dumps(event))
                except Exception:
                    pass

            t1 = asyncio.create_task(client_to_openai())
            t2 = asyncio.create_task(openai_to_client())
            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    except Exception as e:
        try:
            await client_ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
