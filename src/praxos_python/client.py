# my_api_sdk/sync_client.py
import httpx
from typing import Dict, Any, Optional, List

from .config import ClientConfig
from .exceptions import APIError, APIKeyInvalidError
from .utils import parse_httpx_error, handle_response_content
from .models import SyncEnvironment

class SyncClient:
    """Synchronous client for interacting with the API."""
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ):
        self.config = ClientConfig(
            api_key=api_key, base_url=base_url, timeout=timeout, params=params
        )

        self._http_client = httpx.Client(
            base_url=self.config.base_url,
            headers=self.config.common_headers,
            timeout=self.config.timeout,
            params=self.config.params,
            **self.config.httpx_settings
        )

        self.validate_api_key()


    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            response = self._http_client.request(
                method,
                url=endpoint.lstrip('/'),
                params=params,
                json=json_data if not files and not data else None,
                data=data,
                files=files
            )
            response.raise_for_status()
            return handle_response_content(response)
        except httpx.HTTPStatusError as e:
            raise parse_httpx_error(e) from e
        except httpx.RequestError as e:
            raise APIError(status_code=0, message=f"Request failed: {str(e)}") from e
        
    def validate_api_key(self) -> None:
        """Validates the API key."""
        self._request("GET", "api-token-validataion")
        

    def create_environment(self, name: str) -> SyncEnvironment:
        """Creates an environment."""

        if not name:
            raise ValueError("Environment name is required")

        response_data = self._request("POST", "environment", json_data={"name": name})
        return SyncEnvironment(client=self, id=response_data["id"], name=response_data["name"], created_at=response_data["created_at"])

    def get_environments(self) -> List[SyncEnvironment]:
        """Retrieves all environments."""
        response_data = self._request("GET", "environment")
        return [SyncEnvironment(client=self, id=env["id"], name=env["name"], created_at=env["created_at"]) for env in response_data]
    
    # def get_environment(self, name: str) -> SyncEnvironment:
    #     """Retrieves an environment by name."""
    #     # MOCKED RESPONSE - Replace with actual API call using self._request
    #     response_data = {
    #         "id": f"env_sync_{name.replace(' ', '_')}_gt_456", "name": name,
    #         "created_at": datetime.datetime.utcnow().isoformat()
    #     }
    #     # response_data = self._request("GET", f"/environments/{name}")
    #     return SyncEnvironment(client=self, **response_data)

    def close(self) -> None:
        """Closes the underlying httpx client."""
        self._http_client.close()

    def __enter__(self) -> 'SyncClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()