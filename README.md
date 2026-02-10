# FastMCP Map App

A FastAPI application with chat interface, OpenLayers map integration, and local LLM support for natural language map control.

## Features
- Interactive OpenLayers map
- Natural language chat interface powered by local LLM
- Two map control tools with AI-powered location understanding:
  1. Navigate to locations (AI finds coordinates)
  2. Zoom to appropriate levels
- Collapsible API panel for detailed responses and tool calls
- Configurable local model support (Ollama)

## Installation & Running

1. Install dependencies with uv:
```bash
uv sync
```

2. Set up local LLM (Ollama recommended):
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (llama3.2 recommended)
ollama pull llama3.2

# Start Ollama server
ollama serve
```

3. Configure the model (edit `config.json` if needed):
```json
{
  "llm": {
    "provider": "ollama",
    "base_url": "http://localhost:11434/v1",
    "model": "llama3.2"
  }
}
```

4. Run the application:

For development (recommended):
```bash
uv run fastapi dev main.py
```

For production:
```bash
uv run python main.py
```

Alternatively, activate the virtual environment first:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

5. Open your browser and go to: `http://localhost:8000`

## Usage Commands

The app now supports natural language commands via local LLM:

- `"Navigate to New York City"` - AI will find coordinates
- `"Show me the Eiffel Tower"` - AI will locate Paris
- `"Zoom in closer"` - AI will determine appropriate zoom level
- `"Go to Tokyo"` - AI will navigate to Tokyo
- `"Take me to the Grand Canyon"` - AI will find coordinates

**Collapsible API Panel**: Click the "API Responses & Tool Calls" panel to see detailed LLM responses and tool execution data.

## Configuration

Edit `config.json` to customize:
- **LLM Provider**: Change from ollama to other OpenAI-compatible APIs
- **Model**: Select different models (llama3.2, codellama, etc.)
- **API Settings**: Temperature, max tokens, timeout
- **Map Defaults**: Starting position and zoom limits

## Tech Stack
- **Backend**: Python + FastAPI + WebSockets + OpenAI SDK
- **LLM Integration**: Ollama (local) or any OpenAI-compatible API
- **Frontend**: HTML + JavaScript + OpenLayers + Collapsible API Panel
- **Configuration**: JSON-based configuration file
- **No NodeJS required** - everything runs with Python server