"""
Pytest fixtures for retry testing with CI optimization.
"""

import os
from unittest.mock import patch

import pytest

from test.config import TestConfig


@pytest.fixture
def mock_retry_delays():
    """Mock retry delays based on environment."""
    delays = TestConfig.get_retry_delays()

    # Patch AdaptiveRetryStrategy with environment-specific delays
    with patch('src.utils.adaptive_retry.AdaptiveRetryStrategy.__init__') as mock_init:
        def init_with_ci_delays(self):
            """Initialize with CI-aware delays."""
            self.retry_configs = {
                'rate_limit': {
                    'max_attempts': 3,
                    'initial_delay': delays['rate_limit']['initial_delay'],
                    'max_delay': delays['rate_limit']['max_delay'],
                    'exponential_base': delays['rate_limit']['multiplier']
                },
                'timeout': {
                    'max_attempts': 1,
                    'initial_delay': delays['timeout']['initial_delay'],
                    'max_delay': delays['timeout']['max_delay'],
                    'exponential_base': delays['timeout']['multiplier']
                },
                'general': {
                    'max_attempts': 2,
                    'initial_delay': delays['general']['initial_delay'],
                    'max_delay': delays['general']['max_delay'],
                    'exponential_base': delays['general']['multiplier']
                },
                'validation': {
                    'max_attempts': 0,
                    'initial_delay': 0,
                    'max_delay': 0,
                    'exponential_base': 1
                }
            }

        mock_init.side_effect = init_with_ci_delays
        yield


@pytest.fixture
def expected_delays():
    """Get expected delays for assertions."""
    if TestConfig.is_ci_environment():
        return {
            'rate_limit_first': 0.1,
            'rate_limit_second': 0.2,
            'rate_limit_total': 0.3,
            'timeout': 0.05,
            'general': 0.1
        }
    else:
        return {
            'rate_limit_first': 3.0,
            'rate_limit_second': 6.0,
            'rate_limit_total': 9.0,
            'timeout': 0.5,
            'general': 1.0
        }
