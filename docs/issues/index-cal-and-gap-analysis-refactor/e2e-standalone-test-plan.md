# E2E 測試單獨執行計劃

## 執行摘要
建立獨立的 E2E 測試執行環境，繞過全局 mock 設置，實現真正的端對端 API 測試。

## 1. What (什麼)

### 目標
建立一個獨立的 E2E 測試執行環境，使其能夠：
- 繞過全局 mock 設置
- 使用真實的 Azure OpenAI API
- 執行完整的端對端工作流程測試
- 驗證生產環境的實際行為

### 範圍
- Gap Analysis V2 的 E2E 測試（3 個測試案例）
- 未來可擴展至其他 API 的 E2E 測試

## 2. Why (為什麼)

### 現況問題
1. **全局 Mock 衝突**
   - `test/conftest.py` 有 `autouse=True` 的 fixture
   - 自動 mock 所有 OpenAI 和 HTTP 客戶端
   - 導致 E2E 測試無法使用真實 API

2. **測試完整性**
   - E2E 測試需要驗證真實的 API 整合
   - Mock 無法發現實際的整合問題
   - 需要測試真實的網路延遲和錯誤處理

### 預期效益
- 提高測試信心度
- 及早發現整合問題
- 驗證生產環境配置
- 確保 API 合約正確性

## 3. Where (在哪裡)

### 新建檔案結構
```
test/
├── e2e_standalone/                    # 獨立的 E2E 測試目錄
│   ├── __init__.py                    # 空檔案，標記為 Python 包
│   ├── conftest.py                    # 無 mock 的測試配置
│   ├── run_e2e_tests.py              # Python 執行腳本
│   └── test_gap_analysis_v2_e2e.py   # 複製的測試檔案（移除 skip）
│
└── scripts/
    └── run_e2e_standalone.sh          # Shell 執行腳本
```

### 與現有結構的關係
- 獨立於現有的 `test/e2e/` 目錄
- 不受 `test/conftest.py` 影響
- 可以共享 `test/fixtures/` 的測試數據

## 4. When (何時)

### 執行時機
1. **開發階段**
   - 功能開發完成後的驗證
   - API 整合變更後的測試

2. **CI/CD Pipeline**
   - 作為獨立的測試階段
   - 在單元測試和整合測試之後執行
   - 部署前的最終驗證

3. **發布流程**
   - 主要版本發布前
   - API 合約變更時
   - 生產環境配置更新後

### 執行頻率
- 開發時：按需執行
- CI/CD：每次 PR 或合併到主分支
- 定期：每日執行一次完整測試

## 5. Who (誰)

### 相關人員
1. **開發者**
   - 執行測試驗證功能
   - 診斷整合問題
   - 維護測試案例

2. **DevOps 團隊**
   - 配置 CI/CD pipeline
   - 管理測試環境
   - 監控測試執行

3. **QA 團隊**
   - 驗證測試覆蓋率
   - 確認測試品質
   - 回報測試結果

## 6. How (如何)

### 步驟 1：建立目錄結構
```bash
# 建立獨立測試目錄
mkdir -p test/e2e_standalone
touch test/e2e_standalone/__init__.py
```

### 步驟 2：建立無 mock 的 conftest.py
```python
# test/e2e_standalone/conftest.py
"""
E2E 測試配置 - 無 mock，使用真實 API
"""
import os
import pytest
from dotenv import load_dotenv

# 載入真實環境變數
load_dotenv(override=True)

@pytest.fixture(autouse=True)
def setup_e2e_environment():
    """設置 E2E 測試環境"""
    # 確保使用 V2 實作
    os.environ['USE_V2_IMPLEMENTATION'] = 'true'
    os.environ['ENABLE_PARTIAL_RESULTS'] = 'true'
    os.environ['LIGHTWEIGHT_MONITORING'] = 'true'
    os.environ['MONITORING_ENABLED'] = 'true'
    os.environ['ERROR_CAPTURE_ENABLED'] = 'true'
    
    # 禁用資源池以簡化測試
    os.environ['RESOURCE_POOL_ENABLED'] = 'false'
    
    # 標記為真實 E2E 測試
    os.environ['REAL_E2E_TEST'] = 'true'
    
    yield
    
    # 清理環境變數
    if 'REAL_E2E_TEST' in os.environ:
        del os.environ['REAL_E2E_TEST']

@pytest.fixture
def skip_if_no_api_keys():
    """檢查必要的 API 密鑰"""
    required_keys = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'EMBEDDING_API_KEY'
    ]
    
    missing_keys = [key for key in required_keys if not os.environ.get(key)]
    if missing_keys:
        pytest.skip(f"E2E tests require real API keys. Missing: {', '.join(missing_keys)}")
```

### 步驟 3：建立 Python 執行腳本
```python
#!/usr/bin/env python
# test/e2e_standalone/run_e2e_tests.py
"""
獨立執行 E2E 測試的腳本
繞過根目錄的 conftest.py 和全局 mock
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """執行獨立的 E2E 測試"""
    # 取得當前腳本目錄
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # 設置環境變數
    env = os.environ.copy()
    
    # 設置 PYTHONPATH，只包含 src 目錄
    env['PYTHONPATH'] = str(project_root / 'src')
    
    # 設置測試標記
    env['RUNNING_STANDALONE_E2E'] = 'true'
    
    # 建構 pytest 命令
    cmd = [
        sys.executable, '-m', 'pytest',
        'test_gap_analysis_v2_e2e.py',
        '-v',  # 詳細輸出
        '-s',  # 顯示 print 輸出
        '--tb=short',  # 簡短的錯誤追蹤
        '--confcutdir=.',  # 限制 conftest.py 搜索範圍到當前目錄
        '--no-cov',  # 禁用覆蓋率
        '-p', 'no:warnings'  # 減少警告輸出
    ]
    
    # 添加任何額外的命令行參數
    cmd.extend(sys.argv[1:])
    
    print("🚀 Running E2E Tests in Standalone Mode")
    print(f"Working directory: {script_dir}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    # 執行測試
    result = subprocess.run(cmd, env=env, cwd=str(script_dir))
    
    # 返回測試結果
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
```

### 步驟 4：建立 Shell 執行腳本
```bash
#!/bin/bash
# test/scripts/run_e2e_standalone.sh

set -e  # 遇到錯誤立即退出

echo "==============================================="
echo "E2E Standalone Test Runner"
echo "==============================================="
echo "This bypasses global mocks and uses real API calls"
echo "Timestamp: $(date)"
echo

# 取得腳本目錄
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 切換到專案根目錄
cd "$PROJECT_ROOT"

# 檢查環境變數
echo "Checking environment..."
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

# 建立 e2e_standalone 目錄（如果不存在）
if [ ! -d "test/e2e_standalone" ]; then
    echo "Creating e2e_standalone directory..."
    mkdir -p test/e2e_standalone
    touch test/e2e_standalone/__init__.py
fi

# 複製測試檔案（如果需要）
if [ ! -f "test/e2e_standalone/test_gap_analysis_v2_e2e.py" ]; then
    echo "Copying E2E test file..."
    cp test/e2e/test_gap_analysis_v2_e2e.py test/e2e_standalone/
    
    # 移除 skip 標記
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' '/pytestmark = pytest.mark.skip/d' test/e2e_standalone/test_gap_analysis_v2_e2e.py
    else
        # Linux
        sed -i '/pytestmark = pytest.mark.skip/d' test/e2e_standalone/test_gap_analysis_v2_e2e.py
    fi
fi

# 執行測試
echo "Running E2E tests..."
cd test/e2e_standalone

# 使用 Python 腳本執行（如果存在）
if [ -f "run_e2e_tests.py" ]; then
    python run_e2e_tests.py "$@"
else
    # 直接使用 pytest
    python -m pytest test_gap_analysis_v2_e2e.py -v -s --confcutdir=. "$@"
fi

# 記錄結果
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo
    echo "✅ E2E tests passed successfully!"
else
    echo
    echo "❌ E2E tests failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
```

### 步驟 5：整合到現有測試流程

#### 5.1 修改 run_gap_analysis_v2_tests.sh
```bash
# 在 parse_arguments 函數中添加
--e2e-standalone)
    E2E_STANDALONE=true
    STAGE="e2e"
    shift
    ;;

# 在 E2E 測試部分
if [[ "$STAGE" == "e2e" || "$STAGE" == "all" ]]; then
    if [[ "$E2E_STANDALONE" == "true" ]]; then
        # 使用獨立執行方式
        ./test/scripts/run_e2e_standalone.sh
        E2E_EXIT_CODE=$?
    else
        # 原有的執行方式（會被 skip）
        run_e2e_tests
    fi
fi
```

#### 5.2 使用方式
```bash
# 執行獨立的 E2E 測試
./test/scripts/run_e2e_standalone.sh

# 或透過主測試腳本
./test/scripts/run_gap_analysis_v2_tests.sh --e2e-standalone

# 執行特定的測試
./test/scripts/run_e2e_standalone.sh -k "test_complete_workflow"
```

## 技術考量

### 1. Mock 隔離
- 不載入根目錄的 `conftest.py`
- 使用 `--confcutdir` 限制 pytest 的配置搜索範圍
- 設置乾淨的 PYTHONPATH

### 2. 環境變數管理
- 載入 `.env` 檔案以取得真實 API 配置
- 設置必要的功能開關
- 標記為獨立 E2E 測試

### 3. 錯誤處理
- 檢查必要的 API 密鑰
- 提供清晰的錯誤訊息
- 支援 pytest 的各種參數

## 風險與緩解措施

### 1. API 成本
- **風險**：真實 API 調用會產生費用
- **緩解**：
  - 限制測試執行頻率
  - 使用測試專用的 API 配額
  - 監控 API 使用量

### 2. API 配額限制
- **風險**：可能觸發 rate limiting
- **緩解**：
  - 在測試之間添加延遲
  - 使用重試機制
  - 錯開執行時間

### 3. 環境隔離
- **風險**：測試可能影響生產數據
- **緩解**：
  - 使用專用的測試環境
  - 確保 API endpoint 正確
  - 實施資料清理機制

### 4. 密鑰安全
- **風險**：API 密鑰洩露
- **緩解**：
  - 使用環境變數
  - 不將密鑰提交到版本控制
  - 定期輪換密鑰

## 成功指標

1. **功能性**
   - [ ] E2E 測試可以成功執行
   - [ ] 使用真實的 Azure OpenAI API
   - [ ] 所有測試案例通過

2. **可維護性**
   - [ ] 測試獨立於其他測試類型
   - [ ] 易於添加新的 E2E 測試
   - [ ] 清晰的錯誤訊息

3. **整合性**
   - [ ] 可整合到 CI/CD pipeline
   - [ ] 支援本地和遠端執行
   - [ ] 提供執行報告

## 下一步行動

1. **立即執行**
   - 建立目錄結構
   - 實作基本腳本
   - 執行初步測試

2. **短期改進**
   - 添加更多 E2E 測試案例
   - 優化執行時間
   - 改進錯誤報告

3. **長期規劃**
   - 整合到 CI/CD
   - 建立 E2E 測試最佳實踐
   - 擴展到其他 API 測試

## 結論

透過建立獨立的 E2E 測試執行環境，我們可以：
- 真正驗證 API 的端對端功能
- 避免 mock 帶來的假陽性結果
- 提高對生產環境的信心

這個方案在不影響現有測試架構的前提下，提供了一個實用的 E2E 測試解決方案。