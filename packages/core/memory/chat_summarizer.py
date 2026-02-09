"""
Chat Summarizer

Periodically summarizes chat history to reduce tokens while preserving context.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import re


class ChatSummarizer:
    """
    Summarizes chat history to reduce token usage.
    
    Strategy:
    - Summarize old messages (beyond recent window)
    - Preserve recent messages for context
    - Maintain key information in summary
    """
    
    def __init__(
        self,
        recent_window: int = 5,  # Keep last N messages unsummarized
        summarize_after: int = 10,  # Summarize when history exceeds this
        max_summary_length: int = 500  # Max characters for summary
    ):
        """
        Initialize chat summarizer.
        
        Args:
            recent_window: Number of recent messages to keep unsummarized
            summarize_after: Trigger summarization when history exceeds this count
            max_summary_length: Maximum length for summary
        """
        self.recent_window = recent_window
        self.summarize_after = summarize_after
        self.max_summary_length = max_summary_length
    
    def should_summarize(self, history: List[Dict]) -> bool:
        """
        Check if history should be summarized.
        
        Args:
            history: List of chat messages
            
        Returns:
            True if summarization should be triggered
        """
        return len(history) > self.summarize_after
    
    def summarize_history(
        self,
        history: List[Dict],
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize chat history.
        
        Args:
            history: List of chat messages
            query: Current query (for context)
            
        Returns:
            Dict with:
            - summarized_history: Summarized messages
            - summary: Summary text
            - original_count: Original message count
            - new_count: New message count
        """
        if not self.should_summarize(history):
            return {
                "summarized_history": history,
                "summary": None,
                "original_count": len(history),
                "new_count": len(history),
                "was_summarized": False
            }
        
        # Keep recent messages
        recent_messages = history[-self.recent_window:]
        
        # Messages to summarize
        old_messages = history[:-self.recent_window]
        
        # Create summary of old messages
        summary = self._create_summary(old_messages, query)
        
        # Create summarized history: summary + recent messages
        summarized_history = []
        
        if summary:
            summarized_history.append({
                "role": "system",
                "content": f"Previous conversation summary: {summary}",
                "is_summary": True
            })
        
        summarized_history.extend(recent_messages)
        
        return {
            "summarized_history": summarized_history,
            "summary": summary,
            "original_count": len(history),
            "new_count": len(summarized_history),
            "was_summarized": True
        }
    
    def _create_summary(self, messages: List[Dict], query: Optional[str] = None) -> str:
        """
        Create summary of messages.
        
        Args:
            messages: Messages to summarize
            query: Current query for context
            
        Returns:
            Summary text
        """
        if not messages:
            return ""
        
        # Extract key information from messages
        user_questions = []
        assistant_answers = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                # Extract question (first sentence or first 100 chars)
                question = content.split('.')[0] if '.' in content else content[:100]
                user_questions.append(question.strip())
            elif role == "assistant":
                # Extract key points from answer (first sentence)
                answer = content.split('.')[0] if '.' in content else content[:150]
                assistant_answers.append(answer.strip())
        
        # Build summary
        summary_parts = []
        
        if user_questions:
            questions_text = "; ".join(user_questions[:5])  # Top 5 questions
            if len(user_questions) > 5:
                questions_text += f" (and {len(user_questions) - 5} more)"
            summary_parts.append(f"User asked: {questions_text}")
        
        if assistant_answers:
            answers_text = "; ".join(assistant_answers[:5])  # Top 5 answers
            if len(assistant_answers) > 5:
                answers_text += f" (and {len(assistant_answers) - 5} more)"
            summary_parts.append(f"Assistant answered: {answers_text}")
        
        summary = ". ".join(summary_parts)
        
        # Truncate if too long
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length] + "..."
        
        return summary
    
    async def summarize_with_llm(
        self,
        history: List[Dict],
        query: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize history using LLM (more accurate but costs tokens).
        
        Args:
            history: List of chat messages
            query: Current query for context
            tenant_id: Tenant identifier
            
        Returns:
            Dict with summarized history and summary
        """
        if not self.should_summarize(history):
            return {
                "summarized_history": history,
                "summary": None,
                "original_count": len(history),
                "new_count": len(history),
                "was_summarized": False
            }
        
        # Keep recent messages
        recent_messages = history[-self.recent_window:]
        old_messages = history[:-self.recent_window]
        
        # Build prompt for summarization
        old_conversation = "\n".join([
            f"{msg.get('role', 'user').title()}: {msg.get('content', '')}"
            for msg in old_messages
        ])
        
        summary_prompt = f"""Summarize the following conversation history in 2-3 sentences, preserving key topics and answers:

{old_conversation}

Summary:"""
        
        # Use LLM to generate summary
        try:
            from packages.core.llm import get_llm_client, get_model_for_task
            provider, model = get_model_for_task("chat")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.3)
            
            response = await llm_client.generate(
                prompt=summary_prompt,
                temperature=0.3,
                max_tokens=200,
                tenant_id=tenant_id,
                feature_tag="chat_summarizer"
            )
            
            summary = response.content.strip()
            
            # Create summarized history
            summarized_history = []
            if summary:
                summarized_history.append({
                    "role": "system",
                    "content": f"Previous conversation summary: {summary}",
                    "is_summary": True
                })
            
            summarized_history.extend(recent_messages)
            
            return {
                "summarized_history": summarized_history,
                "summary": summary,
                "original_count": len(history),
                "new_count": len(summarized_history),
                "was_summarized": True
            }
        except Exception as e:
            print(f"[WARNING] LLM summarization failed: {e}, using simple summary")
            # Fallback to simple summary
            return self.summarize_history(history, query)
