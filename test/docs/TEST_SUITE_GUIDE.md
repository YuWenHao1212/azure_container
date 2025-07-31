# 完整測試套件執行指南

## 🚀 快速開始

### 執行測試套件

```bash
cd /Users/yuwenhao/Documents/GitHub/azure_container

# 前景執行（可以看到即時輸出）
./test/scripts/run_complete_test_suite.sh

# 背景執行（推薦）
./test/scripts/run_complete_test_suite.sh --background
# 或
./test/scripts/run_complete_test_suite.sh -b
```

### 背景執行監控

當使用背景執行時，會顯示：
```
Starting test suite in background...
Test report will be saved to: /Users/yuwenhao/Documents/GitHub/azure_container/test/reports/test_report_20250731_1430.txt
Test suite running in background (PID: 12345)
Monitor progress with: tail -f /tmp/test_suite_20250731_1430.log
```

監控執行進度：
```bash
# 即時查看測試進度
tail -f /tmp/test_suite_20250731_1430.log

# 檢查測試是否還在執行
ps aux | grep 12345
```

## 📊 測試涵蓋範圍

測試套件包含以下測試：

### 1. 單元測試
- **Health Check** (`test/unit/test_health.py`)
  - 健康檢查端點測試
  - API 基本功能驗證

- **Keyword Extraction** (`test/unit/test_keyword_extraction.py`)
  - 關鍵字提取核心功能
  - 輸入驗證測試

- **Keyword Extraction Extended** (`test/unit/test_keyword_extraction_extended.py`)
  - 進階關鍵字提取功能
  - 邊界條件測試

- **Language Detection** (`test/unit/test_language_detection.py`)
  - 語言檢測功能（26個測試）
  - 中英混合語言處理

- **Prompt Manager** (`test/unit/test_prompt_manager.py`)
  - Prompt 管理器測試（24個測試）
  - 多語言 prompt 支援

### 2. 整合測試
- **Keyword Extraction Language Integration** (`test/integration/test_keyword_extraction_language.py`)
  - 語言檢測與關鍵字提取整合（14個測試）
  - 端到端測試

### 3. 效能測試
- **Keyword Extraction Performance** (`test/performance/test_keyword_extraction_performance_simple.py`)
  - API 回應時間測試
  - 並發負載測試
  - SLA 合規性驗證

## 📁 測試報告

測試完成後會生成兩種報告：

### 1. 文字報告
路徑：`/Users/yuwenhao/Documents/GitHub/azure_container/test/reports/test_report_YYYYMMDD_HHMM.txt`

範例內容：
```
======================================
Complete Test Suite Report
======================================
Generated: Thu Jul 31 14:30:00 CST 2025
Project: Azure Container API
Environment: Development
======================================

Running unit_health...
  Status: PASSED
  Duration: 2s
  Results: 9 passed in 2.13s

Running unit_keyword_extraction...
  Status: PASSED
  Duration: 5s
  Results: 45 passed in 5.24s

[更多測試結果...]

======================================
Test Summary
======================================
Total Test Suites: 7
Passed: 7
Failed: 0
Success Rate: 100%

Individual Test Statistics:
Total Tests Run: 132
Tests Passed: 132
Tests Failed: 0
```

### 2. JSON 報告
路徑：`/Users/yuwenhao/Documents/GitHub/azure_container/test/reports/test_report_YYYYMMDD_HHMM.json`

包含結構化的測試結果，方便程式化處理。

## 🔍 查看測試結果

```bash
# 查看最新的文字報告
ls -la test/reports/*.txt | tail -1
cat test/reports/test_report_20250731_1430.txt

# 查看最新的 JSON 報告
ls -la test/reports/*.json | tail -1
cat test/reports/test_report_20250731_1430.json | jq '.'

# 查看特定測試套件的詳細日誌
cat /tmp/unit_keyword_extraction_output.log
```

## ⚠️ 注意事項

1. **環境要求**
   - 確保已安裝所有依賴：`pip install -r requirements.txt`
   - 需要有效的 `.env` 檔案包含 API keys

2. **Port 8000**
   - 測試會自動清理 port 8000
   - 如有其他服務使用此 port，請先停止

3. **背景執行**
   - 使用 `nohup` 確保測試在關閉 terminal 後繼續執行
   - 測試完成後會自動停止

4. **測試時間**
   - 完整測試套件預計執行時間：5-10 分鐘
   - 效能測試可能因網路狀況而有所不同

## 🛠️ 故障排除

如果測試失敗：

1. **檢查 API 服務器日誌**
   ```bash
   cat /tmp/api_server.log
   ```

2. **檢查個別測試日誌**
   ```bash
   ls -la /tmp/*_output.log
   cat /tmp/unit_keyword_extraction_output.log
   ```

3. **確認環境變數**
   ```bash
   cat .env | grep API_KEY
   ```

4. **手動測試 API**
   ```bash
   curl http://localhost:8000/health
   ```