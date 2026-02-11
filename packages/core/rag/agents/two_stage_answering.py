"""
Two-Stage Answering

Advanced enterprise pattern: Start with minimal context, expand if needed.
Stage 1: Send top 2 chunks, ask if answerable
Stage 2: If not answerable, expand context and call again
"""

from typing import Dict, Any, Optional, List
from packages.core.llm import get_llm_client, get_model_for_task


class TwoStageAnswering:
    """
    Two-stage answering system.
    
    Stage 1: Mini context (top 2 chunks)
    - Ask model: Is answerable? yes/no
    - If yes → answer with mini context
    - If no → expand to full context → Stage 2
    
    Stage 2: Full context
    - Use all retrieved chunks
    - Generate full answer
    """
    
    def __init__(self, tenant_id: str, enabled: bool = True):
        """
        Initialize two-stage answering.
        
        Args:
            tenant_id: Tenant ID for LLM calls
            enabled: Whether two-stage answering is enabled
        """
        self.tenant_id = tenant_id
        self.enabled = enabled
    
    async def check_answerable(
        self,
        query: str,
        mini_context: str
    ) -> Dict[str, Any]:
        """
        Stage 1: Check if query is answerable with mini context.
        
        Args:
            query: User query
            mini_context: Mini context (top 2 chunks)
            
        Returns:
            Dict with:
            - answerable: bool
            - confidence: float (0.0-1.0)
            - reasoning: str
        """
        if not self.enabled:
            return {
                "answerable": True,
                "confidence": 1.0,
                "reasoning": "Two-stage answering disabled"
            }
        
        try:
            provider, model = get_model_for_task("chat")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.0)
            
            prompt = f"""Can you answer this question using ONLY the provided context?

Context:
{mini_context}

Question: {query}

Answer with ONLY JSON:
{{
  "answerable": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""
            
            response = await llm_client.generate(
                prompt=prompt,
                temperature=0.0,
                max_tokens=100,
                tenant_id=self.tenant_id,
                feature_tag="two_stage_answerable_check"
            )
            
            import json
            import re
            
            content = response.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "answerable": bool(result.get("answerable", False)),
                    "confidence": float(result.get("confidence", 0.5)),
                    "reasoning": result.get("reasoning", "")
                }
            else:
                # Fallback: assume answerable if can't parse
                return {
                    "answerable": True,
                    "confidence": 0.5,
                    "reasoning": "Failed to parse response, assuming answerable"
                }
                
        except Exception as e:
            print(f"[TWO_STAGE] Error checking answerable: {e}")
            # Fallback: assume answerable
            return {
                "answerable": True,
                "confidence": 0.5,
                "reasoning": f"Error: {str(e)}, assuming answerable"
            }
    
    def get_mini_context(self, chunks: List[Dict[str, Any]], top_n: int = 2) -> str:
        """
        Get mini context from top N chunks.
        
        Args:
            chunks: List of chunk dicts
            top_n: Number of top chunks to use (default: 2)
            
        Returns:
            Mini context string
        """
        if not chunks:
            return ""
        
        mini_chunks = chunks[:top_n]
        context_parts = []
        
        for i, chunk in enumerate(mini_chunks, 1):
            chunk_text = chunk.get("metadata", {}).get("text", "")
            if chunk_text:
                context_parts.append(f"[{i}] {chunk_text}")
        
        return "\n\n".join(context_parts)
