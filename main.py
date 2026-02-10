import json
import asyncio
from typing import Any, Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

# Store map state
map_state = {
    "center": [0, 0],
    "zoom": 2
}

# Store connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Tool 1: Navigate to specific location
async def navigate_to_location(latitude: float, longitude: float) -> Dict[str, Any]:
    """Navigate the map to a specific latitude and longitude."""
    global map_state
    map_state["center"] = [longitude, latitude]  # OpenLayers uses [lon, lat]
    
    response = {
        "type": "tool_result",
        "tool": "navigate_to_location",
        "result": f"Map navigated to coordinates: {latitude}, {longitude}",
        "map_state": map_state.copy()
    }
    
    await manager.broadcast(json.dumps(response))
    return response

# Tool 2: Zoom to specific level
async def zoom_to_level(zoom_level: int) -> Dict[str, Any]:
    """Zoom the map to a specific level."""
    global map_state
    map_state["zoom"] = max(0, min(20, zoom_level))  # Clamp between 0 and 20
    
    response = {
        "type": "tool_result", 
        "tool": "zoom_to_level",
        "result": f"Map zoomed to level: {zoom_level}",
        "map_state": map_state.copy()
    }
    
    await manager.broadcast(json.dumps(response))
    return response

# Tool registry
TOOLS = {
    "navigate_to_location": navigate_to_location,
    "zoom_to_level": zoom_to_level
}

@app.get("/", response_class=HTMLResponse)
async def get():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>FastMCP Map App</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v7.5.2/ol.css">
    <script src="https://cdn.jsdelivr.net/npm/ol@v7.5.2/dist/ol.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }
        .container {
            display: flex;
            height: 100vh;
        }
        .map-container {
            flex: 1;
            height: 100%;
        }
        .chat-container {
            width: 350px;
            display: flex;
            flex-direction: column;
            border-left: 1px solid #ccc;
        }
        .chat-messages {
            flex: 1;
            padding: 10px;
            overflow-y: auto;
            background: #f9f9f9;
        }
        .chat-input {
            padding: 10px;
            border-top: 1px solid #ccc;
        }
        .chat-input input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .message {
            margin-bottom: 10px;
            padding: 8px;
            border-radius: 4px;
        }
        .user-message {
            background: #e3f2fd;
            text-align: right;
        }
        .system-message {
            background: #f3e5f5;
        }
        .tool-result {
            background: #e8f5e8;
        }
        #map {
            height: 100%;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="map-container">
            <div id="map"></div>
        </div>
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Type a command (e.g., 'navigate to 40.7128 -74.0060' or 'zoom to 10')">
            </div>
        </div>
    </div>

    <script>
        // Initialize OpenLayers map
        const map = new ol.Map({
            target: 'map',
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.OSM()
                })
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([0, 0]),
                zoom: 2
            })
        });

        // WebSocket connection
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            displayMessage(data.content, data.type);
            
            if (data.type === 'tool_result') {
                // Update map state based on tool result
                if (data.map_state) {
                    const center = ol.proj.fromLonLat(data.map_state.center);
                    map.getView().animate({
                        center: center,
                        zoom: data.map_state.zoom,
                        duration: 1000
                    });
                }
            }
        };

        function displayMessage(content, type) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.textContent = content;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            
            if (message) {
                displayMessage(message, 'user-message');
                ws.send(JSON.stringify({
                    type: 'chat_message',
                    content: message
                }));
                input.value = '';
            }
        }

        // Handle Enter key in input
        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Display welcome message
        displayMessage('Welcome! Try commands like:', 'system-message');
        displayMessage('• "navigate to 40.7128 -74.0060"', 'system-message');
        displayMessage('• "zoom to 10"', 'system-message');
    </script>
</body>
</html>
"""

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "chat_message":
                content = message["content"].lower()
                
                # Parse commands
                if "navigate to" in content or "go to" in content:
                    # Extract coordinates
                    import re
                    coords = re.findall(r'[-]?\d+\.?\d*', content)
                    if len(coords) >= 2:
                        lat = float(coords[0])
                        lon = float(coords[1])
                        result = await navigate_to_location(lat, lon)
                        await manager.send_personal_message(json.dumps({
                            "type": "tool_result",
                            "content": result["result"],
                            "map_state": result["map_state"]
                        }), websocket)
                    else:
                        await manager.send_personal_message(json.dumps({
                            "type": "system-message",
                            "content": "Please provide latitude and longitude coordinates."
                        }), websocket)
                        
                elif "zoom to" in content or "zoom" in content:
                    # Extract zoom level
                    import re
                    zoom_levels = re.findall(r'\d+', content)
                    if zoom_levels:
                        zoom = int(zoom_levels[0])
                        result = await zoom_to_level(zoom)
                        await manager.send_personal_message(json.dumps({
                            "type": "tool_result", 
                            "content": result["result"],
                            "map_state": result["map_state"]
                        }), websocket)
                    else:
                        await manager.send_personal_message(json.dumps({
                            "type": "system-message",
                            "content": "Please provide a zoom level (0-20)."
                        }), websocket)
                        
                else:
                    await manager.send_personal_message(json.dumps({
                        "type": "system-message",
                        "content": "I didn't understand that. Try 'navigate to [lat] [lon]' or 'zoom to [level]'."
                    }), websocket)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)