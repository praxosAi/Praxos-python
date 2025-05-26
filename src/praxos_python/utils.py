import httpx
from typing import Dict, Any
from .exceptions import APIError, APIKeyInvalidError

def parse_httpx_error(e: httpx.HTTPStatusError) -> APIError:
    """Helper to parse HTTPStatusError into APIError."""
    error_message = str(e)
    response_data = {}
    try:
        error_details = e.response.json()
        response_data = error_details
        if isinstance(error_details, dict):
            error_message = error_details.get("message", error_details.get("error", str(e)))
        
    except Exception:
        pass

    if e.response.status_code == 401:
        return APIKeyInvalidError(message=error_message, response_data=response_data)
    
    return APIError(status_code=e.response.status_code, message=error_message, response_data=response_data)

def handle_response_content(response: httpx.Response) -> Dict[str, Any]:
    """
    Processes httpx.Response content after raise_for_status.
    Assumes response.raise_for_status() has been called.
    """
    if response.status_code == 204: # No Content
        return {}
    if not response.content:
        return {}
    return response.json()