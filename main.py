import asyncio
import json
import os

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from system_prompt import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, dispatch_tool

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"

app = FastAPI(title="Snapdeal Voice Bot")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_proxy(client_ws: WebSocket):
    await client_ws.accept()

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    try:
        async with websockets.connect(REALTIME_URL, additional_headers=headers) as openai_ws:
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],
                    "instructions": SYSTEM_PROMPT,
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": None,
                    "tools": TOOL_SCHEMAS,
                    "tool_choice": "auto",
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
                        event = json.loads(raw)
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
                                    "call_id": event["call_id"],
                                    "output": json.dumps(result),
                                },
                            }))
                            await openai_ws.send(json.dumps({"type": "response.create"}))
                        else:
                            await client_ws.send_text(json.dumps(event))
                except Exception:
                    pass

            await asyncio.gather(client_to_openai(), openai_to_client())

    except Exception as e:
        try:
            await client_ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
