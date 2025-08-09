# Index Cal & Gap Analysis V3 性能優化計劃

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-09  
**狀態**: 實驗規劃中  
**目標**: P95 響應時間從 9.12s → 5s（45% 改善）

## 1. 執行摘要

### 1.1 當前狀態（V2 已實施）
- **P50 響應時間**: 7.42 秒
- **P95 響應時間**: 9.12 秒  
- **最小響應時間**: 6.44 秒
- **平均響應時間**: 7.41 秒
- **成功率**: 100%

### 1.2 優化目標
- **P95 < 5 秒**（降低 45%）
- **P50 < 4 秒**（降低 46%）
- **保持 100% 成功率**
- **維持結果品質**

## 2. 性能分析

### 2.1 時間分布（基於架構分析）

```
┌─────────────────────────────────────────────────────────┐
│                  API 總響應時間: ~9.1s                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Phase 1: Embedding Generation (~1.2s, 13%)             │
│  ├─ Resume Embedding: ~600ms                            │
│  └─ JD Embedding: ~600ms (可並行)                        │
│                                                          │
│  Phase 2: Index Calculation (~2.0s, 22%)                │
│  ├─ Keyword Matching: ~50ms (0.5%)                      │
│  └─ Index LLM Call: ~1.95s (21.5%)                      │
│                                                          │
│  Phase 3: Gap Analysis (~5.9s, 65%)                     │
│  ├─ Context Preparation: ~100ms (1%)                    │
│  └─ Gap Analysis LLM Call: ~5.8s (64%) 🔴 主要瓶頸        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 關鍵發現

1. **主要瓶頸**: Gap Analysis LLM 調用佔總時間 64%
2. **依賴關係**: Gap Analysis 需要 Index 結果（matched/missing keywords）
3. **快速操作**: Keyword matching 只需 50ms，有並行潛力
4. **架構問題**: 當前 V2 實際為序列執行，非真正並行

### 2.3 V2 實施問題分析

從 `CombinedAnalysisServiceV2` 代碼分析：
```python
async def _execute_parallel_analysis():
    # 實際上是序列執行！
    # Phase 1 → Phase 2 → Phase 3
    # 沒有真正的並行處理
```

## 3. 實驗計劃

### 3.1 快速測量實驗（5 個樣本）

#### 實驗設計
```python
# 在 combined_analysis_v2.py 添加詳細時間點
timing_points = {
    "start": time.time(),
    "embedding_start": None,
    "embedding_end": None,
    "keyword_match_start": None,
    "keyword_match_end": None,
    "index_llm_start": None,
    "index_llm_end": None,
    "gap_context_start": None,
    "gap_context_end": None,
    "gap_llm_start": None,
    "gap_llm_end": None,
    "end": None
}
```

#### 測試數據
- 使用標準測試 JD 和 Resume（200+ 字元）
- 5 個連續請求，收集時間數據
- 計算各階段平均時間和變異性

### 3.2 優化實驗矩陣

| 實驗 | 優化策略 | 預期節省 | 風險 | 優先級 |
|------|---------|---------|------|--------|
| **A** | 並行 Keyword Matching | 0-50ms | 低 | 高 |
| **B** | True Parallel Phases | 1-2s | 中 | 高 |
| **C** | Gap Analysis Prompt 優化 | 2-3s | 中 | 高 |
| **D** | Streaming Response | 感知改善 | 低 | 中 |
| **E** | Context Size 優化 | 0.5-1s | 低 | 中 |

## 4. 優化方案

### 4.1 短期優化（1-2 天）

#### 方案 A: 並行 Keyword Matching
```python
async def _execute_optimized_analysis():
    # 並行執行 Embedding 和 Keyword Matching
    embedding_task = create_task(generate_embeddings())
    keyword_task = create_task(match_keywords())  # 只需 50ms
    
    embeddings = await embedding_task
    keywords = await keyword_task
    
    # 繼續 Index 和 Gap Analysis
```
**預期改善**: 節省 0-50ms（邊際效益）

#### 方案 B: 真正的並行處理
```python
async def _true_parallel_execution():
    # Phase 1: Embedding (可真正並行)
    resume_emb_task = create_task(get_resume_embedding())
    jd_emb_task = create_task(get_jd_embedding())
    
    # Phase 2: Index 準備（不依賴 embedding 的部分）
    keyword_prep_task = create_task(prepare_keywords())
    
    # 等待必要結果
    resume_emb = await resume_emb_task
    jd_emb = await jd_emb_task
    keywords = await keyword_prep_task
    
    # Index LLM call
    index_result = await calculate_index_with_llm(...)
    
    # Gap Analysis（仍需等待 Index）
    gap_result = await analyze_gap(index_result, ...)
```
**預期改善**: 節省 1-2 秒

### 4.2 中期優化（3-5 天）

#### 方案 C: Gap Analysis Prompt 工程
```python
# 原始 Prompt（複雜，產生大量輸出）
original_prompt = """
Provide comprehensive gap analysis with:
1. Detailed skill gaps
2. Experience gaps  
3. Education gaps
4. Recommendations
5. Priority rankings
...
"""

# 優化 Prompt（精簡，聚焦關鍵輸出）
optimized_prompt = """
Based on matched ({matched_count}) and missing ({missing_count}) keywords:
List TOP 5 gaps and brief recommendations.
Format: JSON with gaps[] and recommendations[]
"""
```
**預期改善**: 節省 2-3 秒（減少 token 生成）

#### 方案 D: Streaming Response
```python
async def stream_combined_analysis():
    # 立即返回 Index 結果
    yield {"index_calculation": index_result, "status": "processing"}
    
    # Gap Analysis 完成後追加
    yield {"gap_analysis": gap_result, "status": "complete"}
```
**預期改善**: 感知延遲降低 2-3 秒

### 4.3 長期優化（評估後決定）

#### 方案 E: 智能 Context 管理
- 根據 Index 結果動態調整 Gap Analysis 輸入
- matched_keywords 多時簡化分析
- missing_keywords 多時深入分析

#### 方案 F: 模型選擇優化
- Gap Analysis 使用 GPT-4.1-mini（更快）
- 複雜案例才升級到 GPT-4.1

## 5. 實施路線圖

### Phase 1: 測量（立即）
- [ ] 添加詳細時間追蹤點
- [ ] 執行 5 個測試樣本
- [ ] 分析時間分布數據

### Phase 2: 快速優化（Day 1）
- [ ] 實施並行 Keyword Matching
- [ ] 修正 V2 並行架構問題
- [ ] 測試驗證改善效果

### Phase 3: Prompt 優化（Day 2）
- [ ] 分析現有 Gap Analysis prompt
- [ ] 設計優化版本（減少 50% tokens）
- [ ] A/B 測試品質影響

### Phase 4: 驗證部署（Day 3）
- [ ] 執行完整效能測試
- [ ] 確認 P95 < 5s 目標
- [ ] 準備生產部署

## 6. 成功指標

### 必須達成
- ✅ P95 響應時間 < 5 秒
- ✅ 維持 100% 成功率
- ✅ 結果品質不降低

### 期望達成
- P50 響應時間 < 4 秒
- Gap Analysis 時間減少 40%
- 用戶滿意度提升

## 7. 風險與緩解

| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| Prompt 優化影響品質 | 高 | A/B 測試，保留原版本 |
| 並行處理引入 race condition | 中 | 完整測試，錯誤處理 |
| LLM 模型切換不穩定 | 中 | Feature flag 控制 |

## 8. 決策記錄

### 為什麼不先考慮快取？
- 用戶要求先考慮 worst case（無快取）
- 快取命中率在真實場景中較低
- 專注於根本性能改善

### 為什麼 Gap Analysis 是重點？
- 佔總時間 64%，最大改善空間
- Prompt 工程可顯著減少處理時間
- 不需要架構大改

### 為什麼保持 5 個樣本測試？
- 快速獲得方向性數據
- 避免過度測試延誤優化
- 足夠識別主要瓶頸

## 9. 附錄

### A. 測試命令
```bash
# 執行性能測試
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh

# 查看最新結果
cat test/logs/test_suite_real_api_perf_e2e_*_summary.json | jq '.tests[0].p95_time_s'
```

### B. 監控查詢
```python
# 查看 phase timings
logger.info(f"Phase timings: {phase_timings}")
```

### C. 相關文檔
- [V2 重構計劃](../index-cal-and-gap-analysis-refactor/refactoring-plan.md)
- [V2 實施完成報告](../../memory/index-cal-gap-analysis-v2-refactor-completion.md)

---

**下一步行動**: 實施詳細時間追蹤點，執行 5 個測試樣本