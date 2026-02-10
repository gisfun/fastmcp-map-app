import json
import asyncio
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from openai import AsyncOpenAI
import httpx

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

app = FastAPI()

# Initialize OpenAI client for local model
client = AsyncOpenAI(
    api_key=config["llm"]["api_key"],
    base_url=config["llm"]["base_url"]
)

# Store map state
map_state = {
    "center": config["map"]["default_center"],
    "zoom": config["map"]["default_zoom"]
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

# LLM Integration
async def call_llm(messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Call the local LLM with messages and optional tools."""
    try:
        params = {
            "model": config["llm"]["model"],
            "messages": messages,
            "temperature": config["llm"]["temperature"],
            "max_tokens": config["llm"]["max_tokens"]
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        response = await client.chat.completions.create(**params)
        content = response.choices[0].message.content
        tool_calls = getattr(response.choices[0].message, 'tool_calls', None)
        
        # If no tool calls, try to extract JSON from text response
        if not tool_calls and content:
            extracted_tool = extract_tool_from_text(content)
            if extracted_tool:
                tool_calls = [extracted_tool]
        
        return {
            "success": True,
            "content": content,
            "tool_calls": tool_calls
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": None,
            "tool_calls": None
        }

def extract_tool_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract tool call from non-JSON LLM response text."""
    import re
    
    # Try to find JSON in the text
    json_patterns = [
        r'\{[^{}]*"function_name"[^{}]*\}',  # {function_name: "...", parameters: {...}}
        r'\{[^{}]*"tool"[^{}]*\}',          # {"tool": "...", "arguments": {...}}
        r'\{[^{}]*"navigate_to"[^{}]*\}',     # {"navigate_to": {...}}
        r'\{[^{}]*"zoom_to"[^{}]*\}',        # {"zoom_to": ...}
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                
                # Convert to tool call format
                if "function_name" in parsed:
                    return {
                        "type": "function",
                        "function": {
                            "name": parsed["function_name"],
                            "arguments": json.dumps(parsed.get("parameters", {}))
                        }
                    }
                elif "tool" in parsed:
                    return {
                        "type": "function", 
                        "function": {
                            "name": parsed["tool"],
                            "arguments": json.dumps(parsed.get("arguments", {}))
                        }
                    }
                elif "navigate_to_location" in parsed:
                    return {
                        "type": "function",
                        "function": {
                            "name": "navigate_to_location",
                            "arguments": json.dumps(parsed.get("navigate_to_location", {}))
                        }
                    }
                elif "zoom_to_level" in parsed:
                    return {
                        "type": "function",
                        "function": {
                            "name": "zoom_to_level", 
                            "arguments": json.dumps(parsed.get("zoom_to_level", {}))
                        }
                    }
                    
            except json.JSONDecodeError:
                continue
    
    # Try to extract coordinates from text patterns
    if any(word in text.lower() for word in ["navigate", "go to", "show me", "take me"]):
        coords = extract_coordinates_from_text(text)
        if coords:
            return {
                "type": "function",
                "function": {
                    "name": "navigate_to_location",
                    "arguments": json.dumps({
                        "latitude": coords["lat"],
                        "longitude": coords["lon"]
                    })
                }
            }
    
    # Try to extract zoom from text
    if any(word in text.lower() for word in ["zoom", "closer", "further", "level"]):
        zoom = extract_zoom_from_text(text)
        if zoom is not None:
            return {
                "type": "function",
                "function": {
                    "name": "zoom_to_level",
                    "arguments": json.dumps({"zoom_level": zoom})
                }
            }
    
    return None

def extract_coordinates_from_text(text: str) -> Optional[Dict[str, float]]:
    """Extract coordinates from text using various patterns."""
    import re
    
    # Known locations
    locations = {
        "new york": {"lat": 40.7128, "lon": -74.0060},
        "nyc": {"lat": 40.7128, "lon": -74.0060},
        "london": {"lat": 51.5074, "lon": -0.1278},
        "paris": {"lat": 48.8566, "lon": 2.3522},
        "tokyo": {"lat": 35.6762, "lon": 139.6503},
        "sydney": {"lat": -33.8688, "lon": 151.2093},
        "eiffel tower": {"lat": 48.8584, "lon": 2.2945},
        "grand canyon": {"lat": 36.1069, "lon": -112.1129},
        "statue of liberty": {"lat": 40.6892, "lon": -74.0445}
    }
    
    text_lower = text.lower()
    for place, coords in locations.items():
        if place in text_lower:
            return coords
    
    # Try to find numeric coordinates
    coord_pattern = r'(-?\d+\.?\d*)[^-\d]*(-?\d+\.?\d*)'
    matches = re.findall(coord_pattern, text)
    for lat_str, lon_str in matches:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return {"lat": lat, "lon": lon}
        except ValueError:
            continue
    
    return None

def extract_zoom_from_text(text: str) -> Optional[int]:
    """Extract zoom level from text - only respond if user explicitly mentions zoom."""
    import re
    
    text_lower = text.lower()
    
    # Only respond to explicit zoom requests
    zoom_patterns = [
        r'zoom\s*(?:to\s*)?(\d+)',           # "zoom to 10", "zoom 5"
        r'zoom\s*(?:in|out)',                # "zoom in", "zoom out"
        r'(?:zoom|set)\s+level\s*to?\s*(\d+)', # "zoom level to 10"
    ]
    
    # Check for explicit zoom commands
    for pattern in zoom_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if match.groups():  # Has numeric capture group
                zoom = int(match.group(1))
                return max(0, min(20, zoom))
            else:  # "zoom in" or "zoom out"
                if "out" in match.group():
                    return 3   # Zoom out
                elif "in" in match.group():
                    return 10  # Zoom in
                else:
                    return 8   # Default moderate zoom
    
    # Be very strict about relative zoom terms - require explicit "zoom"
    explicit_zoom_phrases = [
        "zoom in", "zoom out", "zoom closer", "zoom further",
        "i want to zoom", "please zoom", "can you zoom"
    ]
    
    for phrase in explicit_zoom_phrases:
        if phrase in text_lower:
            if "out" in phrase or "further" in text_lower:
                return 3
            elif "in" in phrase or "closer" in text_lower:
                return 10
    
    return None

def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get tool definitions for LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": "navigate_to_location",
                "description": "Navigate the map to a specific latitude and longitude",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude coordinate (-90 to 90)"
                        },
                        "longitude": {
                            "type": "number", 
                            "description": "Longitude coordinate (-180 to 180)"
                        }
                    },
                    "required": ["latitude", "longitude"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "zoom_to_level",
                "description": "Zoom the map to a specific level",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zoom_level": {
                            "type": "integer",
                            "description": "Zoom level (0-20, where 0 is most zoomed out)"
                        }
                    },
                    "required": ["zoom_level"]
                }
            }
        }
    ]

async def execute_tool_call(tool_call: Any) -> Dict[str, Any]:
    """Execute a tool call from the LLM."""
    if hasattr(tool_call, 'function'):
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
    elif isinstance(tool_call, dict) and 'function' in tool_call:
        function_name = tool_call['function']['name']
        arguments = json.loads(tool_call['function']['arguments'])
    else:
        return {
            "type": "error",
            "content": f"Invalid tool call format: {tool_call}"
        }
    
    if function_name == "navigate_to_location":
        return await navigate_to_location(arguments["latitude"], arguments["longitude"])
    elif function_name == "zoom_to_level":
        return await zoom_to_level(arguments["zoom_level"])
    else:
        return {
            "type": "error",
            "content": f"Unknown tool: {function_name}"
        }

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
            width: 500px;
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
        .api-panel {
            border-top: 1px solid #ccc;
            background: #f5f5f5;
        }
        .api-panel-header {
            padding: 10px;
            background: #e0e0e0;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .api-panel-header:hover {
            background: #d5d5d5;
        }
        .api-panel-content {
            padding: 10px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            background: #fafafa;
            border-top: 1px solid #ddd;
        }
        .api-panel-content.hidden {
            display: none;
        }
        .arrow {
            transition: transform 0.2s;
        }
        .arrow.collapsed {
            transform: rotate(-90deg);
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
            <div class="model-info" id="modelInfo" style="padding: 8px; background: #e8f4fd; border-bottom: 1px solid #ccc; font-size: 12px;">
                Loading model info...
            </div>
            <div class="chat-messages" id="chatMessages"></div>
            <div class="api-panel">
                <div class="api-panel-header">
                    <span onclick="toggleApiPanel()">API Responses & Tool Calls</span>
                    <div>
                        <button onclick="clearApiPanel()" style="margin-right: 10px; padding: 2px 8px; font-size: 12px;">Clear</button>
                        <span class="arrow" id="apiPanelArrow">▼</span>
                    </div>
                </div>
                <div class="api-panel-content" id="apiPanelContent"></div>
            </div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Type a command (e.g., 'Navigate to New York City' or 'Zoom in closer')">
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
            
            // Display API response in collapsible panel
            if (data.api_response) {
                displayApiResponse(data.api_response);
            }
            
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

        function toggleApiPanel() {
            const content = document.getElementById('apiPanelContent');
            const arrow = document.getElementById('apiPanelArrow');
            
            content.classList.toggle('hidden');
            arrow.classList.toggle('collapsed');
        }

        function clearApiPanel() {
            const contentDiv = document.getElementById('apiPanelContent');
            contentDiv.textContent = '';
            displayApiResponse({message: 'Panel cleared'});
            // Remove the clear message after 1 second
            setTimeout(() => {
                const lines = contentDiv.textContent.split('\\n');
                if (lines.length > 2) {
                    contentDiv.textContent = lines.slice(0, -2).join('\\n');
                }
            }, 1000);
        }

        function displayApiResponse(response) {
            const contentDiv = document.getElementById('apiPanelContent');
            const timestamp = new Date().toLocaleTimeString();
            const responseText = `[${timestamp}] ${JSON.stringify(response, null, 2)}\\n`;
            
            // Add new response
            contentDiv.textContent += responseText;
            
            // Keep only last 50 responses to prevent memory issues
            const lines = contentDiv.textContent.split('\\n');
            if (lines.length > 100) { // Keep buffer, remove old ones
                contentDiv.textContent = lines.slice(-100).join('\\n');
            }
            
            // Ensure we scroll to bottom (use requestAnimationFrame for reliability)
            requestAnimationFrame(() => {
                contentDiv.scrollTop = contentDiv.scrollHeight;
            });
        }

        // Display model info in header and chat
        const llmModel = '""" + config["llm"]["model"].replace("'", "\\'") + """';
        const llmEndpoint = '""" + config["llm"]["base_url"].replace("'", "\\'") + """';
        const modelInfoDiv = document.getElementById('modelInfo');
        modelInfoDiv.innerHTML = '🤖 <strong>' + llmModel + '</strong> | 🔗 <strong>' + llmEndpoint + '</strong>';
        
        displayMessage('🤖 Model: ' + llmModel, 'system-message');
        displayMessage('🔗 Endpoint: ' + llmEndpoint, 'system-message');
        displayMessage('---', 'system-message');
        
        // Display welcome message
        displayMessage('Welcome! Try natural language commands like:', 'system-message');
        displayMessage('• "Navigate to New York City"', 'system-message');
        displayMessage('• "Show me the Eiffel Tower"', 'system-message');
        displayMessage('• "Zoom in closer"', 'system-message');
        displayMessage('• "Go to Tokyo"', 'system-message');
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
                content = message["content"]
                
                # Prepare messages for LLM
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that controls an interactive map. When users ask to navigate to locations, use the navigate_to_location tool. When they ask to zoom, use the zoom_to_level tool. For locations, use appropriate coordinates for the requested place."
                    },
                    {
                        "role": "user", 
                        "content": content
                    }
                ]
                
                # Get tool definitions
                tools = get_tool_definitions()
                
                # Call LLM
                llm_response = await call_llm(messages, tools)
                
                # Store API response for display
                api_response_data = {
                    "user_message": content,
                    "llm_response": llm_response
                }
                
                if llm_response["success"]:
                    if llm_response["tool_calls"]:
                        # Execute tool calls
                        for tool_call in llm_response["tool_calls"]:
                            tool_result = await execute_tool_call(tool_call)
                            
                            # Send tool result to client
                            await manager.send_personal_message(json.dumps({
                                "type": "tool_result",
                                "content": tool_result.get("result", "Tool executed"),
                                "map_state": tool_result.get("map_state", map_state.copy()),
                                "api_response": api_response_data
                            }), websocket)
                    else:
                        # Just send the LLM response
                        await manager.send_personal_message(json.dumps({
                            "type": "llm_response",
                            "content": llm_response["content"],
                            "api_response": api_response_data
                        }), websocket)
                else:
                    # Handle LLM error
                    await manager.send_personal_message(json.dumps({
                        "type": "system-message",
                        "content": f"LLM Error: {llm_response['error']}. Using fallback command parsing.",
                        "api_response": api_response_data
                    }), websocket)
                    
                    # Fallback to old parsing method
                    content_lower = content.lower()
                    if "navigate to" in content_lower or "go to" in content_lower:
                        await manager.send_personal_message(json.dumps({
                            "type": "system-message",
                            "content": "Please provide coordinates in the format 'navigate to [latitude] [longitude]' when LLM is unavailable."
                        }), websocket)
                    elif "zoom" in content_lower:
                        await manager.send_personal_message(json.dumps({
                            "type": "system-message", 
                            "content": "Please provide a zoom level in the format 'zoom to [level]' when LLM is unavailable."
                        }), websocket)
                    else:
                        await manager.send_personal_message(json.dumps({
                            "type": "system-message",
                            "content": "I couldn't process that request. Please try again or use specific commands."
                        }), websocket)
                        
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    # Display LLM connection info
    llm_config = config["llm"]
    print(f"🚀 FastMCP Map App starting...")
    print(f"📍 LLM Provider: {llm_config['provider']}")
    print(f"🔗 Endpoint: {llm_config['base_url']}")
    print(f"🤖 Model: {llm_config['model']}")
    print(f"🌐 Map Interface: http://localhost:8000")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host=config["app"]["host"], 
        port=config["app"]["port"]
    )