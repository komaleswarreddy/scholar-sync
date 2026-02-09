"""
Rate Limiter

Implements debounce and rate limiting to prevent accidental multi-calls.
"""

import time
from typing import Dict, Optional, Any
from collections import defaultdict
from threading import Lock
from datetime import datetime, timedelta


class RateLimiter:
    """
    Rate limiter with debounce functionality.
    
    Prevents:
    - Accidental duplicate requests
    - Rapid-fire requests
    - Spam/abuse
    """
    
    def __init__(
        self,
        max_requests_per_minute: int = 30,
        debounce_seconds: float = 2.0,
        max_requests_per_hour: int = 500
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum requests per minute per user
            debounce_seconds: Minimum seconds between identical requests (debounce)
            max_requests_per_hour: Maximum requests per hour per user
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.debounce_seconds = debounce_seconds
        self.max_requests_per_hour = max_requests_per_hour
        
        # Track requests per user: user_id -> list of timestamps
        self._user_requests: Dict[str, list] = defaultdict(list)
        
        # Track last request per user+query (for debounce): (user_id, query_hash) -> timestamp
        self._last_requests: Dict[tuple, float] = {}
        
        # Thread safety
        self._lock = Lock()
        
        # Cleanup old entries periodically
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _cleanup_old_entries(self):
        """Remove old request timestamps to prevent memory growth."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_minute = current_time - 60
        cutoff_hour = current_time - 3600
        
        with self._lock:
            for user_id in list(self._user_requests.keys()):
                # Keep only requests from last hour
                self._user_requests[user_id] = [
                    ts for ts in self._user_requests[user_id]
                    if ts > cutoff_hour
                ]
                
                # Remove empty entries
                if not self._user_requests[user_id]:
                    del self._user_requests[user_id]
            
            # Clean up old debounce entries (older than debounce_seconds * 2)
            cutoff_debounce = current_time - (self.debounce_seconds * 2)
            self._last_requests = {
                k: v for k, v in self._last_requests.items()
                if v > cutoff_debounce
            }
            
            self._last_cleanup = current_time
    
    def _hash_query(self, query: str) -> str:
        """Create a simple hash of the query for debounce."""
        # Normalize query: lowercase, strip whitespace
        normalized = query.lower().strip()
        # Simple hash (can be improved)
        return str(hash(normalized))
    
    def check_rate_limit(
        self,
        user_id: str,
        query: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if request should be allowed based on rate limits and debounce.
        
        Args:
            user_id: User identifier
            query: User query/message
            tenant_id: Optional tenant identifier
            
        Returns:
            Dict with:
            - allowed: bool
            - reason: str (if not allowed)
            - retry_after: float (seconds to wait)
        """
        self._cleanup_old_entries()
        
        current_time = time.time()
        query_hash = self._hash_query(query)
        debounce_key = (user_id, query_hash)
        
        with self._lock:
            # 1. Check debounce (same query from same user)
            if debounce_key in self._last_requests:
                last_request_time = self._last_requests[debounce_key]
                time_since = current_time - last_request_time
                
                if time_since < self.debounce_seconds:
                    retry_after = self.debounce_seconds - time_since
                    return {
                        "allowed": False,
                        "reason": "debounce",
                        "retry_after": retry_after,
                        "message": f"Please wait {retry_after:.1f} seconds before sending the same query again."
                    }
            
            # 2. Check requests per minute
            user_requests = self._user_requests[user_id]
            cutoff_minute = current_time - 60
            recent_requests = [ts for ts in user_requests if ts > cutoff_minute]
            
            if len(recent_requests) >= self.max_requests_per_minute:
                # Find oldest request in the minute window
                oldest_recent = min(recent_requests)
                retry_after = 60 - (current_time - oldest_recent)
                return {
                    "allowed": False,
                    "reason": "rate_limit_minute",
                    "retry_after": retry_after,
                    "message": f"Rate limit exceeded. Maximum {self.max_requests_per_minute} requests per minute. Please wait {retry_after:.1f} seconds."
                }
            
            # 3. Check requests per hour
            cutoff_hour = current_time - 3600
            hourly_requests = [ts for ts in user_requests if ts > cutoff_hour]
            
            if len(hourly_requests) >= self.max_requests_per_hour:
                # Find oldest request in the hour window
                oldest_hourly = min(hourly_requests)
                retry_after = 3600 - (current_time - oldest_hourly)
                return {
                    "allowed": False,
                    "reason": "rate_limit_hour",
                    "retry_after": retry_after,
                    "message": f"Rate limit exceeded. Maximum {self.max_requests_per_hour} requests per hour. Please wait {retry_after/60:.1f} minutes."
                }
            
            # All checks passed - record request
            self._user_requests[user_id].append(current_time)
            self._last_requests[debounce_key] = current_time
            
            return {
                "allowed": True,
                "reason": "ok"
            }
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get rate limit statistics for a user.
        
        Returns:
            Dict with request counts and limits
        """
        current_time = time.time()
        
        with self._lock:
            user_requests = self._user_requests.get(user_id, [])
            
            cutoff_minute = current_time - 60
            cutoff_hour = current_time - 3600
            
            recent_count = len([ts for ts in user_requests if ts > cutoff_minute])
            hourly_count = len([ts for ts in user_requests if ts > cutoff_hour])
            
            return {
                "requests_last_minute": recent_count,
                "requests_last_hour": hourly_count,
                "max_per_minute": self.max_requests_per_minute,
                "max_per_hour": self.max_requests_per_hour,
                "debounce_seconds": self.debounce_seconds,
            }
