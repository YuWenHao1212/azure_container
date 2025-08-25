# Test Tools

This directory contains diagnostic and monitoring tools for the Azure Container API project.

## Available Tools

### LLM2 Fallback Monitor (`llm2_fallback_monitor.py`)

**Tool ID**: TOOL-LLM2-MON-01

Monitor the fallback rate of LLM2 (Additional Manager) in the Resume Tailoring API. This tool helps detect when the system falls back to using original resume content for Education, Projects, and Certifications sections.

#### Usage

```bash
# Basic usage - run 10 tests
python test/tools/llm2_fallback_monitor.py

# Run 100 tests with 1 second delay
python test/tools/llm2_fallback_monitor.py -n 100 --delay 1

# Save full API responses for analysis
python test/tools/llm2_fallback_monitor.py -n 20 --save-responses --verbose

# Quick check with 3 tests
python test/tools/llm2_fallback_monitor.py -n 3 --verbose
```

#### Command Line Options

- `-n, --num-tests`: Number of tests to run (default: 10)
- `--delay`: Delay in seconds between tests (default: 2)
- `--verbose`: Show detailed output for each test
- `--save-responses`: Save full API responses to separate JSON files
- `--api-url`: API endpoint URL (default: production)
- `--api-key`: API key for authentication

#### Output

- **Summary Report**: Saved to `/tmp/llm2_fallback_test_results_{N}tests_{timestamp}.json`
- **Full Responses**: Saved to `/tmp/llm2_fallback_test_{timestamp}/` (when using `--save-responses`)
  - `test_config.json`: Test configuration and metadata
  - `response_001.json`, `response_002.json`, etc.: Complete request/response pairs with metadata
- **Console Output**: Real-time test results and statistics

#### Saved Response Format

When using `--save-responses`, each response file contains:
```json
{
  "request": {
    "job_description": "...",
    "original_resume": "...",
    "original_index": {...},
    "options": {...}
  },
  "response": {
    // Complete API response
  },
  "metadata": {
    "test_number": 1,
    "timestamp": "2025-08-25T08:55:56.151158",
    "response_time_seconds": 10.72,
    "api_url": "..."
  }
}
```

This allows for:
- Complete test reproduction
- Request/response comparison
- Performance analysis
- Debugging API issues

#### Key Metrics

- **Fallback Rate**: Percentage of tests where LLM2 fell back to original content
  - ✅ < 5%: Within acceptable range
  - ⚠️ 5-10%: Warning threshold
  - ❌ > 10%: Error threshold
  
- **Response Time**:
  - P50: < 12s (target)
  - P95: < 20s (target)

#### Exit Codes

- `0`: Success (fallback rate ≤ 10%)
- `1`: Error (fallback rate > 10%)

#### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Monitor LLM2 Fallback Rate
  run: |
    python test/tools/llm2_fallback_monitor.py -n 10
    if [ $? -ne 0 ]; then
      echo "LLM2 fallback rate exceeded threshold!"
      exit 1
    fi
```

## Adding New Tools

When adding new diagnostic tools to this directory:

1. Use descriptive names that indicate the tool's purpose
2. Include a Tool ID in the docstring (format: `TOOL-{AREA}-{PURPOSE}-{NUMBER}`)
3. Add comprehensive help text and examples
4. Update this README with usage instructions
5. Consider adding exit codes for CI/CD integration
6. Include proper error handling and logging

## Tool Maintenance

### Updating Test Data

When API formats change, update the test data in the tools:
- `ORIGINAL_RESUME`: Ensure it matches the current HTML format
- `JOB_DESCRIPTION`: Update with relevant keywords
- `GAP_ANALYSIS`: Ensure fields match the API response format

### Performance Considerations

- Tools should complete within reasonable time limits
- Use appropriate delays between API calls to avoid rate limiting
- Consider implementing retry logic for transient failures

## Related Documentation

- [Resume Format V3 Specification](../../docs/issues/tailor-resume-refactor-V3/Resume_Format_V3_Complete_Specification.md)
- [Resume Tailoring Test Specification](../../docs/issues/tailor-resume-refactor/test-spec-resume-tailoring.md)
- [API Error Codes Standard](../../docs/development/FASTAPI_ERROR_CODES_STANDARD.md)