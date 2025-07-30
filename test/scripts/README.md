# Test Scripts

This directory contains various test scripts for different levels of testing.

## Level 1: Code Style Check

**Script**: `run_style.sh`

### Purpose
Performs code style checking using `ruff` for Python code, focusing on:
- Health check endpoint (`/health`)
- Keyword extraction endpoint (`/api/v1/extract-jd-keywords`)

### Features
- Checks Python code style against PEP 8 and other style conventions
- Validates import sorting
- Checks naming conventions
- Generates timestamped log files
- Provides colored terminal output
- Returns appropriate exit codes for CI/CD integration

### Usage
```bash
# Run style checks
./test/scripts/run_style.sh

# Or from the test/scripts directory
./run_style.sh
```

### Requirements
- `ruff` must be installed: `pip install ruff`
- No AI credentials required
- Unix-like environment (bash)

### Output
- **Terminal**: Colored output showing pass/fail status for each file
- **Log File**: Detailed results saved to `test/logs/level1_style_YYYYMMDD_HHMMSS.log`
- **Exit Code**: 0 for success, 1 for failure

### Files Checked
1. `src/main.py` - Contains health check endpoint
2. `src/api/v1/keyword_extraction.py` - Keyword extraction API endpoint
3. `src/models/keyword_extraction.py` - Data models
4. `src/services/keyword_extraction.py` - Service implementation
5. `src/services/keyword_extraction_v2.py` - Enhanced service version
6. `src/services/keyword_standardizer.py` - Keyword standardization

### Configuration
The project uses `.ruff.toml` for configuration. If not present, the script uses sensible defaults.

### Example Output
```
=====================================
Level 1: Code Style Check
=====================================
Project Root: /path/to/azure_container
Log File: /path/to/test/logs/level1_style_20250730_120000.log

✅ PASSED: src/main.py
✅ PASSED: src/api/v1/keyword_extraction.py
❌ FAILED: src/models/keyword_extraction.py
  E501 Line too long (92 > 88 characters)

Summary
=====================================
Total files checked: 6
Passed: 5
Failed: 1
Missing: 0
Success rate: 83.33%
```