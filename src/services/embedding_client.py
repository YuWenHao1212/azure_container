"""
Azure OpenAI Embedding Client for text embeddings.
Following FHS architecture principles.
"""
import logging

import httpx
from pydantic import BaseModel


class EmbeddingResponse(BaseModel):
    """Response model for embedding API."""
    embedding: list[float]
    index: int


class AzureEmbeddingClient:
    """Azure OpenAI client for text embeddings."""

    def __init__(self, endpoint: str, api_key: str):
        """
        Initialize Azure Embedding client

        Args:
            endpoint: Azure OpenAI Embedding endpoint URL
            api_key: API key
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key

        # Set up HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=60.0),
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "Azure-FastAPI-Embedding-Client/1.0.0"
            }
        )

        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Create embeddings for a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: API call failed
        """
        if not texts:
            return []

        # Clean texts - remove empty strings
        cleaned_texts = [text for text in texts if text and text.strip()]
        if not cleaned_texts:
            return []

        payload = {
            "input": cleaned_texts
        }

        self.logger.info(f"Creating embeddings for {len(cleaned_texts)} texts")

        try:
            response = await self.client.post(
                self.endpoint,
                json=payload
            )

            if response.status_code != 200:
                error_detail = response.text or f"HTTP {response.status_code}"
                self.logger.error(f"Embedding API error: {error_detail}")
                raise Exception(f"Embedding API error ({response.status_code}): {error_detail}")

            result = response.json()

            # Extract embeddings from response
            embeddings_data = result.get("data", [])

            # Sort by index to ensure correct order
            embeddings_data.sort(key=lambda x: x.get("index", 0))

            # Extract embedding vectors
            embeddings = [item.get("embedding", []) for item in embeddings_data]

            self.logger.info(f"Successfully created {len(embeddings)} embeddings")

            return embeddings

        except Exception as e:
            self.logger.error(f"Error creating embeddings: {e}")
            raise

    async def create_embedding(self, text: str) -> list[float]:
        """
        Create embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            Exception: API call failed
        """
        embeddings = await self.create_embeddings([text])
        return embeddings[0] if embeddings else []

    async def close(self):
        """Close HTTP client connection"""
        if self.client:
            await self.client.aclose()
            self.logger.info("Azure Embedding client closed")

    async def __aenter__(self):
        """async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async context manager exit"""
        await self.close()


# Factory function for dependency injection (deprecated - use llm_factory)
def get_azure_embedding_client() -> AzureEmbeddingClient:
    """
    Factory function: Create AzureEmbedding client instance

    DEPRECATED: Use get_embedding_client from llm_factory instead
    This function is kept for backward compatibility

    Returns:
        AzureEmbeddingClient: Configured client instance
    """
    from src.services.llm_factory import get_embedding_client

    return get_embedding_client(model="embedding-3-large")


def get_course_embedding_client() -> AzureEmbeddingClient:
    """
    Factory function: Create course embedding client instance

    DEPRECATED: Use get_embedding_client from llm_factory instead
    This function is kept for backward compatibility

    Returns:
        AzureEmbeddingClient: Configured client instance for course embeddings
    """
    from src.services.llm_factory import get_embedding_client

    return get_embedding_client(model="embedding-3-small", api_name="course_search")
