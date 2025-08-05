# Gap Analysis V2 測試腳本使用指南

## 概述

`run_gap_analysis_v2_tests.sh` 是專門為 Index Calculation and Gap Analysis V2 功能設計的測試腳本，能夠執行符合 `test-spec-index-cal-gap-analysis.md` 規格的全部 43 個測試案例。

## 特點

- ✅ 涵蓋全部 43 個測試案例（單元/整合/效能/E2E）
- ✅ 基於測試規格文檔 v1.0.1 設計
- ✅ 支援階段性執行和背景執行
- ✅ 詳細的測試報告和統計
- ✅ 優先級分類（P0/P1/P2）
- ✅ 跨平台兼容（macOS/Linux）

## 測試案例分佈

| 測試類型 | 數量 | 測試案例編號 | 測試檔案 |
|----------|------|-------------|----------|
| 單元測試 | 20 個 | API-GAP-001-UT 到 API-GAP-020-UT | `test/unit/test_gap_analysis_v2.py` |
| 整合測試 | 14 個 | API-GAP-001-IT 到 API-GAP-014-IT | `test/integration/test_gap_analysis_v2_integration_complete.py` |
| 效能測試 | 5 個 | API-GAP-001-PT 到 API-GAP-005-PT | `test/performance/test_gap_analysis_v2_performance.py` |
| E2E 測試 | 4 個 | API-GAP-001-E2E 到 API-GAP-004-E2E | `test/e2e/test_gap_analysis_v2_e2e.py` |

## 使用方法

### 基本用法

```bash
# 執行所有 43 個測試案例
./test/scripts/run_gap_analysis_v2_tests.sh

# 顯示幫助訊息
./test/scripts/run_gap_analysis_v2_tests.sh --help
```

### 階段性執行

```bash
# 僅執行單元測試（20 個測試）
./test/scripts/run_gap_analysis_v2_tests.sh --stage unit

# 僅執行整合測試（14 個測試）
./test/scripts/run_gap_analysis_v2_tests.sh --stage integration

# 僅執行效能測試（5 個測試）
./test/scripts/run_gap_analysis_v2_tests.sh --stage performance

# 僅執行 E2E 測試（4 個測試）
./test/scripts/run_gap_analysis_v2_tests.sh --stage e2e
```

### 進階選項

```bash
# 背景執行所有測試
./test/scripts/run_gap_analysis_v2_tests.sh --background

# 詳細輸出模式
./test/scripts/run_gap_analysis_v2_tests.sh --verbose

# 組合使用
./test/scripts/run_gap_analysis_v2_tests.sh --stage unit --verbose
```

## 輸出與報告

### 測試執行過程

腳本會即時顯示每個測試的執行狀態：

```
[0;34mRunning API-GAP-001-UT (P0)...[0m
  [0;32m✓ PASSED[0m (1s)

[0;34mRunning API-GAP-002-UT (P0)...[0m
  [0;31m✗ FAILED[0m (2s)
  Error details saved to: test_API-GAP-002-UT_20250804_112615.log
```

### 詳細測試報告

執行完成後會產生包含以下資訊的詳細報告：

- **執行摘要**: 總測試數、通過率、失敗數
- **測試類型統計**: 各類型測試的成功率
- **優先級統計**: P0/P1/P2 測試的通過情況
- **失敗測試詳情**: 失敗測試的日誌檔案位置

### 日誌檔案

- **主日誌**: `test/logs/gap_analysis_v2_[timestamp].log`
- **個別測試日誌**: `test/logs/test_[test-id]_[timestamp].log`（僅失敗測試保留）

## 環境需求

### 必要條件

- Python 3.11.8（透過 pyenv 管理）
- 專案虛擬環境已啟動
- `.env` 檔案已配置（包含必要的 API keys）

### 相依套件

確保已安裝所有測試相依套件：

```bash
# 安裝測試相依套件
pip install -r test/requirements.txt

# 或使用完整專案相依套件
pip install -r requirements.txt
```

### 超時工具

腳本會自動偵測並使用適當的超時工具：

1. `gtimeout`（來自 coreutils，推薦用於 macOS）
2. `timeout`（Linux 內建）
3. 如果都不可用，則使用無超時的 pytest

在 macOS 上安裝 coreutils：

```bash
brew install coreutils
```

## 故障排除

### 常見問題

1. **timeout 命令不存在**
   - 解決方案：安裝 `brew install coreutils`

2. **測試失敗率過高**
   - 檢查 `.env` 檔案配置
   - 確認 API 服務正常運行
   - 查看個別測試日誌檔案

3. **ImportError 或模組找不到**
   - 確認虛擬環境已啟動
   - 安裝 `test/requirements.txt` 中的相依套件

### 除錯技巧

```bash
# 執行單一測試進行除錯
python -m pytest test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_combined_analysis_service_initialization -v

# 查看測試日誌
tail -f test/logs/gap_analysis_v2_[latest].log

# 查看失敗測試詳細日誌
cat test/logs/test_API-GAP-XXX-XX_[timestamp].log
```

## 與其他測試腳本的關係

- **獨立運行**: 不依賴 `run_complete_test_suite.sh`
- **專門設計**: 僅針對 Gap Analysis V2 的 43 個測試案例
- **互補功能**: 可與完整測試套件腳本併用

## 測試規格符合性

此腳本完全符合 `test-spec-index-cal-gap-analysis.md` v1.0.1 的要求：

- ✅ 涵蓋全部 43 個指定測試案例
- ✅ 正確的優先級分類
- ✅ 適當的超時設定
- ✅ 詳細的報告格式
- ✅ Ruff 程式碼品質檢查兼容

## 更新紀錄

- **v1.0.0** (2025-08-04): 初始版本，支援 43 個測試案例的完整執行

---

**維護者**: Claude Code + WenHao  
**最後更新**: 2025-08-04  
**相關文檔**: `test-spec-index-cal-gap-analysis.md`, `test-validation-report.md`