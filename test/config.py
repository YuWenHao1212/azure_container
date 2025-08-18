"""
Test configuration module for CI/CD and local environments
"""
import os


class TestConfig:
    """Configuration for test execution in different environments."""

    @staticmethod
    def is_ci_environment():
        """Check if running in CI environment."""
        return os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'

    @staticmethod
    def get_test_timeout():
        """Get test timeout based on environment."""
        if TestConfig.is_ci_environment():
            return 60  # Longer timeout for CI
        return 30  # Default timeout for local

    @staticmethod
    def get_retry_delays():
        """Get retry delays based on environment."""
        if TestConfig.is_ci_environment():
            # Shorter delays for CI to speed up tests
            return {
                'initial_delay': 0.1,
                'max_delay': 1.0,
                'exponential_base': 1.5
            }
        # Default delays for local development
        return {
            'initial_delay': 1.0,
            'max_delay': 10.0,
            'exponential_base': 2.0
        }

    @staticmethod
    def get_max_retries():
        """Get maximum retry attempts."""
        if TestConfig.is_ci_environment():
            return 2  # Fewer retries in CI
        return 3  # Default retries for local

    @staticmethod
    def should_skip_integration_tests():
        """Check if integration tests should be skipped."""
        return os.getenv('SKIP_INTEGRATION_TESTS') == 'true'

    @staticmethod
    def get_test_database_url():
        """Get test database URL."""
        return os.getenv('TEST_DATABASE_URL', 'postgresql://test:test@localhost/test_db')

    @staticmethod
    def get_mock_api_key():
        """Get mock API key for testing."""
        return 'test-api-key-12345'
