# 完整測試套件執行指南

## 📋 文檔資訊
- **版本**: 2.0.0
- **最後更新**: 2025-08-01
- **基於**: TEST_SPEC.md v2.2.0
- **測試案例總數**: 113個

## 🚀 快速開始

### 執行測試套件

```bash
cd /Users/yuwenhao/Documents/GitHub/azure_container

# 執行完整測試套件（前景執行）
./test/scripts/run_complete_test_suite.sh

# 僅執行效能測試
./test/scripts/run_complete_test_suite.sh --performance
# 或
./test/scripts/run_complete_test_suite.sh -p

# 查看幫助訊息
./test/scripts/run_complete_test_suite.sh --help

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

測試套件包含以下測試（共113個測試案例）：

### 1. 單元測試（96個）

#### 健康檢查模組 (9個測試)
- **Health Check** (`test/unit/test_health.py`)
  - 健康檢查端點測試
  - API 基本功能驗證
  - 版本資訊與環境驗證

#### 關鍵字提取模組 (79個測試)
- **Keyword Extraction Core** (`test/unit/test_keyword_extraction.py` - 11個測試)
  - 關鍵字提取核心功能
  - 輸入驗證測試
  - 錯誤處理測試

- **Language Detection** (`test/unit/test_language_detection.py` - 29個測試)
  - 語言檢測功能（英文、繁體中文、簡體中文等）
  - 中英混合語言處理（20%閾值規則）
  - 不支援語言的拒絕處理

- **Prompt Manager** (`test/unit/test_prompt_manager.py` - 24個測試)
  - Prompt 管理器測試
  - 多語言 prompt 支援（英文、繁體中文）
  - Prompt 版本管理與快取

- **Keyword Extraction Extended** (`test/unit/test_keyword_extraction_extended.py` - 16個測試)
  - 進階關鍵字提取功能
  - 邊界條件測試
  - 服務資源清理測試

#### LLM Factory 模組 (8個測試)
- **LLM Factory Deployment Mapping** (`test/unit/test_llm_factory_deployment_mapping.py`)
  - GPT-4.1 和 GPT-4.1 Mini 部署映射
  - 模型容錯回退機制
  - Smart Client 參數處理

### 2. 整合測試（16個）

#### 健康檢查整合 (1個測試)
- **Health Check Integration** (`test/integration/test_health_integration.py`)
  - 健康檢查含依賴服務狀態（已實作）

#### 關鍵字提取整合 (15個測試)
- **Keyword Extraction Language Integration** (`test/integration/test_keyword_extraction_language.py` - 14個測試)
  - 語言檢測與關鍵字提取整合
  - 端到端測試
  - 不支援語言的錯誤回應驗證

- **Azure OpenAI Integration** (`test/integration/test_azure_openai_integration.py` - 1個測試)
  - Azure OpenAI 服務整合測試（已實作）

### 3. 效能測試（1個）
- **Keyword Extraction Performance** (`test/performance/test_keyword_extraction_performance_simple.py`)
  - API 回應時間測試（< 3秒）
  - 並發負載測試
  - SLA 合規性驗證

## 📈 測試統計摘要

| 模組 | 單元測試 | 整合測試 | 效能測試 | 總計 |
|------|----------|----------|----------|------|
| 健康檢查 | 9 | 1 | 0 | 10 |
| 關鍵字提取 | 79 | 15 | 1 | 95 |
| LLM Factory | 8 | 0 | 0 | 8 |
| **總計** | **96** | **16** | **1** | **113**

## 📁 測試報告

測試執行時會即時顯示詳細的測試統計表格，測試完成後會生成兩種報告：

### 即時測試統計表格

執行測試時會顯示詳細的模組統計：

```
=== 詳細測試統計 ===

| 模組              | 單元測試 (通過/失敗) | 整合測試 (通過/失敗) | 效能測試 (通過/失敗) | 總計 (通過/失敗) |
|-------------------|---------------------|---------------------|---------------------|------------------|
| 健康檢查          | 9/0                 | 1/0                 | 0/0                 | 10/0             |
| 關鍵字提取        | 27/0                | 1/0                 | 1/0                 | 29/0             |
| 語言檢測          | 29/0                | 14/0                | 0/0                 | 43/0             |
| Prompt管理        | 24/0                | 0/0                 | 0/0                 | 24/0             |
| LLM Factory       | 8/0                 | 0/0                 | 0/0                 | 8/0              |
|-------------------|---------------------|---------------------|---------------------|------------------|
| **總計**          | **96/0**            | **16/0**            | **1/0**             | **113/0**        |

效能測試詳情:
------------------------------------------------------------
測試案例             | 平均回應時間 | SLA 狀態
---------------------|--------------|----------
Small JD (200 chars) | 2145.23 ms   | ✅ PASS
Medium JD (500 chars)| 2456.78 ms   | ✅ PASS
Large JD (1000+ chars)| 2789.12 ms   | ✅ PASS
---------------------|--------------|----------
整體平均             | 2463.71 ms   | ✅ PASS

SLA 目標: < 3000ms
```

### 1. 文字報告
路徑：`/Users/yuwenhao/Documents/GitHub/azure_container/test/reports/test_report_YYYYMMDD_HHMM.txt`

範例內容：
```
======================================
Complete Test Suite Report
======================================
Generated: Thu Aug 01 10:30:00 CST 2025
Project: Azure Container API
Environment: Development
======================================

Running unit_health...
  Status: PASSED
  Duration: 2s
  Results: 9 passed in 2.13s

Running unit_keyword_extraction...
  Status: PASSED
  Duration: 8s
  Results: 11 passed in 8.24s

Running unit_language_detection...
  Status: PASSED
  Duration: 5s
  Results: 29 passed in 5.12s

Running unit_prompt_manager...
  Status: PASSED
  Duration: 3s
  Results: 24 passed in 3.45s

Running unit_keyword_extraction_extended...
  Status: PASSED
  Duration: 6s
  Results: 16 passed in 6.78s

Running unit_llm_factory_deployment_mapping...
  Status: PASSED
  Duration: 2s
  Results: 8 passed in 2.34s

Running integration_health...
  Status: PASSED
  Duration: 3s
  Results: 1 passed in 3.01s

Running integration_keyword_extraction_language...
  Status: PASSED
  Duration: 12s
  Results: 14 passed in 12.56s

Running integration_azure_openai...
  Status: PASSED
  Duration: 5s
  Results: 1 passed in 5.23s

Running performance_keyword_extraction...
  Status: PASSED
  Duration: 30s
  Results: 1 passed in 30.45s

======================================
Test Summary
======================================
Total Test Suites: 10
Passed: 10
Failed: 0
Success Rate: 100%

Individual Test Statistics:
Total Tests Run: 113
Tests Passed: 113
Tests Failed: 0

Test Coverage by Module:
- Health Check: 10/10 (100%)
- Keyword Extraction: 95/95 (100%)
- LLM Factory: 8/8 (100%)
```

### 2. JSON 報告
路徑：`/Users/yuwenhao/Documents/GitHub/azure_container/test/logs/test_report_YYYYMMDD_HHMM.json`

包含結構化的測試結果，方便程式化處理。

## 🔍 查看測試結果

```bash
# 查看最新的文字報告
ls -la test/logs/*.txt | tail -1
cat test/logs/test_report_20250801_1030.txt

# 查看最新的 JSON 報告
ls -la test/logs/*.json | tail -1
cat test/logs/test_report_20250801_1030.json | jq '.'

# 查看特定測試套件的詳細日誌
cat /tmp/unit_keyword_extraction_output.log
cat /tmp/unit_language_detection_output.log
cat /tmp/unit_llm_factory_deployment_mapping_output.log
```

## 🧪 個別測試執行

除了完整測試套件，也可以執行個別測試：

```bash
# 執行特定測試文件
pytest test/unit/test_health.py -v
pytest test/unit/test_keyword_extraction.py -v
pytest test/unit/test_language_detection.py -v
pytest test/unit/test_prompt_manager.py -v
pytest test/unit/test_keyword_extraction_extended.py -v
pytest test/unit/test_llm_factory_deployment_mapping.py -v

# 執行特定測試案例
pytest test/unit/test_keyword_extraction.py::test_extract_keywords_success -v

# 執行整合測試
pytest test/integration/ -v

# 執行效能測試
pytest test/performance/test_keyword_extraction_performance_simple.py -v
```

## 🚀 效能測試專用模式

當只需要執行效能測試時，可使用 `--performance` 參數：

```bash
# 快速執行效能測試（約 1-2 分鐘）
./test/scripts/run_complete_test_suite.sh --performance

# 效能測試會：
# 1. 自動啟動 API 服務器
# 2. 執行效能測試套件
# 3. 顯示詳細的效能統計
# 4. 自動清理資源
```

效能測試結果範例：
```
=== Performance Test Only ===
Timestamp: Thu Aug 01 10:30:00 CST 2025

Starting API Server
  ✓ Server started

Running Performance Test
  ✓ Performance test passed

Results:
  Small JD (200 chars) - Average: 2145.23 ms
  Medium JD (500 chars) - Average: 2456.78 ms
  Large JD (1000+ chars) - Average: 2789.12 ms
  Overall Average Response Time: 2463.71 ms
  SLA Status: ✅ All tests passed (< 3000ms)
```

## ⚠️ 注意事項

1. **環境要求**
   - 確保已安裝所有依賴：`pip install -r requirements.txt`
   - 需要有效的 `.env` 檔案包含 API keys
   - Python 版本需求：3.8+

2. **Port 8000**
   - 測試會自動清理 port 8000
   - 如有其他服務使用此 port，請先停止

3. **背景執行**
   - 使用 `nohup` 確保測試在關閉 terminal 後繼續執行
   - 測試完成後會自動停止

4. **測試時間**
   - 完整測試套件預計執行時間：10-15 分鐘
   - 效能測試可能因網路狀況而有所不同
   - 單元測試：約 3-5 分鐘
   - 整合測試：約 2-3 分鐘
   - 效能測試：約 5-7 分鐘

5. **測試文件名稱**
   - 效能測試實際執行文件：`test_keyword_extraction_performance_simple.py`
   - 注意：另有 `test_keyword_extraction_performance.py` 但未被執行腳本使用

6. **報告清理機制**
   - 測試腳本會自動保留最新的 6 份報告
   - 成功執行時會清理所有臨時檔案
   - 失敗時會保留錯誤日誌供除錯使用

7. **Python 版本**
   - 腳本預設使用 pyenv 設定 Python 3.11.8
   - 確保系統已安裝 pyenv 或手動調整 Python 版本

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
   cat /tmp/unit_language_detection_output.log
   cat /tmp/unit_prompt_manager_output.log
   cat /tmp/unit_llm_factory_deployment_mapping_output.log
   ```

3. **確認環境變數**
   ```bash
   cat .env | grep -E "(API_KEY|DEPLOYMENT|ENDPOINT)"
   ```

4. **手動測試 API**
   ```bash
   curl http://localhost:8000/health
   ```

5. **常見問題**
   - **Port 8000 被佔用**：使用 `lsof -i :8000` 找出佔用程序
   - **API Key 無效**：確認 `.env` 中的 Azure OpenAI 配置正確
   - **測試超時**：檢查網路連接和 Azure 服務狀態

## 📋 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2025-07-30 | 初始版本 |
| 2.0.0 | 2025-08-01 | 更新至 113 個測試案例，新增 LLM Factory 測試 |
| 2.1.0 | 2025-08-01 | 新增 --performance 選項說明、詳細測試統計表格、報告清理機制 |

---

**基於**: TEST_SPEC.md v2.2.0  
**維護者**: 測試團隊