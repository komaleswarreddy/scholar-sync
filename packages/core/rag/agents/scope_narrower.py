"""
Scope Narrowing Agent

Narrows the scope of retrieval to reduce irrelevant chunks.
Analyzes query to determine specific focus areas.
"""

from typing import List, Dict, Any, Optional
from packages.core.llm import get_llm_client, get_model_for_task


class ScopeNarrower:
    """
    Agent that narrows retrieval scope to reduce irrelevant chunks.
    
    Strategies:
    - Extract key entities and concepts
    - Identify specific topics
    - Filter by document sections
    - Focus on relevant time periods or contexts
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    async def narrow_scope(
        self,
        query: str,
        available_sources: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Narrow retrieval scope based on query analysis.
        
        Args:
            query: User query
            available_sources: Optional list of available source IDs
            conversation_history: Optional conversation history
            
        Returns:
            Dict with:
            - focused_query: Narrowed query
            - key_terms: List of key terms to focus on
            - filters: Optional metadata filters
            - max_chunks: Suggested max chunks to retrieve
        """
        if not query or len(query.split()) <= 2:
            return {
                "focused_query": query,
                "key_terms": query.split(),
                "filters": None,
                "max_chunks": 5
            }
        
        try:
            # Use LLM to analyze query and narrow scope
            provider, model = get_model_for_task("chat")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.2)
            
            history_context = ""
            if conversation_history:
                recent = conversation_history[-2:]
                history_context = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in recent
                ])
            
            prompt = f"""Analyze this query and narrow its scope for better information retrieval.

Query: {query}
{f'Context: {history_context}' if history_context else ''}

Extract:
1. Key terms and concepts (3-5 most important)
2. Specific focus areas
3. Suggested max chunks to retrieve (3-10)

Return JSON:
{{
  "key_terms": ["term1", "term2"],
  "focused_query": "narrowed query",
  "max_chunks": 5
}}"""

            response = await llm_client.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=150,
                tenant_id=self.tenant_id,
                feature="scope_narrower"
            )
            
            # Parse response
            import json
            import re
            
            content = response.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "focused_query": result.get("focused_query", query),
                    "key_terms": result.get("key_terms", query.split()[:5]),
                    "filters": None,
                    "max_chunks": result.get("max_chunks", 5)
                }
            else:
                # Fallback
                return {
                    "focused_query": query,
                    "key_terms": query.split()[:5],
                    "filters": None,
                    "max_chunks": 5
                }
                
        except Exception as e:
            print(f"[SCOPE_NARROWER] Error narrowing scope: {e}")
            # Fallback
            return {
                "focused_query": query,
                "key_terms": query.split()[:5],
                "filters": None,
                "max_chunks": 5
            }
    
    def extract_key_terms(self, query: str) -> List[str]:
        """
        Extract key terms from query (simple version).
        
        Args:
            query: User query
            
        Returns:
            List of key terms
        """
        # Remove stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "can", "what", "how", "why", "when", "where", "who"}
        
        words = query.lower().split()
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return key_terms[:5]  # Top 5 terms
