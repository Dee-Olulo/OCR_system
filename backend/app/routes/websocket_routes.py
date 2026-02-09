from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.notification_service import notification_service

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await notification_service.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back (optional)
            await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        notification_service.disconnect(websocket, user_id)