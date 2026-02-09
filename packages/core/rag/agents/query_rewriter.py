"""
Query Rewriter Agent

Rewrites user queries to improve retrieval recall.
Expands queries with synonyms, related terms, and context.
"""

from typing import Optional, Dict, Any
from packages.core.llm import get_llm_client, get_model_for_task


class QueryRewriter:
    """
    Agent that rewrites queries to improve retrieval.
    
    Strategies:
    - Expand with synonyms and related terms
    - Add context from conversation history
    - Clarify ambiguous terms
    - Break down complex queries
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    async def rewrite_query(
        self,
        query: str,
        conversation_history: Optional[list] = None,
        max_rewrites: int = 3,
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Rewrite query to improve retrieval recall while preserving semantic intent.
        
        Args:
            query: Original user query
            conversation_history: Optional conversation history for context
            max_rewrites: Maximum number of rewritten queries to return
            confidence_threshold: Minimum confidence to use rewritten queries
            
        Returns:
            Dict with:
            - queries: List of rewritten queries (includes original as first item)
            - confidence: Confidence score for rewrites (0.0 to 1.0)
            - used_rewrites: Whether rewrites will be used (based on confidence)
        """
        from config.settings import settings
        
        if not query or not query.strip():
            return {
                "queries": [query],
                "confidence": 1.0,
                "used_rewrites": False
            }
        
        # For simple queries, return as-is
        if len(query.split()) <= 3:
            return {
                "queries": [query],
                "confidence": 1.0,
                "used_rewrites": False
            }
        
        try:
            # Use lightweight model for query rewriting
            provider, model = get_model_for_task("chat")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.3)
            
            # Build prompt for query rewriting - emphasize preserving semantic intent
            history_context = ""
            if conversation_history:
                recent_messages = conversation_history[-3:]  # Last 3 messages
                history_context = "\n".join([
                    f"User: {msg.get('content', '')}" 
                    for msg in recent_messages 
                    if msg.get('role') == 'user'
                ])
            
            rewrite_prompt = f"""Rewrite the following query to improve information retrieval while PRESERVING the exact semantic intent. Generate {max_rewrites} alternative phrasings that:

CRITICAL RULES:
1. Keep the semantic meaning IDENTICAL - do not change the question's intent
2. Use synonyms and related terms that mean the same thing
3. Do NOT over-specialize generic queries - keep them general if original was general
4. Expand abbreviations and acronyms only if helpful
5. Add context from conversation ONLY if it clarifies the query
6. Do NOT narrow the scope - keep the query broad if original was broad

Original query: {query}
{f'Recent conversation context:\n{history_context}' if history_context else ''}

Return JSON with confidence score:
{{
  "queries": ["query1", "query2", "query3"],
  "confidence": 0.85,
  "reasoning": "Brief explanation of why these rewrites preserve intent"
}}"""

            response = await llm_client.generate(
                prompt=rewrite_prompt,
                temperature=0.3,
                max_tokens=300,
                tenant_id=self.tenant_id,
                feature="query_rewriter"
            )
            
            # Parse JSON response
            import json
            import re
            
            content = response.content.strip()
            
            # Extract JSON object
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                rewritten_queries = result.get("queries", [])
                confidence = float(result.get("confidence", 0.5))
                
                # Ensure we have strings and limit count
                rewritten_queries = [
                    str(q).strip() 
                    for q in rewritten_queries[:max_rewrites]
                    if q and str(q).strip()
                ]
                
                # Always include original query first
                if query not in rewritten_queries:
                    rewritten_queries.insert(0, query)
                else:
                    # Move original to front if it's in the list
                    rewritten_queries.remove(query)
                    rewritten_queries.insert(0, query)
                
                # Check if confidence meets threshold
                used_rewrites = confidence >= confidence_threshold
                
                # If confidence too low, only use original
                if not used_rewrites:
                    rewritten_queries = [query]
                
                return {
                    "queries": rewritten_queries[:max_rewrites + 1],  # +1 for original
                    "confidence": confidence,
                    "used_rewrites": used_rewrites,
                    "reasoning": result.get("reasoning", "")
                }
            else:
                # Fallback: return original query
                return {
                    "queries": [query],
                    "confidence": 0.0,
                    "used_rewrites": False,
                    "reasoning": "Failed to parse rewrite response"
                }
                
        except Exception as e:
            print(f"[QUERY_REWRITER] Error rewriting query: {e}")
            # Fallback: return original query
            return {
                "queries": [query],
                "confidence": 0.0,
                "used_rewrites": False,
                "reasoning": f"Error: {str(e)}"
            }
    
    async def expand_query(self, query: str) -> str:
        """
        Expand query with synonyms and related terms (simpler version).
        
        Args:
            query: Original query
            
        Returns:
            Expanded query
        """
        # Simple expansion: add common synonyms
        # In production, could use WordNet, embeddings, or LLM
        
        expansions = {
            "explain": ["describe", "clarify", "elaborate"],
            "what": ["define", "describe", "explain"],
            "how": ["method", "process", "steps"],
            "why": ["reason", "cause", "purpose"],
        }
        
        words = query.lower().split()
        expanded_words = []
        
        for word in words:
            expanded_words.append(word)
            # Add first synonym if found
            for key, synonyms in expansions.items():
                if key in word:
                    expanded_words.append(synonyms[0])
                    break
        
        expanded_query = " ".join(expanded_words)
        return expanded_query if expanded_query != query else query
