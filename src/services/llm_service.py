"""
LLM Service for Resume Formatting.
Handles LLM interactions for resume formatting using Azure OpenAI.
"""
import logging
from datetime import datetime
from typing import Any

from src.core.monitoring_service import monitoring_service
from src.services.exceptions import LLMServiceError
from src.services.openai_client import (
    AzureOpenAIClient,
    AzureOpenAIError,
    get_azure_openai_client,
)
from src.services.token_tracking_mixin import TokenTrackingMixin
from src.services.unified_prompt_service import UnifiedPromptService

logger = logging.getLogger(__name__)


class LLMService(TokenTrackingMixin):
    """LLM 服務封裝 - 用於履歷格式化"""

    def __init__(self, openai_client: AzureOpenAIClient = None):
        self.prompt_service = UnifiedPromptService()
        self.openai_client = openai_client or get_azure_openai_client()

    async def format_resume(
        self,
        task: str,
        data: dict[str, Any]
    ) -> str:
        """
        使用 LLM 格式化履歷

        Args:
            task: 任務名稱 (resume_format)
            data: 包含 ocr_text 和 supplement_info 的資料

        Returns:
            格式化後的 HTML 內容
        """
        start_time = datetime.now()

        try:
            # 1. 獲取 prompt
            logger.info(f"Getting prompt for task: {task}")
            system_prompt, user_prompt = self.prompt_service.get_prompt(
                task=task,
                version="v1.0.0",
                data=data
            )

            # 2. 呼叫 Azure OpenAI
            logger.info("Calling Azure OpenAI for resume formatting")
            response = await self.openai_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # 較低的溫度以確保一致性
                max_tokens=4000,
                stream=False
            )

            # 3. 提取 HTML 內容
            if not response or "choices" not in response:
                raise LLMServiceError("Invalid response from Azure OpenAI")

            html_content = response["choices"][0]["message"]["content"]

            # 4. 追蹤 token 使用
            if "usage" in response:
                token_info = self.track_openai_usage(
                    response=response,
                    task_name="resume_format",
                    endpoint="chat_completion"
                )
                logger.info(f"Token usage: {token_info}")

            # 5. 記錄成功事件
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            monitoring_service.track_event("LLMFormatSuccess", {
                "task": task,
                "duration_ms": duration_ms,
                "output_length": len(html_content),
                "has_supplement_info": bool(data.get("supplement_info") != "null")
            })

            return self._extract_html_content(html_content)

        except AzureOpenAIError as e:
            logger.error(f"Azure OpenAI error: {e!s}")
            monitoring_service.track_event("LLMFormatError", {
                "task": task,
                "error_type": "AzureOpenAIError",
                "error_message": str(e)
            })
            raise LLMServiceError(f"LLM formatting failed: {e!s}") from e

        except Exception as e:
            logger.error(f"Unexpected error in LLM formatting: {e!s}")
            monitoring_service.track_event("LLMFormatError", {
                "task": task,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            raise LLMServiceError(f"LLM formatting failed: {e!s}") from e

    def _extract_html_content(self, content: str) -> str:
        """
        從 LLM 回應中提取 HTML 內容
        移除可能的 markdown 標記或其他包裝
        """
        if not content:
            return ""

        # 移除可能的 markdown code block 標記
        import re

        # 移除 ```html 和 ``` 標記
        content = re.sub(r'^```html?\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n?```\s*$', '', content, flags=re.MULTILINE)

        # 移除多餘的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        return content.strip()

    async def close(self):
        """關閉資源"""
        if self.openai_client:
            await self.openai_client.close()
