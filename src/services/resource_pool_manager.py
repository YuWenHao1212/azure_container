"""
Resource Pool Manager for Azure Container API.

Manages reusable OpenAI client connections to reduce initialization overhead.
Key feature for Index Cal and Gap Analysis V2 performance improvement.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class ResourcePoolManager:
    """
    Resource pool manager for OpenAI clients.

    Reduces client initialization overhead by maintaining a pool of reusable clients.
    Target: 90% reduction in initialization overhead.
    """

    def __init__(
        self,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        idle_timeout: int = 300  # 5 minutes
    ):
        """
        Initialize resource pool manager.

        Args:
            min_pool_size: Minimum number of clients to maintain in pool
            max_pool_size: Maximum number of clients allowed
            idle_timeout: Timeout for idle client cleanup (seconds)
        """
        self.settings = get_settings()
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.idle_timeout = idle_timeout

        # Client pool management
        self.available_clients: asyncio.Queue = asyncio.Queue()
        self.active_clients: list[Any] = []  # Will hold AsyncOpenAI instances
        self.total_created = 0

        # Synchronization and state
        self.pool_lock = asyncio.Lock()
        self.initialized = False

        # Statistics for monitoring
        self.stats = {
            "clients_created": 0,
            "clients_reused": 0,
            "current_pool_size": 0,
            "peak_pool_size": 0,
            "initialization_time_ms": 0
        }

    async def initialize(self):
        """Initialize the resource pool with minimum number of clients."""
        if self.initialized:
            return

        async with self.pool_lock:
            if self.initialized:
                return

            init_start = time.time()

            # Pre-create minimum number of clients
            for _ in range(self.min_pool_size):
                client = await self._create_client()
                await self.available_clients.put(client)

            self.initialized = True
            init_time_ms = (time.time() - init_start) * 1000
            self.stats["initialization_time_ms"] = init_time_ms

            logger.info(
                f"Resource pool initialized with {self.min_pool_size} clients "
                f"in {init_time_ms:.2f}ms"
            )

    async def _create_client(self) -> Any:
        """
        Create a new OpenAI client with optimized configuration.

        Returns:
            Configured AsyncOpenAI client
        """
        # Lazy import to avoid module not found errors in test environments
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            logger.error("OpenAI SDK not installed. Please install it with: pip install openai")
            raise ImportError("OpenAI SDK is required for ResourcePoolManager") from e

        # Use environment-specific configuration
        if hasattr(self.settings, 'gpt41_mini_japaneast_endpoint'):
            # GPT-4.1 Mini configuration for keyword extraction
            client = AsyncOpenAI(
                api_key=self.settings.gpt41_mini_japaneast_api_key,
                base_url=f"{self.settings.gpt41_mini_japaneast_endpoint}/openai/deployments/{self.settings.gpt41_mini_japaneast_deployment}",
                default_headers={
                    "api-key": self.settings.gpt41_mini_japaneast_api_key
                },
                default_query={
                    "api-version": self.settings.gpt41_mini_japaneast_api_version
                },
                timeout=30.0,  # Reasonable timeout
                max_retries=2   # Built-in retries
            )
        else:
            # Fallback to main Azure OpenAI configuration
            client = AsyncOpenAI(
                api_key=self.settings.azure_openai_api_key,
                base_url=f"{self.settings.azure_openai_endpoint}/openai/deployments/{self.settings.azure_openai_gpt4_deployment}",
                default_headers={
                    "api-key": self.settings.azure_openai_api_key
                },
                default_query={
                    "api-version": self.settings.azure_openai_api_version
                },
                timeout=30.0,
                max_retries=2
            )

        self.total_created += 1
        self.stats["clients_created"] += 1
        self.stats["current_pool_size"] += 1
        self.stats["peak_pool_size"] = max(
            self.stats["peak_pool_size"],
            self.stats["current_pool_size"]
        )

        return client

    @asynccontextmanager
    async def get_client(self):
        """
        Get a client from the pool using context manager pattern.

        Automatically handles client acquisition and return.
        """
        if not self.initialized:
            await self.initialize()

        client = None
        try:
            # Try to get client from pool with short timeout
            try:
                client = await asyncio.wait_for(
                    self.available_clients.get(),
                    timeout=0.1
                )
                self.stats["clients_reused"] += 1

            except TimeoutError:
                # No available client, create new one if under limit
                if self.total_created < self.max_pool_size:
                    client = await self._create_client()
                else:
                    # At limit, wait for available client
                    client = await self.available_clients.get()
                    self.stats["clients_reused"] += 1

            yield client

        finally:
            # Return client to pool
            if client:
                await self.available_clients.put(client)

    def get_stats(self) -> dict[str, Any]:
        """
        Get resource pool statistics for monitoring.

        Returns:
            Dict containing pool statistics and efficiency metrics
        """
        total_usage = self.stats["clients_reused"] + self.stats["clients_created"]

        return {
            "pool_stats": self.stats.copy(),
            "efficiency": {
                "reuse_rate": (
                    self.stats["clients_reused"] / total_usage
                    if total_usage > 0 else 0
                ),
                "pool_utilization": (
                    (self.stats["current_pool_size"] - self.available_clients.qsize()) /
                    self.stats["current_pool_size"]
                    if self.stats["current_pool_size"] > 0 else 0
                ),
                "average_init_time_ms": self.stats["initialization_time_ms"]
            },
            "health": {
                "is_initialized": self.initialized,
                "available_clients": self.available_clients.qsize(),
                "total_clients": self.stats["current_pool_size"]
            }
        }

    async def cleanup(self):
        """Clean up resources and close connections."""
        async with self.pool_lock:
            # Close all clients (they will be garbage collected)
            while not self.available_clients.empty():
                try:
                    client = await self.available_clients.get_nowait()
                    # AsyncOpenAI doesn't require explicit close
                    del client
                except asyncio.QueueEmpty:
                    break

            self.stats["current_pool_size"] = 0
            self.initialized = False

            logger.info("Resource pool cleaned up")
