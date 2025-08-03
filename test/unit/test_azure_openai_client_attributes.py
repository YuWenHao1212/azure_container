"""
單元測試：確保 AzureOpenAIClient 有必要的屬性
這個測試防止 AttributeError 的回歸問題
"""
import pytest

from src.services.openai_client import AzureOpenAIClient


class TestAzureOpenAIClientAttributes:
    """測試 AzureOpenAIClient 的屬性初始化"""

    def test_azure_openai_client_has_retry_attributes(self):
        """
        TEST: UNIT-AOAI-001
        確保 AzureOpenAIClient 初始化時包含所有必要的重試屬性
        這是為了防止 'AttributeError: max_retries' 的問題
        """
        # Arrange
        test_endpoint = "https://test.openai.azure.com"
        test_api_key = "test-api-key"
        test_deployment = "test-deployment"

        # Act
        client = AzureOpenAIClient(
            endpoint=test_endpoint,
            api_key=test_api_key,
            deployment_name=test_deployment
        )

        # Assert - 檢查必要的屬性
        assert hasattr(client, 'max_retries'), "AzureOpenAIClient missing 'max_retries' attribute"
        assert hasattr(client, 'retry_delays'), "AzureOpenAIClient missing 'retry_delays' attribute"

        # 檢查屬性類型和值
        assert isinstance(client.max_retries, int), "max_retries should be an integer"
        assert isinstance(client.retry_delays, list), "retry_delays should be a list"
        assert client.max_retries > 0, "max_retries should be positive"
        assert len(client.retry_delays) > 0, "retry_delays should not be empty"
        assert all(isinstance(delay, (int, float)) for delay in client.retry_delays), \
            "All retry delays should be numeric"

    def test_azure_openai_client_retry_configuration_values(self):
        """
        TEST: UNIT-AOAI-002
        驗證重試配置的具體值是否正確
        """
        # Arrange & Act
        client = AzureOpenAIClient(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            deployment_name="test"
        )

        # Assert - 檢查具體的配置值
        assert client.max_retries == 3, "max_retries should be 3"
        assert client.retry_delays == [1, 2, 4], "retry_delays should be [1, 2, 4] for exponential backoff"

    def test_azure_openai_client_all_required_attributes(self):
        """
        TEST: UNIT-AOAI-003
        全面檢查所有必要的屬性是否存在
        """
        # Arrange
        required_attributes = [
            'endpoint', 'api_key', 'api_version', 'deployment_id',
            'client', 'logger', 'max_retries', 'retry_delays'
        ]

        # Act
        client = AzureOpenAIClient(
            endpoint="https://test.openai.azure.com",
            api_key="test-key"
        )

        # Assert
        for attr in required_attributes:
            assert hasattr(client, attr), f"AzureOpenAIClient missing required attribute: {attr}"

    @pytest.mark.asyncio
    async def test_client_cleanup(self):
        """
        TEST: UNIT-AOAI-004
        確保客戶端可以正確清理資源
        """
        # Arrange
        client = AzureOpenAIClient(
            endpoint="https://test.openai.azure.com",
            api_key="test-key"
        )

        # Act & Assert - 確保 close 方法存在且可以調用
        assert hasattr(client, 'close'), "AzureOpenAIClient should have a close method"
        await client.close()  # 應該不會拋出異常
