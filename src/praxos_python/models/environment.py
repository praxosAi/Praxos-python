import os
import time
import logging
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

    def get_context(self, query: str, top_k: int = 1) -> Union[Context, List[Context]]:
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
    
    def search(self, query: str, top_k: int = 10, search_modality: str = "intelligent",
               source_id: str = None, target_type: str = None, source_type: str = None,
               target_label: str = None, source_label: str = None,
               target_type_oid: str = None, source_type_oid: str = None,
               relationship_type: str = None, relationship_label: str = None,
               # New node-based parameters
               node_type: str = None, node_label: str = None, node_kind: str = None,
               has_sentence: bool = None, include_graph_context: bool = True,
               # Temporal filtering
               temporal_filter: Dict[str, Any] = None,
               # Anchor-based filtering
               known_anchors: List[Dict[str, Any]] = None,
               anchor_max_hops: int = 2,
               # Filtering already-seen nodes
               exclude_nodes: List[str] = None) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple modalities.
        
        Args:
            query: Search query text (required)
            top_k: Number of results to return
            search_modality: "intelligent", "fast", "node_vec", "vec_edge", or "type_vec" (default: intelligent)
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
            
            # New node-based filters (for fast and node_vec searches)
            node_type: Filter by node type (e.g., "schema:Person")
            node_label: Filter by node label
            node_kind: Filter by node kind ("entity", "literal", "edge_sentence")
            has_sentence: Filter nodes that have generated sentences
            include_graph_context: Include graph context in results (node_vec provides advanced graph traversal)
            
            # Temporal filtering
            temporal_filter: Temporal filtering options (dict with timepoint_type, time_period, etc.)
            
            # Anchor-based filtering (for graph traversal from specific anchor points)
            known_anchors: List of anchor points to constrain search space. Each anchor can specify:
                          - id: Exact node ID
                          - type: Node type (e.g., "PhoneType", "schema:Person")
                          - label: Node label
                          - value: Node value (for literals)
                          - kind: Node kind ("entity", "literal")
            anchor_max_hops: Maximum graph distance from any anchor point (default: 2)
        
        Returns:
            List of search results with scores and data
        """
        # Validate search modality  
        valid_modalities = ["fast", "node_vec", "vec_edge", "type_vec", "intelligent"]
        if search_modality not in valid_modalities:
            raise ValueError(f"Invalid search modality. Must be one of: {valid_modalities}")
        
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
        
        # Add anchor-based filtering if provided
        if known_anchors:
            payload["known_anchors"] = known_anchors
            payload["anchor_max_hops"] = anchor_max_hops

        # Add node exclusion filtering if provided
        if exclude_nodes:
            payload["exclude_node_ids"] = exclude_nodes

        logger = logging.getLogger(__name__)
        search_start = time.time()
        
        logger.info(f"PRAXOS-PYTHON: Starting search - query='{query[:50]}...', modality={search_modality}, top_k={top_k}")
        
        response_data = self._client._request("POST", "/search", json_data=payload)
        
        search_time = time.time() - search_start
        results = response_data.get("hits", [])
        
        logger.info(f"PRAXOS-PYTHON: Search completed in {search_time:.3f}s, returned {len(results)} results")
        
        return results
    
    def intelligent_search(self, query: str, max_results: int = 20, source_id: str = None, 
                          enable_multi_strategy: bool = True, force_strategy: str = None) -> Dict[str, Any]:
        """
        AI-powered intelligent search that automatically analyzes queries and selects optimal strategies.
        
        This method uses AI to:
        - Analyze query intent and extract meaningful terms
        - Find relevant types from your type unification collection
        - Detect temporal anchors and create appropriate filters
        - Route through optimal search strategies (node_vec, fast, etc.)
        - Combine results from multiple strategies when beneficial
        
        Args:
            query: Natural language search query
            max_results: Maximum results to return (default: 20)
            source_id: Optional source ID filter
            enable_multi_strategy: Allow backup strategies if primary doesn't return enough results (default: True)
            force_strategy: Force a specific strategy, overriding AI selection (optional)
        
        Returns:
            Dictionary containing:
            - hits: List of search results
            - intelligent_analysis: AI analysis metadata including:
                - execution_plan: Strategy selection reasoning
                - strategies_used: List of strategies executed
                - type_analysis: Detected types and confidence
                - execution_time: Total processing time
        
        Example:
            # Simple intelligent search
            results = env.intelligent_search("financial transactions in November 2023")
            
            # Access results
            for hit in results["hits"]:
                print(f"Score: {hit['score']:.3f}")
                print(f"Sentence: {hit['sentence']}")
                print(f"Data: {hit['data']}")
            
            # Access AI analysis
            analysis = results["intelligent_analysis"]
            print(f"Strategies used: {analysis['strategies_used']}")
            print(f"Execution time: {analysis['execution_time']:.3f}s")
        """
        # Build search payload - intelligent search goes directly to search service
        payload = {
            "query": query,
            "environment_id": self.id,
            "search_modality": "intelligent",
            "top_k": max_results,
            "include_graph_context": True
        }
        
        # Add optional parameters
        if source_id:
            payload["source_id"] = source_id
        # Note: enable_multi_strategy and force_strategy are handled by the intelligent search service
        
        logger = logging.getLogger(__name__)
        search_start = time.time()
        
        logger.info(f"PRAXOS-PYTHON: Starting intelligent search - query='{query[:50]}...', max_results={max_results}")
        
        # Call the search endpoint - the response will include intelligent analysis
        response_data = self._client._request("POST", "/search", json_data=payload)
        
        search_time = time.time() - search_start
        hits = response_data.get("hits", [])
        
        logger.info(f"PRAXOS-PYTHON: Intelligent search completed in {search_time:.3f}s, returned {len(hits)} results")
        
        # Return full response including intelligent analysis
        return {
            "hits": hits,
            "intelligent_analysis": response_data.get("intelligent_analysis", {}),
            "query_analysis": response_data.get("query_analysis", {}),
            "graph_stats": response_data.get("graph_stats", {})
        }
    
    def search_fast(self, query: str, top_k: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Fast Qdrant-based search with basic filtering.
        Optimized for speed over complex graph relationships.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            **kwargs: Additional filters (node_type, node_kind, has_sentence, etc.)
        
        Returns:
            List of search results optimized for speed
        """
        return self.search(query=query, top_k=top_k, search_modality="fast", **kwargs)
    
    def search_graph(self, query: str, top_k: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Neo4j graph-aware search with relationship traversal.
        Optimized for complex graph relationships and traversal.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            **kwargs: Additional filters and graph context options
        
        Returns:
            List of search results with full graph context
        """
        kwargs.setdefault('include_graph_context', True)
        return self.search(query=query, top_k=top_k, search_modality="node_vec", **kwargs)

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
    
    def search_from_anchors(self, anchors: List[Dict[str, Any]], query: str, max_hops: int = 2, **kwargs) -> List[Dict[str, Any]]:
        """
        Search entities within k-hops of specified anchor points.
        
        Args:
            anchors: List of anchor points to constrain search space
            query: Semantic search query for connected entities
            max_hops: Maximum graph distance from any anchor point
            **kwargs: Additional search parameters
        
        Returns:
            List of entities within k-hops of anchor points
        """
        kwargs.setdefault('search_modality', 'node_vec')  # Force graph search
        return self.search(
            query=query,
            known_anchors=anchors,
            anchor_max_hops=max_hops,
            **kwargs
        )
    
    def search_from_element(self, element_id: str, query: str, max_hops: int = 2, **kwargs) -> List[Dict[str, Any]]:
        """
        Search entities connected to a specific element ID.
        
        Args:
            element_id: Node ID to start search from
            query: Semantic search query for connected entities
            max_hops: Maximum graph distance to traverse
            **kwargs: Additional search parameters
        
        Returns:
            List of entities connected to the known element
        """
        return self.search_from_anchors(
            anchors=[{"id": element_id}],
            query=query,
            max_hops=max_hops,
            **kwargs
        )
    
    def search_from_phone(self, phone: str, query: str = "related entities", **kwargs) -> List[Dict[str, Any]]:
        """
        Search entities connected to a phone number.
        
        Args:
            phone: Phone number to search from
            query: What to look for (default: "related entities")
            **kwargs: Additional search parameters
        
        Returns:
            List of entities connected to the phone number
        """
        return self.search_from_anchors(
            anchors=[{"value": phone, "type": "PhoneType"}],
            query=query,
            **kwargs
        )
    
    def search_from_email(self, email: str, query: str = "related entities", **kwargs) -> List[Dict[str, Any]]:
        """
        Search entities connected to an email address.
        
        Args:
            email: Email address to search from
            query: What to look for (default: "related entities")
            **kwargs: Additional search parameters
        
        Returns:
            List of entities connected to the email
        """
        return self.search_from_anchors(
            anchors=[{"value": email, "type": "EmailType"}],
            query=query,
            **kwargs
        )
    
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
    

    def add_conversation(self, messages: List[Union[Message, Dict[str, str]]], name: str=None, description: str=None) -> SyncSource:
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
        
    def add_business_data(self, data: Dict[str, Any], name: str=None, description: str=None, 
                         root_entity_type: str="schema:Thing", metadata: Dict[str, Any]=None,
                         processing_config: Dict[str, Any]=None) -> SyncSource:
        """
        Adds business data source with enhanced JSON processing.
        
        Args:
            data: JSON data to process
            name: Optional source name
            description: Optional description
            root_entity_type: Root entity type for JSON processing (default: "schema:Thing")
            metadata: Additional metadata for processing
            processing_config: Custom processing configuration
            
        Returns:
            SyncSource object
        """
        payload = {
            "data": data,
            "name": name,
            "description": description,
            "root_entity_type": root_entity_type,
            "metadata": metadata or {},
            "processing_config": processing_config or {}
        }

        response_data = self._client._request("POST", f"/sources", params={"environment_id": self.id}, json_data=payload)
        return SyncSource(client=self._client, **response_data)
    
    def add_networkx_graph(self, graph, name: str=None, description: str=None,
                          metadata: Dict[str, Any]=None, processing_config: Dict[str, Any]=None) -> SyncSource:
        """
        Adds a NetworkX graph as a source for processing.
        
        Args:
            graph: NetworkX MultiDiGraph or DiGraph object
            name: Optional source name
            description: Optional description
            metadata: Additional metadata for processing
            processing_config: Custom processing configuration (e.g., skip steps)
            
        Returns:
            SyncSource object
            
        Example:
            import networkx as nx
            G = nx.MultiDiGraph()
            G.add_node("person_1", type="schema:Person", name="John Doe")
            G.add_node("org_1", type="schema:Organization", name="Acme Corp")
            G.add_edge("person_1", "org_1", type="WORKS_AT")
            
            source = env.add_networkx_graph(
                graph=G,
                name="my_graph",
                processing_config={"generate_sentences": True, "generate_facts": False}
            )
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("NetworkX is required for graph ingestion. Install with: pip install networkx")
        
        if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph, nx.MultiGraph)):
            raise ValueError("Graph must be a NetworkX graph object")
        
        # Convert to node-link format for API transmission
        graph_data = nx.node_link_data(graph)
        
        payload = {
            "graph_data": graph_data,
            "name": name,
            "description": description,
            "metadata": metadata or {},
            "processing_config": processing_config or {}
        }

        response_data = self._client._request(
            "POST", 
            f"/sources", 
            params={"environment_id": self.id, "type": "networkx_graph"}, 
            json_data=payload
        )
        return SyncSource(client=self._client, **response_data)

    def enrich(self, node_ids: Union[str, List[str]], k: int = 2, generate_sentences: bool = False) -> Dict[str, Any]:
        """
        Enriches a given node or list of nodes by finding the closest entity and retrieving all entities up to k hops away.

        Args:
            node_ids: A single node ID or a list of node IDs to enrich.
            k: The number of hops to traverse for enrichment.
            generate_sentences: Whether to generate contextual sentences using LLM (default: False)

        Returns:
            A dictionary containing the enriched data for each node.
        """
        if not node_ids:
            raise ValueError("node_ids cannot be empty")

        payload = {
            "node_ids": node_ids,
            "k": k,
            "generate_sentences": generate_sentences
        }

        response_data = self._client._request("POST", "/enrich", json_data=payload)
        return response_data

    def extract_intelligent(self, query: str, strategy: str = 'entity_extraction',
                           max_results: int = 20, source_id: str = None) -> Dict[str, Any]:
        """
        Use intelligent extraction to find entities or literals with forced strategy.
        Leverages AI classification but forces a specific extraction strategy.

        Args:
            query: Natural language query describing what to extract
            strategy: Extraction strategy - 'entity_extraction' or 'literal_extraction'
            max_results: Maximum results to return
            source_id: Optional source ID filter

        Returns:
            Dictionary containing:
            - hits: List of extracted items
            - intelligent_analysis: AI classification metadata
            - strategies_used: Strategies executed

        Examples:
            # Extract all Person entities
            people = env.extract_intelligent("people I know", strategy='entity_extraction')

            # Extract all email addresses
            emails = env.extract_intelligent("email addresses", strategy='literal_extraction')
        """
        if strategy not in ['entity_extraction', 'literal_extraction', 'anchored_entity_extraction', 'anchored_literal_extraction']:
            raise ValueError(f"Invalid strategy. Must be one of: entity_extraction, literal_extraction, anchored_entity_extraction, anchored_literal_extraction")

        # Use intelligent search endpoint with forced strategy
        payload = {
            "query": query,
            "user_id": self._client.config.params.get("user_id", "default_user") if self._client.config.params else "default_user",
            "environment_id": self.id,
            "max_results": max_results,
            "force_strategy": strategy,
            "enable_multi_strategy": False  # Force single strategy
        }

        if source_id:
            payload["source_id"] = source_id

        logger = logging.getLogger(__name__)
        logger.info(f"PRAXOS-PYTHON: Intelligent extraction - query='{query[:50]}...', strategy={strategy}")

        response_data = self._client._request("POST", "/search/intelligent", json_data=payload)

        # Format response for easier consumption
        return {
            "hits": response_data.get("primary_results", []),
            "intelligent_analysis": response_data.get("type_analysis", {}),
            "strategies_used": response_data.get("strategies_used", []),
            "execution_time": response_data.get("execution_time", 0)
        }

    def get_nodes_by_type(self, type_name: str, include_literals: bool = True,
                         include_relationships: bool = False, source_id: str = None,
                         max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Get all nodes of a specific type with their properties.
        Intuitive wrapper around extract_items for type-based retrieval.

        Args:
            type_name: Type or label of nodes to retrieve (e.g., "schema:Person", "Vehicle")
            include_literals: Include connected literal properties (default: True)
            include_relationships: Include connected entity relationships (default: False)
            source_id: Optional source ID filter
            max_results: Maximum results to return (default: 100)

        Returns:
            List of nodes with their properties and optional relationships

        Examples:
            # Get all Person entities
            people = env.get_nodes_by_type("schema:Person")

            # Get all vehicles from a specific source
            vehicles = env.get_nodes_by_type("Vehicle", source_id="import_2024")

            # Get integrations with relationships
            integrations = env.get_nodes_by_type(
                "schema:Integration",
                include_relationships=True
            )
        """
        logger = logging.getLogger(__name__)
        logger.info(f"PRAXOS-PYTHON: Getting nodes by type - type={type_name}, include_literals={include_literals}")

        # Use extract_items endpoint
        payload = {
            "label": type_name,
            "environment_id": self.id,
            "user_id": self._client.config.params.get("user_id", "default_user") if self._client.config.params else "default_user"
        }

        if source_id:
            payload["source_id"] = source_id

        response_data = self._client._request("POST", "/extract-items", json_data=payload)
        results = response_data.get("results", [])

        logger.info(f"PRAXOS-PYTHON: Found {len(results)} nodes of type {type_name}")

        # Limit results
        return results[:max_results]
    
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

    def ingest_trigger(self, text: str) -> Dict[str, Any]:
        """
        Ingests a natural language trigger into the system for this environment.

        Args:
            text: The natural language text of the trigger.

        Returns:
            A dictionary containing the ingestion status response.
        """
        if not text:
            raise ValueError("Trigger text is required")

        json_data = {
            "text": text,
            "environment_id": self.id,
        }
        return self._client._request("POST", "ingest-trigger", json_data=json_data)

    def evaluate_event(self, event_json: Dict, provider: str) -> Dict[str, Any]:
        """
        Evaluates an incoming event against the rules in this environment.

        Args:
            event_json: The event payload as a dictionary.
            provider: The source provider of the event (e.g., 'gmail', 'outlook').

        Returns:
            A dictionary containing the evaluation results, including any fired rules.
        """
        if not event_json:
            raise ValueError("Event JSON is required")
        if not provider:
            raise ValueError("Provider is required")

        json_data = {
            "event_json": event_json,
            "environment_id": self.id,
            "provider": provider,
        }
        return self._client._request("POST", "evaluate-event", json_data=json_data)
