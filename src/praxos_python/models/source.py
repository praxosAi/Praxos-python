from typing import Dict, Any

class BaseSourceAttributes:
    """
    Base attributes for a Source resource.
    Ensures consistent initialization with core fields.
    """
    def __init__(self, id: str, environment_id: str, name: str, created_at: str, description: str, **kwargs):
        self.id = id
        self.name = name
        self.created_at = created_at
        self._environment_id = environment_id
        self.description = description


class SyncSource(BaseSourceAttributes):
    """Represents a synchronous Source resource."""
    def __init__(self, client, id: str, environment_id: str, name: str, created_at: str, description: str, **data: Any):
        super().__init__(id=id, environment_id=environment_id, name=name, created_at=created_at, description=description, **data)
        self._client = client
        

    def __repr__(self) -> str:
        return f"<SyncSource id='{self.id}' name='{self.name}'>"

    def get_status(self) -> Dict[str, Any]:
        """Gets the status of the source."""
        print(f"SDK (Sync Source: {self.name}): API to get status...") 
        return self._client._request("GET", f"/sources/{self.id}/status")