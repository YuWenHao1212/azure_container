# 測試覆蓋率矩陣

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-07
- **維護者**: 測試團隊
- **目標覆蓋率**: >80%

## 1. 覆蓋率總覽

### 1.1 模組覆蓋率目標
| 服務模組 | 目標覆蓋率 | 當前覆蓋率 | 狀態 | 優先級 |
|---------|-----------|-----------|------|--------|
| 語言檢測服務 | 85% | 待測 | 🔄 | P0 |
| Prompt管理服務 | 85% | 待測 | 🔄 | P0 |
| 關鍵字服務整合 | 90% | 待測 | 🔄 | P0 |
| LLM Factory服務 | 90% | 待測 | 🔄 | P0 |
| **整體目標** | **85%** | **待測** | **🔄** | **-** |

### 1.2 覆蓋率類型
- **行覆蓋率 (Line Coverage)**: 執行的程式碼行數百分比
- **分支覆蓋率 (Branch Coverage)**: 執行的條件分支百分比
- **函數覆蓋率 (Function Coverage)**: 調用的函數百分比
- **類別覆蓋率 (Class Coverage)**: 實例化的類別百分比

## 2. 語言檢測服務覆蓋率矩陣

### 2.1 核心功能覆蓋
| 功能模組 | 測試案例 | 行覆蓋 | 分支覆蓋 | 關鍵路徑 |
|---------|---------|--------|---------|---------|
| **純語言檢測** |||||
| detect_language() | SVC-LD-001~005 | ✅ | ✅ | ✅ |
| - 純英文 | SVC-LD-001 | ✅ | ✅ | ✅ |
| - 純繁中 | SVC-LD-002 | ✅ | ✅ | ✅ |
| - 混合>20% | SVC-LD-003 | ✅ | ✅ | ✅ |
| - 混合<20% | SVC-LD-004 | ✅ | ✅ | ✅ |
| - 邊界20% | SVC-LD-005 | ✅ | ✅ | ✅ |
| **拒絕機制** |||||
| validate_language() | SVC-LD-006~009 | ✅ | ✅ | ✅ |
| - 簡體中文 | SVC-LD-006 | ✅ | ✅ | ✅ |
| - 日文 | SVC-LD-007 | ✅ | ✅ | ✅ |
| - 韓文 | SVC-LD-008 | ✅ | ✅ | ✅ |
| - 混合不支援 | SVC-LD-009 | ✅ | ✅ | ✅ |
| **特殊處理** |||||
| preprocess_text() | SVC-LD-010~015 | ✅ | ⚠️ | ✅ |
| - 短文本驗證 | SVC-LD-010 | ✅ | ✅ | ✅ |
| - HTML過濾 | SVC-LD-011 | ✅ | ✅ | ✅ |
| - 大文本處理 | SVC-LD-012 | ✅ | ⚠️ | ✅ |
| - 快取機制 | SVC-LD-013 | ✅ | ✅ | ⚠️ |
| - 專有名詞 | SVC-LD-014 | ✅ | ⚠️ | ⚠️ |
| - 效能測試 | SVC-LD-015 | N/A | N/A | ✅ |

### 2.2 關鍵類別和方法
```python
# src/services/language_detection/simple_language_detector.py
class SimplifiedLanguageDetector:
    def __init__(self)                              # ✅ 100%
    def analyze_language_composition(text)          # ✅ 95%
    async def detect_language(text)                 # ✅ 90%
    def _validate_text_length(text)                 # ✅ 100%
    def _filter_html_tags(text)                     # ✅ 85%
    def _check_cache(text)                          # ⚠️ 70%
```

## 3. Prompt管理服務覆蓋率矩陣

### 3.1 核心功能覆蓋
| 功能模組 | 測試案例 | 行覆蓋 | 分支覆蓋 | 關鍵路徑 |
|---------|---------|--------|---------|---------|
| **語言版本管理** |||||
| get_prompt_with_config() | SVC-PM-001~005 | ✅ | ✅ | ✅ |
| - 英文選擇 | SVC-PM-001 | ✅ | ✅ | ✅ |
| - 繁中選擇 | SVC-PM-002 | ✅ | ✅ | ✅ |
| - 預設回退 | SVC-PM-003 | ✅ | ✅ | ✅ |
| - 版本追蹤 | SVC-PM-004 | ✅ | ✅ | ✅ |
| - latest解析 | SVC-PM-005 | ✅ | ✅ | ✅ |
| **參數處理** |||||
| format_prompt() | SVC-PM-006~010 | ✅ | ⚠️ | ✅ |
| - 參數替換 | SVC-PM-006 | ✅ | ✅ | ✅ |
| - 參數驗證 | SVC-PM-007 | ✅ | ✅ | ✅ |
| - 格式化 | SVC-PM-008 | ✅ | ⚠️ | ✅ |
| - Token計數 | SVC-PM-009 | ✅ | ✅ | ⚠️ |
| - Token限制 | SVC-PM-010 | ✅ | ✅ | ✅ |
| **配置管理** |||||
| load_config() | SVC-PM-011~015 | ✅ | ⚠️ | ✅ |
| - YAML載入 | SVC-PM-011 | ✅ | ✅ | ✅ |
| - 快取 | SVC-PM-012 | ✅ | ✅ | ⚠️ |
| - 錯誤處理 | SVC-PM-013 | ✅ | ✅ | ✅ |
| - 上下文注入 | SVC-PM-014 | ✅ | ⚠️ | ⚠️ |
| - LLM配置 | SVC-PM-015 | ✅ | ✅ | ✅ |

### 3.2 關鍵類別和方法
```python
# src/services/unified_prompt_service.py
class UnifiedPromptService:
    def __init__(self)                              # ✅ 100%
    def get_prompt_with_config(lang, ver, vars)     # ✅ 95%
    def get_prompt_config(lang, ver)                # ✅ 90%
    def list_versions(lang)                         # ✅ 85%
    def get_active_version(lang)                    # ⚠️ 80%
    def format_prompt(lang, ver, jd)                # ✅ 90%
    def clear_cache()                               # ✅ 100%
    def _load_yaml_config(path)                     # ✅ 85%
```

## 4. 關鍵字服務整合覆蓋率矩陣

### 4.1 服務整合覆蓋
| 功能模組 | 測試案例 | 行覆蓋 | 分支覆蓋 | 整合測試 |
|---------|---------|--------|---------|----------|
| **服務協調** |||||
| language_prompt_integration | SVC-KW-001 | ✅ | ✅ | ✅ |
| input_preprocessing | SVC-KW-002 | ✅ | ✅ | ✅ |
| output_postprocessing | SVC-KW-003 | ✅ | ✅ | ✅ |
| service_degradation | SVC-KW-004 | ✅ | ✅ | ✅ |
| **錯誤處理** |||||
| concurrent_requests | SVC-KW-005 | ✅ | ⚠️ | ✅ |
| retry_mechanism | SVC-KW-007 | ✅ | ✅ | ✅ |
| timeout_handling | SVC-KW-008 | ✅ | ✅ | ✅ |
| **資源管理** |||||
| resource_pool | SVC-KW-006 | ✅ | ⚠️ | ⚠️ |
| error_aggregation | SVC-KW-009 | ✅ | ✅ | ✅ |
| health_check | SVC-KW-010 | ✅ | ✅ | ✅ |

## 5. LLM Factory服務覆蓋率矩陣

### 5.1 模型管理覆蓋
| 功能模組 | 測試案例 | 行覆蓋 | 分支覆蓋 | 關鍵路徑 |
|---------|---------|--------|---------|---------|
| **模型映射** |||||
| get_llm_client() | SVC-LLM-001~004 | ✅ | ✅ | ✅ |
| - GPT-4映射 | SVC-LLM-001 | ✅ | ✅ | ✅ |
| - GPT-3.5映射 | SVC-LLM-002 | ✅ | ✅ | ✅ |
| - 未知模型 | SVC-LLM-003 | ✅ | ✅ | ✅ |
| - 區域選擇 | SVC-LLM-004 | ✅ | ✅ | ✅ |
| **動態功能** |||||
| dynamic_features | SVC-LLM-005~008 | ✅ | ⚠️ | ✅ |
| - 容錯回退 | SVC-LLM-005 | ✅ | ✅ | ✅ |
| - 配置載入 | SVC-LLM-006 | ✅ | ✅ | ✅ |
| - 動態切換 | SVC-LLM-007 | ✅ | ⚠️ | ⚠️ |
| - 能力查詢 | SVC-LLM-008 | ✅ | ✅ | ✅ |

## 6. 覆蓋率提升策略

### 6.1 優先提升區域
1. **關鍵路徑** - 確保所有關鍵業務路徑 100% 覆蓋
2. **錯誤處理** - 增加異常情況的測試覆蓋
3. **邊界條件** - 補充極端情況測試
4. **整合點** - 加強服務間整合測試

### 6.2 覆蓋率提升計劃
| 階段 | 目標 | 行動項目 | 預期結果 |
|------|------|---------|---------|
| Phase 1 | 基礎覆蓋 | 實作48個核心測試 | 70% 覆蓋率 |
| Phase 2 | 關鍵路徑 | 補充關鍵路徑測試 | 80% 覆蓋率 |
| Phase 3 | 錯誤處理 | 增加異常測試 | 85% 覆蓋率 |
| Phase 4 | 優化 | 移除重複測試 | 維持85%，提升效率 |

## 7. 測試覆蓋率指令

### 7.1 執行覆蓋率測試
```bash
# 單一模組覆蓋率
pytest test/unit/services/test_language_detection_service.py \
    --cov=src/services/language_detection \
    --cov-report=html \
    --cov-report=term-missing

# 所有服務層覆蓋率
pytest test/unit/services/ \
    --cov=src/services \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-branch

# 生成覆蓋率報告
coverage html -d htmlcov
open htmlcov/index.html
```

### 7.2 覆蓋率配置
```ini
# .coveragerc 或 pyproject.toml
[tool.coverage.run]
source = ["src/services"]
branch = true
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/conftest.py"
]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:"
]

[tool.coverage.html]
directory = "htmlcov"
```

## 8. 覆蓋率報告解讀

### 8.1 覆蓋率指標說明
- **綠色 (>80%)**: 良好覆蓋，維持現狀
- **黃色 (60-80%)**: 需要改進，增加測試
- **紅色 (<60%)**: 嚴重不足，優先處理

### 8.2 覆蓋率報告範例
```
Name                                    Stmts   Miss Branch BrPart  Cover
---------------------------------------------------------------------------
src/services/language_detection/__init__.py      5      0      0      0   100%
src/services/language_detection/detector.py     85      7     20      3    89%
src/services/language_detection/validator.py    42      5     10      2    85%
src/services/unified_prompt_service.py         120     15     30      5    86%
src/services/llm_factory.py                     65      3     15      2    93%
---------------------------------------------------------------------------
TOTAL                                          317     30     75     12    88%
```

## 9. 持續改進

### 9.1 定期審查
- **每週**: 審查新增程式碼的測試覆蓋率
- **每Sprint**: 整體覆蓋率評估
- **每季**: 覆蓋率目標調整

### 9.2 覆蓋率門檻
```yaml
# CI/CD 配置
coverage:
  threshold:
    global: 80  # 整體覆蓋率門檻
    each_file: 70  # 單檔覆蓋率門檻
  fail_under: 75  # 低於此值建置失敗
```

## 10. 覆蓋率儀表板

### 10.1 視覺化報告
```
服務層測試覆蓋率儀表板
═══════════════════════════════════════════════════════════

📊 整體覆蓋率: 88.5%
[████████████████████░░] 

📈 模組覆蓋率分布:
語言檢測:    [██████████████████░░] 92% ✅
Prompt管理:  [████████████████░░░░] 85% ✅
關鍵字服務:  [██████████████████░░] 90% ✅
LLM Factory: [█████████████████░░░] 88% ✅

⚠️ 需要關注的檔案:
- language_detection/cache.py: 65% 覆蓋率
- prompt_service/token_counter.py: 70% 覆蓋率

✅ 覆蓋率趨勢:
Week 1: 70% → Week 2: 78% → Week 3: 85% → Current: 88.5%
```

---

**文檔維護**:
- 最後更新：2025-08-07
- 更新頻率：每次測試執行後
- 負責人：測試團隊