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
    
    def _serialize_tool_calls(self, tool_calls):
        """Convert tool call objects to JSON-serializable format"""
        if not tool_calls:
            return None
        
        serialized = []
        for tool_call in tool_calls:
            if hasattr(tool_call, 'function'):
                # OpenAI tool call object
                serialized.append({
                    "id": getattr(tool_call, 'id', None),
                    "type": getattr(tool_call, 'type', 'function'),
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })
            elif isinstance(tool_call, dict):
                # Already a dict
                serialized.append(tool_call)
            else:
                # Fallback for unknown formats
                serialized.append(str(tool_call))
        
        return serialized

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
        
        # Conversation loop for multi-tool interactions
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            # Call LLM
            llm_response = await self.llm_client.call_llm(messages, tools)
            
            # Process LLM response
            if not llm_response.get("success"):
                print(f"LLM call failed: {llm_response.get('error')}")
                await self.send_safe_message(websocket, {
                    "type": "system-message",
                    "content": f"LLM error: {llm_response.get('error', 'Unknown error')}"
                })
                break
            
            print(f"Iteration {iteration}: Processing LLM response - content: {llm_response.get('content')}, tool_calls: {llm_response.get('tool_calls')}")
            
            parsed_response = parse_llm_response(
                llm_response.get("content", ""),
                llm_response.get("thinking_content"),
                llm_response.get("tool_calls")
            )
            
            print(f"Parsed response type: {parsed_response.get('type')}, tool_calls: {parsed_response.get('tool_calls')}")
            
            # Store API response for display - include complete tool calling details
            api_response_data = {
                "user_message": content,
                "llm_success": llm_response.get("success", False),
                "llm_content": llm_response.get("content", ""),
                "llm_error": llm_response.get("error"),
                "has_tool_calls": bool(llm_response.get("tool_calls")),
                "tool_calls": self._serialize_tool_calls(llm_response.get("tool_calls")),
                "parsed_tool_calls": self._serialize_tool_calls(parsed_response.get("tool_calls")),
                "response_type": parsed_response.get("type"),
                "thinking_content": parsed_response.get("thinking_content")
            }
            
            # If no tool calls, we're done
            if not parsed_response.get("tool_calls") and not llm_response.get("tool_calls"):
                # Send final text response
                response_content = parsed_response.get("content", "") or llm_response.get("content", "")
                if parsed_response.get("json_response"):
                    response_content = f"{response_content}\n\nJSON: {json.dumps(parsed_response['json_response'], indent=2)}"
                
                await self.send_safe_message(websocket, {
                    "type": "llm_response",
                    "content": response_content,
                    "thinking_content": parsed_response.get("thinking_content"),
                    "api_response": api_response_data
                })
                break
            
            # Execute tool calls
            tool_results = []
            tool_calls_to_execute = parsed_response.get("tool_calls") or []
            
            for tool_call in tool_calls_to_execute:
                print(f"Executing tool call: {tool_call}")
                
                # Extract tool name and arguments
                if hasattr(tool_call, 'function'):
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                elif isinstance(tool_call, dict) and 'function' in tool_call:
                    tool_name = tool_call['function']['name']
                    arguments = json.loads(tool_call['function']['arguments'])
                else:
                    continue
                
                print(f"Sending tool call to frontend: {tool_name} with args: {arguments}")
                
                await self.send_safe_message(websocket, {
                    "type": "tool_call",
                    "tool": tool_name,
                    "arguments": arguments,
                    "thinking_content": parsed_response.get("thinking_content"),
                    "api_response": api_response_data
                })
                
                # Execute the tool
                tool_result = await self.map_tools.execute_tool_call(tool_call)
                tool_results.append(tool_result)
                
                print(f"Tool result received: {tool_result}")
                
                # Send tool result to client
                result_data = {
                    "type": "tool_result",
                    "tool": tool_result.get("tool"),
                    "content": tool_result.get("result", "Tool executed"),
                    "map_state": self.map_state.copy(),
                    "api_response": api_response_data
                }
                
                # Include coordinates if this was a geocoding result
                if tool_result.get("tool") == "geocode_address" and "coordinates" in tool_result:
                    result_data["coordinates"] = tool_result["coordinates"]
                
                await self.send_safe_message(websocket, result_data)
            
            # Add tool results to conversation for next iteration
            if tool_results:
                tool_result_messages = []
                for i, result in enumerate(tool_results):
                    tool_result_messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": str(i)  # Simple ID for now
                    })
                
                messages.extend(tool_result_messages)
                iteration += 1
            else:
                break
        
        if iteration >= max_iterations:
            await self.send_safe_message(websocket, {
                "type": "system-message",
                "content": "Maximum tool iterations reached. Please try again."
            })
    
    async def send_safe_message(self, websocket: WebSocket, data: Dict[str, Any]):
        """Send message with proper JSON serialization error handling"""
        try:
            message_json = json.dumps(data)
            print(f"Sending message via WebSocket: {message_json}")
            await self.manager.send_personal_message(message_json, websocket)
            print(f"Message sent successfully: {data.get('type')}")
        except (TypeError, ValueError) as e:
            print(f"Serialization error: {e}")
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