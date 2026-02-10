# FastMCP Map App

A simple FastAPI application with a chat interface and OpenLayers map integration.

## Features
- Interactive OpenLayers map
- Chat interface with natural language commands
- Two map control tools:
  1. Navigate to specific location (by latitude/longitude)
  2. Zoom to specific level

## Installation & Running

1. Install dependencies with uv:
```bash
uv sync
```

2. Run the application:
```bash
uv run python main.py
```

Alternatively, activate the virtual environment first:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

3. Open your browser and go to: `http://localhost:8000`

## Usage Commands

In the chat interface, you can type:
- `"navigate to 40.7128 -74.0060"` - Go to New York City coordinates
- `"go to 51.5074 -0.1278"` - Alternative command for London
- `"zoom to 10"` - Set zoom level to 10
- `"zoom 15"` - Alternative zoom command

## Tech Stack
- **Backend**: Python + FastAPI + WebSockets
- **Frontend**: HTML + JavaScript + OpenLayers
- **No NodeJS required** - everything runs with Python server