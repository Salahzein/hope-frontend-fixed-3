"""
Result caching service to track when results were last fetched
and implement automatic refresh mechanism
"""
import time
import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ResultCache:
    def __init__(self):
        # In-memory cache: {cache_key: (timestamp, results)}
        self.cache: Dict[str, Tuple[float, any]] = {}
        self.refresh_interval_hours = 24  # Refresh results after 24 hours
    
    def _generate_cache_key(self, query: str, business_type: str, time_range: str, user_id: str, result_count: int = None) -> str:
        """Generate a unique cache key for the search parameters"""
        if result_count is not None:
            return f"{query}_{business_type}_{time_range}_{user_id}_{result_count}"
        return f"{query}_{business_type}_{time_range}_{user_id}"
    
    def get_cached_results(self, query: str, business_type: str, time_range: str, user_id: str, result_count: int = None) -> Optional[any]:
        """Get cached results if they exist and are fresh"""
        cache_key = self._generate_cache_key(query, business_type, time_range, user_id, result_count)
        
        if cache_key not in self.cache:
            logger.info(f"🔍 CACHE MISS: No cached results for key: {cache_key}")
            return None
        
        timestamp, results = self.cache[cache_key]
        age_hours = (time.time() - timestamp) / 3600
        
        if age_hours > self.refresh_interval_hours:
            logger.info(f"🔄 CACHE EXPIRED: Results are {age_hours:.1f} hours old, need refresh")
            del self.cache[cache_key]
            return None
        
        logger.info(f"✅ CACHE HIT: Using cached results from {age_hours:.1f} hours ago")
        return (results, age_hours)
    
    def cache_results(self, query: str, business_type: str, time_range: str, user_id: str, results_with_age: Tuple[Any, float], result_count: int = None):
        """Cache results with current timestamp"""
        cache_key = self._generate_cache_key(query, business_type, time_range, user_id, result_count)
        timestamp = time.time()
        
        results, age_hours = results_with_age
        self.cache[cache_key] = (timestamp, results)
        logger.info(f"💾 CACHED: Stored results for key: {cache_key}")
    
    def should_refresh(self, query: str, business_type: str, time_range: str, user_id: str, result_count: int = None) -> bool:
        """Check if results should be refreshed"""
        cache_key = self._generate_cache_key(query, business_type, time_range, user_id, result_count)
        
        if cache_key not in self.cache:
            return True
        
        timestamp, _ = self.cache[cache_key]
        age_hours = (time.time() - timestamp) / 3600
        
        return age_hours > self.refresh_interval_hours
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        if total_entries == 0:
            return {"total_entries": 0, "oldest_entry_hours": 0, "newest_entry_hours": 0}
        
        current_time = time.time()
        ages = [(current_time - timestamp) / 3600 for timestamp, _ in self.cache.values()]
        
        return {
            "total_entries": total_entries,
            "oldest_entry_hours": max(ages),
            "newest_entry_hours": min(ages)
        }

# Global cache instance
result_cache = ResultCache()
