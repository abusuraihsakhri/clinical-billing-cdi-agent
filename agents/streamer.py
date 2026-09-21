"""Minimal WebSocket event broadcaster used by optional API integrations."""
import json
from typing import Any, Dict, List


class TelemetryBroadcaster:
    """Broadcast structured application events to connected WebSocket clients."""

    def __init__(self):
        self.active_connections: List[Any] = []

    async def connect(self, websocket: Any):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: Any):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        message = json.dumps({
            "system": "clinical-billing-cdi-agent",
            "event_type": event_type,
            "payload": data,
        })
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


GLOBAL_STREAMER = TelemetryBroadcaster()
