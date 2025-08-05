# Ruff Test Commands

## Quick Commands
```bash
# Check all code
ruff check . --line-length=120

# Check src directory only
ruff check src/ --line-length=120

# Check with auto-fix
ruff check . --fix --line-length=120

# Check tests only
ruff check test/ --line-length=120

# Check src and test only
ruff check src/ test/ --line-length=120

# Check Gap Analysis V2 tests
ruff check test/unit/test_gap_analysis_v2.py test/integration/test_gap_analysis_v2_api.py test/performance/test_gap_analysis_v2_performance.py test/e2e/test_gap_analysis_v2_e2e.py --line-length=120
```

## Shell Script
```bash
# Run ruff test script (if available)
./scripts/ruff-test.sh {quick|full|test|fix|fix-all|gap-v2|pre-commit}
```

## Makefile Commands
```bash
make ruff-quick    # Quick check src/ and test/
make ruff-full     # Full project check
make ruff-test     # Test files only
make ruff-fix      # Auto-fix (safe)
make ruff-fix-all  # Auto-fix (all)
make ruff-gap-v2   # Gap Analysis V2 tests
```

## Common Fixes
```bash
# Fix trailing whitespace
ruff check . --fix --select W293

# Fix import sorting
ruff check . --fix --select I

# Show statistics
ruff check . --statistics
```