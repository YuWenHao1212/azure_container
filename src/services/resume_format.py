"""
Resume Format Service.
Main service for formatting OCR text into structured HTML resumes.
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from src.core.monitoring_service import monitoring_service
from src.models.resume_format import (
    CorrectionsMade,
    ResumeFormatData,
    SectionsDetected,
    SupplementInfo,
)
from src.services.exceptions import LLMServiceError, ProcessingError
from src.services.html_validator import HTMLValidator
from src.services.llm_factory import get_llm_client
from src.services.openai_client import (
    AzureOpenAIClient,
    AzureOpenAIRateLimitError,
    # get_azure_openai_client, # Replaced with LLM Factory
)
from src.services.resume_text_processor import ResumeTextProcessor
from src.services.token_tracking_mixin import TokenTrackingMixin
from src.services.unified_prompt_service import UnifiedPromptService

logger = logging.getLogger(__name__)


class ResumeFormatService(TokenTrackingMixin):
    """履歷格式化服務"""

    def __init__(self, openai_client: AzureOpenAIClient = None):
        super().__init__()  # Initialize TokenTrackingMixin
        self.openai_client = openai_client or get_llm_client(api_name="resume_format")
        self.prompt_service = UnifiedPromptService(task_path="resume_format")
        self.text_processor = ResumeTextProcessor()
        self.html_validator = HTMLValidator()

    async def format_resume(
        self,
        ocr_text: str,
        supplement_info: SupplementInfo | None = None
    ) -> ResumeFormatData:
        """
        格式化履歷主流程

        Args:
            ocr_text: OCR 提取的文字 (格式: 第一行types, 第二行content)
            supplement_info: 可選的補充資訊

        Returns:
            ResumeFormatData: 格式化後的履歷資料
        """
        start_time = datetime.now()

        try:
            # 1. 預處理 OCR 文字
            logger.info("Starting OCR text preprocessing")
            cleaned_text = self.text_processor.preprocess_ocr_text(ocr_text)

            # 2. 準備 LLM 輸入
            # OCR 輸出格式: 第一行是逗號分隔的 types, 第二行是逗號分隔的內容
            logger.info("Preparing LLM input")
            llm_input = self._prepare_llm_input(cleaned_text, supplement_info)

            # 3. 呼叫 LLM 進行格式化
            logger.info("Calling LLM for resume formatting")
            formatted_html = await self._call_llm_with_retry(llm_input)

            # 4. 文字後處理 (OCR 錯誤修正等)
            logger.info("Post-processing HTML content")
            processed_html = self.text_processor.postprocess_html(formatted_html)

            # 5. HTML 驗證和清理
            logger.info("Validating and cleaning HTML")
            validated_html = self.html_validator.validate_and_clean(processed_html)

            # 6. 檢測區段
            sections_detected = self._detect_sections(validated_html)

            # 7. 計算修正統計
            corrections_made = self._calculate_corrections()

            # 8. 記錄使用的補充資訊
            supplement_used = self._track_supplement_usage(
                validated_html, supplement_info
            )

            # 記錄成功事件
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            monitoring_service.track_event("ResumeFormatSuccess", {
                "ocr_text_length": len(ocr_text),
                "has_supplement_info": bool(supplement_info),
                "processing_time_ms": duration_ms,
                "sections_detected_count": sum(1 for v in sections_detected.model_dump().values() if v),
                "total_corrections": sum(corrections_made.model_dump().values())
            })

            return ResumeFormatData(
                formatted_resume=validated_html,
                sections_detected=sections_detected,
                corrections_made=corrections_made,
                supplement_info_used=supplement_used
            )

        except AzureOpenAIRateLimitError:
            # Re-raise rate limit errors without wrapping
            raise

        except Exception as e:
            logger.error(f"Resume formatting failed: {e!s}")

            # 記錄失敗事件
            monitoring_service.track_event("ResumeFormatError", {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "ocr_text_length": len(ocr_text)
            })

            raise ProcessingError(f"Resume formatting failed: {e!s}") from e

    def _prepare_llm_input(
        self,
        cleaned_text: str,
        supplement_info: SupplementInfo | None
    ) -> dict[str, Any]:
        """準備 LLM 輸入資料"""
        # 將補充資訊轉換為字典格式
        supplement_dict = {}
        if supplement_info:
            supplement_dict = {
                k: v for k, v in supplement_info.model_dump().items()
                if v is not None
            }

        return {
            "ocr_text": cleaned_text,
            "supplement_info": supplement_dict or "null"
        }

    async def _call_llm_with_retry(
        self,
        llm_input: dict[str, Any],
        max_retries: int = 3
    ) -> str:
        """使用重試機制呼叫 LLM"""
        retry_delays = [2.0, 4.0, 8.0]

        for attempt in range(max_retries):
            try:
                # 使用 UnifiedPromptService 獲取 prompt 和配置
                full_prompt, llm_config = self.prompt_service.get_prompt_with_config(
                    language="en",  # Resume format prompts are in English
                    version="1.0.0",
                    variables=llm_input
                )

                # 解析 system 和 user prompts
                # UnifiedPromptService 會將 system 和 user prompts 結合
                # 我們需要分離它們以符合 chat_completion 的格式
                logger.info(f"Getting prompt config for task: {self.prompt_service.TASK_PATH}")
                prompt_config = self.prompt_service.get_prompt_config("en", "1.0.0")
                system_prompt = prompt_config.get_system_prompt()
                user_prompt = prompt_config.format_user_prompt(**llm_input)

                logger.info(
                    f"Prompt config loaded - system: {len(system_prompt) if system_prompt else 0} chars, "
                    f"user template exists: {hasattr(prompt_config, 'user_prompt')}"
                )

                # 準備訊息
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_prompt})

                # Debug logging
                logger.debug(f"System prompt length: {len(system_prompt) if system_prompt else 0}")
                logger.debug(f"User prompt length: {len(user_prompt)}")
                logger.debug(f"User prompt preview: {user_prompt[:200]}...")

                # 呼叫 Azure OpenAI
                logger.info(f"Calling Azure OpenAI (attempt {attempt + 1}/{max_retries})")
                logger.info(f"Messages being sent: {len(messages)} messages")
                for i, msg in enumerate(messages):
                    logger.info(f"Message {i+1} - Role: {msg['role']}, Content length: {len(msg['content'])}")
                    if len(msg['content']) < 200:
                        logger.info(f"Message {i+1} content: {msg['content']}")

                response = await self.openai_client.chat_completion(
                    messages=messages,
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens,
                    top_p=llm_config.top_p,
                    frequency_penalty=llm_config.frequency_penalty,
                    presence_penalty=llm_config.presence_penalty,
                    stream=False
                )

                # 提取回應內容
                if not response or "choices" not in response:
                    raise LLMServiceError("Invalid response from Azure OpenAI")

                content = response["choices"][0]["message"]["content"]

                # 追蹤 token 使用
                if "usage" in response:
                    token_info = self.track_openai_usage(
                        response=response,
                        operation="resume_format"
                    )
                    logger.info(f"Token usage: {token_info}")

                # 檢查結果是否有效
                if not content or not content.strip():
                    raise LLMServiceError("LLM returned empty response")

                # 清理 HTML 內容 (移除可能的 markdown 標記)
                cleaned_content = self._extract_html_content(content)

                return cleaned_content

            except AzureOpenAIRateLimitError:
                # Don't retry rate limit errors, re-raise immediately
                raise

            except Exception as e:
                logger.warning(
                    f"LLM call failed on attempt {attempt + 1}: {e!s}"
                )

                monitoring_service.track_event("LLMRetryAttempt", {
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delays[attempt])
                else:
                    raise LLMServiceError(
                        f"LLM formatting failed after {max_retries} attempts: {e!s}"
                    ) from e

    def _detect_sections(self, html: str) -> SectionsDetected:
        """檢測履歷中的各個區段"""
        sections_dict = self.html_validator.detect_sections(html)
        return SectionsDetected(**sections_dict)

    def _calculate_corrections(self) -> CorrectionsMade:
        """計算修正統計"""
        stats = self.text_processor.get_correction_stats()
        return CorrectionsMade(**stats)

    def _track_supplement_usage(
        self,
        html: str,
        supplement_info: SupplementInfo | None
    ) -> list[str]:
        """追蹤使用了哪些補充資訊"""
        if not supplement_info:
            return []

        used_fields = []

        # 檢查每個補充資訊欄位是否在最終 HTML 中出現
        if supplement_info.name and supplement_info.name in html:
            used_fields.append("name")

        if supplement_info.email and supplement_info.email in html:
            used_fields.append("email")

        if supplement_info.linkedin and supplement_info.linkedin in html:
            used_fields.append("linkedin")

        if supplement_info.phone and supplement_info.phone in html:
            used_fields.append("phone")

        if supplement_info.location and supplement_info.location in html:
            used_fields.append("location")

        return used_fields

    def _extract_html_content(self, content: str) -> str:
        """
        從 LLM 回應中提取 HTML 內容
        移除可能的 markdown 標記或其他包裝
        """
        if not content:
            return ""

        # 移除可能的 markdown code block 標記

        # 移除 ```html 和 ``` 標記
        content = re.sub(r'^```html?\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n?```\s*$', '', content, flags=re.MULTILINE)

        # 移除多餘的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        return content.strip()
