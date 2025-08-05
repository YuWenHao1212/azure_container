"""
Unit tests for LLM Factory deployment mapping functionality.

Tests the new DEPLOYMENT_MAP feature that maps model names to Azure deployment names.
"""

import os
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Mock environment variables before imports
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'

from src.services.llm_factory import DEPLOYMENT_MAP, _create_client, get_llm_client, get_llm_client_smart


class TestLLMFactoryDeploymentMapping:
    """Test cases for deployment name mapping in LLM Factory."""

    def test_deployment_map_constants(self):
        """Test that DEPLOYMENT_MAP contains expected mappings."""
        expected_mappings = {
            "gpt4o-2": "gpt-4.1-japan",
            "gpt41-mini": "gpt-4-1-mini-japaneast"
        }

        assert expected_mappings == DEPLOYMENT_MAP
        assert len(DEPLOYMENT_MAP) == 2

    @patch('src.services.llm_factory.get_azure_openai_client')
    def test_gpt4o2_deployment_mapping(self, mock_get_client):
        """Test that gpt4o-2 model uses correct deployment name."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        client = _create_client("gpt4o-2")

        # Verify get_azure_openai_client was called with correct deployment_name
        mock_get_client.assert_called_once_with(deployment_name="gpt-4.1-japan")
        assert client == mock_client

    @patch('src.services.llm_factory.get_gpt41_mini_client')
    def test_gpt41_mini_deployment_mapping(self, mock_get_gpt41_client):
        """Test that gpt41-mini model uses GPT-4.1 mini client."""
        mock_client = Mock()
        mock_get_gpt41_client.return_value = mock_client

        client = _create_client("gpt41-mini")

        # Verify GPT-4.1 mini client was called
        mock_get_gpt41_client.assert_called_once()
        assert client == mock_client

    @patch('src.services.llm_factory.get_gpt41_mini_client')
    @patch('src.services.llm_factory.get_azure_openai_client')
    def test_gpt41_mini_fallback_to_gpt4o2(self, mock_get_client, mock_get_gpt41_client):
        """Test fallback from GPT-4.1 mini to GPT-4o-2 on error."""
        # Mock GPT-4.1 mini client to raise exception
        mock_get_gpt41_client.side_effect = Exception("GPT-4.1 mini unavailable")

        # Mock fallback client
        mock_fallback_client = Mock()
        mock_get_client.return_value = mock_fallback_client

        client = _create_client("gpt41-mini")

        # Verify fallback was called with correct deployment name
        mock_get_client.assert_called_once_with(deployment_name="gpt-4.1-japan")
        assert client == mock_fallback_client

    @patch('src.services.llm_factory.get_azure_openai_client')
    def test_unknown_model_uses_default_mapping(self, mock_get_client):
        """Test that unknown model uses default deployment name."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        client = _create_client("unknown-model")

        # Should use default deployment name for unknown models
        mock_get_client.assert_called_once_with(deployment_name="gpt-4.1-japan")
        assert client == mock_client

    @patch('src.services.llm_factory._create_client')
    @patch('src.services.llm_factory.get_settings')
    def test_get_llm_client_with_model_parameter(self, mock_get_settings, mock_create_client):
        """Test get_llm_client with direct model specification."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        result = get_llm_client(model="gpt4o-2")

        # Verify _create_client was called with correct model
        mock_create_client.assert_called_once_with("gpt4o-2")
        assert result == mock_client

    @patch('src.services.llm_factory._create_client')
    @patch('src.services.llm_factory.get_settings')
    def test_get_llm_client_smart_with_request_model(self, mock_get_settings, mock_create_client):
        """Test get_llm_client_smart with request model parameter."""
        mock_settings = Mock()
        mock_settings.enable_llm_model_override = True
        mock_get_settings.return_value = mock_settings

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        result = get_llm_client_smart(
            api_name="test",
            request_model="gpt41-mini"
        )

        # Verify _create_client was called with request model
        mock_create_client.assert_called_once_with("gpt41-mini")
        assert result == mock_client

    @patch('src.services.llm_factory._create_client')
    @patch('src.services.llm_factory.get_settings')
    def test_get_llm_client_smart_with_header_model(self, mock_get_settings, mock_create_client):
        """Test get_llm_client_smart with HTTP header model."""
        mock_settings = Mock()
        mock_settings.enable_llm_model_override = True
        mock_settings.enable_llm_model_header = True
        mock_get_settings.return_value = mock_settings

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        headers = {"X-LLM-Model": "gpt4o-2"}
        result = get_llm_client_smart(
            api_name="test",
            headers=headers
        )

        # Verify _create_client was called with header model
        mock_create_client.assert_called_once_with("gpt4o-2")
        assert result == mock_client
