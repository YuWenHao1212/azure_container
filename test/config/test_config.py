"""
Test configuration for CI/CD optimization.

This module provides test configuration that adapts based on the environment.
In CI environment, it uses reduced delays for faster test execution.
"""

import os
from typing import Any, Dict


class TestConfig:
    """Test configuration with environment-aware settings."""

    @staticmethod
    def is_ci_environment() -> bool:
        """Check if running in CI environment."""
        # GitHub Actions sets CI=true
        # Also check for common CI environment variables
        return any([
            os.environ.get('CI') == 'true',
            os.environ.get('GITHUB_ACTIONS') == 'true',
            os.environ.get('JENKINS_URL') is not None,
            os.environ.get('GITLAB_CI') == 'true'
        ])

    @staticmethod
    def get_retry_delays() -> dict[str, dict[str, Any]]:
        """Get retry delay configuration based on environment."""
        if TestConfig.is_ci_environment():
            # CI mode: Use minimal delays for faster testing
            return {
                'rate_limit': {
                    'initial_delay': 0.1,   # 100ms instead of 3s
                    'max_delay': 0.5,       # 500ms instead of 20s
                    'multiplier': 2
                },
                'timeout': {
                    'initial_delay': 0.05,  # 50ms instead of 0.5s
                    'max_delay': 0.05,
                    'multiplier': 1
                },
                'general': {
                    'initial_delay': 0.1,   # 100ms instead of 1s
                    'max_delay': 0.2,       # 200ms instead of 2s
                    'multiplier': 1
                }
            }
        else:
            # Local development: Use realistic delays
            return {
                'rate_limit': {
                    'initial_delay': 3.0,
                    'max_delay': 20.0,
                    'multiplier': 2
                },
                'timeout': {
                    'initial_delay': 0.5,
                    'max_delay': 0.5,
                    'multiplier': 1
                },
                'general': {
                    'initial_delay': 1.0,
                    'max_delay': 2.0,
                    'multiplier': 1
                }
            }

    @staticmethod
    def get_test_timeout() -> int:
        """Get test timeout in seconds."""
        if TestConfig.is_ci_environment():
            return 10  # Shorter timeout in CI
        else:
            return 30  # Normal timeout for local testing

    @staticmethod
    def get_resource_pool_wait_time() -> float:
        """Get resource pool wait time."""
        if TestConfig.is_ci_environment():
            return 0.1  # 100ms in CI
        else:
            return 1.0  # 1s in local
