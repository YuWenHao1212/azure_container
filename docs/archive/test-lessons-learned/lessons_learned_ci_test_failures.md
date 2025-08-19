# Lessons Learned: CI/CD 測試失敗除錯案例

## 事件摘要
**日期**: 2025-08-19  
**問題**: Course Batch Query 單元測試在本地通過但在 GitHub Actions CI 中失敗  
**影響**: CI/CD pipeline 無法部署，阻塞了所有後續提交  
**解決時間**: 約 2 小時

## 問題描述

### 症狀
- 本地執行 `python test/scripts/pre_commit_check_advanced.py` 全部 217 個測試通過
- GitHub Actions CI 中 Course Batch Query 有 8 個單元測試失敗（只有 2/10 通過）
- 錯誤訊息：`Database configuration not found. Please set POSTGRES_* environment variables`

### 時間線
1. **Commit 386ff72** (2025-08-18) - ✅ 所有測試通過
2. **Commit 13f6bba** (2025-08-18) - ❌ 新增 HTML 格式化功能後測試開始失敗
3. **Commit a4ced8b** (2025-08-19) - ❌ 修復 TestConfig 但問題仍存在
4. **Commit ce8848e** (2025-08-19) - ✅ 修復根本原因，測試通過

## 根本原因分析

### 1. 程式碼變更問題

在 commit `13f6bba` 中重構 `get_courses_by_ids` 方法時，新增了無條件的資料庫初始化：

```python
# 問題程式碼（13f6bba）
async def get_courses_by_ids(self, request):
    # ...
    if uncached_ids:
        # 無條件呼叫 initialize
        await self.initialize()  # ❌ 問題在這裡
        async with self._connection_pool.acquire() as conn:
            # ...
```

### 2. 環境差異

#### 本地環境
- 存在配置檔案：
  - `tools/coursera_db_manager/config/postgres_connection.json`
  - `temp/postgres_connection.json`
- `initialize()` 方法可以找到配置檔案並成功載入

#### CI 環境
- 乾淨的環境，沒有配置檔案
- 沒有設定 `POSTGRES_*` 環境變數（單元測試不需要真實資料庫）
- `initialize()` 找不到任何配置，拋出錯誤

### 3. 測試設計問題

單元測試已經 mock 了 `_connection_pool`：
```python
# test/unit/test_course_batch_unit.py
service = CourseSearchService()
service._connection_pool = AsyncMock()  # 已經 mock
```

但程式碼仍然呼叫 `initialize()`，試圖建立真實的資料庫連線。

## 解決方案

### 修復程式碼

```python
# 修復後的程式碼（ce8848e）
async def get_courses_by_ids(self, request):
    # ...
    if uncached_ids:
        # 只在連線池不存在時才初始化
        if not self._connection_pool:  # ✅ 加入條件判斷
            await self.initialize()
        async with self._connection_pool.acquire() as conn:
            # ...
```

## 學到的教訓

### 1. 單元測試設計原則
- **完全隔離**: 單元測試不應依賴外部資源（資料庫、檔案、網路）
- **Mock 優先**: 已經 mock 的資源不應再被初始化
- **環境無關**: 測試應該在任何環境下都能執行

### 2. 防禦性編程
- **條件初始化**: 檢查資源是否已存在再決定是否初始化
- **優雅降級**: 在找不到配置時提供有意義的錯誤訊息
- **最小依賴**: 減少對外部配置的依賴

### 3. CI/CD 最佳實踐
- **環境一致性**: 確保本地測試環境盡可能接近 CI 環境
- **早期檢測**: 在本地模擬 CI 環境進行測試
  ```bash
  # 模擬 CI 環境測試
  CI=true GITHUB_ACTIONS=true python -m pytest
  ```
- **詳細日誌**: 在 CI 失敗時提供足夠的診斷資訊

### 4. 除錯技巧
- **二分法**: 使用 git bisect 或手動比對找出問題引入的 commit
- **差異分析**: 比較正常和異常版本的程式碼差異
  ```bash
  git diff 386ff72..13f6bba -- src/services/course_search.py
  ```
- **診斷腳本**: 建立專門的診斷腳本來收集環境資訊

## 預防措施

### 1. 程式碼審查清單
- [ ] 新增的初始化邏輯是否有條件判斷？
- [ ] 單元測試是否真正獨立於外部資源？
- [ ] 重構是否保留了原有的防禦性檢查？

### 2. 測試策略
- 在 PR 階段就執行完整的測試套件
- 使用 GitHub Actions 的 pull request 觸發器進行預檢
- 建立專門的 CI 環境測試腳本

### 3. 監控和警報
- 設定 CI 失敗通知
- 追蹤測試成功率趨勢
- 定期檢查測試執行時間

## 相關檔案和工具

### 診斷工具
- `/test/scripts/diagnose_ci_env.py` - CI 環境診斷腳本
- `/test/scripts/test_single_course_batch.py` - 單一測試除錯腳本

### 配置檔案
- `/test/config.py` - 測試環境配置
- `/.github/workflows/ci-cd-main.yml` - CI/CD 配置

### 關鍵程式碼
- `/src/services/course_search.py` - CourseSearchService.get_courses_by_ids()
- `/test/unit/test_course_batch_unit.py` - Course Batch Query 單元測試

## 總結

這次事件突顯了單元測試環境隔離的重要性。主要教訓是：
1. **單元測試必須完全獨立** - 不依賴任何外部配置或資源
2. **重構時保留防禦性檢查** - 不要移除條件判斷邏輯
3. **環境差異是常見問題來源** - 始終考慮本地與 CI 環境的差異

透過這次經驗，我們改進了測試的健壯性，並建立了更好的除錯流程。

---

**文件版本**: 1.0.0  
**建立日期**: 2025-08-19  
**作者**: Claude Code + WenHao  
**標籤**: #CI/CD #Testing #Debugging #LessonsLearned