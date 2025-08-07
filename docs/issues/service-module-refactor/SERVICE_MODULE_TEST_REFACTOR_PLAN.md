# 服務層模組測試重構計劃

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-07
- **維護者**: 測試團隊
- **狀態**: 實施中

## 1. 重構背景與目標

### 1.1 現狀問題
1. **缺少專門的服務層單元測試** - TEST_SPEC_SERVICE_MODULES.md 定義了74個測試，但實際檔案不存在
2. **測試層級混淆** - 服務層邏輯被測試在 API 層級，而非獨立的單元測試
3. **過度測試** - 相同場景在 unit 和 integration 測試中重複
4. **Mock 策略不一致** - 需要統一的 Mock 方法
5. **缺少測試總結報告** - 需要清晰的測試分布和結果統計

### 1.2 重構目標
- ✅ 建立真正的服務層單元測試（精簡但完整）
- ✅ 從74個測試精簡至48個核心測試
- ✅ 消除重複測試，提升測試效率
- ✅ 實施統一的 Mock 策略
- ✅ 確保測試資料符合 API 要求（>200字元）
- ✅ 新增視覺化測試總結報告

## 2. 測試架構設計

### 2.1 目錄結構
```
test/
├── unit/
│   └── services/                              # 新建服務層測試目錄
│       ├── conftest.py                        # 共用 fixtures
│       ├── test_language_detection_service.py # 14個測試
│       ├── test_unified_prompt_service.py     # 15個測試
│       ├── test_keyword_service_integration.py # 10個測試
│       └── test_llm_factory_service.py        # 8個測試
└── scripts/
    └── run_service_modules_tests.sh           # 專用測試腳本
```

### 2.2 測試分布設計（47個核心測試）

| 服務模組 | 原測試數 | 新測試數 | 精簡率 | 重點覆蓋 |
|---------|---------|---------|-------|---------|
| 語言檢測 | 27 | 14 | -48% | 核心語言檢測、拒絕機制、邊界條件 |
| Prompt管理 | 29 | 15 | -48% | 版本管理、參數處理、配置載入 |
| 關鍵字服務 | 10 | 10 | 0% | 保持原有整合測試 |
| LLM Factory | 8 | 8 | 0% | 保持原有映射測試 |
| **總計** | **74** | **47** | **-36%** | **核心功能全覆蓋** |

## 3. 測試案例規劃

### 3.1 語言檢測服務 (SVC-LD)
```
14個單元測試
├── 核心功能 (5個)
│   ├── SVC-LD-001: 純英文檢測
│   ├── SVC-LD-002: 純繁體中文檢測
│   ├── SVC-LD-003: 混合語言 >20% 繁中
│   ├── SVC-LD-004: 混合語言 <20% 繁中
│   └── SVC-LD-005: 邊界條件 =20% 繁中
├── 拒絕機制 (4個)
│   ├── SVC-LD-006: 拒絕簡體中文
│   ├── SVC-LD-007: 拒絕日文
│   ├── SVC-LD-008: 拒絕韓文
│   └── SVC-LD-009: 拒絕混合不支援語言
└── 特殊處理 (5個)
    ├── SVC-LD-010: 短文本處理 (<200字元)
    ├── SVC-LD-011: HTML標籤過濾
    ├── SVC-LD-012: 大量文字處理 (3000字元)
    ├── SVC-LD-013: 技術專有名詞處理
    └── SVC-LD-014: 效能基準測試 (<100ms)
```

### 3.2 Prompt管理服務 (SVC-PM)
```
15個單元測試
├── 語言版本管理 (5個)
│   ├── SVC-PM-001: 英文prompt選擇
│   ├── SVC-PM-002: 繁中prompt選擇
│   ├── SVC-PM-003: 預設回退機制
│   ├── SVC-PM-004: 版本追蹤功能
│   └── SVC-PM-005: latest版本解析
├── 參數格式化 (5個)
│   ├── SVC-PM-006: 參數替換功能
│   ├── SVC-PM-007: 參數驗證 (>200字元)
│   ├── SVC-PM-008: Prompt格式化
│   ├── SVC-PM-009: Token計數功能
│   └── SVC-PM-010: Token限制檢查
└── 配置處理 (5個)
    ├── SVC-PM-011: YAML載入解析
    ├── SVC-PM-012: 快取機制
    ├── SVC-PM-013: 檔案錯誤處理
    ├── SVC-PM-014: 上下文注入
    └── SVC-PM-015: LLM配置提取
```

### 3.3 關鍵字服務整合 (SVC-KW)
```
10個單元測試（保持原有）
├── 服務協調 (4個)
│   ├── SVC-KW-001: 語言檢測與Prompt整合
│   ├── SVC-KW-002: 輸入預處理 (驗證>200字元)
│   ├── SVC-KW-003: 輸出後處理
│   └── SVC-KW-004: 服務降級機制
├── 錯誤處理 (3個)
│   ├── SVC-KW-005: 併發請求處理
│   ├── SVC-KW-007: 重試機制
│   └── SVC-KW-008: 超時處理
└── 資源管理 (3個)
    ├── SVC-KW-006: 資源池管理
    ├── SVC-KW-009: 錯誤聚合
    └── SVC-KW-010: 健康檢查
```

### 3.4 LLM Factory服務 (SVC-LLM)
```
8個單元測試（保持原有）
├── 模型映射 (4個) 
│   ├── SVC-LLM-001: GPT-4部署映射
│   ├── SVC-LLM-002: GPT-3.5部署映射 <- 沒有 gpt3.5
│   ├── SVC-LLM-003: 未知模型處理
│   └── SVC-LLM-004: 區域選擇邏輯
└── 動態功能 (4個)
    ├── SVC-LLM-005: 容錯回退機制
    ├── SVC-LLM-006: 配置載入
    ├── SVC-LLM-007: 動態模型切換
    └── SVC-LLM-008: 模型能力查詢
```

## 4. Mock 策略

### 4.1 統一Mock原則
參考 `test/integration/test_keyword_extraction_language.py` 的實作方式：

1. **使用 pytest fixtures 管理所有 mocks**
2. **Mock 所有外部依賴**（Azure OpenAI, 檔案系統, 網路請求）
3. **使用 AsyncMock 處理異步操作**
4. **保持測試完全獨立性**

### 4.2 Mock 實作範例
```python
@pytest.fixture
def mock_azure_openai_client():
    """Mock Azure OpenAI client for service tests."""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[Mock(
                message=Mock(
                    content='{"keywords": ["Python", "FastAPI"]}'
                )
            )]
        )
    )
    return client
```

詳細Mock策略請參考：[MOCK_STRATEGY_GUIDE.md](./MOCK_STRATEGY_GUIDE.md)

## 5. 測試資料要求

### 5.1 關鍵要求
⚠️ **重要：所有測試的 JD 和 Resume 必須 > 200 字元**
- API 會對 < 200 字元的輸入返回 422 錯誤
- 所有測試 fixtures 必須提供足夠長度的測試資料
- 短文本測試應該明確測試驗證失敗場景

### 5.2 標準測試資料
詳見：[TEST_DATA_REQUIREMENTS.md](./TEST_DATA_REQUIREMENTS.md)

## 6. 測試報告格式

### 6.1 視覺化報告設計
測試腳本將產生三種視圖：

1. **測試分布矩陣** - 顯示各模組的測試數量和通過/失敗統計
2. **進度條視圖** - 直觀顯示各模組的測試完成度
3. **統計摘要** - 整體成功率和執行時間統計

### 6.2 報告範例
```
📊 測試分布與結果矩陣
═══════════════════════════════════════════════════════════════════
| 測試模組    | 單元測試      | 整合測試 | 效能測試 | 總計         | 狀態 |
|-------------|---------------|----------|----------|--------------|------|
| 語言檢測    | 15 ✅(15/0)   | -        | -        | 15 ✅(15/0)  | ✅   |
| Prompt管理  | 15 ⚠️(14/1)   | -        | -        | 15 ⚠️(14/1)  | ⚠️   |
| 關鍵字服務  | 10 ❌(5/5)    | -        | -        | 10 ❌(5/5)   | ❌   |
| LLM Factory | 8  ✅(8/0)    | -        | -        | 8  ✅(8/0)   | ✅   |
|-------------|---------------|----------|----------|--------------|------|
| **總計**    | 48 (42/6)     | 0        | 0        | 48 (42/6)    | ⚠️   |
| **成功率**  | 87.5%         | -        | -        | 87.5%        |      |
```

詳細格式說明：[TEST_SUMMARY_REPORT_FORMAT.md](./TEST_SUMMARY_REPORT_FORMAT.md)

## 7. 實施計劃

### 7.1 階段劃分

| 階段 | 任務 | 預計工時 | 完成標準 |
|------|------|---------|---------|
| Phase 1 | 建立測試檔案結構和fixtures | 2小時 | 目錄結構完成，基礎fixtures就緒 |
| Phase 2 | 實作語言檢測服務測試 | 3小時 | 14個測試全部通過 |
| Phase 3 | 實作Prompt管理服務測試 | 3小時 | 15個測試全部通過 |
| Phase 4 | 整理關鍵字和LLM Factory測試 | 2小時 | 18個測試全部通過 |
| Phase 5 | 建立測試執行腳本和報告 | 2小時 | 視覺化報告正常顯示 |
| Phase 6 | 執行覆蓋率分析和優化 | 1小時 | 覆蓋率>80% |

### 7.2 成功標準

- ✅ 所有47個測試通過
- ✅ 測試資料符合 >200 字元要求
- ✅ 包含 <200 字元的驗證錯誤測試
- ✅ 無需真實API調用（100% Mock）
- ✅ 單一測試執行時間 < 100ms
- ✅ 總測試套件執行時間 < 5秒
- ✅ 測試覆蓋率 > 80%
- ✅ 通過 Ruff 檢查（無錯誤）

## 8. 維護指南

### 8.1 新增測試規範
1. 遵循 `SVC-[模組]-[序號]-UT` 編號格式
2. 使用統一的 Mock 策略
3. 確保測試資料符合長度要求
4. 更新測試分布統計

### 8.2 文檔同步
- 測試實作變更時同步更新 TEST_SPEC_SERVICE_MODULES.md
- 保持測試編號的一致性和可追溯性
- 定期審查和更新測試覆蓋率報告

## 9. 相關文檔

- [TEST_SPEC_SERVICE_MODULES.md](../TEST_SPEC_SERVICE_MODULES.md) - 服務層測試規格
- [MOCK_STRATEGY_GUIDE.md](./MOCK_STRATEGY_GUIDE.md) - Mock策略指南
- [TEST_COVERAGE_MATRIX.md](./TEST_COVERAGE_MATRIX.md) - 測試覆蓋率矩陣
- [TEST_DATA_REQUIREMENTS.md](./TEST_DATA_REQUIREMENTS.md) - 測試資料要求
- [TEST_SUMMARY_REPORT_FORMAT.md](./TEST_SUMMARY_REPORT_FORMAT.md) - 測試報告格式

---

**文檔維護**:
- 最後更新：2025-08-07
- 下次審查：每個Sprint結束時
- 負責團隊：測試團隊與開發團隊共同維護