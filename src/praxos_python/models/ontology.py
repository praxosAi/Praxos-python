from typing import Any

class BaseOntologyAttributes:
    """
    Base attributes for an Ontology resource.
    Ensures consistent initialization with core fields.
    """
    def __init__(self, id: str, name: str, description: str, **kwargs):
        self.id = id
        self.name = name
        self.description = description

class SyncOntology(BaseOntologyAttributes):
    """Represents an Ontology resource."""
    def __init__(self, client, id: str, name: str, description: str, **data: Any):
        super().__init__(id=id, name=name, description=description, **data)
        self._client = client

    def __repr__(self) -> str:
        return f"<Ontology id='{self.id}' name='{self.name}'>"