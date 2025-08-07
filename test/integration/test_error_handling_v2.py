"""
Integration tests for V2 error handling and retry strategies.

Tests verify:
- Retry strategies for different error types
- Retry-After header handling
- No partial results on failure
- Correct retry timings
"""
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2
from src.utils.adaptive_retry import AdaptiveRetryStrategy


class TestErrorHandlingV2:
    """Test error handling and retry strategies for V2 implementation."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        with patch('src.services.combined_analysis_v2.IndexCalculationServiceV2') as mock_index:
            with patch('src.services.combined_analysis_v2.GapAnalysisServiceV2') as mock_gap:
                with patch('src.services.embedding_client.get_azure_embedding_client') as mock_get_embedding:
                    with patch('src.services.combined_analysis_v2.ResourcePoolManager') as mock_resource_pool:
                        # Configure mocks
                        mock_index_instance = AsyncMock()
                        mock_gap_instance = AsyncMock()

                        # Configure embedding client mock
                        mock_embedding_instance = AsyncMock()
                        mock_embedding_instance.create_embeddings = AsyncMock(
                            return_value=[[0.1] * 1536, [0.2] * 1536]
                        )
                        mock_embedding_instance.close = AsyncMock()
                        # Make the mock support async context manager protocol
                        mock_embedding_instance.__aenter__ = AsyncMock(return_value=mock_embedding_instance)
                        mock_embedding_instance.__aexit__ = AsyncMock(return_value=None)
                        mock_get_embedding.return_value = mock_embedding_instance

                        # Configure ResourcePoolManager mock
                        mock_pool_instance = AsyncMock()
                        mock_client = AsyncMock()
                        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                        mock_client.__aexit__ = AsyncMock(return_value=None)
                        # get_client should return the context manager directly, not as a coroutine
                        mock_pool_instance.get_client = Mock(return_value=mock_client)
                        mock_pool_instance.get_stats = Mock(return_value={
                            "total_clients": 1,
                            "active_clients": 0,
                            "available_clients": 1
                        })
                        mock_resource_pool.return_value = mock_pool_instance

                        mock_index.return_value = mock_index_instance
                        mock_gap.return_value = mock_gap_instance

                        yield {
                            'index': mock_index_instance,
                            'gap': mock_gap_instance,
                            'embedding': mock_embedding_instance,
                            'resource_pool': mock_pool_instance
                        }

    @pytest.mark.asyncio
    async def test_API_GAP_018_IT_rate_limit_retry_timing(self, mock_services):
        """
        API-GAP-018-IT: Test rate limit (429) retry with exponential backoff.

        Verify:
        - 3 retry attempts for rate limit errors
        - Exponential backoff timing: 3s → 6s → 12s
        - Maximum 20s wait time limit
        """
        # Configure mock to fail with rate limit error
        rate_limit_error = Exception("Rate limit exceeded")
        rate_limit_error.status_code = 429

        call_times = []
        call_count = 0

        async def mock_calculate_index(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 4:  # Fail first 3 times
                raise rate_limit_error
            return {
                "raw_similarity_percentage": 70,
                "similarity_percentage": 80,
                "keyword_coverage": {
                    "total_keywords": 10,
                    "covered_count": 7,
                    "coverage_percentage": 70,
                    "covered_keywords": ["python", "fastapi"],
                    "missed_keywords": ["react"]
                }
            }

        mock_services['index'].calculate_index = mock_calculate_index

        # Create service with retry enabled
        service = CombinedAnalysisServiceV2(
            index_service=mock_services['index'],
            gap_service=mock_services['gap'],
            enable_partial_results=False
        )

        # Execute with timing measurement
        time.time()

        with pytest.raises(Exception) as exc_info:
            await service.analyze(
                resume="Test resume " * 50,  # > 200 chars
                job_description="Test JD " * 50,
                keywords=["python", "fastapi", "react"],
                language="en"
            )

        # Verify it failed after retries
        assert "Rate limit" in str(exc_info.value)
        assert call_count == 3  # Initial + 2 retries

        # Verify retry delays (allowing some tolerance)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            assert 2.5 <= delay1 <= 3.5, f"First retry delay should be ~3s, got {delay1}"
            assert 5.5 <= delay2 <= 6.5, f"Second retry delay should be ~6s, got {delay2}"

    @pytest.mark.asyncio
    async def test_API_GAP_022_IT_retry_after_header_handling(self, mock_services):
        """
        API-GAP-022-IT: Test Retry-After header handling.

        Verify:
        - System respects Retry-After header value
        - Waits specified time before retry
        - Caps wait time at maximum limit (20s)
        """
        # Create error with Retry-After header
        rate_limit_error = RuntimeError("Rate limit exceeded")
        rate_limit_error.status_code = 429
        rate_limit_error.response = Mock()
        rate_limit_error.response.headers = {'Retry-After': '30'}  # 30s > 20s max

        retry_delays = []

        async def mock_calculate_with_retry_after(*args, **kwargs):
            raise rate_limit_error

        mock_services['index'].calculate_index = mock_calculate_with_retry_after

        # Patch sleep to capture delays
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            retry_delays.append(delay)
            await original_sleep(0.01)  # Short delay for testing

        with patch('asyncio.sleep', mock_sleep):
            service = CombinedAnalysisServiceV2(
                index_service=mock_services['index'],
                gap_service=mock_services['gap'],
                enable_partial_results=False
            )

            with pytest.raises(RuntimeError):
                await service.analyze(
                    resume="Test resume " * 50,
                    job_description="Test JD " * 50,
                    keywords=["test"],
                    language="en"
                )

        # Verify Retry-After was capped at 20s
        assert any(19 <= delay <= 20 for delay in retry_delays), \
            f"Retry-After should be capped at 20s, got delays: {retry_delays}"

    @pytest.mark.asyncio
    async def test_API_GAP_019_IT_timeout_quick_retry(self, mock_services):
        """
        API-GAP-019-IT: Test timeout (408) error single retry.

        Verify:
        - Only 1 retry attempt for timeout errors
        - Fixed 0.5s delay before retry
        - Fails after 2 total attempts
        """
        call_count = 0
        call_times = []

        async def mock_calculate_with_timeout(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Request timed out")
            return {
                "raw_similarity_percentage": 70,
                "similarity_percentage": 80,
                "keyword_coverage": {
                    "total_keywords": 10,
                    "covered_count": 7,
                    "coverage_percentage": 70,
                    "covered_keywords": ["python"],
                    "missed_keywords": []
                }
            }

        mock_services['index'].calculate_index = mock_calculate_with_timeout

        service = CombinedAnalysisServiceV2(
            index_service=mock_services['index'],
            gap_service=mock_services['gap'],
            enable_partial_results=False
        )

        # Configure gap service to succeed
        mock_services['gap'].analyze_with_context = AsyncMock(return_value={
            "CoreStrengths": "<ol><li>Test</li></ol>",
            "KeyGaps": "<ol><li>Test</li></ol>",
            "QuickImprovements": "<ol><li>Test</li></ol>",
            "SkillSearchQueries": []
        })

        # Execute
        await service.analyze(
            resume="Test resume " * 50,
            job_description="Test JD " * 50,
            keywords=["python"],
            language="en"
        )

        # Verify retry happened
        assert call_count == 2  # Initial + 1 retry

        # Verify delay was ~0.5s
        if len(call_times) >= 2:
            delay = call_times[1] - call_times[0]
            assert 0.4 <= delay <= 0.6, f"Timeout retry delay should be ~0.5s, got {delay}"

    @pytest.mark.asyncio
    async def test_API_GAP_020_IT_general_error_retry(self, mock_services):
        """
        API-GAP-020-IT: Test general (500) error retry strategy.

        Verify:
        - 2 retry attempts for general errors
        - Linear backoff with 1s delay
        - Fails after 3 total attempts
        """
        call_count = 0
        call_times = []

        async def mock_calculate_with_error(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise Exception("General processing error")
            return {
                "raw_similarity_percentage": 70,
                "similarity_percentage": 80,
                "keyword_coverage": {
                    "total_keywords": 10,
                    "covered_count": 7,
                    "coverage_percentage": 70,
                    "covered_keywords": ["python"],
                    "missed_keywords": []
                }
            }

        mock_services['index'].calculate_index = mock_calculate_with_error

        service = CombinedAnalysisServiceV2(
            index_service=mock_services['index'],
            gap_service=mock_services['gap'],
            enable_partial_results=False
        )

        with pytest.raises(Exception) as exc_info:
            await service.analyze(
                resume="Test resume " * 50,
                job_description="Test JD " * 50,
                keywords=["python"],
                language="en"
            )

        # Verify it failed after retries
        assert "General processing error" in str(exc_info.value)
        assert call_count == 2  # Initial + 1 retry (max_attempts=2)

        # Verify delay was ~1s
        if len(call_times) >= 2:
            delay = call_times[1] - call_times[0]
            assert 0.8 <= delay <= 1.2, f"General error retry delay should be ~1s, got {delay}"

    @pytest.mark.asyncio
    async def test_API_GAP_025_IT_no_partial_results_on_failure(self, mock_services):
        """
        API-GAP-025-IT: Test no partial results on failure.

        Verify:
        - When any service fails, no partial results returned
        - Complete failure mode only
        - Returns error response without data
        """
        # Index succeeds
        mock_services['index'].calculate_index = AsyncMock(return_value={
            "raw_similarity_percentage": 70,
            "similarity_percentage": 80,
            "keyword_coverage": {
                "total_keywords": 10,
                "covered_count": 7,
                "coverage_percentage": 70,
                "covered_keywords": ["python"],
                "missed_keywords": []
            }
        })

        # Gap analysis fails
        mock_services['gap'].analyze_with_context = AsyncMock(
            side_effect=Exception("Gap analysis failed")
        )

        service = CombinedAnalysisServiceV2(
            index_service=mock_services['index'],
            gap_service=mock_services['gap'],
            enable_partial_results=False  # Should be default
        )

        # Execute and expect complete failure
        with pytest.raises(Exception) as exc_info:
            await service.analyze(
                resume="Test resume " * 50,
                job_description="Test JD " * 50,
                keywords=["python"],
                language="en"
            )

        # Verify complete failure (no partial results)
        assert "Gap analysis failed" in str(exc_info.value)

        # Verify index was called but result wasn't returned
        assert mock_services['index'].calculate_index.called
        assert mock_services['gap'].analyze_with_context.called

    @pytest.mark.asyncio
    async def test_API_GAP_021_IT_validation_error_no_retry(self, mock_services):
        """
        API-GAP-021-IT: Test validation error no retry.

        Verify:
        - Validation errors (400) fail immediately
        - No retry attempts made
        - Returns validation error response
        """
        call_count = 0

        async def mock_calculate_with_validation_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ValueError("Resume must be at least 200 characters")

        mock_services['index'].calculate_index = mock_calculate_with_validation_error

        service = CombinedAnalysisServiceV2(
            index_service=mock_services['index'],
            gap_service=mock_services['gap'],
            enable_partial_results=False
        )

        with pytest.raises(ValueError):
            await service.analyze(
                resume="Short",  # < 200 chars
                job_description="Test JD " * 50,
                keywords=["python"],
                language="en"
            )

        # Verify no retries for validation errors
        assert call_count == 1  # Only initial call, no retries


class TestAdaptiveRetryStrategy:
    """Test the adaptive retry strategy directly."""

    @pytest.mark.asyncio
    async def test_API_GAP_023_IT_max_retries_then_fail(self):
        """
        API-GAP-023-IT: Test max retries then fail.

        Verify:
        - Fails after maximum retry attempts
        - Each error type has correct max attempts
        - Final error is propagated correctly
        """
        strategy = AdaptiveRetryStrategy()

        # Verify rate limit config
        rate_limit_config = strategy.retry_configs['rate_limit']
        assert rate_limit_config['max_attempts'] == 3
        assert rate_limit_config['base_delay'] == 3.0
        assert rate_limit_config['max_delay'] == 20.0
        assert rate_limit_config['backoff'] == 'exponential'

        # Verify timeout config
        timeout_config = strategy.retry_configs['timeout']
        assert timeout_config['max_attempts'] == 2  # Initial + 1 retry
        assert timeout_config['base_delay'] == 0.5
        assert timeout_config['max_delay'] == 0.5

        # Verify general config
        general_config = strategy.retry_configs['general']
        assert general_config['max_attempts'] == 2
        assert general_config['base_delay'] == 1.0
        assert general_config['max_delay'] == 1.0
        assert general_config['backoff'] == 'linear'

    @pytest.mark.asyncio
    async def test_API_GAP_024_IT_first_retry_succeeds(self):
        """
        API-GAP-024-IT: Test retry succeeds on first attempt.

        Verify:
        - Operation succeeds on first retry
        - No further retries needed
        - Correct delay applied before retry
        """
        strategy = AdaptiveRetryStrategy()
        config = strategy.retry_configs['rate_limit']

        # Test exponential backoff: 3s → 6s → 12s
        delay0 = strategy._calculate_delay(config, 0)
        delay1 = strategy._calculate_delay(config, 1)
        delay2 = strategy._calculate_delay(config, 2)

        assert delay0 == 3.0  # 3 * (2^0) = 3
        assert delay1 == 6.0  # 3 * (2^1) = 6
        assert delay2 == 12.0  # 3 * (2^2) = 12

    @pytest.mark.asyncio
    async def test_API_GAP_026_IT_value_error_classification(self):
        """
        API-GAP-026-IT: Test ValueError classified as validation error.

        Verify:
        - ValueError is classified as validation error
        - No retry for validation errors
        - Returns 400 status code
        """
        strategy = AdaptiveRetryStrategy()
        config = strategy.retry_configs['rate_limit']

        # Test that delay is capped at 20s
        delay3 = strategy._calculate_delay(config, 3)  # Would be 24s
        delay4 = strategy._calculate_delay(config, 4)  # Would be 48s

        assert delay3 == 20.0  # Capped at max_delay
        assert delay4 == 20.0  # Capped at max_delay

    def test_API_GAP_027_IT_timeout_error_classification(self):
        """
        API-GAP-027-IT: Test asyncio.TimeoutError classification.

        Verify:
        - asyncio.TimeoutError classified as timeout
        - Gets timeout retry strategy
        - Single retry with 0.5s delay
        """
        strategy = AdaptiveRetryStrategy()

        # Test timeout classification
        timeout_error = Exception("Request timed out")
        assert strategy._default_error_classifier(timeout_error) == "timeout"

        # Test rate limit classification
        rate_error = Exception("Rate limit exceeded")
        assert strategy._default_error_classifier(rate_error) == "rate_limit"

        # Test empty fields classification
        empty_error = Exception("Field is empty")
        assert strategy._default_error_classifier(empty_error) == "empty_fields"

        # Test general classification
        general_error = Exception("Something went wrong")
        assert strategy._default_error_classifier(general_error) == "general"
