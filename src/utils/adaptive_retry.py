"""
Adaptive Retry Strategy for Azure Container API.

Implements intelligent retry logic based on error classification.
Key component for Index Cal and Gap Analysis V2 reliability improvement.
"""
import asyncio
import logging
import secrets
from collections.abc import Callable
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AdaptiveRetryStrategy:
    """
    Adaptive retry strategy that adjusts retry behavior based on error types.

    Improves service reliability by using appropriate retry patterns for different
    error scenarios (timeouts, rate limits, empty fields, etc.).
    """

    def __init__(self):
        """Initialize adaptive retry strategy with error-specific configurations."""
        # Error type specific retry configurations
        self.retry_configs = {
            "empty_fields": {
                "max_attempts": 2,
                "base_delay": 1.0,
                "max_delay": 3.0,
                "backoff": "linear",
                "jitter": True
            },
            "timeout": {
                "max_attempts": 3,
                "base_delay": 0.5,
                "max_delay": 5.0,
                "backoff": "exponential",
                "jitter": True
            },
            "rate_limit": {
                "max_attempts": 3,
                "base_delay": 5.0,
                "max_delay": 30.0,
                "backoff": "exponential",
                "jitter": False
            },
            "general": {
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 10.0,
                "backoff": "exponential",
                "jitter": True
            }
        }

        # Statistics for monitoring retry effectiveness
        self.retry_stats = {
            error_type: {"attempts": 0, "successes": 0, "failures": 0}
            for error_type in self.retry_configs
        }

    async def execute_with_retry(
        self,
        func: Callable,
        error_classifier: Optional[Callable] = None,
        on_retry: Optional[Callable] = None
    ) -> Any:
        """
        Execute function with adaptive retry logic.

        Args:
            func: Async function to execute
            error_classifier: Function to classify errors (returns error type string)
            on_retry: Optional callback function called on each retry

        Returns:
            Result of successful function execution

        Raises:
            Last exception if all retries fail
        """
        last_error = None
        error_type = "general"

        max_attempts = self._get_max_attempts()

        for attempt in range(max_attempts):
            try:
                # Execute the function
                result = await func()

                # Success - update stats if this was a retry
                if attempt > 0:
                    self.retry_stats[error_type]["successes"] += 1
                    logger.info(
                        f"Retry succeeded on attempt {attempt + 1} "
                        f"for {error_type} error"
                    )

                return result

            except Exception as e:
                last_error = e

                # Classify the error
                error_type = error_classifier(e) if error_classifier else self._default_error_classifier(e)

                config = self.retry_configs.get(error_type, self.retry_configs["general"])

                # Check if we should continue retrying
                if attempt >= config["max_attempts"] - 1:
                    self.retry_stats[error_type]["failures"] += 1
                    logger.error(
                        f"All {config['max_attempts']} retry attempts failed "
                        f"for {error_type} error: {e!s}"
                    )
                    raise

                # Calculate delay for this retry
                delay = self._calculate_delay(config, attempt)

                # Update retry statistics
                self.retry_stats[error_type]["attempts"] += 1

                logger.warning(
                    f"Attempt {attempt + 1} failed with {error_type} error: {e!s}. "
                    f"Retrying in {delay:.2f}s..."
                )

                # Execute retry callback if provided
                if on_retry:
                    try:
                        await on_retry(attempt, error_type, delay)
                    except Exception as callback_error:
                        logger.warning(f"Retry callback failed: {callback_error}")

                # Wait before retrying
                await asyncio.sleep(delay)

        # This should never be reached due to the break conditions above
        raise last_error

    def _calculate_delay(self, config: dict[str, Any], attempt: int) -> float:
        """
        Calculate retry delay based on configuration and attempt number.

        Args:
            config: Retry configuration for the error type
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        base_delay = config["base_delay"]
        max_delay = config["max_delay"]
        backoff = config["backoff"]

        # Calculate base delay using backoff strategy
        if backoff == "linear":
            delay = base_delay * (attempt + 1)
        elif backoff == "exponential":
            delay = base_delay * (2 ** attempt)
        else:
            delay = base_delay

        # Limit to maximum delay
        delay = min(delay, max_delay)

        # Add jitter if enabled
        if config.get("jitter", False):
            jitter = secrets.randbelow(int(delay * 100)) / 1000.0  # Secure random jitter
            delay += jitter

        return delay

    def _default_error_classifier(self, error: Exception) -> str:
        """
        Default error classifier based on error message content.

        Args:
            error: Exception to classify

        Returns:
            Error type string
        """
        error_msg = str(error).lower()

        # Check for specific error patterns
        if "timeout" in error_msg or "timed out" in error_msg:
            return "timeout"
        elif "rate" in error_msg and "limit" in error_msg:
            return "rate_limit"
        elif any(word in error_msg for word in ["empty", "missing", "blank", "required"]):
            return "empty_fields"
        else:
            return "general"

    def _get_max_attempts(self) -> int:
        """Get the maximum number of attempts across all error types."""
        return max(config["max_attempts"] for config in self.retry_configs.values())

    def get_stats(self) -> dict[str, Any]:
        """
        Get retry statistics for monitoring and analysis.

        Returns:
            Dict containing retry statistics and success rates
        """
        total_stats = {
            "total_retries": sum(stats["attempts"] for stats in self.retry_stats.values()),
            "total_successes": sum(stats["successes"] for stats in self.retry_stats.values()),
            "total_failures": sum(stats["failures"] for stats in self.retry_stats.values()),
            "by_error_type": self.retry_stats.copy()
        }

        # Calculate overall retry success rate
        if total_stats["total_retries"] > 0:
            total_stats["retry_success_rate"] = (
                total_stats["total_successes"] / total_stats["total_retries"]
            )
        else:
            total_stats["retry_success_rate"] = 0.0

        # Calculate success rates by error type
        for error_type, stats in self.retry_stats.items():
            if stats["attempts"] > 0:
                total_stats["by_error_type"][error_type]["success_rate"] = (
                    stats["successes"] / stats["attempts"]
                )
            else:
                total_stats["by_error_type"][error_type]["success_rate"] = 0.0

        return total_stats

    def reset_stats(self):
        """Reset retry statistics (useful for testing or periodic resets)."""
        for error_type in self.retry_stats:
            self.retry_stats[error_type] = {"attempts": 0, "successes": 0, "failures": 0}

        logger.info("Adaptive retry statistics reset")
