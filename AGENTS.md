# AGENTS.md

This file contains guidelines for agentic coding agents working on the FastMCP Map App repository.

## Project Overview

FastMCP Map App is a Python FastAPI application with real-time WebSocket communication and an OpenLayers map interface. The app provides a chat interface for controlling map navigation through natural language commands.

## Build/Test Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Activate virtual environment (alternative approach)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Running the Application
```bash
# Run the main application
uv run python main.py

# Or with activated venv
python main.py
```

### Testing
This project currently has no formal test suite. When implementing tests, use:
```bash
# Run tests (when available)
python -m pytest

# Run specific test file
python -m pytest tests/test_specific.py

# Run with coverage
python -m pytest --cov=.
```

### Code Quality
No linting or formatting tools are currently configured. Recommended tools for Python:
```bash
# Code formatting
black .

# Import sorting
isort .

# Linting
flake8 .

# Type checking
mypy .
```

## Code Style Guidelines

### Python Code Style
- Follow PEP 8 for Python code formatting
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black standard)
- Use f-strings for string formatting
- Prefer type hints for all function parameters and return values

### Import Organization
```python
# Standard library imports first
import json
import asyncio
from typing import Any, Dict, List

# Third-party imports next
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# Local imports last (when modules are added)
```

### Naming Conventions
- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_underscore_prefix`
- **Global variables**: `descriptive_snake_case`

### Type Hints
Always include type hints for function parameters and return values:
```python
async def navigate_to_location(latitude: float, longitude: float) -> Dict[str, Any]:
    """Navigate the map to a specific latitude and longitude."""
    pass
```

### Error Handling
- Use try-except blocks for WebSocket operations
- Handle `WebSocketDisconnect` explicitly
- Return meaningful error messages as JSON responses
- Use appropriate HTTP status codes for API endpoints

### Async/Await Patterns
- All WebSocket handlers must be async
- Use `await` for all async operations
- Keep async functions focused on single responsibilities
- Use `asyncio` utilities when needed for concurrent operations

### Documentation
- Use docstrings for all functions and classes
- Follow Google-style or reST docstring format
- Include parameter types and return value descriptions
- Document complex algorithms or business logic

### Frontend Code (HTML/JavaScript)
- Keep HTML structure semantic and accessible
- Use modern JavaScript (ES6+) features
- Organize CSS with BEM-like class naming
- Implement proper error handling for WebSocket connections
- Use event listeners for user interactions

### WebSocket Communication
- All WebSocket messages must be JSON formatted
- Include message `type` field for routing
- Use consistent message structure:
```python
{
    "type": "message_type",
    "content": "message_content",
    "additional_data": {}
}
```

### State Management
- Global state should be minimal and well-documented
- Use the existing `map_state` dict for map-related state
- WebSocket connections managed through `ConnectionManager`
- Always copy mutable state before broadcasting

### Security Considerations
- Validate all user inputs in WebSocket messages
- Sanitize coordinates and numeric inputs
- Implement rate limiting for WebSocket connections if needed
- Never expose internal server details in error messages

## Project Structure

```
fastmcp-map-app/
├── main.py              # Main FastAPI application
├── requirements.txt     # Python dependencies
├── pyproject.toml      # Project configuration
├── README.md           # Project documentation
└── .venv/             # Virtual environment
```

## Development Workflow

1. Always run the application after changes to verify functionality
2. Test WebSocket connections and map interactions
3. Verify coordinate parsing and zoom level constraints
4. Check that all async operations complete properly
5. Ensure no memory leaks from unclosed WebSocket connections

## Adding New Features

When adding new map tools or chat commands:
1. Create async function for the tool
2. Add to `TOOLS` registry dictionary
3. Update command parsing in WebSocket handler
4. Add appropriate error handling and validation
5. Update frontend to handle new tool result types
6. Test end-to-end functionality

## Common Patterns

### Adding New Map Tools
```python
async def new_tool(param1: type1, param2: type2) -> Dict[str, Any]:
    """Tool description."""
    global map_state
    # Modify map_state as needed
    
    response = {
        "type": "tool_result",
        "tool": "new_tool",
        "result": "Description of what happened",
        "map_state": map_state.copy()
    }
    
    await manager.broadcast(json.dumps(response))
    return response
```

### WebSocket Message Handling
```python
if message["type"] == "chat_message":
    content = message["content"].lower()
    # Parse and handle commands
    if "command_pattern" in content:
        # Extract parameters
        # Call tool function
        # Send response
```