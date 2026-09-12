"""
Core Events

Socket.IO event emitter for real-time updates for Lead Agent.
"""

import socketio

# Global Socket.IO async server instance
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[],
    logger=False,
    engineio_logger=False,
)

# Socket.IO ASGI app wrapper
socket_app = socketio.ASGIApp(sio, socketio_path="/socket.io")


async def emit_event(event: str, data: dict, room: str | None = None):
    """Emit a Socket.IO event to connected clients."""
    if room:
        await sio.emit(event, data, room=room)
    else:
        await sio.emit(event, data)


# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"Socket.IO client connected: {sid}")


@sio.event
async def disconnect(sid, *args):
    """Handle client disconnection."""
    print(f"Socket.IO client disconnected: {sid}")


@sio.event
async def join_workspace(sid, data):
    """Join a room for scoped events. For Lead Agent, we use a global room or workspace room."""
    workspace_id = data.get("workspace_id", "lead_agent")
    if workspace_id:
        await sio.enter_room(sid, workspace_id)
        # Also join the generic lead_agent room
        await sio.enter_room(sid, "lead_agent")
        await sio.emit("joined", {"workspace_id": workspace_id}, room=sid)
