"""
FastMCP Map App - Clean, refactored version
"""
import json
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

from websocket_handler import WebSocketHandler

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize global state
map_state = {
    "center": config["map"]["default_center"],
    "zoom": config["map"]["default_zoom"]
}

# Create app and handler
app = FastAPI()
handler = WebSocketHandler(config, map_state)


@app.get("/", response_class=HTMLResponse)
async def get():
    """Serve the main HTML interface"""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FastMCP Map App</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v7.5.2/ol.css">
    <script src="https://cdn.jsdelivr.net/npm/ol@v7.5.2/dist/ol.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        .container {{
            display: flex;
            height: 100vh;
        }}
        .map-container {{
            flex: 1;
            height: 100%;
        }}
        .chat-container {{
            width: 500px;
            display: flex;
            flex-direction: column;
            border-left: 1px solid #ccc;
        }}
        .model-info {{
            padding: 8px;
            background: #e8f4fd;
            border-bottom: 1px solid #ccc;
            font-size: 12px;
        }}
        .chat-messages {{
            flex: 1;
            padding: 10px;
            overflow-y: auto;
            background: #f9f9f9;
        }}
        .api-panel {{
            border-top: 1px solid #ccc;
            background: #f5f5f5;
        }}
        .api-panel-header {{
            padding: 10px;
            background: #e0e0e0;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .api-panel-header:hover {{
            background: #d5d5d5;
        }}
        .api-panel-content {{
            padding: 10px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            background: #fafafa;
            border-top: 1px solid #ddd;
        }}
        .api-panel-content.hidden {{
            display: none;
        }}
        .arrow {{
            transition: transform 0.2s;
        }}
        .arrow.collapsed {{
            transform: rotate(-90deg);
        }}
        .chat-input {{
            padding: 10px;
            border-top: 1px solid #ccc;
        }}
        .chat-input input {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }}
        .message {{
            margin-bottom: 10px;
            padding: 8px;
            border-radius: 4px;
        }}
        .user-message {{
            background: #e3f2fd;
            text-align: right;
        }}
        .system-message {{
            background: #f3e5f5;
        }}
        .tool-result {{
            background: #e8f5e8;
        }}
        #map {{
            height: 100%;
            width: 100%;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="map-container">
            <div id="map"></div>
        </div>
        <div class="chat-container">
            <div class="model-info" id="modelInfo">
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
                <input type="text" id="chatInput" placeholder="Type a command (e.g., 'Navigate to New York City' or 'Zoom to level 10')">
            </div>
        </div>
    </div>

    <script>
        // Initialize OpenLayers map
        const map = new ol.Map({{
            target: 'map',
            layers: [
                new ol.layer.Tile({{
                    source: new ol.source.OSM()
                }})
            ],
            view: new ol.View({{
                center: ol.proj.fromLonLat([0, 0]),
                zoom: 2
            }})
        }});

        // WebSocket connection
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onmessage = function(event) {{
            console.log('WebSocket message received:', event.data);
            const data = JSON.parse(event.data);
            console.log('Parsed data:', data);
            
            displayMessage(data.content, data.type);
            
            // Display API response in collapsible panel
            if (data.api_response) {{
                displayApiResponse(data.api_response);
            }}
            
            // Display tool call requests
            if (data.type === 'tool_call') {{
                console.log('Tool call received:', data.tool, data.arguments);
                const messagesDiv = document.getElementById('chatMessages');
                const toolDiv = document.createElement('div');
                toolDiv.style.marginBottom = '8px';
                toolDiv.style.padding = '10px';
                toolDiv.style.background = '#fff3e0';
                toolDiv.style.border = '1px solid #ff9800';
                toolDiv.style.borderRadius = '4px';
                toolDiv.innerHTML = `<strong>🔧 Tool Call:</strong> ${{data.tool}}<br><small>Arguments: ${{JSON.stringify(data.arguments)}}</small>`;
                
                messagesDiv.appendChild(toolDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}
            
            // Format LLM responses for better readability
            if (data.type === 'llm_response' && data.content) {{
                const formattedDiv = document.createElement('div');
                formattedDiv.style.marginTop = '5px';
                formattedDiv.style.padding = '8px';
                formattedDiv.style.background = '#f0f8ff';
                formattedDiv.style.border = '1px solid #b3d9ff';
                formattedDiv.style.borderRadius = '4px';
                formattedDiv.innerHTML = '<strong>🤖 AI Response:</strong><br>' + data.content.replace(/\\\\n/g, '<br>');
                
                const messagesDiv = document.getElementById('chatMessages');
                messagesDiv.appendChild(formattedDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}
            
            // Display thinking content if available
            if (data.thinking_content) {{
                displayThinkingContent(data.thinking_content);
            }}
            
            if (data.type === 'tool_result') {{
                console.log('Tool result received:', data.tool, data.map_state);
                // Update map state based on tool result
                if (data.map_state) {{
                    const center = ol.proj.fromLonLat(data.map_state.center);
                    console.log('Animating to center:', center, 'zoom:', data.map_state.zoom);
                    map.getView().animate({{
                        center: center,
                        zoom: data.map_state.zoom,
                        duration: 1000
                    }});
                }}
            }}
        }};

        function displayMessage(content, type) {{
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${{type}}`;
            messageDiv.textContent = content;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}

        function toggleApiPanel() {{
            const content = document.getElementById('apiPanelContent');
            const arrow = document.getElementById('apiPanelArrow');
            
            content.classList.toggle('hidden');
            arrow.classList.toggle('collapsed');
        }}

        function clearApiPanel() {{
            const contentDiv = document.getElementById('apiPanelContent');
            contentDiv.textContent = '';
            displayApiResponse({{"message": 'Panel cleared'}});
            // Remove clear message after 1 second
            setTimeout(() => {{
                const lines = contentDiv.textContent.split('\\\\n');
                if (lines.length > 2) {{
                    contentDiv.textContent = lines.slice(0, -2).join('\\\\n');
                }}
            }}, 1000);
        }}

        function displayApiResponse(response) {{
            const contentDiv = document.getElementById('apiPanelContent');
            const timestamp = new Date().toLocaleTimeString();
            const responseText = `[${{timestamp}}] ${{JSON.stringify(response, null, 2)}}\\\\n`;
            
            // Add new response
            contentDiv.textContent += responseText;
            
            // Keep only last 50 responses to prevent memory issues
            const lines = contentDiv.textContent.split('\\\\n');
            if (lines.length > 100) {{ // Keep buffer, remove old ones
                contentDiv.textContent = lines.slice(-100).join('\\\\n');
            }}
            
            // Ensure we scroll to bottom (use requestAnimationFrame for reliability)
            requestAnimationFrame(() => {{
                contentDiv.scrollTop = contentDiv.scrollHeight;
            }});
        }}

        function sendMessage() {{
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            
            if (message) {{
                displayMessage(message, 'user-message');
                ws.send(JSON.stringify({{
                    type: 'chat_message',
                    content: message
                }}));
                input.value = '';
            }}
        }}

        function displayThinkingContent(thinkingContent) {{
            if (!thinkingContent) return;
            
            const messagesDiv = document.getElementById('chatMessages');
            const thinkingDiv = document.createElement('div');
            thinkingDiv.style.marginBottom = '8px';
            thinkingDiv.style.padding = '10px';
            thinkingDiv.style.background = '#fff9c4';
            thinkingDiv.style.border = '1px solid #fbc02d';
            thinkingDiv.style.borderRadius = '4px';
            thinkingDiv.style.fontStyle = 'italic';
            thinkingDiv.innerHTML = '<strong>🤔 Thinking:</strong><br>' + thinkingContent.replace(/\\\\n/g, '<br>');
            
            messagesDiv.appendChild(thinkingDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}

        // Handle Enter key in input
        document.getElementById('chatInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                sendMessage();
            }}
        }});

        // Display model info
        const llmModel = '{config["llm"]["model"].replace("'", "\\\\'")}';
        const llmEndpoint = '{config["llm"]["base_url"].replace("'", "\\\\'")}';
        const modelInfoDiv = document.getElementById('modelInfo');
        modelInfoDiv.innerHTML = '🤖 <strong>' + llmModel + '</strong> | 🔗 <strong>' + llmEndpoint + '</strong>';
        
        // Display welcome message
        displayMessage('Welcome! Try natural language commands like:', 'system-message');
        displayMessage('• "Navigate to New York City"', 'system-message');
        displayMessage('• "Show me Eiffel Tower"', 'system-message');
        displayMessage('• "Zoom to level 10"', 'system-message');
        displayMessage('• "Go to Tokyo"', 'system-message');
    </script>
</body>
</html>
"""


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    await handler.handle_websocket(websocket)


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