"""
WebSocket routes
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from app.services.websocket_manager import WebsocketManager

router = APIRouter()

# This endpoint would handle websocket connections
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await WebsocketManager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo the received message back
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        WebsocketManager.disconnect(websocket, user_id)

# Test endpoint for WebSocket connections
@router.get("/test-websocket")
async def test_websocket():
    return {"message": "WebSocket endpoint is ready"}