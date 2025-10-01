# my_api_sdk/sync_client.py
import httpx
import time
import logging
from typing import Dict, Any, Optional, List

from .config import ClientConfig
from .exceptions import APIError, APIKeyInvalidError
from .utils import parse_httpx_error, handle_response_content
from .models import SyncEnvironment, SyncOntology
from pydantic import BaseModel
from typing import Type, Union
from pydantic import TypeAdapter

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
        logger = logging.getLogger(__name__)
        
        # Log request details
        request_start = time.time()
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"
        logger.info(f"PRAXOS-PYTHON: Starting {method} request to {url}")
        
        try:
            # Time the actual HTTP request
            http_start = time.time()
            response = self._http_client.request(
                method,
                url=endpoint.lstrip('/'),
                params=params,
                json=json_data if not files and not data else None,
                data=data,
                files=files
            )
            http_time = time.time() - http_start
            
            # Time response processing
            processing_start = time.time()
            response.raise_for_status()
            result = handle_response_content(response)
            processing_time = time.time() - processing_start
            
            total_time = time.time() - request_start
            
            logger.info(f"PRAXOS-PYTHON: {method} {endpoint} completed - "
                       f"http_request={http_time:.3f}s, "
                       f"response_processing={processing_time:.3f}s, "
                       f"total_time={total_time:.3f}s, "
                       f"status_code={response.status_code}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            error_time = time.time() - request_start
            logger.error(f"PRAXOS-PYTHON: {method} {endpoint} failed with HTTP error in {error_time:.3f}s - {e}")
            raise parse_httpx_error(e) from e
        except httpx.RequestError as e:
            error_time = time.time() - request_start
            logger.error(f"PRAXOS-PYTHON: {method} {endpoint} failed with request error in {error_time:.3f}s - {e}")
            raise APIError(status_code=0, message=f"Request failed: {str(e)}") from e
        
    def validate_api_key(self) -> None:
        """Validates the API key."""
        self._request("GET", "api-token-validataion")
        

    def create_environment(self, name: str, description: str=None, ontologies: List[Union[SyncOntology, str]]=None) -> SyncEnvironment:
        """Creates an environment."""

        if not name:
            raise ValueError("Environment name is required")
        
        ontology_ids = [ontology.id if isinstance(ontology, SyncOntology) else ontology for ontology in ontologies] if ontologies else None

        response_data = self._request("POST", "environment", json_data={"name": name, "description": description, "ontology_ids": ontology_ids})
        return SyncEnvironment(client=self, **response_data)

    def get_environments(self) -> List[SyncEnvironment]:
        """Retrieves all environments."""
        response_data = self._request("GET", "environment")
        return [SyncEnvironment(client=self, **env) for env in response_data]
    
    def get_environment(self, id: str=None, name: str=None) -> SyncEnvironment:
        """Retrieves an environment by name or id."""

        if id is None and name is None:
            raise ValueError("Either id or name must be provided")
        
        if id:
            response_data = self._request("GET", "environment", params={"id": id})
        else:
            response_data = self._request("GET", "environment", params={"name": name})
        return SyncEnvironment(client=self, **response_data)
    
    def create_ontology(self, name: str, schemas: List[Type[BaseModel]], description: str=None) -> SyncOntology:
        """Creates an ontology."""
        if not name:
            raise ValueError("Ontology name is required")
        
        if not schemas:
            raise ValueError("At least one schema is required")
        
        if not isinstance(schemas, list):
            raise ValueError("Schemas must be a list")
        
        json_schema = TypeAdapter(Union[tuple(schemas)]).json_schema()
        response_data = self._request("POST", "ontology", json_data={"name": name, "description": description, "schemas": json_schema})
        return SyncOntology(client=self, **response_data)
        
    
    def get_ontology(self, id: str=None, name: str=None) -> SyncOntology:
        """Retrieves an ontology by name or id."""

        if id is None and name is None:
            raise ValueError("Either id or name must be provided")
        
        if id:
            response_data = self._request("GET", "ontology", params={"id": id})
        else:
            response_data = self._request("GET", "ontology", params={"name": name})
        return SyncOntology(client=self, **response_data)
    
    def get_ontologies(self) -> List[SyncOntology]:
        """Retrieves all ontologies."""
        response_data = self._request("GET", "ontology")
        return [SyncOntology(client=self, **ontology) for ontology in response_data]

    def search_types(self, description: str, environment_id: str, limit: Optional[int] = None, kind: Optional[str] = None) -> Dict[str, Any]:
        """
        Searches for types based on a description.
        
        Args:
            description: A natural language description of the type.
            environment_id: The ID of the environment to search in.
            limit: The maximum number of results to return.
            kind: The kind of type to search for ('entity' or 'literal').
        
        Returns:
            A dictionary containing the search results.
        """
        if not description:
            raise ValueError("Description is required")
        if not environment_id:
            raise ValueError("Environment ID is required")

        json_data = {
            "description": description,
            "environment_id": environment_id,
        }
        if limit:
            json_data["limit"] = limit
        if kind:
            json_data["kind"] = kind
            
        return self._request("POST", "search/type", json_data=json_data)

    def close(self) -> None:
        """Closes the underlying httpx client."""
        self._http_client.close()

    def __enter__(self) -> 'SyncClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()