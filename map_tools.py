"""Map tools module for executing navigation and zoom operations
"""
import json
import asyncio
from typing import Any, Dict, Optional


class MapTools:
    """Handles map navigation and zoom operations"""
    
    def __init__(self, map_state: Dict[str, Any]):
        self.map_state = map_state
    
    async def execute_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        """Execute a tool call from LLM"""
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
        
        print(f"Executing tool: {function_name} with arguments: {arguments}")
        
        if function_name == "navigate_to_location":
            return await self.navigate_to_location(arguments["latitude"], arguments["longitude"])
        elif function_name == "zoom_to_level":
            return await self.zoom_to_level(arguments["zoom_level"])
        else:
            return {
                "type": "error",
                "content": f"Unknown tool: {function_name}"
            }
    
    async def navigate_to_location(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Navigate the map to a specific latitude and longitude."""
        print(f"navigate_to_location called with lat: {latitude}, lon: {longitude}")
        print(f"Current map_state before navigation: {self.map_state}")
        
        self.map_state["center"] = [longitude, latitude]  # OpenLayers uses [lon, lat]
        
        response = {
            "type": "tool_result",
            "tool": "navigate_to_location",
            "result": f"Map navigated to coordinates: {latitude}, {longitude}",
            "map_state": self.map_state.copy()
        }
        
        print(f"navigate_to_location result: {response}")
        return response
    
    async def zoom_to_level(self, zoom_level: int) -> Dict[str, Any]:
        """Zoom the map to a specific level."""
        print(f"zoom_to_level called with level: {zoom_level}")
        print(f"Current map_state before zoom: {self.map_state}")
        
        self.map_state["zoom"] = max(0, min(20, zoom_level))  # Clamp between 0 and 20
        
        response = {
            "type": "tool_result",
            "tool": "zoom_to_level",
            "result": f"Map zoomed to level: {zoom_level}",
            "map_state": self.map_state.copy()
        }
        
        print(f"zoom_to_level result: {response}")
        return response