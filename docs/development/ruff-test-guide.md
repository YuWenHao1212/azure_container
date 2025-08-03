# Ruff Test Custom Commands Guide

## 概述

本文檔提供了在 Azure Container 專案中使用 Ruff 進行程式碼品質檢查的自定義指令集。

## 基本指令

### 1. 檢查所有程式碼
```bash
# 檢查整個專案
ruff check .

# 只檢查 src 目錄
ruff check src/

# 檢查並顯示統計資訊
ruff check . --statistics
```

### 2. 自動修復
```bash
# 安全修復
ruff check . --fix

# 包含較不安全的修復
ruff check . --fix --unsafe-fixes
```

## 自定義指令集

### 1. 快速檢查 (Quick Check)
```bash
# 別名：ruff-quick
alias ruff-quick='ruff check src/ test/ --line-length=120'
```

### 2. 完整檢查 (Full Check)
```bash
# 別名：ruff-full
alias ruff-full='ruff check . --line-length=120 --statistics'
```

### 3. 測試檔案檢查 (Test Check)
```bash
# 別名：ruff-test
alias ruff-test='ruff check test/ --line-length=120'
```

### 4. 自動修復 (Auto Fix)
```bash
# 別名：ruff-fix
alias ruff-fix='ruff check . --fix --line-length=120'

# 別名：ruff-fix-all (包含 unsafe fixes)
alias ruff-fix-all='ruff check . --fix --unsafe-fixes --line-length=120'
```

### 5. Gap Analysis V2 測試檢查
```bash
# 別名：ruff-gap-v2
alias ruff-gap-v2='ruff check test/unit/test_gap_analysis_v2.py test/integration/test_gap_analysis_v2_api.py test/performance/test_gap_analysis_v2_performance.py test/e2e/test_gap_analysis_v2_e2e.py --line-length=120'
```

## Shell Script 版本

創建檔案 `scripts/ruff-test.sh`:

```bash
#!/bin/bash

# Ruff Test Script for Azure Container Project

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Main function
run_ruff_test() {
    local test_type=$1
    local line_length=120
    
    case $test_type in
        "quick")
            echo -e "${YELLOW}Running quick check on src/ and test/...${NC}"
            ruff check src/ test/ --line-length=$line_length
            print_status $? "Quick check completed"
            ;;
            
        "full")
            echo -e "${YELLOW}Running full project check...${NC}"
            ruff check . --line-length=$line_length --statistics
            print_status $? "Full check completed"
            ;;
            
        "test")
            echo -e "${YELLOW}Running test files check...${NC}"
            ruff check test/ --line-length=$line_length
            print_status $? "Test check completed"
            ;;
            
        "fix")
            echo -e "${YELLOW}Running auto-fix (safe)...${NC}"
            ruff check . --fix --line-length=$line_length
            print_status $? "Auto-fix completed"
            ;;
            
        "fix-all")
            echo -e "${YELLOW}Running auto-fix (including unsafe)...${NC}"
            ruff check . --fix --unsafe-fixes --line-length=$line_length
            print_status $? "Full auto-fix completed"
            ;;
            
        "gap-v2")
            echo -e "${YELLOW}Running Gap Analysis V2 tests check...${NC}"
            ruff check test/unit/test_gap_analysis_v2.py \
                      test/integration/test_gap_analysis_v2_api.py \
                      test/performance/test_gap_analysis_v2_performance.py \
                      test/e2e/test_gap_analysis_v2_e2e.py \
                      --line-length=$line_length
            print_status $? "Gap Analysis V2 tests check completed"
            ;;
            
        "pre-commit")
            echo -e "${YELLOW}Running pre-commit checks...${NC}"
            
            # Check src
            echo "Checking source files..."
            ruff check src/ --line-length=$line_length
            src_status=$?
            
            # Check tests
            echo "Checking test files..."
            ruff check test/ --line-length=$line_length
            test_status=$?
            
            # Summary
            if [ $src_status -eq 0 ] && [ $test_status -eq 0 ]; then
                echo -e "${GREEN}✓ All checks passed! Ready to commit.${NC}"
                exit 0
            else
                echo -e "${RED}✗ Some checks failed. Please fix before committing.${NC}"
                exit 1
            fi
            ;;
            
        *)
            echo "Usage: $0 {quick|full|test|fix|fix-all|gap-v2|pre-commit}"
            echo ""
            echo "Options:"
            echo "  quick      - Quick check on src/ and test/"
            echo "  full       - Full project check with statistics"
            echo "  test       - Check only test files"
            echo "  fix        - Auto-fix with safe fixes only"
            echo "  fix-all    - Auto-fix including unsafe fixes"
            echo "  gap-v2     - Check Gap Analysis V2 test files"
            echo "  pre-commit - Pre-commit check for src/ and test/"
            exit 1
            ;;
    esac
}

# Run the script
run_ruff_test "$1"
```

## Makefile 版本

在專案根目錄的 `Makefile` 中添加：

```makefile
# Ruff commands
.PHONY: ruff-quick ruff-full ruff-test ruff-fix ruff-fix-all ruff-gap-v2 ruff-pre-commit

RUFF_LINE_LENGTH := 120

ruff-quick:
	@echo "Running quick Ruff check..."
	@ruff check src/ test/ --line-length=$(RUFF_LINE_LENGTH)

ruff-full:
	@echo "Running full Ruff check..."
	@ruff check . --line-length=$(RUFF_LINE_LENGTH) --statistics

ruff-test:
	@echo "Running Ruff check on tests..."
	@ruff check test/ --line-length=$(RUFF_LINE_LENGTH)

ruff-fix:
	@echo "Running Ruff auto-fix (safe)..."
	@ruff check . --fix --line-length=$(RUFF_LINE_LENGTH)

ruff-fix-all:
	@echo "Running Ruff auto-fix (all)..."
	@ruff check . --fix --unsafe-fixes --line-length=$(RUFF_LINE_LENGTH)

ruff-gap-v2:
	@echo "Running Ruff check on Gap Analysis V2 tests..."
	@ruff check test/unit/test_gap_analysis_v2.py \
		test/integration/test_gap_analysis_v2_api.py \
		test/performance/test_gap_analysis_v2_performance.py \
		test/e2e/test_gap_analysis_v2_e2e.py \
		--line-length=$(RUFF_LINE_LENGTH)

ruff-pre-commit:
	@echo "Running pre-commit Ruff checks..."
	@ruff check src/ --line-length=$(RUFF_LINE_LENGTH) && \
	ruff check test/ --line-length=$(RUFF_LINE_LENGTH) && \
	echo "✓ All checks passed!"
```

## 使用方式

### 1. 使用別名（Alias）
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
source ~/.bashrc  # 或 source ~/.zshrc

# 使用
ruff-quick
ruff-test
ruff-fix
```

### 2. 使用 Shell Script
```bash
# 賦予執行權限
chmod +x scripts/ruff-test.sh

# 使用
./scripts/ruff-test.sh quick
./scripts/ruff-test.sh fix
./scripts/ruff-test.sh pre-commit
```

### 3. 使用 Makefile
```bash
# 快速檢查
make ruff-quick

# 完整檢查
make ruff-full

# 自動修復
make ruff-fix

# 檢查 Gap Analysis V2 測試
make ruff-gap-v2

# Pre-commit 檢查
make ruff-pre-commit
```

## Git Pre-commit Hook

創建 `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running Ruff checks before commit..."

# Run ruff check
if command -v ruff &> /dev/null; then
    ruff check src/ test/ --line-length=120
    if [ $? -ne 0 ]; then
        echo "❌ Ruff check failed. Please fix the issues before committing."
        exit 1
    fi
else
    echo "⚠️  Ruff is not installed. Skipping checks."
fi

echo "✅ Ruff checks passed!"
exit 0
```

## VS Code 整合

在 `.vscode/settings.json` 中添加：

```json
{
    "ruff.args": ["--line-length=120"],
    "ruff.lint.run": "onSave",
    "ruff.format.args": ["--line-length=120"],
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": true,
            "source.organizeImports.ruff": true
        }
    }
}
```

## 常見問題

### 1. 特定規則說明
- **E501**: 行太長（超過設定的字元限制）
- **F401**: 導入但未使用的模組
- **F821**: 未定義的名稱
- **RUF002**: 文檔字符串中的全角字符
- **W293**: 空行包含空格
- **S110**: try-except-pass（可能隱藏錯誤）
- **B007**: 未使用的迴圈控制變數
- **SIM117**: 多個 with 語句應合併

### 2. 忽略特定錯誤
```bash
# 忽略特定檔案的特定規則
ruff check src/main.py --ignore=E501,F401

# 在程式碼中忽略
x = 1  # noqa: F841
```

### 3. 專案特定配置
參考 `pyproject.toml` 中的 Ruff 配置部分。

## 相關連結
- [Ruff 官方文檔](https://docs.astral.sh/ruff/)
- [Ruff 規則列表](https://docs.astral.sh/ruff/rules/)
- [專案 pyproject.toml](../../pyproject.toml)