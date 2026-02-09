from fastapi import WebSocket
from typing import Dict, Set
import json

class NotificationService:
    """Service to manage WebSocket connections and send notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a WebSocket client"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        print(f"✓ WebSocket connected for user: {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket client"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"✓ WebSocket disconnected for user: {user_id}")
    
    async def send_notification(self, user_id: str, notification: dict):
        """Send notification to a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(notification)
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast(self, notification: dict):
        """Broadcast notification to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_notification(user_id, notification)

# Global instance
notification_service = NotificationService()