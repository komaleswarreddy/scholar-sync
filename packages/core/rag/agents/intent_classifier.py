"""
Intent Classifier

Classifies user intent to enable correct routing of tasks.
Determines what type of query the user is asking.
"""

from enum import Enum
from typing import Dict, Optional, List
from packages.core.llm import get_llm_client, get_model_for_task


class UserIntent(str, Enum):
    """User intent types."""
    QUESTION = "question"  # Asking a question
    EXPLANATION = "explanation"  # Requesting explanation
    SUMMARY = "summary"  # Requesting summary
    COMPARISON = "comparison"  # Comparing concepts
    DEFINITION = "definition"  # Asking for definition
    HOW_TO = "how_to"  # Asking how to do something
    ANALYSIS = "analysis"  # Requesting analysis
    CREATION = "creation"  # Creating content (quiz, flashcards, etc.)
    GENERAL = "general"  # General conversation


class IntentClassifier:
    """
    Classifies user intent for correct routing.
    
    Intent types:
    - question: Direct question
    - explanation: Request for explanation
    - summary: Request for summary
    - comparison: Comparing multiple things
    - definition: Asking for definition
    - how_to: Step-by-step instructions
    - analysis: Deep analysis request
    - creation: Content generation request
    - general: General conversation
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    async def classify_intent(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, any]:
        """
        Classify user intent.
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            
        Returns:
            Dict with:
            - intent: UserIntent enum value
            - confidence: Confidence score (0.0 to 1.0)
            - reasoning: Optional reasoning
        """
        if not query:
            return {
                "intent": UserIntent.GENERAL,
                "confidence": 0.5,
                "reasoning": "Empty query"
            }
        
        # Quick keyword-based classification first
        quick_intent = self._quick_classify(query)
        if quick_intent["confidence"] > 0.8:
            return quick_intent
        
        # Use LLM for more accurate classification
        try:
            provider, model = get_model_for_task("chat")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.1)
            
            history_context = ""
            if conversation_history:
                recent = conversation_history[-2:]
                history_context = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in recent
                ])
            
            prompt = f"""Classify the user's intent from this query.

Query: {query}
{f'Context: {history_context}' if history_context else ''}

Intent types:
- question: Direct question (What is X? Who did Y?)
- explanation: Request explanation (Explain X, Tell me about Y)
- summary: Request summary (Summarize, Give me an overview)
- comparison: Comparing things (Compare X and Y, Difference between)
- definition: Asking for definition (What is X, Define Y)
- how_to: Step-by-step instructions (How to X, Steps to Y)
- analysis: Deep analysis (Analyze X, Break down Y)
- creation: Content generation (Create quiz, Generate flashcards)
- general: General conversation

Return JSON:
{{
  "intent": "question",
  "confidence": 0.9,
  "reasoning": "User is asking a direct question"
}}"""

            response = await llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=100,
                tenant_id=self.tenant_id,
                feature="intent_classifier"
            )
            
            # Parse response
            import json
            import re
            
            content = response.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                intent_str = result.get("intent", "general").lower()
                
                # Map to enum
                intent_map = {
                    "question": UserIntent.QUESTION,
                    "explanation": UserIntent.EXPLANATION,
                    "summary": UserIntent.SUMMARY,
                    "comparison": UserIntent.COMPARISON,
                    "definition": UserIntent.DEFINITION,
                    "how_to": UserIntent.HOW_TO,
                    "analysis": UserIntent.ANALYSIS,
                    "creation": UserIntent.CREATION,
                    "general": UserIntent.GENERAL,
                }
                
                intent = intent_map.get(intent_str, UserIntent.GENERAL)
                
                return {
                    "intent": intent,
                    "confidence": float(result.get("confidence", 0.7)),
                    "reasoning": result.get("reasoning", "")
                }
            else:
                return quick_intent
                
        except Exception as e:
            print(f"[INTENT_CLASSIFIER] Error classifying intent: {e}")
            return quick_intent
    
    def _quick_classify(self, query: str) -> Dict[str, any]:
        """Quick keyword-based classification."""
        query_lower = query.lower()
        
        # Question patterns
        if any(word in query_lower for word in ["what", "who", "when", "where", "why", "which"]):
            if "?" in query:
                return {
                    "intent": UserIntent.QUESTION,
                    "confidence": 0.9,
                    "reasoning": "Contains question words and question mark"
                }
        
        # Explanation patterns
        if any(word in query_lower for word in ["explain", "tell me about", "describe", "elaborate"]):
            return {
                "intent": UserIntent.EXPLANATION,
                "confidence": 0.85,
                "reasoning": "Contains explanation request words"
            }
        
        # Summary patterns
        if any(word in query_lower for word in ["summarize", "summary", "overview", "brief"]):
            return {
                "intent": UserIntent.SUMMARY,
                "confidence": 0.85,
                "reasoning": "Contains summary request words"
            }
        
        # Comparison patterns
        if any(word in query_lower for word in ["compare", "difference", "versus", "vs", "contrast"]):
            return {
                "intent": UserIntent.COMPARISON,
                "confidence": 0.9,
                "reasoning": "Contains comparison words"
            }
        
        # Definition patterns
        if any(word in query_lower for word in ["define", "definition", "what is", "what are"]):
            return {
                "intent": UserIntent.DEFINITION,
                "confidence": 0.85,
                "reasoning": "Contains definition request words"
            }
        
        # How-to patterns
        if query_lower.startswith("how to") or query_lower.startswith("how do"):
            return {
                "intent": UserIntent.HOW_TO,
                "confidence": 0.9,
                "reasoning": "Starts with how-to pattern"
            }
        
        # Creation patterns
        if any(word in query_lower for word in ["create", "generate", "make", "build"]):
            return {
                "intent": UserIntent.CREATION,
                "confidence": 0.8,
                "reasoning": "Contains creation words"
            }
        
        # Default
        return {
            "intent": UserIntent.GENERAL,
            "confidence": 0.5,
            "reasoning": "No clear intent pattern detected"
        }
