"""
Restricted Retriever

Syllabus-locked RAG that only uses approved corpus.
"""

from typing import List, Dict, Optional, Any
from packages.core.rag.retriever import Retriever


class RestrictedRetriever:
    """
    Restricted retriever that only accesses approved sources.
    
    Ensures only syllabus-approved content is retrieved.
    """
    
    def __init__(
        self,
        base_retriever: Retriever,
        approved_source_ids: List[str],
        strict_mode: bool = True
    ):
        """
        Initialize restricted retriever.
        
        Args:
            base_retriever: Base retriever to wrap
            approved_source_ids: List of approved source IDs
            strict_mode: Strictly enforce restrictions (default: True)
        """
        self.base_retriever = base_retriever
        self.approved_source_ids = set(approved_source_ids) if approved_source_ids else set()
        self.strict_mode = strict_mode
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filter: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        query_embedding: Optional[List[float]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve with source restrictions.
        
        Args:
            query: Query text
            top_k: Number of results
            filter: Optional filter dict
            conversation_history: Optional conversation history
            query_embedding: Optional query embedding
            **kwargs: Additional arguments
            
        Returns:
            Retrieval results with only approved sources
        """
        # Merge approved source filter with existing filter
        if filter is None:
            filter = {}
        
        # Add approved source restriction
        if self.approved_source_ids:
            existing_source_filter = filter.get("source_id", {})
            
            if isinstance(existing_source_filter, dict) and "$in" in existing_source_filter:
                # Intersect with approved sources
                requested_sources = set(existing_source_filter["$in"])
                approved_intersection = requested_sources.intersection(self.approved_source_ids)
                
                if self.strict_mode and not approved_intersection:
                    # No approved sources in request
                    return {
                        "matches": [],
                        "query": query,
                        "namespace": self.base_retriever.tenant_id,
                        "restricted": True,
                        "message": "No approved sources available for this query"
                    }
                
                filter["source_id"] = {"$in": list(approved_intersection)}
            else:
                # Set to approved sources only
                filter["source_id"] = {"$in": list(self.approved_source_ids)}
        else:
            # No approved sources configured - block all
            if self.strict_mode:
                return {
                    "matches": [],
                    "query": query,
                    "namespace": self.base_retriever.tenant_id,
                    "restricted": True,
                    "message": "No approved sources configured"
                }
        
        # Call base retriever with restricted filter
        results = await self.base_retriever.retrieve(
            query=query,
            top_k=top_k,
            filter=filter,
            conversation_history=conversation_history,
            query_embedding=query_embedding,
            **kwargs
        )
        
        # Additional filtering: ensure all returned sources are approved
        if results.get("matches") and self.approved_source_ids:
            approved_matches = [
                match for match in results["matches"]
                if match.get("metadata", {}).get("source_id") in self.approved_source_ids
            ]
            results["matches"] = approved_matches
        
        results["restricted"] = True
        results["approved_sources_count"] = len(self.approved_source_ids)
        
        return results
    
    def add_approved_source(self, source_id: str):
        """Add a source to approved list."""
        self.approved_source_ids.add(source_id)
    
    def remove_approved_source(self, source_id: str):
        """Remove a source from approved list."""
        self.approved_source_ids.discard(source_id)
    
    def is_source_approved(self, source_id: str) -> bool:
        """Check if a source is approved."""
        return source_id in self.approved_source_ids
    
    def get_approved_sources(self) -> List[str]:
        """Get list of approved source IDs."""
        return list(self.approved_source_ids)
