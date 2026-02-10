"""
Message parsing utilities for extracting tool calls and handling text
"""
import json
import re
from typing import Any, Dict, Optional


def extract_json_tool_call(json_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract tool call from JSON object."""
    if "function_name" in json_obj:
        return {
            "type": "function",
            "function": {
                "name": json_obj["function_name"],
                "arguments": json.dumps(json_obj.get("parameters", {}))
            }
        }
    elif "navigate_to_location" in json_obj:
        return {
            "type": "function",
            "function": {
                "name": "navigate_to_location",
                "arguments": json.dumps(json_obj["navigate_to_location"])
            }
        }
    elif "zoom_to_level" in json_obj:
        return {
            "type": "function",
            "function": {
                "name": "zoom_to_level", 
                "arguments": json.dumps(json_obj["zoom_to_level"])
            }
        }
    return None


def extract_tool_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract tool call from non-JSON LLM response text."""
    text_lower = text.lower()
    
    # Known locations database
    locations = {
        "new york": {"lat": 40.7128, "lon": -74.0060},
        "nyc": {"lat": 40.7128, "lon": -74.0060},
        "london": {"lat": 51.5074, "lon": -0.1278},
        "paris": {"lat": 48.8566, "lon": 2.3522},
        "tokyo": {"lat": 35.6762, "lon": 139.6503},
        "sydney": {"lat": -33.8688, "lon": 151.2093},
        "eiffel tower": {"lat": 48.8584, "lon": 2.2945},
        "grand canyon": {"lat": 36.1069, "lon": -112.1129},
        "statue of liberty": {"lat": 40.6892, "lon": -74.0445}
    }
    
    # Check for location mentions
    if any(word in text_lower for word in ["navigate", "go to", "show me", "take me"]):
        for place, coords in locations.items():
            if place in text_lower:
                return {
                    "type": "function",
                    "function": {
                        "name": "navigate_to_location",
                        "arguments": json.dumps({
                            "latitude": coords["lat"],
                            "longitude": coords["lon"]
                        })
                    }
                }
    
    # Try to find numeric coordinates
    if any(word in text_lower for word in ["navigate", "go to", "show me", "take me"]):
        coord_pattern = r'(-?\d+\.?\d*)[^-\d]*(-?\d+\.?\d*)'
        match = re.search(coord_pattern, text)
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return {
                        "type": "function",
                        "function": {
                            "name": "navigate_to_location",
                            "arguments": json.dumps({
                                "latitude": lat,
                                "longitude": lon
                            })
                        }
                    }
            except ValueError:
                pass
    
    return None


def extract_zoom_from_text(text: str) -> Optional[int]:
    """Extract zoom level from text - only respond to explicit numeric zoom requests."""
    text_lower = text.lower()
    
    # Only respond to EXPLICIT numeric zoom requests
    zoom_patterns = [
        r'zoom\s*(?:to\s*)?(\d+)',           # "zoom to 10", "zoom 5"
        r'(?:zoom|set)\s+level\s*to?\s*(\d+)', # "zoom level to 10"
    ]
    
    # Check for explicit numeric zoom commands only
    for pattern in zoom_patterns:
        match = re.search(pattern, text_lower)
        if match and match.groups():  # Must have numeric capture group
            zoom = int(match.group(1))
            return max(0, min(20, zoom))
    
    return None


def parse_llm_response(content: str, thinking_content: Optional[str] = None) -> Dict[str, Any]:
    """Parse LLM response for tool calls or text responses"""
    try:
        # Try to parse as JSON first
        json_response = json.loads(content.strip())
        if isinstance(json_response, dict):
            if "response" in json_response:
                # This is a text response in JSON format
                return {
                    "type": "text_response",
                    "content": json_response["response"],
                    "thinking_content": thinking_content,
                    "tool_calls": None,
                    "json_response": json_response
                }
            # Check if it's a direct tool call JSON
            extracted_tool = extract_json_tool_call(json_response)
            if extracted_tool:
                return {
                    "type": "tool_calls",
                    "tool_calls": [extracted_tool],
                    "content": None,
                    "thinking_content": thinking_content
                }
    except json.JSONDecodeError:
        pass
    
    # Fallback to text extraction
    extracted_tool = extract_tool_from_text(content)
    if extracted_tool:
        return {
            "type": "tool_calls",
            "tool_calls": [extracted_tool],
            "content": None,
            "thinking_content": thinking_content
        }
    
    # Default to text response
    return {
        "type": "text_response",
        "content": content,
        "thinking_content": thinking_content,
        "tool_calls": None
    }