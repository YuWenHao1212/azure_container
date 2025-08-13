# V4 架構實作指南

## 🎯 實作重點

本文檔詳細說明如何從 V3 並行架構遷移到 V4 順序執行架構。

## 📋 改動清單

### 1. 核心服務改動

#### `combined_analysis_v2.py` 改動項目

- [x] 移除 `minimal_index_result` 建立
- [x] 改變 Gap Analysis 執行時機（等待 Index 完成）
- [x] 移除未使用的 `keyword_coverage` 變數
- [x] 調整時間追蹤邏輯

### 2. Prompt 改動

#### `v2.1.1.yaml` 改動項目

- [x] 新增 `Similarity Score: {similarity_score}%` 到 context
- [x] 更新匹配度判斷邏輯（基於相似度分數）
- [x] 調整時程建議（40%/50%/70%/80% 門檻）
- [x] 更新範例（Strong/Moderate/Limited/Poor）

### 3. 服務整合改動

#### `gap_analysis_v2.py` 改動項目

- [x] 新增 `{similarity_score}` 佔位符替換
- [x] 保留 `{coverage_percentage}` 相容性

## 🔧 詳細實作步驟

### Step 1: 修改並行執行邏輯

**位置**: `src/services/combined_analysis_v2.py`, Line 225-300

**原始程式碼（V3）**：
```python
# 1. 啟動關鍵字和 Embeddings（並行）
keyword_task = asyncio.create_task(...)
embedding_task = asyncio.create_task(...)

# 2. 等待關鍵字完成
keyword_coverage = await keyword_task

# 3. 立即啟動 Gap Analysis（不等 Index）
minimal_index_result = {
    "similarity_percentage": 0,  # 假值
}
gap_task = asyncio.create_task(
    self.gap_service.analyze_with_context(
        index_result=minimal_index_result
    )
)

# 4. Index 在背景執行
index_task = asyncio.create_task(...)

# 5. 等待兩者完成
gap_result = await gap_task
index_result = await index_task
```

**新程式碼（V4）**：
```python
# 1. 啟動關鍵字和 Embeddings（並行）
keyword_task = asyncio.create_task(...)
embedding_task = asyncio.create_task(...)

# 2. 等待兩者完成
await keyword_task
await embedding_task

# 3. 執行 Index Calculation（順序）
index_result = await self.index_service.calculate_index(
    resume=resume,
    job_description=job_description,
    keywords=keywords
)

# 4. 執行 Gap Analysis（使用真實 index_result）
gap_result = await self.gap_service.analyze_with_context(
    resume=resume,
    job_description=job_description,
    index_result=index_result,  # 真實相似度
    language=language,
    options=analysis_options
)
```

### Step 2: 更新 Prompt 模板

**位置**: `src/prompts/gap_analysis/v2.1.1.yaml`

**關鍵改動**：

1. **Context 區塊新增相似度**：
```yaml
<context>
Similarity Score: {similarity_score}%  # 新增
Covered Keywords: {covered_keywords}
Missing Keywords: {missing_keywords}
Keyword Coverage: {coverage_percentage}%
</context>
```

2. **評估邏輯更新**：
```yaml
Opening (30-35 words): Position Assessment
- Determine match level based on similarity score:
  * Strong match (80%+): "You're a strong candidate"
  * Good potential (70-79%): "You show good potential"
  * Moderate (50-70%): "moderate/good alignment"
  * Limited (40-50%): "foundational skills"
  * Poor (<40%): "significant development needed"
```

### Step 3: 更新佔位符處理

**位置**: `src/services/gap_analysis_v2.py`, Line 235-250

**新增佔位符替換**：
```python
# 替換 similarity_score（新增）
user_prompt = user_prompt.replace(
    "{similarity_score}",
    str(index_result.get('similarity_percentage', 0))
)

# 保留既有的替換
user_prompt = user_prompt.replace(
    "{coverage_percentage}",
    str(keyword_coverage.get('coverage_percentage', 0))
)
```

## 🧪 測試驗證

### 單元測試確認

```bash
# 執行 Gap Analysis 測試
pytest test/unit/services/test_gap_analysis_v2.py -v

# 執行整合測試
pytest test/integration/test_gap_analysis_v2_integration_complete.py -v
```

### 手動測試腳本

```python
# scripts/test_v4_architecture.py
import asyncio
import time
from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2

async def test_v4():
    service = CombinedAnalysisServiceV2()
    
    start = time.time()
    result = await service.analyze(
        resume="...",
        job_description="...",
        keywords=["Python", "FastAPI"],
        language="en"
    )
    
    print(f"Total time: {time.time() - start:.2f}s")
    print(f"Similarity: {result['index_calculation']['similarity_percentage']}%")
    print(f"Gap Analysis received similarity: Check logs")
    
asyncio.run(test_v4())
```

## 📊 效能基準測試

### 預期指標

| 階段 | V3 時間 | V4 時間 | 說明 |
|------|---------|---------|------|
| 關鍵字匹配 | 50ms | 50ms | 無變化 |
| Embeddings | 1300ms | 1300ms | 無變化 |
| Index Calculation | 1200ms | 1200ms | 無變化 |
| Gap Analysis | 1750ms | 1000ms | 較快（有完整 context） |
| **總時間** | **~2500ms** | **~3500ms** | **+1秒** |

### 監控重點

```python
# 日誌中應該看到
INFO: Index calculation completed: similarity=72%
INFO: Gap Analysis starting with similarity_score=72
INFO: Loaded gap_analysis prompt version: 2.1.1
```

## 🚨 常見問題

### Q1: Gap Analysis 仍使用 0% 相似度？

**檢查點**：
1. 確認 `combined_analysis_v2.py` 已更新為順序執行
2. 確認 `v2.1.1.yaml` 包含 `{similarity_score}` 佔位符
3. 確認 `gap_analysis_v2.py` 有替換邏輯

### Q2: 效能下降太多？

**優化選項**：
1. 考慮快取 embeddings
2. 使用更快的 embedding 模型
3. 實作漸進式回應

### Q3: 測試失敗？

**可能原因**：
1. Mock 資料需要更新（加入 similarity_percentage）
2. 時間斷言需要調整（預期時間增加）
3. 並行測試假設需要更新

## 📝 檢查清單

部署前確認：

- [ ] Ruff 檢查通過
- [ ] 所有測試通過（174 個測試）
- [ ] 日誌顯示正確的相似度傳遞
- [ ] Docker 映像建置成功
- [ ] 健康檢查端點正常

## 🔄 回滾程序

如需回滾到 V3：

1. **Git 回滾**：
```bash
git revert <v4-commit-hash>
git push origin main
```

2. **快速切換**（使用環境變數）：
```bash
# 可以加入功能開關（未實作）
USE_V3_PARALLEL=true
```

3. **Container Apps 回滾**：
```bash
az containerapp revision list \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi

az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --revision <v3-revision>
```

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-13  
**作者**: AI Resume Advisor Team