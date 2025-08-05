# Index Calculation V2 Testing Guide

本指南說明 Index Calculation V2 測試架構的使用方式，包含 Mock 與 Real API 測試的分離策略。

## 概述

Index Calculation V2 測試分為兩個主要腳本：

1. **Mock Tests**: `run_index_calculation_unit_integration.sh` - 使用 mock 服務的單元與整合測試
2. **Real API Tests**: `run_index_calculation_real_api_perf_e2e.sh` - 使用真實 Azure API 的效能與端到端測試

## 測試策略分離

### Mock Tests (無需 Azure API)
- **測試類型**: Unit Tests (10個) + Integration Tests (14個) = 總共24個測試
- **執行時間**: ~3-5分鐘
- **用途**: 快速驗證功能邏輯、CI/CD 流水線
- **優點**: 無外部依賴、執行快速、成本為零

### Real API Tests (需要 Azure API)
- **測試類型**: Performance Tests (3個) + E2E Tests (2個) = 總共5個測試
- **執行時間**: ~5-8分鐘
- **用途**: 真實環境驗證、效能基準測試
- **注意**: 需要 Azure OpenAI API 金鑰、會產生 API 成本

## 使用指南

### 1. Mock Tests 腳本

```bash
# 執行所有 mock 測試 (24個測試)
./test/scripts/run_index_calculation_unit_integration.sh

# 只執行單元測試 (10個測試)
./test/scripts/run_index_calculation_unit_integration.sh --stage unit

# 只執行整合測試 (14個測試)
./test/scripts/run_index_calculation_unit_integration.sh --stage integration

# 詳細輸出模式
./test/scripts/run_index_calculation_unit_integration.sh --verbose
```

### 2. Real API Tests 腳本

```bash
# 執行所有真實 API 測試 (5個測試)
./test/scripts/run_index_calculation_real_api_perf_e2e.sh

# 只執行效能測試 (3個測試)
./test/scripts/run_index_calculation_real_api_perf_e2e.sh --stage performance

# 只執行端到端測試 (2個測試)
./test/scripts/run_index_calculation_real_api_perf_e2e.sh --stage e2e

# 背景執行模式 (效能測試建議使用)
./test/scripts/run_index_calculation_real_api_perf_e2e.sh --stage performance &
```

### 3. 整合到主測試套件

```bash
# 透過主測試套件執行 Index Calculation 測試
./test/scripts/run_complete_test_suite.sh --include-index-calculation

# 只執行 mock 測試部分
./test/scripts/run_complete_test_suite.sh --stage unit --stage integration

# 包含效能測試 (會執行真實 API 測試)
./test/scripts/run_complete_test_suite.sh --include-performance
```

## 測試 ID 對照表

### Unit Tests (API-IC-001-UT ~ API-IC-010-UT)
| Test ID | 測試名稱 | 優先級 | 說明 |
|---------|----------|--------|------|
| API-IC-001-UT | test_service_initialization | P0 | 服務初始化測試 |
| API-IC-002-UT | test_cache_key_generation | P0 | 快取鍵生成測試 |
| API-IC-003-UT | test_cache_ttl_expiration | P1 | 快取TTL過期測試 |
| API-IC-004-UT | test_cache_lru_eviction | P1 | 快取LRU淘汰測試 |
| API-IC-005-UT | test_similarity_calculation_integration | P0 | 相似度計算整合測試 |
| API-IC-006-UT | test_sigmoid_transform_parameters | P0 | Sigmoid轉換參數測試 |
| API-IC-007-UT | test_keyword_coverage_analysis | P0 | 關鍵字覆蓋分析測試 |
| API-IC-008-UT | test_tinymce_html_cleaning | P1 | TinyMCE HTML清理測試 |
| API-IC-009-UT | test_taskgroup_parallel_execution | P0 | TaskGroup並行執行測試 |
| API-IC-010-UT | test_taskgroup_error_handling | P0 | TaskGroup錯誤處理測試 |

### Integration Tests (API-IC-101-IT ~ API-IC-114-IT)
| Test ID | 測試名稱 | 優先級 | 說明 |
|---------|----------|--------|------|
| API-IC-101-IT | test_api_endpoint_basic_functionality | P0 | API端點基本功能測試 |
| API-IC-102-IT | test_cache_behavior_integration | P0 | 快取行為整合測試 |
| API-IC-103-IT | test_input_validation | P0 | 輸入驗證測試 |
| API-IC-104-IT | test_azure_openai_rate_limit_error | P0 | Azure OpenAI 速率限制錯誤處理測試 |
| API-IC-105-IT | test_azure_openai_auth_error | P0 | Azure OpenAI 認證錯誤處理測試 |
| API-IC-106-IT | test_azure_openai_server_error | P0 | Azure OpenAI 伺服器錯誤處理測試 |
| API-IC-107-IT | test_concurrent_request_handling | P1 | 並發請求處理測試 |
| API-IC-108-IT | test_large_document_handling | P1 | 大文檔處理測試 |
| API-IC-109-IT | test_service_stats_endpoint | P2 | 服務統計端點測試 |
| API-IC-110-IT | test_cross_language_content | P1 | 跨語言內容測試 |
| API-IC-111-IT | test_high_concurrency_functionality | P0 | 高並發功能測試（應用層） |
| API-IC-112-IT | test_memory_management | P1 | 記憶體管理測試（無洩漏） |
| API-IC-113-IT | test_cache_lru_functionality | P1 | 快取LRU功能測試 |
| API-IC-114-IT | test_error_recovery_mechanism | P0 | 錯誤恢復機制測試（重試邏輯） |

### Performance Tests (API-IC-201-PT ~ API-IC-203-PT)
| Test ID | 測試名稱 | 執行時間 | 說明 |
|---------|----------|----------|------|
| API-IC-201-PT | test_response_time_benchmark | 30s | 響應時間基準測試（真實API效能） |
| API-IC-202-PT | test_cache_performance | 30s | 快取效能測試（對真實API的加速效果） |
| API-IC-203-PT | test_high_concurrency_load | 60s | 高並發負載測試（真實API吞吐量） |

### E2E Tests (API-IC-301-E2E, API-IC-303-E2E)
| Test ID | 測試名稱 | 執行時間 | 說明 |
|---------|----------|----------|------|
| API-IC-301-E2E | test_complete_workflow | 60s | 完整工作流程測試（真實API） |
| API-IC-303-E2E | test_integration_with_external_services | 60s | 外部服務整合測試（監控、日誌） |

## 環境需求

### Mock Tests 環境需求
```bash
# 基本 Python 環境即可
python >= 3.8
pytest
pytest-asyncio
pytest-timeout
```

### Real API Tests 環境需求
```bash
# 除了基本環境外，還需要：
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan
EMBEDDING_API_KEY=your-embedding-key
EMBEDDING_ENDPOINT=https://your-endpoint.openai.azure.com/openai/deployments/embedding-3-large-japan/embeddings?api-version=2023-05-15
```

## 日誌與除錯

### 日誌檔案位置
```
test/logs/
├── test_suite_index_calculation_unit_integration_YYYYMMDD_HHMM.log
├── test_suite_index_calculation_real_api_perf_e2e_YYYYMMDD_HHMM.log
└── test_API-IC-XXX-XX_YYYYMMDD_HHMMSS.log  # 個別測試失敗日誌
```

### 除錯指令
```bash
# 查看最新的 mock 測試日誌
tail -f test/logs/test_suite_index_calculation_unit_integration_*.log | head -1

# 查看最新的真實 API 測試日誌
tail -f test/logs/test_suite_index_calculation_real_api_perf_e2e_*.log | head -1

# 查看特定測試失敗詳情
cat test/logs/test_API-IC-001-UT_*.log

# 執行單一測試進行詳細除錯
pytest test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_service_initialization -v -s
```

## 效能基準

### Mock Tests 效能目標
- **單元測試**: 平均每個測試 < 2s
- **整合測試**: 平均每個測試 < 5s
- **總執行時間**: < 5分鐘

### Real API Tests 效能目標
- **P50 響應時間**: < 5000ms
- **P95 響應時間**: < 10000ms
- **並發成功率**: > 95%
- **記憶體使用**: < 2GB

## 故障排除

### 常見問題

1. **Mock 測試失敗**
   ```bash
   # 檢查 mock 設定
   pytest test/unit/test_index_calculation_v2.py -v --tb=long
   
   # 確認測試檔案路徑
   ls -la test/unit/test_index_calculation_v2.py
   ls -la test/integration/test_index_calculation_v2_api.py
   ```

2. **Real API 測試失敗**
   ```bash
   # 檢查環境變數
   echo $AZURE_OPENAI_API_KEY
   echo $AZURE_OPENAI_ENDPOINT
   
   # 測試 API 連接
   curl -H "api-key: $AZURE_OPENAI_API_KEY" "$AZURE_OPENAI_ENDPOINT/openai/deployments?api-version=2023-05-15"
   ```

3. **LLM Factory 錯誤**
   ```bash
   # 確認沒有直接使用 OpenAI SDK
   grep -r "get_azure_openai_client" src/
   grep -r "AsyncAzureOpenAI" src/
   
   # 確認使用 LLM Factory
   grep -r "get_llm_client" src/
   ```

## 最佳實踐

### 開發階段
1. 優先執行 Mock Tests 進行快速迭代
2. 功能穩定後執行 Real API Tests 驗證
3. 使用 `--verbose` 模式進行詳細除錯

### CI/CD 流水線
1. Pull Request: 只執行 Mock Tests
2. Merge to Main: 執行完整測試套件
3. Release: 執行包含效能測試的完整驗證

### 成本控制
1. 開發期間主要使用 Mock Tests
2. 定期執行 Real API Tests (如每日一次)
3. 效能測試建議在背景執行避免阻塞

## 相關檔案

- `test/scripts/run_index_calculation_unit_integration.sh` - Mock 測試腳本
- `test/scripts/run_index_calculation_real_api_perf_e2e.sh` - Real API 測試腳本
- `test/scripts/run_complete_test_suite.sh` - 主測試套件
- `test/unit/test_index_calculation_v2.py` - 單元測試
- `test/integration/test_index_calculation_v2_api.py` - 整合測試
- `test/performance/test_index_calculation_v2_performance.py` - 效能測試
- `test/e2e/test_index_calculation_v2_e2e_real_api.py` - 端到端測試

## 測試分類調整說明

### 從 PT 移至 IT 的測試
- **API-IC-204-PT → API-IC-110-IT**: 記憶體管理測試（檢查洩漏是功能性問題）
- **API-IC-205-PT → API-IC-111-IT**: 快取LRU功能測試（驗證邏輯正確性）

### 從 E2E 移至 IT 的測試
- **API-IC-302-E2E → API-IC-112-IT**: 錯誤恢復機制測試（可用 mock 模擬錯誤）

### 新增的 IT 測試
- **API-IC-109-IT**: 高並發功能測試（測試應用層並發處理能力）

### 測試分類原則
- **IT (Integration Test)**: 功能性驗證、使用 mock、可頻繁執行
- **PT (Performance Test)**: 真實 API 效能基準、測量響應時間和吞吐量
- **E2E (End-to-End Test)**: 完整流程驗證、跨系統整合、真實環境

---

**文檔版本**: 2.0.0  
**建立日期**: 2025-01-05  
**更新日期**: 2025-08-05  
**適用範圍**: Index Calculation V2 Testing Architecture  
**維護者**: Azure Container API Team