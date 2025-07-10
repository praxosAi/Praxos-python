import os
from typing import List, Dict, Any, Type, Union
from pydantic import BaseModel
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
    def __init__(self, id: str, name: str, created_at: str, description: str, **kwargs):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.description = description

class SyncEnvironment(BaseEnvironmentAttributes):
    """Represents a synchronous Environment resource."""
    def __init__(self, client, id: str, name: str, created_at: str, description: str, **data: Any):
        super().__init__(id=id, name=name, created_at=created_at, description=description, **data)
        self._client = client

    def __repr__(self) -> str:
        return f"<SyncEnvironment id='{self.id}' name='{self.name}'>"

    def get_context(self, query: str, top_k: int = 1) -> Context|List[Context]:
        """Gets context for an LLM using vec_edge search modality."""
        response_data = self._client._request(
            "POST", f"/search", json_data={"query": query, "top_k": top_k, "environment_id": self.id, "search_modality": "vec_edge"}
        )

        contexts = []
        for context in response_data["hits"]:
            sentence = context.get("sentence", "")
            contexts.append(Context(score=context["score"], data=context["data"], sentence=sentence))

        if top_k == 1:
            return contexts[0]
        else:
            return contexts
    
    def search(self, query: str, top_k: int = 10, search_modality: str = "node_vec", 
               source_id: str = None, target_type: str = None, source_type: str = None,
               target_label: str = None, source_label: str = None, 
               target_type_oid: str = None, source_type_oid: str = None,
               relationship_type: str = None, relationship_label: str = None,
               # New node-based parameters
               node_type: str = None, node_label: str = None, node_kind: str = None,
               has_sentence: bool = None, include_graph_context: bool = True,
               # Temporal filtering
               temporal_filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple modalities.
        
        Args:
            query: Search query text (required)
            top_k: Number of results to return
            search_modality: "node_vec", "vec_edge", or "type_vec" (default: node_vec)
            source_id: Optional source ID filter
            
            # Legacy edge-based filters (for backward compatibility)
            target_type: Optional target node type filter
            source_type: Optional source node type filter
            target_label: Optional target node label filter
            source_label: Optional source node label filter
            target_type_oid: Optional target node type OID filter
            source_type_oid: Optional source node type OID filter
            relationship_type: Optional relationship type filter
            relationship_label: Optional relationship label filter
            
            # New node-based filters (for node_vec searches)
            node_type: Filter by node type (e.g., "schema:Person")
            node_label: Filter by node label
            node_kind: Filter by node kind ("entity", "literal", "edge_sentence")
            has_sentence: Filter nodes that have generated sentences
            include_graph_context: Include graph context in results
            
            # Temporal filtering
            temporal_filter: Temporal filtering options (dict with timepoint_type, time_period, etc.)
        
        Returns:
            List of search results with scores and data
        """
        payload = {
            "query": query,
            "environment_id": self.id,
            "search_modality": search_modality,
            "top_k": top_k,
            "include_graph_context": include_graph_context
        }
        
        # Legacy edge-based filters (for backward compatibility)
        if source_id:
            payload["source_id"] = source_id
        if target_type:
            payload["target_type"] = target_type
        if source_type:
            payload["source_type"] = source_type
        if target_label:
            payload["target_label"] = target_label
        if source_label:
            payload["source_label"] = source_label
        if target_type_oid:
            payload["target_type_oid"] = target_type_oid
        if source_type_oid:
            payload["source_type_oid"] = source_type_oid
        if relationship_type:
            payload["relationship_type"] = relationship_type
        if relationship_label:
            payload["relationship_label"] = relationship_label
        
        # New node-based filters
        if node_type:
            payload["node_type"] = node_type
        if node_label:
            payload["node_label"] = node_label
        if node_kind:
            payload["node_kind"] = node_kind
        if has_sentence is not None:
            payload["has_sentence"] = has_sentence
        if temporal_filter:
            payload["temporal_filter"] = temporal_filter
        
        response_data = self._client._request("POST", "/search", json_data=payload)
        return response_data.get("hits", [])
    
    def search_with_types(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search with automatic type inference using AI classification.
        Uses the type_vec modality to automatically infer source and target types.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
        
        Returns:
            List of search results with type classification metadata
        """
        return self.search(query=query, top_k=top_k, search_modality="type_vec")
    
    def search_entities(self, query: str, entity_types: List[str] = None, top_k: int = 10, 
                       include_temporal: bool = False) -> List[Dict[str, Any]]:
        """
        Entity-centric search focusing on entities with generated sentences.
        
        Args:
            query: Search query text
            entity_types: Optional list of entity types to filter by
            top_k: Number of results to return
            include_temporal: Include temporal context in results
        
        Returns:
            List of entity search results with comprehensive context
        """
        if entity_types:
            # Search each entity type and combine results
            all_results = []
            for entity_type in entity_types:
                results = self.search(
                    query=query,
                    search_modality="node_vec",
                    node_kind="entity",
                    node_type=entity_type,
                    has_sentence=True,
                    top_k=top_k,
                    include_graph_context=True
                )
                all_results.extend(results)
            
            # Sort by score and limit results
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            return all_results[:top_k]
        else:
            return self.search(
                query=query,
                search_modality="node_vec",
                node_kind="entity",
                has_sentence=True,
                top_k=top_k,
                include_graph_context=True
            )
    
    def search_temporal(self, query: str, timepoint_type: str = None, time_period: str = None, 
                       top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Temporal-aware search using TimePoint nodes for filtering.
        
        Args:
            query: Search query text
            timepoint_type: Type of TimePoint to filter by (e.g., "Quarter", "Month")
            time_period: Specific time period (e.g., "2023-Q4", "January")
            top_k: Number of results to return
        
        Returns:
            List of search results filtered by temporal criteria
        """
        temporal_filter = {}
        if timepoint_type:
            temporal_filter["timepoint_type"] = timepoint_type
        if time_period:
            temporal_filter["time_period"] = time_period
        
        return self.search(
            query=query,
            search_modality="node_vec",
            temporal_filter=temporal_filter if temporal_filter else None,
            top_k=top_k,
            include_graph_context=True
        )
    
    def search_sentences(self, query: str, sentence_types: List[str] = None, 
                        top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search within generated sentences across different node types.
        
        Args:
            query: Search query text
            sentence_types: Node kinds to search within (default: ["entity", "edge_sentence"])
            top_k: Number of results to return
        
        Returns:
            List of sentence-based search results
        """
        if not sentence_types:
            sentence_types = ["entity", "edge_sentence"]
        
        all_results = []
        for sentence_type in sentence_types:
            results = self.search(
                query=query,
                search_modality="node_vec",
                node_kind=sentence_type,
                has_sentence=True,
                top_k=top_k,
                include_graph_context=True
            )
            all_results.extend(results)
        
        # Sort by score and limit results
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:top_k]
    
    def fetch_graph_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch nodes from Neo4j graph by their node IDs.
        
        Args:
            node_ids: List of Neo4j node IDs to fetch
        
        Returns:
            List of graph nodes with their properties and literals
        """
        payload = {
            "node_ids": node_ids,
            "environment_id": self.id
        }
        
        response_data = self._client._request("POST", "/fetch-graph-nodes", json_data=payload)
        return response_data.get("results", [])
    
    def extract_items(self, schema: Union[str, Type[BaseModel]], source_id: str = None, page_idx: str = None):
        """
        Extracts entities from a schema/label.
        
        Args:
            schema: Schema name or Pydantic model class
            source_id: Optional source ID filter
            page_idx: Optional page index filter
        
        Returns:
            List of extracted entity items
        """
        schema_name = schema if isinstance(schema, str) else schema.__name__

        payload = {
            "extraction_type": "entities",
            "label": schema_name,
            "environment_id": self.id
        }
        
        if source_id:
            payload["source_id"] = source_id
        if page_idx:
            payload["page_idx"] = page_idx

        response_data = self._client._request("POST", f"/extract", json_data=payload)
        return response_data.get("items", [])
    
    def extract_literals(self, literal_type: str, mode: str = "literals_only", 
                        source_id: str = None, page_idx: str = None) -> Dict[str, Any]:
        """
        Extract literals of a specific type from the graph.
        
        Args:
            literal_type: Type of literal to extract (e.g., 'EmailType', 'PhoneNumberType')
            mode: "literals_only" to get just the literals, "full_entities" to get entities with literals
            source_id: Optional source ID filter
            page_idx: Optional page index filter
        
        Returns:
            Dictionary with extraction results based on mode
        """
        if mode not in ["literals_only", "full_entities"]:
            raise ValueError("mode must be 'literals_only' or 'full_entities'")
        
        payload = {
            "extraction_type": "literals",
            "literal_type": literal_type,
            "mode": mode,
            "environment_id": self.id
        }
        
        if source_id:
            payload["source_id"] = source_id
        if page_idx:
            payload["page_idx"] = page_idx
        
        response_data = self._client._request("POST", "/extract", json_data=payload)
        return response_data
    

    def add_conversation(self, messages: List[Message|Dict[str, str]], name: str=None, description: str=None) -> SyncSource:
        """Adds a conversation source."""
        if len(messages) == 0:
            raise ValueError("Messages must be a non-empty list")
        
        messages = [Message.from_dict(message) if isinstance(message, dict) else message for message in messages]
        
        payload = {
            "messages": [message.to_dict() for message in messages],
            "description": description
        }

        if name:
            payload["name"] = name

        response_data = self._client._request("POST", f"/sources", params={"type": "conversation", "environment_id": self.id}, json_data=payload)
        return SyncSource(client=self._client, **response_data)

    def add_file(self, path: str, name: str=None, description: str=None) -> SyncSource:
        """Adds a file source."""
        global ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE

        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        file_extension = path.split('.')[-1]
        if file_extension not in ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE:
            raise ValueError(f"File extension {file_extension} is not supported. Supported extensions are: {', '.join(ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE.keys())}")
        
        if name is None:
            name = '.'.join(os.path.basename(path).split('.')[:-1])

        try:
            with open(path, 'rb') as f:
                files = {'file': (name, f, ACCEPTABLE_SOURCE_EXTENSIONS_TO_CONTENT_TYPE[file_extension])}
                form_data = {"type": "file", "name": name, "description": description}
                response_data = self._client._request(
                    "POST", f"sources", params={"environment_id": self.id}, data=form_data, files=files
                )
            return SyncSource(client=self._client, **response_data)
        except FileNotFoundError:
            raise ValueError(f"File not found: {path}")
        except Exception as e:
            raise APIError(status_code=0, message=f"Sync file upload failed: {str(e)}") from e
        
    def add_business_data(self, data: Dict[str, Any], name: str=None, description: str=None) -> SyncSource:
        """Adds business data source."""
        payload = {
            "data": data,
            "name": name,
            "description": description
        }

        response_data = self._client._request("POST", f"/sources", params={"environment_id": self.id}, json_data=payload)
        return SyncSource(client=self._client, **response_data)
    
    def get_sources(self) -> List[SyncSource]:
        """Gets all sources for the environment."""
        response_data = self._client._request("GET", f"/sources", params={"environment_id": self.id})
        return [SyncSource(client=self._client, **source) for source in response_data]

    def get_source(self, id: str=None, name: str=None) -> SyncSource:
        """Gets a source for the environment."""
        if id is None and name is None:
            raise ValueError("Either id or name must be provided")
        
        if id:
            response_data = self._client._request("GET", f"/sources", params={"environment_id": self.id, "id": id})
        else:
            response_data = self._client._request("GET", f"/sources", params={"environment_id": self.id, "name": name})

        return SyncSource(client=self._client, **response_data)
