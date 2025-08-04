"""
Azure OpenAI Client for GPT-4o-2 model integration.
Following FHS architecture principles.
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AzureOpenAIError(Exception):
    """Base exception for Azure OpenAI client errors."""
    pass


class AzureOpenAIRateLimitError(AzureOpenAIError):
    """Exception for rate limit errors (429)."""
    pass


class AzureOpenAIAuthError(AzureOpenAIError):
    """Exception for authentication errors (401, 403)."""
    pass


class AzureOpenAIServerError(AzureOpenAIError):
    """Exception for server errors (500+)."""
    pass


class AzureOpenAIClient:
    """Azure OpenAI client for GPT-4o-2 model integration."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str = "gpt-4o-2",
        api_version: str = "2024-02-15-preview"
    ):
        """
        初始化 Azure OpenAI 客戶端

        Args:
            endpoint: Azure OpenAI 端點 URL
            api_key: API 金鑰
            deployment_name: 部署名稱 (動態指定, 預設為 gpt-4o-2 保持向後相容)
            api_version: API 版本
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.api_version = api_version
        self.deployment_id = deployment_name  # 使用動態指定的部署名稱

        # 設置 HTTP 客戶端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=60.0),  # 30s 連接超時, 60s 讀取超時
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "Azure-FastAPI-Client/1.0.0"
            }
        )

        # Register with resource manager
        try:
            from src.core.resource_manager import resource_manager
            resource_manager.register_connection(self.client)
        except ImportError:
            pass  # Resource manager not available

        # 配置日誌
        self.logger = logger
        self.logger.info(f"Initialized AzureOpenAI client for deployment: {self.deployment_id}")  # 指數退避: 1s, 2s, 4s

        # 初始化重試配置 - 修復缺失的屬性
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # 指數退避: 1s, 2s, 4s  # 指數退避: 1s, 2s, 4s

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o-2",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """
        調用 chat completion API

        Args:
            messages: 對話訊息列表
            model: 模型名稱 (固定使用 gpt-4o-2)
            temperature: 溫度參數 (0.0-1.0)
            max_tokens: 最大生成 token 數
            stream: 是否使用串流模式
            **kwargs: 其他 OpenAI API 參數

        Returns:
            Dict[str, Any]: non-streaming 模式的回應
            AsyncGenerator[Dict[str, Any], None]: streaming 模式的回應生成器

        Raises:
            AzureOpenAIError: API 調用失敗
        """
        # 驗證輸入
        if not messages:
            raise ValueError("Messages list cannot be empty")

        if not all(isinstance(msg, dict) and "role" in msg and "content" in msg for msg in messages):
            raise ValueError("Invalid message format. Each message must have 'role' and 'content'")

        # 構建請求 URL
        url = f"{self.endpoint}/openai/deployments/{self.deployment_id}/chat/completions"

        # 構建請求體
        payload = {
            "messages": messages,
            "temperature": max(0.0, min(1.0, temperature)),  # 限制範圍 0.0-1.0
            "max_tokens": max(1, min(4000, max_tokens)),      # 限制範圍 1-4000
            "stream": stream,
            **kwargs
        }

        # 添加 API 版本參數
        params = {"api-version": self.api_version}

        self.logger.info(
            f"Calling Azure OpenAI chat completion: stream={stream}, "
            f"temperature={temperature}, max_tokens={max_tokens}, "
            f"messages_count={len(messages)}"
        )

        if stream:
            return self._chat_completion_stream(url, payload, params)
        else:
            return await self._chat_completion_non_stream(url, payload, params)

    async def _chat_completion_non_stream(
        self,
        url: str,
        payload: dict[str, Any],
        params: dict[str, str]
    ) -> dict[str, Any]:
        """處理 non-streaming 請求"""
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    url,
                    json=payload,
                    params=params
                )

                # 檢查回應狀態
                await self._handle_response_errors(response, attempt)

                result = response.json()

                self.logger.info(
                    f"Azure OpenAI request successful: "
                    f"usage={result.get('usage', {})}, "
                    f"finish_reason={result.get('choices', [{}])[0].get('finish_reason', 'unknown')}"
                )

                # Track token usage
                from src.core.monitoring_service import monitoring_service
                usage = result.get('usage', {})
                if usage:
                    monitoring_service.track_event(
                        "OpenAITokenUsage",
                        {
                            "deployment": self.deployment_id,
                            "operation": "chat_completion",
                            "prompt_tokens": usage.get('prompt_tokens', 0),
                            "completion_tokens": usage.get('completion_tokens', 0),
                            "total_tokens": usage.get('total_tokens', 0),
                            "model": result.get("model", self.deployment_id),
                            "finish_reason": result.get('choices', [{}])[0].get('finish_reason', 'unknown'),
                            "temperature": payload.get('temperature', 0.7),
                            "max_tokens": payload.get('max_tokens', 1000)
                        }
                    )

                return result

            except (AzureOpenAIRateLimitError, AzureOpenAIServerError) as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

            except (AzureOpenAIAuthError, AzureOpenAIError):
                # Don't wrap these - just re-raise directly
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error in Azure OpenAI request: {e}")
                raise AzureOpenAIError(f"Request failed: {e!s}") from e

        raise AzureOpenAIError("Max retries exceeded")

    async def _chat_completion_stream(
        self,
        url: str,
        payload: dict[str, Any],
        params: dict[str, str]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """處理 streaming 請求"""
        for attempt in range(self.max_retries):
            try:
                async with self.client.stream(
                    "POST",
                    url,
                    json=payload,
                    params=params
                ) as response:

                    # 檢查回應狀態
                    await self._handle_response_errors(response, attempt)

                    self.logger.info("Starting Azure OpenAI streaming response")

                    async for line in response.aiter_lines():
                        line = line.strip()

                        if not line:
                            continue

                        if line.startswith("data: "):
                            data = line[6:]  # 移除 "data: " 前綴

                            if data == "[DONE]":
                                self.logger.info("Azure OpenAI streaming completed")
                                return

                            try:
                                chunk = json.loads(data)
                                yield chunk
                            except json.JSONDecodeError:
                                self.logger.warning(f"Failed to parse streaming data: {data}")
                                continue

                return  # 成功完成, 退出重試循環

            except (AzureOpenAIRateLimitError, AzureOpenAIServerError) as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    self.logger.warning(
                        f"Streaming request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error in Azure OpenAI streaming: {e}")
                raise AzureOpenAIError(f"Streaming request failed: {e!s}") from e

        raise AzureOpenAIError("Max retries exceeded for streaming request")

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
            raise AzureOpenAIAuthError(f"Authentication failed: {error_detail}")

        elif response.status_code == 403:
            raise AzureOpenAIAuthError(f"Permission denied: {error_detail}")

        elif response.status_code == 429:
            # 檢查是否有 Retry-After header
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                self.logger.warning(f"Rate limit hit, Retry-After: {retry_after}s")
            raise AzureOpenAIRateLimitError(f"Rate limit exceeded: {error_detail}")

        elif 500 <= response.status_code < 600:
            raise AzureOpenAIServerError(f"Server error ({response.status_code}): {error_detail}")

        else:
            raise AzureOpenAIError(f"API error ({response.status_code}): {error_detail}")

    async def complete_text(
        self,
        prompt: str,
        temperature: float = 0.1,
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
            AzureOpenAIError: API call failed
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
            self.logger.info("Azure OpenAI client closed")

    async def __aenter__(self):
        """async context manager 入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async context manager 出口"""
        await self.close()


# Factory function for dependency injection
def get_azure_openai_client(deployment_name: str = "gpt-4o-2") -> AzureOpenAIClient:
    """
    工廠函數: 建立 AzureOpenAI 客戶端實例
    從環境變數載入配置

    Args:
        deployment_name: Azure OpenAI 部署名稱 (可選, 預設為 gpt-4o-2)

    Returns:
        AzureOpenAIClient: 配置好的客戶端實例

    Raises:
        ValueError: 缺少必要的環境變數
    """
    import os

    # Support both old (LLM2_*) and new (AZURE_OPENAI_*) environment variables
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("LLM2_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("LLM2_API_KEY")

    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT or LLM2_ENDPOINT environment variable is required")

    if not api_key:
        raise ValueError("AZURE_OPENAI_API_KEY or LLM2_API_KEY environment variable is required")

    return AzureOpenAIClient(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment_name
    )


# Async factory function for dependency injection
async def get_azure_openai_client_async() -> AzureOpenAIClient:
    """
    非同步工廠函數: 建立 AzureOpenAI 客戶端實例

    Returns:
        AzureOpenAIClient: 配置好的客戶端實例
    """
    return get_azure_openai_client()
