"""
Cold Start Handler

Handles graceful degradation for first-use scenarios.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class ColdStartReason(Enum):
    """Reasons for cold start."""
    NO_SOURCES = "no_sources"
    NO_HISTORY = "no_history"
    NO_CACHE = "no_cache"
    FIRST_QUERY = "first_query"
    NEW_TENANT = "new_tenant"


class ColdStartHandler:
    """
    Handles cold-start scenarios gracefully.
    
    Provides fallback logic when:
    - No sources uploaded
    - No conversation history
    - No cache available
    - First query
    - New tenant
    """
    
    def __init__(
        self,
        enable_fallbacks: bool = True
    ):
        """
        Initialize cold start handler.
        
        Args:
            enable_fallbacks: Enable fallback responses
        """
        self.enable_fallbacks = enable_fallbacks
        
        # Fallback messages
        self.fallback_messages = {
            ColdStartReason.NO_SOURCES: (
                "I don't have any documents to reference yet. "
                "Please upload some documents first, and I'll be able to help you with questions about them."
            ),
            ColdStartReason.NO_HISTORY: (
                "This appears to be a new conversation. "
                "I'm ready to help you with questions about your documents!"
            ),
            ColdStartReason.NO_CACHE: (
                "I'm processing your request. This may take a moment as I'm setting things up."
            ),
            ColdStartReason.FIRST_QUERY: (
                "Welcome! I'm here to help you with questions about your documents. "
                "What would you like to know?"
            ),
            ColdStartReason.NEW_TENANT: (
                "Welcome to ScholarSync! Let's get started by uploading some documents, "
                "and then I can help answer questions about them."
            ),
        }
    
    def check_cold_start(
        self,
        has_sources: bool = True,
        has_history: bool = True,
        has_cache: bool = True,
        is_first_query: bool = False,
        is_new_tenant: bool = False
    ) -> Dict[str, Any]:
        """
        Check if we're in a cold start scenario.
        
        Args:
            has_sources: Whether sources are available
            has_history: Whether conversation history exists
            has_cache: Whether cache is available
            is_first_query: Whether this is the first query
            is_new_tenant: Whether this is a new tenant
            
        Returns:
            Dict with:
            - is_cold_start: bool
            - reason: ColdStartReason (if cold start)
            - fallback_message: str (if cold start)
            - should_use_fallback: bool
        """
        reasons = []
        
        if not has_sources:
            reasons.append(ColdStartReason.NO_SOURCES)
        
        if not has_history:
            reasons.append(ColdStartReason.NO_HISTORY)
        
        if not has_cache:
            reasons.append(ColdStartReason.NO_CACHE)
        
        if is_first_query:
            reasons.append(ColdStartReason.FIRST_QUERY)
        
        if is_new_tenant:
            reasons.append(ColdStartReason.NEW_TENANT)
        
        is_cold_start = len(reasons) > 0
        primary_reason = reasons[0] if reasons else None
        
        # Only use fallback for critical cold-start scenarios (no sources or new tenant)
        # Don't block just because there's no history or cache - those are normal
        critical_reasons = [ColdStartReason.NO_SOURCES, ColdStartReason.NEW_TENANT]
        should_use_fallback = (
            is_cold_start and 
            self.enable_fallbacks and 
            primary_reason in critical_reasons
        )
        
        fallback_message = None
        if should_use_fallback and primary_reason:
            fallback_message = self.fallback_messages.get(primary_reason)
        
        return {
            "is_cold_start": is_cold_start,
            "reasons": [r.value for r in reasons],
            "primary_reason": primary_reason.value if primary_reason else None,
            "fallback_message": fallback_message,
            "should_use_fallback": should_use_fallback
        }
    
    def get_fallback_response(
        self,
        reason: ColdStartReason,
        custom_message: Optional[str] = None
    ) -> str:
        """
        Get fallback response for cold start.
        
        Args:
            reason: Cold start reason
            custom_message: Optional custom message
            
        Returns:
            Fallback message
        """
        if custom_message:
            return custom_message
        
        return self.fallback_messages.get(reason, "I'm ready to help. What would you like to know?")
    
    def should_skip_retrieval(
        self,
        cold_start_info: Dict[str, Any]
    ) -> bool:
        """
        Determine if retrieval should be skipped in cold start.
        
        Args:
            cold_start_info: Result from check_cold_start
            
        Returns:
            True if retrieval should be skipped
        """
        # Only skip retrieval if we're using fallback (no sources or new tenant)
        return cold_start_info.get("should_use_fallback", False)
    
    def should_use_simple_response(
        self,
        cold_start_info: Dict[str, Any]
    ) -> bool:
        """
        Determine if simple response should be used.
        
        Args:
            cold_start_info: Result from check_cold_start
            
        Returns:
            True if simple response should be used
        """
        return cold_start_info.get("should_use_fallback", False)
