from typing import Optional, Dict, Any, Union
import httpx
import sys

try:
    if sys.version_info >= (3, 8):
        from importlib.metadata import version, PackageNotFoundError
    else:
        from importlib_metadata import version, PackageNotFoundError

    SDK_VERSION = version("Praxos-python")
except PackageNotFoundError:
    SDK_VERSION = "0.0.0-dev"

DEFAULT_BASE_URL = "https://api.praxos.ai/"

class ClientConfig:
    """Configuration settings for API clients."""
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        params: Optional[Dict[str, Any]] = None,
        httpx_settings: Optional[Dict[str, Any]] = None
    ):
        if not api_key:
            raise ValueError("API key is required.")

        self.api_key = api_key
        self.base_url = httpx.URL(base_url or DEFAULT_BASE_URL)
        self.timeout = timeout
        self.params = params or {}
        self.httpx_settings = httpx_settings or {}

        self.common_headers = {
            "api-key": f"{self.api_key}",
            "User-Agent": f"Praxos Python SDK/{SDK_VERSION}"
        }