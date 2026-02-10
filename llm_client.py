"""
LLM Client module for handling local model communication
"""
import json
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI


class LLMClient:
    """Handles communication with local LLM models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config["llm"]
        self.client = AsyncOpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )
    
    async def call_llm(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Call the LLM with messages and optional tools"""
        try:
            params = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_tokens"]
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**params)
            message = response.choices[0].message
            
            # Extract content fields
            # reasoning_content is the thinking process (if available)
            # content is the actual response text
            thinking_content = getattr(message, 'reasoning_content', None)
            content = getattr(message, 'content', None)
            tool_calls = getattr(message, 'tool_calls', None)
            
            print(f"LLM Response - content: {content}, thinking_content: {thinking_content}, tool_calls: {tool_calls}")
            
            return {
                "success": True,
                "content": content,
                "thinking_content": thinking_content,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": None,
                "tool_calls": None
            }
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM"""
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
    
    def get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        return """You are a helpful assistant that controls an interactive map.

When users ask to navigate to locations, use navigate_to_location tool.
When they ask to zoom, use zoom_to_level tool.
For locations, use appropriate coordinates for the requested place.

IMPORTANT: Always respond in JSON format. If you don't use tools, respond with:
{"response": "your text response here"}

If you use tools, let the tool execution handle the response.

If your model supports reasoning/thinking content:
- Put your thinking process in reasoning_content field
- Put your final response in the content field
- This helps users understand how you reached your conclusion."""