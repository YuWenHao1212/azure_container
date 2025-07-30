"""
Cache performance monitoring and cost tracking.
Monitors cache hit rates and calculates cost savings.
"""
from collections import deque
from datetime import datetime, timezone
from typing import Any

from src.core.monitoring_service import monitoring_service


class CacheMetrics:
    """
    Cache performance monitoring.
    
    Features:
    - Cache hit/miss rate tracking
    - Cost savings calculation
    - Performance improvement tracking
    - Hourly reporting
    """
    
    # OpenAI API pricing (as of 2025)
    OPENAI_PRICING = {
        "gpt-4o": {
            "input": 0.03,   # per 1K tokens
            "output": 0.06   # per 1K tokens
        },
        "gpt-4o-2": {
            "input": 0.03,   # per 1K tokens
            "output": 0.06   # per 1K tokens
        }
    }
    
    # Average tokens for keyword extraction
    AVG_INPUT_TOKENS = 800   # Job description + prompt
    AVG_OUTPUT_TOKENS = 200  # Keywords + metadata
    
    def __init__(self):
        """Initialize cache metrics."""
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_cost_saved": 0.0,
            "total_time_saved_ms": 0.0,
            "api_calls_saved": 0
        }
        
        # Hourly tracking
        self.hourly_stats = deque(maxlen=24)  # Last 24 hours
        self.current_hour_stats = {
            "hour": datetime.now(timezone.utc).hour,
            "requests": 0,
            "hits": 0,
            "misses": 0,
            "cost_saved": 0.0,
            "time_saved_ms": 0.0
        }
        
        # Cache key tracking for analysis
        self.cache_key_stats = {}
        
        # Performance tracking
        self.performance_stats = {
            "avg_cache_retrieval_ms": 0.0,
            "avg_api_call_ms": 1500.0,  # Default estimate
            "cache_retrieval_times": deque(maxlen=100)
        }
    
    def record_cache_access(
        self,
        cache_hit: bool,
        cache_key: str,
        endpoint: str = "/api/v1/extract-jd-keywords",
        processing_time_ms: float | None = None,
        model: str = "gpt-4o-2",
        actual_tokens: dict[str, int] | None = None
    ):
        """
        Record a cache access.
        
        Args:
            cache_hit: Whether the cache was hit
            cache_key: The cache key used
            endpoint: API endpoint
            processing_time_ms: Time taken for the operation
            model: OpenAI model used (for cost calculation)
            actual_tokens: Actual token counts if available
        """
        self.metrics["total_requests"] += 1
        self.current_hour_stats["requests"] += 1
        
        if cache_hit:
            self._record_cache_hit(
                cache_key, 
                processing_time_ms,
                model,
                actual_tokens
            )
        else:
            self._record_cache_miss(
                cache_key,
                processing_time_ms
            )
        
        # Check if hour has changed
        self._check_hour_rollover()
        
        # Send real-time metrics
        self._send_metrics(endpoint)
    
    def _record_cache_hit(
        self,
        cache_key: str,
        retrieval_time_ms: float | None,
        model: str,
        actual_tokens: dict[str, int] | None
    ):
        """Record a cache hit."""
        self.metrics["cache_hits"] += 1
        self.current_hour_stats["hits"] += 1
        self.metrics["api_calls_saved"] += 1
        
        # Track cache key usage
        if cache_key not in self.cache_key_stats:
            self.cache_key_stats[cache_key] = {
                "hits": 0,
                "first_hit": datetime.now(timezone.utc),
                "last_hit": None
            }
        self.cache_key_stats[cache_key]["hits"] += 1
        self.cache_key_stats[cache_key]["last_hit"] = datetime.now(timezone.utc)
        
        # Calculate cost saved
        input_tokens = actual_tokens.get("input", self.AVG_INPUT_TOKENS) if actual_tokens else self.AVG_INPUT_TOKENS
        output_tokens = actual_tokens.get("output", self.AVG_OUTPUT_TOKENS) if actual_tokens else self.AVG_OUTPUT_TOKENS
        
        pricing = self.OPENAI_PRICING.get(model, self.OPENAI_PRICING["gpt-4o-2"])
        cost_saved = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])
        
        self.metrics["total_cost_saved"] += cost_saved
        self.current_hour_stats["cost_saved"] += cost_saved
        
        # Track time saved
        if retrieval_time_ms:
            self.performance_stats["cache_retrieval_times"].append(retrieval_time_ms)
            time_saved = self.performance_stats["avg_api_call_ms"] - retrieval_time_ms
            self.metrics["total_time_saved_ms"] += time_saved
            self.current_hour_stats["time_saved_ms"] += time_saved
    
    def _record_cache_miss(
        self,
        cache_key: str,
        api_call_time_ms: float | None
    ):
        """Record a cache miss."""
        self.metrics["cache_misses"] += 1
        self.current_hour_stats["misses"] += 1
        
        # Update average API call time
        if api_call_time_ms:
            current_avg = self.performance_stats["avg_api_call_ms"]
            total_calls = self.metrics["cache_misses"]
            self.performance_stats["avg_api_call_ms"] = (
                (current_avg * (total_calls - 1) + api_call_time_ms) / total_calls
            )
    
    def _check_hour_rollover(self):
        """Check if the hour has changed and archive stats."""
        current_hour = datetime.now(timezone.utc).hour
        
        if current_hour != self.current_hour_stats["hour"]:
            # Archive current hour stats
            self.hourly_stats.append(self.current_hour_stats.copy())
            
            # Generate hourly report
            self._generate_hourly_report()
            
            # Reset current hour stats
            self.current_hour_stats = {
                "hour": current_hour,
                "requests": 0,
                "hits": 0,
                "misses": 0,
                "cost_saved": 0.0,
                "time_saved_ms": 0.0
            }
    
    def _send_metrics(self, endpoint: str):
        """Send metrics to monitoring service."""
        # Calculate hit rate
        hit_rate = 0.0
        if self.metrics["total_requests"] > 0:
            hit_rate = (self.metrics["cache_hits"] / self.metrics["total_requests"]) * 100
        
        # Send cache hit rate metric
        monitoring_service.track_metric(
            "cache_hit_rate",
            hit_rate,
            {
                "endpoint": endpoint,
                "total_requests": self.metrics["total_requests"],
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"]
            }
        )
        
        # Send cost savings metric
        monitoring_service.track_metric(
            "cache_cost_saved_usd",
            self.metrics["total_cost_saved"],
            {
                "api_calls_saved": self.metrics["api_calls_saved"],
                "avg_cost_per_hit": self.metrics["total_cost_saved"] / self.metrics["cache_hits"] 
                    if self.metrics["cache_hits"] > 0 else 0
            }
        )
        
        # Send performance metric
        avg_cache_time = 0.0
        if self.performance_stats["cache_retrieval_times"]:
            avg_cache_time = sum(self.performance_stats["cache_retrieval_times"]) / len(
                self.performance_stats["cache_retrieval_times"]
            )
        
        monitoring_service.track_metric(
            "cache_performance_improvement",
            self.performance_stats["avg_api_call_ms"] - avg_cache_time,
            {
                "avg_cache_retrieval_ms": avg_cache_time,
                "avg_api_call_ms": self.performance_stats["avg_api_call_ms"]
            }
        )
    
    def _generate_hourly_report(self):
        """Generate and send hourly cache report."""
        stats = self.current_hour_stats
        
        # Calculate hourly hit rate
        hourly_hit_rate = 0.0
        if stats["requests"] > 0:
            hourly_hit_rate = (stats["hits"] / stats["requests"]) * 100
        
        # Send hourly report event
        monitoring_service.track_event(
            "cache_hourly_report",
            {
                "hour": stats["hour"],
                "hit_rate_percent": round(hourly_hit_rate, 2),
                "total_requests": stats["requests"],
                "hits": stats["hits"],
                "misses": stats["misses"],
                "cost_saved_usd": round(stats["cost_saved"], 2),
                "time_saved_minutes": round(stats["time_saved_ms"] / 60000, 2),
                "avg_cost_per_hit": round(
                    stats["cost_saved"] / stats["hits"], 4
                ) if stats["hits"] > 0 else 0
            }
        )
    
    def get_cache_summary(self) -> dict[str, Any]:
        """Get cache performance summary."""
        hit_rate = 0.0
        if self.metrics["total_requests"] > 0:
            hit_rate = (self.metrics["cache_hits"] / self.metrics["total_requests"]) * 100
        
        avg_cache_time = 0.0
        if self.performance_stats["cache_retrieval_times"]:
            avg_cache_time = sum(self.performance_stats["cache_retrieval_times"]) / len(
                self.performance_stats["cache_retrieval_times"]
            )
        
        return {
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": self.metrics["total_requests"],
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "api_calls_saved": self.metrics["api_calls_saved"],
            "total_cost_saved_usd": f"${self.metrics['total_cost_saved']:.2f}",
            "total_time_saved_hours": round(self.metrics["total_time_saved_ms"] / 3600000, 2),
            "avg_cost_per_request_saved": f"${self.metrics['total_cost_saved'] / self.metrics['cache_hits']:.4f}"
                if self.metrics["cache_hits"] > 0 else "$0.00",
            "performance_improvement": {
                "avg_cache_retrieval_ms": f"{avg_cache_time:.2f}",
                "avg_api_call_ms": f"{self.performance_stats['avg_api_call_ms']:.2f}",
                "speedup_factor": f"{self.performance_stats['avg_api_call_ms'] / avg_cache_time:.1f}x"
                    if avg_cache_time > 0 else "N/A"
            },
            "hourly_trend": self._get_hourly_trend()
        }
    
    def _get_hourly_trend(self) -> list[dict[str, Any]]:
        """Get hourly trend data."""
        trend = []
        for stats in self.hourly_stats:
            hit_rate = (stats["hits"] / stats["requests"] * 100) if stats["requests"] > 0 else 0
            trend.append({
                "hour": stats["hour"],
                "hit_rate": f"{hit_rate:.1f}%",
                "requests": stats["requests"],
                "cost_saved": f"${stats['cost_saved']:.2f}"
            })
        
        # Add current hour
        if self.current_hour_stats["requests"] > 0:
            current_hit_rate = (
                self.current_hour_stats["hits"] / self.current_hour_stats["requests"] * 100
            )
            trend.append({
                "hour": self.current_hour_stats["hour"],
                "hit_rate": f"{current_hit_rate:.1f}%",
                "requests": self.current_hour_stats["requests"],
                "cost_saved": f"${self.current_hour_stats['cost_saved']:.2f}",
                "current": True
            })
        
        return trend
    
    def get_top_cached_items(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most frequently cached items."""
        sorted_keys = sorted(
            self.cache_key_stats.items(),
            key=lambda x: x[1]["hits"],
            reverse=True
        )[:limit]
        
        return [
            {
                "cache_key": key[:50] + "..." if len(key) > 50 else key,
                "hits": stats["hits"],
                "first_hit": stats["first_hit"].isoformat(),
                "last_hit": stats["last_hit"].isoformat() if stats["last_hit"] else None,
                "age_hours": (
                    datetime.now(timezone.utc) - stats["first_hit"]
                ).total_seconds() / 3600
            }
            for key, stats in sorted_keys
        ]


# Global cache metrics instance
cache_metrics = CacheMetrics()