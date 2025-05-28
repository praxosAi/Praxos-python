import os
from typing import TYPE_CHECKING, List, Dict, Any
from .source import SyncSource
from ..exceptions import APIError
from .context import Context
from ..types.message import Message

ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE = {
    "pdf": "application/pdf",
    "json": "application/json",
}

class BaseEnvironmentAttributes:
    """
    Base attributes for an Environment resource.
    Ensures consistent initialization with core fields.
    """
    def __init__(self, id: str, name: str, created_at: str, **kwargs):
        self.id = id
        self.name = name
        self.created_at = created_at


class SyncEnvironment(BaseEnvironmentAttributes):
    """Represents a synchronous Environment resource."""
    def __init__(self, client, id: str, name: str, created_at: str, **data: Any):
        super().__init__(id=id, name=name, created_at=created_at, **data)
        self._client = client

    def __repr__(self) -> str:
        return f"<SyncEnvironment id='{self.id}' name='{self.name}'>"

    def get_context(self, query: str, top_k: int = 1) -> Dict[str, Any]|List[Dict[str, Any]]:
        """Gets context for an LLM."""
        # print(f"SDK (Sync Env: {self.name}): API to get context for query '{query}'...") # For debugging
        response_data = self._client._request(
            "POST", f"/search", json_data={"query": query, "top_k": top_k}
        )

        contexts = []
        for context in response_data["hits"]:
            contexts.append(Context(score=context["score"], data=context["data"], sentence=context["sentence"]))

        if top_k == 1:
            return contexts[0]
        else:
            return contexts

    def add_conversation(self, messages: List[Message|Dict[str, str]], source_name: str=None, description: str=None) -> SyncSource:
        """Adds a conversation source."""
        if len(messages) == 0:
            raise ValueError("Messages must be a non-empty list")
        
        messages = [Message.from_dict(message) if isinstance(message, dict) else message for message in messages]
        
        payload = {
            "messages": [message.to_dict() for message in messages],
            "description": description
        }

        if source_name:
            payload["name"] = source_name

        response_data = self._client._request("POST", f"/sources", params={"type": "conversation", "environment_id": self.id}, json_data=payload)
        return SyncSource(client=self._client, **response_data)

    def add_file(self, file_path: str, name: str=None, description: str=None) -> SyncSource:
        """Adds a file source."""
        global ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_extension = file_path.split('.')[-1]
        if file_extension not in ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE:
            raise ValueError(f"File extension {file_extension} is not supported. Supported extensions are: {', '.join(ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE.keys())}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (name, f, ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE[file_extension])}
                form_data = {"type": "file", "name": name, "description": description}
                response_data = self._client._request(
                    "POST", f"sources", params={"environment_id": self.id}, data=form_data, files=files
                )
            return SyncSource(client=self._client, **response_data)
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")
        except Exception as e:
            raise APIError(status_code=0, message=f"Sync file upload failed: {str(e)}") from e