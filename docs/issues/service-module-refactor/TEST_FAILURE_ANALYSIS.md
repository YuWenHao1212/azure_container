# 服務層模組測試失敗分析報告

## 報告資訊
- **生成日期**: 2025-08-07
- **測試總數**: 57 (47 SVC + 10 Helper)
- **執行結果**: 38 passed, 12 failed, 7 errors
- **成功率**: 66.7%

## 1. 執行摘要

### 1.1 測試統計
| 模組 | SVC測試 | Helper測試 | 總計 | 通過 | 失敗 | 錯誤 | 成功率 |
|------|---------|------------|------|------|------|------|--------|
| 語言檢測 | 14 | 4 | 18 | 12 | 6 | 0 | 66.7% |
| Prompt管理 | 15 | 3 | 18 | 11 | 3 | 4 | 61.1% |
| 關鍵字服務 | 10 | 0 | 10 | 8 | 2 | 0 | 80.0% |
| LLM Factory | 8 | 3 | 11 | 7 | 1 | 3 | 63.6% |
| **總計** | **47** | **10** | **57** | **38** | **12** | **7** | **66.7%** |

## 2. 失敗分析

### 2.1 語言檢測服務失敗 (6個)

#### 問題類型 1: detection_time_ms 返回 0
**影響測試**: 
- SVC-LD-001: 純英文檢測
- SVC-LD-002: 純繁體中文檢測
- SVC-LD-005: 邊界條件測試

**根本原因**:
Mock 返回的 `LanguageDetectionResult` 物件中 `detection_time_ms` 被硬編碼為 0

**解決方案**:
```python
# 修改 mock 返回值
return LanguageDetectionResult(
    language='en',
    confidence=0.9,
    is_supported=True,
    detection_time_ms=50  # 改為合理的值
)
```

#### 問題類型 2: SimplifiedLanguageDetector 行為差異
**影響測試**:
- SVC-LD-006: 拒絕簡體中文
- SVC-LD-010: 短文本處理

**根本原因**:
`SimplifiedLanguageDetector` 的實際實作與 mock 行為不一致：
- 實際使用 10% 閾值拒絕不支援語言
- Mock 假設立即拒絕

**解決方案**:
需要更準確地 mock `SimplifiedLanguageDetector` 的行為

#### 問題類型 3: Helper 方法測試失敗
**影響測試**:
- test_analyze_language_composition

**根本原因**:
測試假設 `analyze_language_composition` 是公開方法，但可能是私有或不存在

### 2.2 Prompt 管理服務失敗 (7個：3失敗+4錯誤)

#### 錯誤類型: AttributeError
**症狀**: 'UnifiedPromptService' object has no attribute 'XXX'

**影響方法**:
- get_active_version
- list_versions
- get_prompt_config
- validate_parameters

**根本原因**:
Mock 的 `UnifiedPromptService` 缺少這些方法的定義

### 2.3 關鍵字服務失敗 (2個)

**失敗測試**:
- 併發請求處理
- 資源池管理

**可能原因**:
- 併發測試的 asyncio 處理不當
- Mock 的異步行為不正確

### 2.4 LLM Factory 服務失敗 (4個：1失敗+3錯誤)

**錯誤類型**: ImportError 或 AttributeError
- DEPLOYMENT_MAP 不存在或路徑錯誤
- Mock 配置不完整

## 3. 修復優先級

### P0 - 立即修復 (影響最大)
1. **detection_time_ms = 0 問題**
   - 影響: 6個測試
   - 修復時間: 15分鐘
   - 檔案: `test/unit/services/conftest.py`

2. **UnifiedPromptService 方法缺失**
   - 影響: 7個測試
   - 修復時間: 30分鐘
   - 檔案: `test/unit/services/test_unified_prompt_service.py`

### P1 - 重要修復
3. **SimplifiedLanguageDetector 行為差異**
   - 影響: 2個測試
   - 修復時間: 20分鐘
   - 需要理解實際實作邏輯

4. **LLM Factory DEPLOYMENT_MAP**
   - 影響: 4個測試
   - 修復時間: 20分鐘

### P2 - 次要修復
5. **併發測試問題**
   - 影響: 2個測試
   - 修復時間: 15分鐘

## 4. 快速修復方案

### 4.1 修復 detection_time_ms
```python
# 在 conftest.py 中修改
@pytest.fixture
def mock_language_detector():
    detector = AsyncMock(spec=SimplifiedLanguageDetector)
    detector.detect_language.return_value = LanguageDetectionResult(
        language='en',
        confidence=0.9,
        is_supported=True,
        detection_time_ms=50  # 不要用 0
    )
    return detector
```

### 4.2 修復 UnifiedPromptService
```python
# 添加缺失的方法
mock_service.get_active_version = MagicMock(return_value="1.4.0")
mock_service.list_versions = MagicMock(return_value=["1.0.0", "1.4.0"])
mock_service.get_prompt_config = MagicMock(return_value=mock_config)
mock_service.validate_parameters = AsyncMock(return_value=True)
```

### 4.3 修復 DEPLOYMENT_MAP
```python
# 正確 mock DEPLOYMENT_MAP
with patch('src.services.llm_factory.DEPLOYMENT_MAP', {
    'gpt4o-2': 'gpt-4.1-japan',
    'gpt41-mini': 'gpt-41-mini-japaneast'
}):
    # 測試代碼
```

## 5. 驗證步驟

執行修復後的驗證：
```bash
# 1. 單獨測試語言檢測
pytest test/unit/services/test_language_detection_service.py -v

# 2. 單獨測試 Prompt 管理
pytest test/unit/services/test_unified_prompt_service.py -v

# 3. 執行完整測試套件
./test/scripts/run_service_modules_tests.sh
```

## 6. 預期結果

修復後預期：
- **通過率目標**: > 90% (至少 52/57 通過)
- **無錯誤**: 0 errors
- **失敗數**: < 5 (可接受的邊緣案例)

## 7. 後續改進建議

1. **建立測試基類**: 減少重複的 mock 設定
2. **使用 pytest-asyncio**: 更好地處理異步測試
3. **建立測試資料工廠**: 標準化測試資料生成
4. **實作整合測試**: 驗證服務間的真實互動
5. **持續集成**: 設定 GitHub Actions 自動執行測試

## 8. 學習要點

### 成功經驗
- Mock 策略基本正確
- 測試結構清晰
- 覆蓋了主要功能點

### 需要改進
- Mock 物件需要更完整地模擬真實行為
- 異步測試處理需要加強
- 測試資料需要更貼近實際使用場景

---

**下一步行動**:
1. 根據 P0 優先級開始修復
2. 逐步驗證每個修復
3. 更新測試文檔
4. 執行完整回歸測試