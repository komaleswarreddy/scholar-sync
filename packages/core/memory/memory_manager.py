"""
Memory Manager

Manages session memory and prunes chat history to avoid full chat replay.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import re


class MemoryManager:
    """
    Manages chat session memory with pruning strategies.
    
    Prevents:
    - Full chat replay (too many tokens)
    - Context window overflow
    - Unnecessary token usage
    """
    
    def __init__(
        self,
        max_history_messages: int = 20,  # Maximum messages to keep in history
        max_history_tokens: int = 2000,  # Maximum tokens for history (approximate)
        keep_recent: int = 5,  # Always keep last N messages
        prune_strategy: str = "recent"  # "recent", "relevance", "summary"
    ):
        """
        Initialize memory manager.
        
        Args:
            max_history_messages: Maximum messages in history
            max_history_tokens: Maximum tokens for history (approximate)
            keep_recent: Always keep last N messages
            prune_strategy: Strategy for pruning ("recent", "relevance", "summary")
        """
        self.max_history_messages = max_history_messages
        self.max_history_tokens = max_history_tokens
        self.keep_recent = keep_recent
        self.prune_strategy = prune_strategy
    
    def prune_history(
        self,
        history: List[Dict],
        current_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prune chat history to reduce token usage.
        
        Args:
            history: List of chat messages
            current_query: Current user query (for relevance-based pruning)
            
        Returns:
            Dict with:
            - pruned_history: Pruned message list
            - removed_count: Number of messages removed
            - strategy_used: Pruning strategy used
        """
        if len(history) <= self.max_history_messages:
            # No pruning needed
            return {
                "pruned_history": history,
                "removed_count": 0,
                "strategy_used": "none",
                "original_count": len(history),
                "new_count": len(history)
            }
        
        original_count = len(history)
        
        if self.prune_strategy == "recent":
            # Keep only recent messages
            pruned = history[-self.max_history_messages:]
            removed_count = original_count - len(pruned)
            
        elif self.prune_strategy == "relevance":
            # Keep recent + relevant messages
            pruned = self._prune_by_relevance(history, current_query)
            removed_count = original_count - len(pruned)
            
        elif self.prune_strategy == "summary":
            # Summarize old messages, keep recent
            pruned = self._prune_with_summary(history)
            removed_count = original_count - len(pruned)
            
        else:
            # Default: keep recent
            pruned = history[-self.max_history_messages:]
            removed_count = original_count - len(pruned)
        
        # Additional token-based pruning if needed
        pruned = self._prune_by_tokens(pruned)
        
        return {
            "pruned_history": pruned,
            "removed_count": removed_count,
            "strategy_used": self.prune_strategy,
            "original_count": original_count,
            "new_count": len(pruned)
        }
    
    def _prune_by_relevance(
        self,
        history: List[Dict],
        current_query: Optional[str] = None
    ) -> List[Dict]:
        """Prune by relevance to current query."""
        if not current_query:
            # Fallback to recent if no query
            return history[-self.max_history_messages:]
        
        # Always keep recent messages
        recent = history[-self.keep_recent:]
        old_messages = history[:-self.keep_recent]
        
        if not old_messages:
            return recent
        
        # Extract keywords from current query
        query_keywords = set(re.findall(r'\b\w{3,}\b', current_query.lower()))
        
        # Score old messages by relevance
        scored_messages = []
        for msg in old_messages:
            content = msg.get("content", "").lower()
            content_keywords = set(re.findall(r'\b\w{3,}\b', content))
            
            # Calculate relevance score (keyword overlap)
            if query_keywords:
                overlap = len(query_keywords.intersection(content_keywords))
                relevance_score = overlap / len(query_keywords)
            else:
                relevance_score = 0.0
            
            scored_messages.append((relevance_score, msg))
        
        # Sort by relevance (descending)
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # Keep top relevant messages
        remaining_slots = self.max_history_messages - self.keep_recent
        top_relevant = [msg for _, msg in scored_messages[:remaining_slots]]
        
        # Combine: relevant + recent
        pruned = top_relevant + recent
        
        return pruned
    
    def _prune_with_summary(self, history: List[Dict]) -> List[Dict]:
        """Prune by summarizing old messages."""
        # Keep recent messages
        recent = history[-self.keep_recent:]
        old_messages = history[:-self.keep_recent]
        
        if not old_messages:
            return recent
        
        # Create simple summary of old messages
        user_questions = []
        assistant_answers = []
        
        for msg in old_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                question = content.split('.')[0] if '.' in content else content[:80]
                user_questions.append(question.strip())
            elif role == "assistant":
                answer = content.split('.')[0] if '.' in content else content[:100]
                assistant_answers.append(answer.strip())
        
        # Build summary
        summary_parts = []
        if user_questions:
            summary_parts.append(f"User asked: {'; '.join(user_questions[:3])}")
        if assistant_answers:
            summary_parts.append(f"Assistant answered: {'; '.join(assistant_answers[:3])}")
        
        summary_text = ". ".join(summary_parts)
        if len(summary_text) > 300:
            summary_text = summary_text[:300] + "..."
        
        # Create summary message
        summary_message = {
            "role": "system",
            "content": f"Previous conversation summary: {summary_text}",
            "is_summary": True
        }
        
        # Return: summary + recent
        return [summary_message] + recent
    
    def _prune_by_tokens(self, history: List[Dict]) -> List[Dict]:
        """Additional pruning based on token count."""
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        total_chars = sum(len(msg.get("content", "")) for msg in history)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= self.max_history_tokens:
            return history
        
        # Need to prune more
        # Keep recent messages
        recent = history[-self.keep_recent:]
        old_messages = history[:-self.keep_recent]
        
        # Remove oldest messages until under token limit
        pruned_old = []
        current_tokens = sum(len(msg.get("content", "")) for msg in recent) // 4
        
        for msg in reversed(old_messages):  # Start from most recent old message
            msg_tokens = len(msg.get("content", "")) // 4
            if current_tokens + msg_tokens <= self.max_history_tokens:
                pruned_old.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        return pruned_old + recent
    
    def estimate_history_tokens(self, history: List[Dict]) -> int:
        """Estimate token count for history."""
        total_chars = sum(len(msg.get("content", "")) for msg in history)
        return total_chars // 4  # Rough estimate: 1 token ≈ 4 characters
