# 服務層模組輔助測試規格

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-07
- **維護者**: 測試團隊
- **狀態**: 補充文檔

## 1. 輔助測試概覽

除了 47 個核心 SVC 測試外，實作中包含了 10 個輔助測試（Helper Tests），用於測試服務的輔助方法和工具函數。

### 1.1 測試分布

| 服務模組 | 輔助測試數 | 測試類別 |
|---------|-----------|---------|
| 語言檢測服務 | 4 | TestLanguageDetectionHelperMethods |
| Prompt 管理服務 | 3 | TestPromptServiceHelpers |
| LLM Factory | 3 | TestLLMFactoryHelpers |
| **總計** | **10** | |

## 2. 輔助測試詳細說明

### 2.1 語言檢測服務輔助測試 (4個)

#### HELPER-LD-001: 支援語言檢查
- **測試方法**: `test_is_supported_language`
- **測試目的**: 驗證 `is_supported_language()` 方法正確判斷語言支援
- **驗證項目**:
  - 'en' 和 'zh-TW' 返回 True
  - 'zh-CN', 'ja', 'ko', 'es' 返回 False

#### HELPER-LD-002: 文字長度驗證
- **測試方法**: `test_validate_text_length`
- **測試目的**: 驗證 `validate_text_length()` 方法的邊界條件
- **驗證項目**:
  - 200+ 字元返回 True
  - <200 字元返回 False
  - 空字串返回 False

#### HELPER-LD-003: 取得支援語言清單
- **測試方法**: `test_get_supported_languages`
- **測試目的**: 驗證 `get_supported_languages()` 返回正確清單
- **驗證項目**:
  - 返回包含 'en' 和 'zh-TW'
  - 清單長度為 2

#### HELPER-LD-004: 語言成分分析
- **測試方法**: `test_analyze_language_composition`
- **測試目的**: 驗證 `analyze_language_composition()` 正確分析文字成分
- **驗證項目**:
  - 正確計算英文字元數
  - 正確識別繁體/簡體中文
  - 正確標記不支援語言

### 2.2 Prompt 管理服務輔助測試 (3個)

#### HELPER-PM-001: 版本比較邏輯
- **測試方法**: `test_prompt_version_comparison`
- **測試目的**: 驗證版本號排序和比較邏輯
- **驗證項目**:
  - 正確排序語意化版本號
  - 識別最新版本

#### HELPER-PM-002: 語言代碼正規化
- **測試方法**: `test_language_code_normalization`
- **測試目的**: 驗證語言代碼標準化處理
- **驗證項目**:
  - 'zh', 'zh-tw', 'zh-TW' → 'zh-TW'
  - 'en', 'en-US', 'en-GB' → 'en'
  - 未知語言 → 'en' (預設)

#### HELPER-PM-003: Prompt 模板驗證
- **測試方法**: `test_prompt_template_validation`
- **測試目的**: 驗證模板包含必要的佔位符
- **驗證項目**:
  - 檢查 {job_description} 存在
  - 拒絕缺少必要佔位符的模板

### 2.3 LLM Factory 輔助測試 (3個)

#### HELPER-LLM-001: 部署映射結構
- **測試方法**: `test_deployment_map_structure`
- **測試目的**: 驗證 DEPLOYMENT_MAP 的結構和內容
- **驗證項目**:
  - 關鍵映射存在且正確
  - 映射值為有效字串

#### HELPER-LLM-002: API 名稱映射
- **測試方法**: `test_api_name_to_model_mapping`
- **測試目的**: 驗證 API 名稱到模型的映射
- **驗證項目**:
  - 'keywords' → 'gpt41-mini'
  - 'gap_analysis' → 'gpt4o-2'

#### HELPER-LLM-003: 智慧選擇邏輯
- **測試方法**: `test_smart_client_selection_logic`
- **測試目的**: 驗證智慧型客戶端選擇優先順序
- **驗證項目**:
  - request_model > header hint > api default
  - 未知 API 使用預設模型

## 3. 合併建議

### 3.1 合併策略

為了精簡測試並提高維護性，建議採用以下策略：

#### 選項 A：整合到對應的 SVC 測試中
將輔助方法測試整合到相關的 SVC 測試中作為驗證步驟：
- 優點：減少測試檔案數量，邏輯更集中
- 缺點：SVC 測試會變得較複雜

#### 選項 B：建立單一輔助測試類別
```python
class TestServiceHelpers:
    """統一的服務層輔助方法測試"""
    
    # 語言檢測輔助方法 (2個合併測試)
    def test_language_detection_helpers(self):
        """測試所有語言檢測輔助方法"""
        # 合併 is_supported_language, validate_text_length, 
        # get_supported_languages 的測試
    
    def test_language_composition_analysis(self):
        """測試語言成分分析"""
        # 保持獨立因為較複雜
    
    # Prompt 服務輔助方法 (1個合併測試)
    def test_prompt_service_helpers(self):
        """測試所有 Prompt 服務輔助方法"""
        # 合併版本比較、語言正規化、模板驗證
    
    # LLM Factory 輔助方法 (1個合併測試)
    def test_llm_factory_helpers(self):
        """測試所有 LLM Factory 輔助方法"""
        # 合併部署映射、API映射、智慧選擇
```

#### 選項 C：保持現狀但明確文檔化（推薦）
- 在 TEST_SPEC_SERVICE_MODULES.md 中新增「輔助測試」章節
- 明確說明這 10 個測試的用途和必要性
- 在測試執行報告中分別統計 SVC 測試和輔助測試

### 3.2 實施建議

**短期（立即）**：
- 採用選項 C，保持現有測試但加強文檔
- 更新測試執行腳本以分別報告兩類測試

**中期（下個 Sprint）**：
- 評估哪些輔助測試可以安全移除
- 考慮將高價值的輔助測試提升為 SVC 測試

**長期（重構時）**：
- 實施選項 B，建立統一的輔助測試類別
- 將測試數量控制在 50 個以內（47 SVC + 3 輔助）

## 4. 測試執行統計更新

### 4.1 正確的測試統計
```
總測試數：57
├── SVC 測試：47（符合規格要求）
│   ├── 語言檢測：14
│   ├── Prompt 管理：15
│   ├── 關鍵字服務：10
│   └── LLM Factory：8
└── 輔助測試：10（額外實作）
    ├── 語言檢測輔助：4
    ├── Prompt 服務輔助：3
    └── LLM Factory 輔助：3
```

### 4.2 測試結果分析
```
執行結果（總計 57 個測試）：
├── PASSED：38
├── FAILED：12
└── ERROR：7
```

## 5. 維護指南

### 5.1 新增輔助測試原則
1. 只為**公開的輔助方法**建立測試
2. 避免測試內部實作細節
3. 優先考慮整合到 SVC 測試中
4. 必須在此文檔中記錄

### 5.2 輔助測試編號規範
```
HELPER-[模組]-[序號]
範例：HELPER-LD-001
```

### 5.3 文檔同步
- 修改輔助測試時更新此文檔
- 在主規格文檔中引用此文檔
- 保持測試統計的準確性

---

**文檔維護**:
- 最後更新：2025-08-07
- 審查週期：每個 Sprint
- 負責團隊：測試團隊