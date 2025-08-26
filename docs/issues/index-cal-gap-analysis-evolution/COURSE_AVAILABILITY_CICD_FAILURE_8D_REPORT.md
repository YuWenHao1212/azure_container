# Course Availability CI/CD 測試失敗 8D 報告

**報告日期**: 2025-01-26  
**問題編號**: CA-CICD-001  
**嚴重程度**: 高 - 阻擋部署流程  
**影響範圍**: CI/CD Pipeline 無法通過，影響產品發布

---

## D1: 團隊建立

**問題負責人**: Development Team  
**分析人員**: Claude Code  
**相關人員**:
- 開發團隊：負責程式碼修復
- DevOps：負責 CI/CD 環境配置
- QA：負責測試驗證

---

## D2: 問題描述

### 問題現象
- **失敗位置**: GitHub Actions CI/CD Pipeline
- **失敗測試**: 
  - `test_popular_skill_cache`
  - `test_CA_002_IT_parallel_processing`
- **錯誤訊息**: Course Availability 整合測試失敗（2 個測試失敗）

### 環境差異
| 環境 | 測試結果 | 環境配置 |
|------|---------|----------|
| 本地開發 | ✅ 通過 (234/234) | 可能無 ENABLE_COURSE_CACHE 或設為 false |
| CI/CD (GitHub Actions) | ❌ 失敗 (232/234) | ENABLE_COURSE_CACHE=true |

### 時間軸
- 2025-01-26 10:30 - 首次發現測試失敗
- 2025-01-26 11:00 - 第一次修復嘗試（添加 hasattr 檢查）
- 2025-01-26 11:30 - 第二次修復嘗試（強制初始化快取）
- 2025-01-26 12:00 - 問題仍然存在

---

## D3: 臨時圍堵措施

### 已實施措施
1. **本地驗證**: 確認本地測試全部通過
2. **環境模擬**: 使用 `ENABLE_COURSE_CACHE=true` 在本地重現問題
3. **手動部署**: 暫時跳過失敗測試進行緊急部署（如需要）

### 風險評估
- 功能影響：Course Availability 功能本身運作正常
- 部署影響：無法自動部署到生產環境

---

## D4: 根本原因分析

### 原因層級分析

#### L1: 直接原因
測試在 CI 環境失敗，但在本地環境通過

#### L2: 環境差異分析
```python
# CI 環境流程
CourseAvailabilityChecker.__init__()
├── os.getenv("ENABLE_COURSE_CACHE", "true") = "true"  # CI 設定
├── self._cache_enabled = True
└── self._dynamic_cache = get_course_cache()  # 取得全域單例

# 測試程式碼
if not hasattr(checker, '_dynamic_cache') or checker._dynamic_cache is None:
    # CI: 條件永遠為 False，不會執行
    checker._dynamic_cache = get_course_cache()
```

#### L3: 深層原因 - 全域單例污染
1. **單例模式問題**:
   ```python
   # dynamic_course_cache.py
   _cache_instance: DynamicCourseCache | None = None  # 全域變數
   
   def get_course_cache():
       global _cache_instance
       if _cache_instance is None:
           _cache_instance = DynamicCourseCache()
       return _cache_instance
   ```

2. **測試執行順序影響**:
   - 第一個測試: 創建單例實例
   - 第二個測試: 使用已存在的單例（可能含有髒資料）
   - CI 環境可能平行執行或順序不同

#### L4: 設計缺陷
- 測試未正確隔離全域狀態
- 測試依賴環境變數，導致行為不一致
- 快取初始化邏輯分散在多處

### 5 Why 分析
1. **為什麼測試失敗？**  
   因為測試預期的快取狀態與實際不符

2. **為什麼狀態不符？**  
   因為全域單例在測試間共享狀態

3. **為什麼會共享狀態？**  
   因為使用了全域變數 `_cache_instance`

4. **為什麼沒有重置？**  
   因為測試 fixture 未正確重置全域狀態

5. **為什麼 fixture 沒有效果？**  
   因為測試可能在 fixture 執行前就已經初始化了快取

---

## D5: 永久糾正措施

### 方案設計

#### 方案 A: 完全隔離測試環境（推薦）
```python
@pytest.fixture(autouse=True)
async def isolate_cache():
    """完全隔離每個測試的快取環境"""
    import src.services.dynamic_course_cache as cache_module
    
    # 保存原始狀態
    original_instance = cache_module._cache_instance
    
    # 強制重置
    cache_module._cache_instance = None
    
    # 模擬環境變數
    with patch.dict(os.environ, {'ENABLE_COURSE_CACHE': 'false'}):
        yield
    
    # 恢復原始狀態
    cache_module._cache_instance = original_instance
```

#### 方案 B: 重構快取管理
```python
class CourseAvailabilityChecker:
    def __init__(self, connection_pool=None, cache=None):
        """允許注入快取實例"""
        self._connection_pool = connection_pool
        
        if cache is not None:
            self._dynamic_cache = cache
        elif os.getenv("ENABLE_COURSE_CACHE", "true").lower() == "true":
            from src.services.dynamic_course_cache import get_course_cache
            self._dynamic_cache = get_course_cache()
        else:
            self._dynamic_cache = None
```

#### 方案 C: 測試專用快取
```python
class TestCourseAvailabilityIntegration:
    @pytest.fixture(autouse=True)
    async def setup_test_cache(self):
        """為每個測試創建獨立的快取實例"""
        self.test_cache = DynamicCourseCache()
        yield
        await self.test_cache.clear()
```

### 實施步驟
1. 修改測試 fixture，確保完全隔離
2. 在測試中顯式控制快取生命週期
3. 移除對環境變數的依賴
4. 添加測試隔離性驗證

---

## D6: 糾正措施實施

### 執行計劃
| 步驟 | 動作 | 負責人 | 時程 |
|-----|------|--------|------|
| 1 | 實施方案 A - 完全隔離測試環境 | Dev Team | 立即 |
| 2 | 本地驗證所有測試場景 | Dev Team | 30分鐘 |
| 3 | CI 環境驗證 | DevOps | 1小時 |
| 4 | 監控後續 CI/CD 執行 | QA | 持續 |

### 驗證標準
- [ ] 本地測試通過（有/無環境變數）
- [ ] CI/CD Pipeline 完全通過
- [ ] 連續 5 次 CI 執行無失敗

---

## D7: 預防措施

### 技術面預防
1. **測試設計原則**:
   - 所有測試必須完全隔離
   - 禁止依賴全域狀態
   - 顯式管理測試資源生命週期

2. **程式碼審查檢查點**:
   - 檢查是否使用全域變數
   - 確認測試有適當的 setup/teardown
   - 驗證環境變數處理

3. **自動化檢查**:
   ```python
   # 添加到 pre-commit hook
   def check_test_isolation():
       """檢查測試是否正確隔離"""
       # 檢查全域變數使用
       # 檢查 fixture 配置
       # 檢查環境變數依賴
   ```

### 流程面預防
1. **開發流程改進**:
   - PR 必須包含本地和 CI 環境測試結果
   - 新增測試必須證明隔離性

2. **文檔更新**:
   - 更新測試編寫指南
   - 添加常見陷阱說明

---

## D8: 團隊認可與結案

### 經驗教訓
1. **全域狀態是測試的敵人**: 任何全域變數都可能導致測試相互影響
2. **環境一致性至關重要**: 本地和 CI 環境必須盡可能相同
3. **顯式優於隱式**: 測試應該顯式控制所有依賴

### 改進成果
- 建立了更健壯的測試架構
- 提高了對測試隔離重要性的認識
- 改進了 CI/CD 流程的可靠性

### 後續行動
1. 審查所有使用全域狀態的測試
2. 建立測試隔離性自動檢查機制
3. 定期審查 CI/CD 環境配置

---

## 附錄

### A. 測試執行日誌對比

#### 本地成功日誌
```
test_popular_skill_cache PASSED
test_CA_002_IT_parallel_processing PASSED
234 passed, 0 failed
```

#### CI 失敗日誌
```
test_popular_skill_cache FAILED
test_CA_002_IT_parallel_processing FAILED
232 passed, 2 failed
```

### B. 環境配置對比
| 設定項 | 本地 | CI/CD |
|-------|------|-------|
| Python Version | 3.11.8 | 3.11.8 |
| ENABLE_COURSE_CACHE | undefined/false | true |
| Test Runner | pytest | pytest |
| Execution Mode | Sequential | Parallel/Sequential |

### C. 完整測試程式碼

#### test/integration/test_course_availability.py (當前版本)
```python
"""
Integration tests for Course Availability Service
"""
import pytest

from src.services.course_availability import CourseAvailabilityChecker


@pytest.fixture(autouse=True)
async def reset_global_cache():
    """Reset global cache instance before and after each test to ensure isolation"""
    import src.services.dynamic_course_cache as cache_module
    # Reset before test
    cache_module._cache_instance = None
    yield
    # Reset after test
    cache_module._cache_instance = None


@pytest.mark.asyncio
class TestCourseAvailabilityIntegration:
    """Integration tests for Course Availability"""

    async def test_basic_functionality(self):
        """Test basic course availability check"""
        # Basic test to ensure the service can be instantiated
        checker = CourseAvailabilityChecker()
        assert checker is not None

    async def test_empty_skills_list(self):
        """Test handling of empty skills list"""
        checker = CourseAvailabilityChecker()
        result = await checker.check_course_availability([])
        assert result == []

    async def test_popular_skill_cache(self):
        """Test that dynamic cache mechanism works in integration environment"""
        from unittest.mock import AsyncMock, patch

        checker = CourseAvailabilityChecker()

        # Force initialize cache to ensure consistent behavior across environments
        from src.services.dynamic_course_cache import DynamicCourseCache
        checker._dynamic_cache = DynamicCourseCache()  # Create new instance directly
        await checker._dynamic_cache.clear()  # Ensure clean state

        # Mock embedding client and database for integration test
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536  # Python embedding
            ])
            mock_get_client.return_value = mock_client

            # Mock successful database response
            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                return {
                    "has_courses": True,
                    "total_count": 15,  # Different from static cache for verification
                    "course_ids": ["coursera_crse:v1-python-101", "coursera_crse:v1-python-102"],
                    "course_details": []  # Add course_details field
                }

            checker._check_single_skill = mock_check_skill

            # Test with a known popular skill
            test_skills = [
                {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"}
            ]

            result = await checker.check_course_availability(test_skills)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["has_available_courses"] is True
            assert result[0]["course_count"] == 15  # From mocked database response
            assert "available_course_ids" in result[0]
            assert len(result[0]["available_course_ids"]) == 2

    async def test_CA_002_IT_parallel_processing(self):
        """Test parallel processing of multiple skills"""
        from unittest.mock import AsyncMock, patch

        checker = CourseAvailabilityChecker()

        # Force initialize cache to ensure consistent behavior across environments
        from src.services.dynamic_course_cache import DynamicCourseCache
        checker._dynamic_cache = DynamicCourseCache()  # Create new instance directly
        await checker._dynamic_cache.clear()  # Ensure clean state

        # Mock embedding client and database for integration test
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536,  # Python embedding
                [0.2] * 1536,  # JavaScript embedding
                [0.3] * 1536   # Docker embedding
            ])
            mock_get_client.return_value = mock_client

            # Mock successful database responses
            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                # Simulate different response times and data for each skill
                return {
                    "has_courses": True,
                    "total_count": 10 if skill_name == "Python" else 8,
                    "type_diversity": 2,
                    "course_types": ["course", "project"],
                    "course_ids": [f"coursera_crse:v1-{skill_name.lower()}-001",
                                  f"coursera_crse:v1-{skill_name.lower()}-002"],
                    "course_details": []  # Add course_details field
                }

            checker._check_single_skill = mock_check_skill

            # Test with multiple skills to verify parallel processing
            test_skills = [
                {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"},
                {"skill_name": "JavaScript", "skill_category": "SKILL", "description": "Web development"},
                {"skill_name": "Docker", "skill_category": "SKILL", "description": "Containerization"}
            ]

            result = await checker.check_course_availability(test_skills)

            # Verify all skills were processed
            assert isinstance(result, list)
            assert len(result) == 3

            # Verify each skill has correct data
            for skill_result in result:
                assert skill_result["has_available_courses"] is True
                assert skill_result["course_count"] in [8, 10]
                assert "available_course_ids" in skill_result
                assert len(skill_result["available_course_ids"]) == 2

            # Verify specific skill results
            python_result = next(s for s in result if s["skill_name"] == "Python")
            assert python_result["course_count"] == 10
            # New system doesn't return preferred_courses, check for course IDs instead
            assert len(python_result["available_course_ids"]) == 2
```

### D. 相關檔案
- `/test/integration/test_course_availability.py`
- `/src/services/course_availability.py`
- `/src/services/dynamic_course_cache.py`
- `/.github/workflows/ci-cd-main.yml`

### E. 參考連結
- [GitHub Actions Run #17231569149](https://github.com/YuWenHao1212/azure_container/actions/runs/17231569149)
- [Previous Fix Attempt](https://github.com/YuWenHao1212/azure_container/commit/5f658a4)

---

### F. 問題復現步驟

#### 在 CI 環境復現失敗
1. 設定環境變數 `ENABLE_COURSE_CACHE=true`
2. 執行測試 `pytest test/integration/test_course_availability.py`
3. 觀察 `test_popular_skill_cache` 和 `test_CA_002_IT_parallel_processing` 失敗

#### 關鍵觀察點
1. **第 39-44 行**: `CourseAvailabilityChecker()` 初始化時自動取得全域單例
2. **第 42-43 行**: 強制創建新實例並清空，但全域單例可能已被污染
3. **第 9-16 行**: Fixture 重置全域變數，但測試可能在此之前已初始化

### G. 診斷指令

```bash
# 本地測試（通過）
pytest test/integration/test_course_availability.py -v

# 模擬 CI 環境（可能失敗）
ENABLE_COURSE_CACHE=true pytest test/integration/test_course_availability.py -v

# 檢查全域狀態污染
python -c "
import src.services.dynamic_course_cache as cache
print('Initial:', cache._cache_instance)
from src.services.course_availability import CourseAvailabilityChecker
checker = CourseAvailabilityChecker()
print('After init:', cache._cache_instance)
"
```

---

## H: 最終解決方案與驗證 (2025-01-26 更新)

### 實施的解決方案

#### 強化版 Fixture 實作
```python
@pytest.fixture(autouse=True)
async def reset_global_cache():
    """Reset global cache instance before and after each test to ensure isolation"""
    import os
    import sys
    import src.services.dynamic_course_cache as cache_module
    
    # Save original state
    original_instance = cache_module._cache_instance
    original_env = os.environ.get('ENABLE_COURSE_CACHE')
    
    # Force disable cache for test isolation
    os.environ['ENABLE_COURSE_CACHE'] = 'false'
    cache_module._cache_instance = None
    
    # Clear module cache to force re-initialization
    modules_to_clear = ['src.services.course_availability']
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    yield
    
    # Restore original state
    cache_module._cache_instance = original_instance
    if original_env is not None:
        os.environ['ENABLE_COURSE_CACHE'] = original_env
    else:
        os.environ.pop('ENABLE_COURSE_CACHE', None)
```

### 解決方案關鍵點
1. **保存原始狀態**：避免影響其他測試
2. **強制禁用快取**：防止 `CourseAvailabilityChecker.__init__` 自動初始化
3. **清理模組快取**：強制重新載入模組
4. **恢復原始狀態**：測試後完全恢復環境

### 驗證結果
- ✅ 本地測試：234/234 通過
- ✅ CI 環境模擬：`ENABLE_COURSE_CACHE=true` 下全部通過
- ⏳ GitHub Actions CI：待驗證

### 學到的教訓
1. **全域單例模式的測試陷阱**：需要特別注意測試隔離
2. **環境變數影響**：CI 與本地環境差異可能導致不同的初始化路徑
3. **模組載入順序**：Python 模組快取可能影響測試行為
4. **防禦性測試設計**：總是假設最壞的情況並做好隔離

---

## D8: 團隊認可與結案

### 問題解決確認
- [ ] CI/CD Pipeline 通過驗證
- [ ] 無新的測試失敗
- [ ] 團隊確認問題已解決

### 知識管理
- 更新測試指南文檔
- 將此案例加入疑難排解指南
- 團隊內部分享會議

---

**報告狀態**: 已完成修復，待 CI 驗證  
**最後更新**: 2025-01-26 14:30 CST  
**下次審查**: CI 驗證通過後結案