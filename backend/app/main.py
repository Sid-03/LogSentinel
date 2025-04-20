import asyncio
import datetime 
import random 

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_health, routes_log

app = FastAPI(title="LogSentinel+")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_log.router)

# --- WebSocket log streaming ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

async def simulate_log_lines():
    levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
    messages = [
        "User logged in",
        "File uploaded",
        "Unexpected error occurred",
        "Connection timeout",
        "Job started",
        "Job completed",
        "Disk space low",
        "Service restarted",
        "Configuration updated",
        "Heartbeat received",
    ]
    while True:
        if manager.active_connections:
            now = datetime.datetime.utcnow().isoformat()
            level = random.choice(levels)
            msg = random.choice(messages)
            line = f"{now} [{level}] {msg}"
            await manager.broadcast(line)
        await asyncio.sleep(random.uniform(1, 3))

@app.on_event("startup")
async def start_log_simulator():
    asyncio.create_task(simulate_log_lines())

@app.websocket("/stream-log")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection open, ignore incoming
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)