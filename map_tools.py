"""Map tools module for executing navigation and zoom operations
 """
import json
import asyncio
from typing import Any, Dict, Optional
import aiohttp


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
        elif function_name == "geocode_address":
            return await self.geocode_address(arguments["address"])
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
    
    async def geocode_address(self, address: str) -> Dict[str, Any]:
        """Convert a textual address to latitude/longitude coordinates using ArcGIS geocoding service."""
        print(f"geocode_address called with address: {address}")
        
        # ArcGIS geocoding service URL
        base_url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
        params = {
            "f": "json",
            "maxLocations": "10",
            "outFields": "*",
            "SingleLine": address
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if we found any candidates
                        candidates = data.get("candidates", [])
                        if candidates:
                            # Use the first (best) candidate
                            best_candidate = candidates[0]
                            location = best_candidate.get("location", {})
                            x = location.get("x")  # longitude
                            y = location.get("y")  # latitude
                            score = best_candidate.get("score", 0)
                            address_str = best_candidate.get("address", "")
                            
                            if x is not None and y is not None:
                                # Automatically update map state to navigate to the geocoded location
                                self.map_state["center"] = [x, y]  # OpenLayers uses [lon, lat]
                                self.map_state["zoom"] = 15  # Set reasonable zoom for geocoded locations
                                
                                result = {
                                    "type": "tool_result",
                                    "tool": "geocode_address",
                                    "result": f"Geocoded '{address}' and navigated to: {address_str or f'{y:.6f}, {x:.6f}'} (confidence: {score}%)",
                                    "coordinates": {
                                        "latitude": y,
                                        "longitude": x,
                                        "confidence": score,
                                        "formatted_address": address_str
                                    },
                                    "candidates_count": len(candidates),
                                    "map_state": self.map_state.copy()
                                }
                                print(f"geocode_address result: {result}")
                                return result
                            else:
                                return {
                                    "type": "error",
                                    "content": f"Geocoding service returned invalid coordinates for address: {address}"
                                }
                        else:
                            return {
                                "type": "error", 
                                "content": f"No location found for address: {address}"
                            }
                    else:
                        return {
                            "type": "error",
                            "content": f"Geocoding service returned HTTP {response.status} for address: {address}"
                        }
        except aiohttp.ClientError as e:
            return {
                "type": "error",
                "content": f"Network error when geocoding address '{address}': {str(e)}"
            }
        except Exception as e:
            return {
                "type": "error",
                "content": f"Unexpected error when geocoding address '{address}': {str(e)}"
            }