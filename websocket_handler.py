"""
WebSocket handling module for managing connections and message processing
"""
import json
import asyncio
from typing import Any, Dict, List
from fastapi import WebSocket, WebSocketDisconnect

from llm_client import LLMClient
from message_parser import parse_llm_response
from map_tools import MapTools


class ConnectionManager:
    """Manages WebSocket connections"""
    
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


class WebSocketHandler:
    """Handles WebSocket message processing and LLM integration"""
    
    def __init__(self, config: Dict[str, Any], map_state: Dict[str, Any]):
        self.config = config
        self.map_state = map_state
        self.llm_client = LLMClient(config)
        self.map_tools = MapTools(map_state)
        self.manager = ConnectionManager()
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, str]):
        """Handle incoming WebSocket message"""
        if message["type"] != "chat_message":
            return
        
        content = message["content"]
        
        # Prepare messages for LLM
        messages = [
            {
                "role": "system",
                "content": self.llm_client.get_system_prompt()
            },
            {
                "role": "user", 
                "content": content
            }
        ]
        
        # Get tool definitions
        tools = self.llm_client.get_tool_definitions()
        
        # Call LLM
        llm_response = await self.llm_client.call_llm(messages, tools)
        
        # Store API response for display
        api_response_data = {
            "user_message": content,
            "llm_success": llm_response.get("success", False),
            "llm_content": llm_response.get("content", ""),
            "llm_error": llm_response.get("error"),
            "has_tool_calls": bool(llm_response.get("tool_calls"))
        }
        
        # Process LLM response
        if llm_response.get("success"):
            parsed_response = parse_llm_response(llm_response.get("content", ""))
            
            if parsed_response["type"] == "tool_calls":
                # Execute tool calls
                for tool_call in parsed_response["tool_calls"]:
                    tool_result = await self.map_tools.execute_tool_call(tool_call)
                    
                    # Send tool result to client
                    await self.send_safe_message(websocket, {
                        "type": "tool_result",
                        "content": tool_result.get("result", "Tool executed"),
                        "map_state": self.map_state.copy(),
                        "api_response": api_response_data
                    })
            else:
                # Send text response
                response_content = parsed_response["content"]
                if parsed_response.get("json_response"):
                    # Include the original JSON for display
                    response_content = f"Response: {response_content}\n\nJSON: {json.dumps(parsed_response['json_response'], indent=2)}"
                
                await self.send_safe_message(websocket, {
                    "type": "llm_response",
                    "content": response_content,
                    "api_response": api_response_data
                })
        else:
            # Handle LLM error
            await self.send_safe_message(websocket, {
                "type": "system-message",
                "content": f"LLM Error: {llm_response.get('error', 'Unknown error')}. Using fallback command parsing.",
                "api_response": api_response_data
            })
    
    async def send_safe_message(self, websocket: WebSocket, data: Dict[str, Any]):
        """Send message with proper JSON serialization error handling"""
        try:
            await self.manager.send_personal_message(json.dumps(data), websocket)
        except (TypeError, ValueError) as e:
            error_msg = {
                "type": "system-message",
                "content": f"Message serialization error: {str(e)}"
            }
            await self.manager.send_personal_message(json.dumps(error_msg), websocket)
    
    async def handle_websocket(self, websocket: WebSocket):
        """Main WebSocket handling loop"""
        await self.manager.connect(websocket)
        
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await self.handle_message(websocket, message)
                except json.JSONDecodeError:
                    await self.manager.send_personal_message(json.dumps({
                        "type": "system-message",
                        "content": "Invalid JSON format received"
                    }), websocket)
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)