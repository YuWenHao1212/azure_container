# Azure Container API 測試環境設置指南

## 測試環境配置

### 1. 安裝測試依賴

#### 方法一：使用測試套件腳本（推薦）
測試套件腳本會自動處理所有依賴安裝：
```bash
./test/scripts/run_complete_test_suite.sh --stage unit
```

#### 方法二：手動安裝依賴
如果需要直接使用 pytest，請先安裝所有必要的依賴：

```bash
# 安裝主要依賴
pip install -r requirements.txt

# 安裝測試專用依賴
pip install -r test/requirements.txt
```

### 2. 環境變數配置

在執行測試前，確保設定必要的環境變數：

```bash
# 基本測試環境變數
export CONTAINER_APP_API_KEY="test-api-key"
export USE_V2_IMPLEMENTATION="true"
export MONITORING_ENABLED="false"
export LIGHTWEIGHT_MONITORING="false"
export ERROR_CAPTURE_ENABLED="false"

# 或使用 .env 檔案
cp .env.example .env.test
# 編輯 .env.test 填入測試配置
```

### 3. 執行測試

#### 使用測試套件腳本（推薦）
```bash
# 執行所有測試
./test/scripts/run_complete_test_suite.sh

# 執行特定階段
./test/scripts/run_complete_test_suite.sh --stage unit
./test/scripts/run_complete_test_suite.sh --stage integration
./test/scripts/run_complete_test_suite.sh --stage performance
./test/scripts/run_complete_test_suite.sh --stage e2e
```

#### 直接使用 pytest
```bash
# 執行單元測試
pytest test/unit/test_gap_analysis_v2.py -v

# 執行整合測試
pytest test/integration/test_gap_analysis_v2_integration_complete.py -v

# 執行效能測試（背景執行）
pytest test/performance/test_gap_analysis_v2_performance.py -v &

# 執行 E2E 測試
pytest test/e2e/test_gap_analysis_v2_e2e.py -v
```

## 常見問題解決

### 1. ModuleNotFoundError: No module named 'openai'
**原因**：測試依賴未完整安裝
**解決**：
```bash
pip install -r test/requirements.txt
# 或
pip install openai>=1.0.0
```

### 2. 401 Unauthorized 錯誤
**原因**：未設定 API Key
**解決**：
```bash
export CONTAINER_APP_API_KEY="test-api-key"
```

### 3. KeyError: 'invalid_test_data'
**原因**：測試資料路徑錯誤（已修復）
**解決**：已更新程式碼，使用正確的資料路徑

### 4. 測試超時
**原因**：效能測試需要較長時間
**解決**：使用背景執行
```bash
pytest test/performance/ -v &
```

## 測試資料結構

測試資料位於 `test/fixtures/gap_analysis_v2/test_data_v2.json`，結構如下：
```json
{
  "valid_test_data": {
    "standard_requests": [...],
    "boundary_test_data": {...},
    "invalid_test_data": {...},
    "large_documents": {...},
    "multilingual_content": {...}
  }
}
```

## 開發建議

1. **優先使用測試套件腳本**：自動處理環境配置和依賴
2. **維護測試隔離**：每個測試應該獨立執行
3. **使用 Mock**：避免實際調用外部 API
4. **遵循命名規範**：測試函數使用 `test_API_GAP_XXX_YY` 格式

## 測試覆蓋目標

- 單元測試：> 90%
- 整合測試：> 85%
- 整體覆蓋：> 88%