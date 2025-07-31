"""
Azure OpenAI Client for GPT-4.1 mini model integration.
Optimized for high performance with Japan East deployment.
"""
import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx


class AzureOpenAIGPT41Client:
    """Azure OpenAI client for GPT-4.1 mini model integration."""

    def __init__(self, endpoint: str, api_key: str, deployment_name: str, api_version: str = "2025-01-01-preview"):
        """
        初始化 Azure OpenAI GPT-4.1 mini 客戶端

        Args:
            endpoint: Azure OpenAI 端點 URL
            api_key: API 金鑰
            deployment_name: 部署名稱 (e.g., gpt-4-1-mini-japaneast)
            api_version: API 版本
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.api_version = api_version

        # 設置 HTTP 客戶端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=60.0),  # 30s 連接超時，60s 讀取超時
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "Azure-FastAPI-Client/1.0.0"
            }
        )

        # 設置日誌
        self.logger = logging.getLogger(self.__class__.__name__)

        # 重試配置
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # 指數退避: 1s, 2s, 4s

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """
        調用 chat completion API

        Args:
            messages: 對話訊息列表
            temperature: 溫度參數 (0.0-1.0)
            max_tokens: 最大生成 token 數
            stream: 是否使用串流模式
            **kwargs: 其他 OpenAI API 參數

        Returns:
            Dict[str, Any]: non-streaming 模式的回應
            AsyncGenerator[Dict[str, Any], None]: streaming 模式的回應生成器

        Raises:
            Exception: API 調用失敗
        """
        # 驗證輸入
        if not messages:
            raise ValueError("Messages list cannot be empty")

        if not all(isinstance(msg, dict) and "role" in msg and "content" in msg for msg in messages):
            raise ValueError("Invalid message format. Each message must have 'role' and 'content'")

        # 構建請求 URL
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"

        # 構建請求參數
        request_params = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }

        if stream:
            return self._stream_chat_completion(url, request_params)
        else:
            return await self._non_stream_chat_completion(url, request_params)

    async def _non_stream_chat_completion(self, url: str, request_params: dict[str, Any]) -> dict[str, Any]:
        """處理非串流模式的請求"""
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(url, json=request_params)

                if response.status_code == 200:
                    return response.json()

                # 處理錯誤
                await self._handle_response_errors(response, attempt)

            except httpx.TimeoutException as e:
                self.logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Request timeout after {self.max_retries} attempts") from e

            except httpx.RequestError as e:
                self.logger.error(f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Request failed: {e!s}") from e

            except Exception:
                if attempt == self.max_retries - 1:
                    raise

            # 重試延遲
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                self.logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        raise Exception("Max retries exceeded")

    async def _stream_chat_completion(self, url: str, request_params: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """處理串流模式的請求"""
        # Streaming implementation similar to original but with GPT-4.1 mini
        raise NotImplementedError("Streaming not implemented for GPT-4.1 mini client")

    async def _handle_response_errors(self, response: httpx.Response, attempt: int):
        """處理 HTTP 回應錯誤"""
        if response.status_code == 200:
            return

        error_detail = ""
        try:
            error_data = response.json()
            error_detail = error_data.get("error", {}).get("message", str(error_data))
        except Exception:
            error_detail = response.text or f"HTTP {response.status_code}"

        if response.status_code == 401:
            raise Exception(f"Authentication failed: {error_detail}")

        elif response.status_code == 403:
            raise Exception(f"Permission denied: {error_detail}")

        elif response.status_code == 429:
            # 檢查是否有 Retry-After header
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                self.logger.warning(f"Rate limit hit, Retry-After: {retry_after}s")
            raise Exception(f"Rate limit exceeded: {error_detail}")

        elif 500 <= response.status_code < 600:
            raise Exception(f"Server error ({response.status_code}): {error_detail}")

        else:
            raise Exception(f"API error ({response.status_code}): {error_detail}")

    async def complete_text(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Simple text completion using chat completion API.

        Args:
            prompt: Input prompt text
            temperature: Temperature parameter (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            str: Generated text response

        Raises:
            Exception: API call failed
        """
        messages = [
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        # Extract text content from response
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "").strip()

        return ""

    async def close(self):
        """關閉 HTTP 客戶端連接"""
        if self.client:
            await self.client.aclose()
            self.logger.info("Azure OpenAI GPT-4.1 mini client closed")

    async def __aenter__(self):
        """async context manager 入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async context manager 出口"""
        await self.close()


# Factory function for dependency injection
def get_gpt41_mini_client() -> AzureOpenAIGPT41Client:
    """
    工廠函數：建立 GPT-4.1 mini 客戶端實例
    從環境變數載入配置

    Returns:
        AzureOpenAIGPT41Client: 配置好的客戶端實例

    Raises:
        ValueError: 缺少必要的環境變數
    """
    from src.core.config import get_settings

    settings = get_settings()

    if not settings.gpt41_mini_japaneast_endpoint:
        raise ValueError("GPT41_MINI_JAPANEAST_ENDPOINT environment variable is required")

    if not settings.gpt41_mini_japaneast_api_key:
        raise ValueError("GPT41_MINI_JAPANEAST_API_KEY environment variable is required")

    return AzureOpenAIGPT41Client(
        endpoint=settings.gpt41_mini_japaneast_endpoint,
        api_key=settings.gpt41_mini_japaneast_api_key,
        deployment_name=settings.gpt41_mini_japaneast_deployment,
        api_version=settings.gpt41_mini_japaneast_api_version
    )


# Async factory function for dependency injection
async def get_gpt41_mini_client_async() -> AzureOpenAIGPT41Client:
    """
    非同步工廠函數：建立 GPT-4.1 mini 客戶端實例

    Returns:
        AzureOpenAIGPT41Client: 配置好的客戶端實例
    """
    return get_gpt41_mini_client()
