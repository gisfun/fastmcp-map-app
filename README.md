# FastMCP Map App

This project explores a working example of MCP (Model Context Protocol) tool calling with map-based tools, visual feedback, and AI-powered workflow using OpenCode + GLM 4.7 Flash. While GLM 4.7 Flash showed some issues with code indentation and structure reliability during development, the big-pickle model provided more consistent and reliable results for building this application.

## Features
- Interactive OpenLayers map with real-time navigation
- Natural language chat interface powered by AI models
- Advanced tool-calling ecosystem with map-based tools:
  1. **Geocoding**: Convert addresses/place names to coordinates (ArcGIS service)
  2. **Navigation**: Navigate map to specific coordinates  
  3. **Zoom Control**: Dynamic zoom level adjustment
- Multi-tool conversation workflows with automatic tool chaining
- Visual feedback for all operations with smooth map animations
- Collapsible API panel showing detailed LLM responses and tool execution
- Real-time thinking content display for AI reasoning transparency
- Configurable model support (OpenAI-compatible APIs)

## MCP Tool Calling Implementation

This project demonstrates practical MCP tool calling patterns:

- **Tool Discovery**: AI automatically discovers available map tools
- **Parameter Extraction**: Natural language parsed into tool parameters
- **Tool Chaining**: Geocoding results automatically passed to navigation
- **Conversation Loops**: Multi-turn conversations with tool results fed back to AI
- **Error Handling**: Graceful failure recovery with user-friendly messages

## Installation & Running

1. **Install dependencies** with uv (recommended):
```bash
uv sync
```

2. **Set up AI model** (OpenAI-compatible API required):

   For local models using Ollama:
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a compatible model
ollama pull llama3.2

# Start Ollama server
ollama serve
```

3. **Configure the model** (edit `config.json`):
```json
{
  "llm": {
    "provider": "ollama",
    "base_url": "http://localhost:11434/v1", 
    "model": "llama3.2",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

4. **Run the application**:

For development:
```bash
uv run fastapi dev main.py
```

For production:
```bash
uv run python main.py
```

5. **Access the application**: Open `http://localhost:8000` in your browser

## Demo Screenshot

![FastMCP Map App Demo](demo-screenshot.png)

*Interactive map with AI-powered natural language control and real-time tool execution. The screenshot shows the OpenLayers map interface on the left, chat panel with natural language commands on the right, and the collapsible API panel displaying detailed tool execution results.*

## Usage Examples

The app supports sophisticated natural language commands with automatic tool chaining:

- **"Navigate to 1600 Pennsylvania Ave, Washington DC"** → Geocodes address → Navigates to coordinates
- **"Show me the Eiffel Tower"** → Geocodes landmark → Centers map on location
- **"Take me to Tokyo"** → Geocodes city → Navigates with appropriate zoom
- **"Find Times Square and zoom to level 15"** → Geocodes → Navigates → Sets zoom level
- **"Show me the Statue of Liberty"** → Landmark recognition → Precise navigation

**Interactive Features**:
- Real-time tool execution visualization in the chat panel
- Smooth map animations for all navigation changes
- API response panel showing detailed tool execution data
- AI thinking content display for transparency

## Configuration

Edit `config.json` to customize:

- **LLM Settings**: Provider, model, temperature, max tokens
- **API Configuration**: Base URLs, timeouts, API keys
- **Map Defaults**: Starting coordinates, zoom levels, navigation behavior
- **Tool Parameters**: Geocoding service URLs, confidence thresholds

## Development Notes

### Model Performance Observations

During development, we observed differences in model reliability:

- **GLM 4.7 Flash**: Good reasoning capabilities but inconsistent with code structure and indentation
- **Big-Pickle Model**: More reliable for consistent code generation and debugging
- **Tool Calling**: All models tested showed good tool discovery and chaining capabilities

### Architecture Decisions

- **WebSocket-based**: Real-time bidirectional communication
- **Multi-tool Loops**: Supports complex workflows requiring sequential tool execution
- **State Management**: Centralized map state with proper synchronization
- **Error Recovery**: Comprehensive error handling throughout the tool pipeline

## Possible Next Steps

1. **Testing Implementation**:
   - Unit tests for individual map tools
   - Integration tests for tool calling workflows
   - End-to-end tests for the complete chat-to-map pipeline
   - Performance tests for concurrent WebSocket connections

2. **Enhanced Map Features**:
   - Custom markers and POI (Points of Interest) support
   - Map layer controls (satellite, terrain, street views)
   - Drawing and annotation tools
   - Route planning and direction display

3. **Advanced AI Features**:
   - Context-aware location suggestions
   - Multi-modal input (image recognition for locations)
   - Voice input integration
   - Custom tool creation framework

4. **Production Improvements**:
   - Authentication and user management
   - Rate limiting and API quotas
   - Caching for geocoding results
   - Monitoring and analytics dashboard

5. **MCP Extensions**:
   - Support for additional tool categories
   - Custom tool definition framework
   - Plugin architecture for third-party tools
   - Tool marketplace integration

## Tech Stack

- **Backend**: Python + FastAPI + WebSockets + AsyncIO
- **AI Integration**: OpenAI SDK + MCP tool calling patterns
- **Map Technology**: OpenLayers 7.x with modern WebGL rendering
- **HTTP Client**: aiohttp for async external service calls
- **Configuration**: JSON-based with environment variable support
- **Frontend**: Vanilla JavaScript with modern ES6+ features

## Contributing

This project serves as a reference implementation for MCP tool calling with map interfaces. Contributions are welcome, especially in the areas of testing, performance optimization, and new tool implementations.

---

**Note**: This is an exploration project demonstrating MCP tool calling capabilities. The focus is on creating a robust foundation for AI-powered map interactions that can be extended and customized for specific use cases.