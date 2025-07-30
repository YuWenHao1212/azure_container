# Azure Container API - 測試套件

本目錄包含 Azure Container API 專案的完整測試套件，採用 4 層測試架構組織。

## 📚 測試文檔

### 核心文檔
- **[TEST_STRATEGY.md](TEST_STRATEGY.md)** - 測試策略：定義整體測試方針和品質目標
- **[TEST_SPEC.md](TEST_SPEC.md)** - 測試規格：測試案例模板和編號系統
- **[TEST_MATRIX.md](TEST_MATRIX.md)** - 測試矩陣：API 端點與測試類型的覆蓋追蹤
- **[TDD_WORKFLOW.md](TDD_WORKFLOW.md)** - TDD 工作流程：新功能開發的標準流程

### 如何使用這些文檔

#### 1. 開發新功能時 (TDD 流程)
```bash
# 1. 查看 TDD_WORKFLOW.md 了解完整流程
# 2. 在 TEST_SPEC.md 定義測試案例
# 3. 更新 TEST_MATRIX.md 標記開發狀態
# 4. 先寫測試，再寫程式碼
```

#### 2. 撰寫測試時
```bash
# 1. 使用 TEST_SPEC.md 的模板格式
# 2. 確保測試案例有對應的需求編號 (REQ-XXX)
# 3. 更新 TEST_MATRIX.md 的覆蓋狀態
```

#### 3. 評估測試品質時
```bash
# 1. 檢查 TEST_STRATEGY.md 的品質目標是否達成
# 2. 查看 TEST_MATRIX.md 的覆蓋率統計
# 3. 確認高優先級 (P0) 功能都有充分測試
```

#### 4. 維護測試文檔
```bash
# 每次新增/修改測試後：
git add test/TEST_MATRIX.md
git commit -m "test: update test coverage matrix"

# 定期檢視（每週）：
- 更新 TEST_MATRIX.md 的執行狀態
- 調整 TEST_STRATEGY.md 的優先級
- 新增 TEST_SPEC.md 的測試案例
```

## 測試結構

```
test/
├── scripts/                    # 測試腳本 (Level 0 & 1)
│   ├── run_level0_tests.sh    # YAML prompt 驗證
│   ├── check_prompts.py       # Prompt 驗證器
│   └── run_style.sh           # 程式碼風格檢查
├── unit/                       # 單元測試 (Level 2)
│   ├── test_health.py         # 健康檢查端點測試
│   └── test_keyword_extraction.py  # 關鍵字提取測試
├── integration/               # 整合測試 (Level 3)
├── logs/                      # 測試執行日誌
├── reports/                   # 測試報告
├── run_all_tests.sh          # 主測試執行器
├── run_level1_tests.sh       # Level 1 執行器
├── run_level2_tests.py       # Level 2 執行器
└── requirements.txt          # 測試相依套件
```

## 🎯 4 層測試架構

### Level 0: Prompt 驗證
- **目的**: 驗證 YAML prompt 檔案的語法和結構
- **工具**: 自訂 Python 驗證器 (`check_prompts.py`)
- **覆蓋範圍**: 
  - YAML 語法驗證
  - 必要欄位驗證
  - 版本格式檢查
  - 語言變體一致性
  - 多輪配置驗證
- **執行時間**: < 5 秒
- **執行指令**: `bash scripts/run_level0_tests.sh`

### Level 1: 程式碼風格檢查
- **目的**: 確保程式碼品質和一致性
- **工具**: Ruff (Python linter 和 formatter)
- **覆蓋範圍**:
  - PEP 8 規範
  - Import 排序 (isort)
  - 命名慣例
  - 行長度限制
  - Type annotation 檢查
- **執行時間**: < 10 秒
- **執行指令**: `bash run_level1_tests.sh`

### Level 2: 單元測試
- **目的**: 使用 mock 相依套件測試個別函數和類別
- **覆蓋範圍**: 
  - 健康檢查端點 (`/health`)
  - 關鍵字提取端點 (`/api/v1/extract-jd-keywords`)
- **主要特點**:
  - 所有外部相依套件都被 mock (OpenAI API 等)
  - 不會實際呼叫 API
  - 執行速度快
  - 完整的錯誤場景測試
- **執行時間**: < 30 秒
- **執行指令**: `python run_level2_tests.py`

### Level 3: 整合測試
- **目的**: 測試 API 端點與真實服務的互動
- **覆蓋範圍**:
  - 端對端 API 工作流程
  - 服務整合驗證
  - 跨服務錯誤處理
  - 效能基準測試
- **執行時間**: 30-60 秒
- **執行指令**: `bash scripts/run_level3_tests.sh` (即將推出)

## 🚀 快速開始

### 執行所有測試
依序執行所有測試層級：
```bash
cd test/
bash run_all_tests.sh
```

### 執行特定層級
```bash
# Level 0: Prompt 驗證
bash scripts/run_level0_tests.sh

# Level 1: 程式碼風格
bash run_level1_tests.sh

# Level 2: 單元測試
python run_level2_tests.py

# Level 3: 整合測試 (即將推出)
bash scripts/run_level3_tests.sh
```

## 📊 測試執行指南

### 何時執行各層級測試

| 情境 | Level 0 | Level 1 | Level 2 | Level 3 |
|------|---------|---------|---------|---------|
| Prompt 變更 | ✅ | - | - | - |
| 程式碼格式調整 | - | ✅ | - | - |
| 函數變更 | - | ✅ | ✅ | - |
| API 變更 | - | ✅ | ✅ | ✅ |
| 提交前 | ✅ | ✅ | ✅ | - |
| 部署前 | ✅ | ✅ | ✅ | ✅ |

### 預期執行時間
- **Level 0**: < 5 秒
- **Level 1**: < 10 秒
- **Level 2**: < 30 秒
- **Level 3**: 30-60 秒
- **所有層級**: < 2 分鐘

## 執行測試

### 前置需求
```bash
pip install -r test/requirements.txt
```

### 執行所有單元測試
```bash
python test/run_level2_tests.py
```

### 執行特定測試檔案
```bash
pytest test/unit/test_health.py -v
pytest test/unit/test_keyword_extraction.py -v
```

### 執行單一測試
```bash
pytest test/unit/test_health.py::TestHealthCheck::test_health_check_success -v
```

## 測試覆蓋率

### 健康檢查測試 (9 個測試)
- ✅ 成功的健康檢查回應
- ✅ 回應格式驗證
- ✅ 版本資訊正確性
- ✅ 總是回傳健康狀態
- ✅ 時間戳記格式驗證
- ✅ HTTP 方法驗證 (非 GET 回傳 405)
- ✅ 不需要認證
- ✅ CORS headers 存在
- ✅ Mock 時間戳記測試

### 關鍵字提取測試 (10 個測試)
- ✅ 成功的關鍵字提取
- ✅ 驗證錯誤處理 (描述過短)
- ✅ 無效的 max_keywords 參數
- ✅ Azure OpenAI 速率限制錯誤處理
- ✅ 逾時錯誤處理
- ✅ 品質警告偵測
- ✅ 回應格式驗證
- ✅ 中文職缺描述支援
- ✅ 錯誤時的服務清理
- ✅ 長職缺描述的邊界案例

## Mock 策略

所有測試都使用完整的 mock 來避免外部相依：

1. **環境變數**: 為所有 API keys 和端點設置測試值
2. **OpenAI Clients**: 在 import 時就進行 mock 以防止初始化錯誤
3. **服務相依**: 使用 `unittest.mock` 進行 mock
4. **監控服務**: Mock 以避免測試期間的遙測

## 測試結果

最新測試執行 (2025-07-30 21:43:33):
- **總測試數**: 19
- **通過**: 19
- **失敗**: 0
- **結束碼**: 0
- **狀態**: ✅ 通過

## 日誌檔案

測試執行日誌儲存在 `test/logs/` 目錄，格式如下：
- 完整日誌: `level2_unit_YYYYMMDD_HHMMSS.log`
- 摘要: `level2_unit_YYYYMMDD_HHMMSS_summary.txt`

## 📝 注意事項

### 一般測試原則
- 測試不需要任何 Azure 或 OpenAI 憑證 (除了 Level 3)
- Level 0-2 的所有外部 API 呼叫都被 mock
- 測試設計為快速且可靠
- 遵循 AAA 模式: Arrange, Act, Assert

### CI/CD 整合
測試套件設計為易於 CI/CD 整合：
- 結束碼指示成功 (0) 或失敗 (非零)
- JSON 摘要報告供自動化解析
- 詳細日誌供除錯使用
- 漸進式測試提供快速回饋

### 疑難排解
- 檢查 `logs/` 目錄的詳細錯誤訊息
- 確保安裝所有相依套件: `pip install -r requirements.txt`
- 驗證環境變數設置正確
- 執行個別測試進行針對性除錯