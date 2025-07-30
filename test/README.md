# Azure Container API - Test Suite

This directory contains the test suite for the Azure Container API project.

## Test Structure

```
test/
├── unit/                    # Unit tests (Level 2)
│   ├── test_health.py      # Health check endpoint tests
│   └── test_keyword_extraction.py  # Keyword extraction endpoint tests
├── logs/                   # Test execution logs
├── conftest.py            # Pytest configuration
├── requirements.txt       # Test dependencies
└── run_level2_tests.py    # Test runner script
```

## Test Levels

### Level 2: Unit Tests
- **Purpose**: Test individual functions and classes with mocked dependencies
- **Coverage**: 
  - Health check endpoint (`/health`)
  - Keyword extraction endpoint (`/api/v1/extract-jd-keywords`)
- **Key Features**:
  - All external dependencies mocked (OpenAI API, etc.)
  - No actual API calls made
  - Fast execution
  - Comprehensive error scenario testing

## Running Tests

### Prerequisites
```bash
pip install -r test/requirements.txt
```

### Run All Unit Tests
```bash
python test/run_level2_tests.py
```

### Run Specific Test File
```bash
pytest test/unit/test_health.py -v
pytest test/unit/test_keyword_extraction.py -v
```

### Run Single Test
```bash
pytest test/unit/test_health.py::TestHealthCheck::test_health_check_success -v
```

## Test Coverage

### Health Check Tests (9 tests)
- ✅ Successful health check response
- ✅ Response format validation
- ✅ Version information correctness
- ✅ Always returns healthy status
- ✅ Timestamp format validation
- ✅ HTTP method validation (405 for non-GET)
- ✅ No authentication required
- ✅ CORS headers presence
- ✅ Mocked timestamp testing

### Keyword Extraction Tests (10 tests)
- ✅ Successful keyword extraction
- ✅ Validation error handling (short description)
- ✅ Invalid max_keywords parameter
- ✅ Azure OpenAI rate limit error handling
- ✅ Timeout error handling
- ✅ Quality warning detection
- ✅ Response format validation
- ✅ Chinese job description support
- ✅ Service cleanup on error
- ✅ Edge case with long job descriptions

## Mocking Strategy

All tests use comprehensive mocking to avoid external dependencies:

1. **Environment Variables**: Set test values for all API keys and endpoints
2. **OpenAI Clients**: Mocked at import time to prevent initialization errors
3. **Service Dependencies**: Mocked using `unittest.mock`
4. **Monitoring Service**: Mocked to avoid telemetry during tests

## Test Results

Latest test run (2025-07-30 21:43:33):
- **Total Tests**: 19
- **Passed**: 19
- **Failed**: 0
- **Exit Code**: 0
- **Status**: ✅ PASSED

## Log Files

Test execution logs are saved to `test/logs/` with the format:
- Full log: `level2_unit_YYYYMMDD_HHMMSS.log`
- Summary: `level2_unit_YYYYMMDD_HHMMSS_summary.txt`

## Notes

- Tests do not require any Azure or OpenAI credentials
- All external API calls are mocked
- Tests are designed to be fast and reliable
- Follow AAA pattern: Arrange, Act, Assert