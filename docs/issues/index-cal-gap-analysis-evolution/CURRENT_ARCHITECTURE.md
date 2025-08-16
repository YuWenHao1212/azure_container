# 當前架構詳解 - Index Cal & Gap Analysis V4

**文檔版本**: 1.0.0  
**最後更新**: 2025-08-16  
**架構版本**: V4 (Production)  
**狀態**: ✅ Active in Production

## 🎯 架構設計理念

V4 架構選擇**準確性優先**策略，確保 Gap Analysis 使用真實的相似度分數進行評估，提供可靠的職涯建議。

## 🏗️ 架構演進歷程

### V1: 完全順序執行（原始版本）
```
關鍵字匹配 → Embeddings → Index Calculation → Gap Analysis
總時間：約 4-5 秒
```

### V2: 部分並行
```
關鍵字匹配 → Embeddings → [Index + Gap 並行]
總時間：約 3-4 秒
```

### V3: 激進並行優化（之前版本）
```
時間軸 (ms)
T=0    ├── 關鍵字匹配 (50ms)
       └── Embeddings 生成 (1300ms)
       
T=50   ├── 關鍵字完成 ✓
       ├── Gap Analysis 啟動（使用 minimal_index_result）
       └── Embeddings 繼續...

T=1300 ├── Embeddings 完成 ✓
       └── Index Calculation 啟動

T=1800 └── Gap Analysis 完成 ✓（未使用真實 similarity_score）

T=2500 └── Index Calculation 完成（結果未被 Gap Analysis 使用）
```

**V3 問題**：
- Gap Analysis 使用假的 similarity_score (設為 0)
- 無法根據真實相似度判斷匹配程度
- 評估不準確，可能誤導求職者

### V4: 準確性優先架構（當前版本）
```
時間軸 (ms)
T=0    ├── 關鍵字匹配 (50ms)
       └── Embeddings 生成 (1300ms)

T=1300 ├── Embeddings 完成 ✓
       └── Index Calculation 啟動

T=2500 ├── Index Calculation 完成 ✓（包含真實 similarity_score）
       └── Gap Analysis 啟動（使用完整 index_result）

T=3500 └── Gap Analysis 完成 ✓（準確評估）
```

## 🔄 主要程式碼改變

### 1. CombinedAnalysisServiceV2 (`src/services/combined_analysis_v2.py`)

**之前（V3）**：
```python
# Gap Analysis 立即開始，使用假的 index_result
minimal_index_result = {
    "keyword_coverage": keyword_coverage,
    "similarity_percentage": 0,  # 假的分數！
    "raw_similarity_percentage": 0,
}

gap_task = asyncio.create_task(
    self.gap_service.analyze_with_context(
        index_result=minimal_index_result,  # 不準確
        ...
    )
)

# Index 在背景執行，結果未被使用
index_task = asyncio.create_task(
    self.index_service.calculate_index(...)
)
```

**現在（V4）**：
```python
# 先完成 Index Calculation
index_result = await self.index_service.calculate_index(
    resume=resume,
    job_description=job_description,
    keywords=keywords
)

# 再執行 Gap Analysis，使用真實的 index_result
gap_result = await self.gap_service.analyze_with_context(
    index_result=index_result,  # 包含真實 similarity_score
    ...
)
```

### 2. Gap Analysis Prompt (`src/prompts/gap_analysis/v2.1.1.yaml`)

**新增 Similarity Score 支援**：
```yaml
user: |
  <context>
  Similarity Score: {similarity_score}%  # 新增：真實相似度分數
  Covered Keywords: {covered_keywords}
  Missing Keywords: {missing_keywords}
  Keyword Coverage: {coverage_percentage}%
  </context>
```

**基於 Similarity Score 的評估邏輯**：
```yaml
Opening (30-35 words): Position Assessment
- Determine match level based on similarity score:
  * Strong match (80%+): "You're a strong candidate"
  * Good potential (70-79%): "You show good potential"
  * Moderate (50-70%): "You have moderate/good alignment"
  * Limited (40-50%): "While you have foundational skills"
  * Poor (<40%): "This role requires significant development"
```

## 📊 效能影響分析

### 時間成本
| 指標 | V3 (並行) | V4 (順序) | 差異 |
|------|-----------|-----------|------|
| 總回應時間 | ~2.5 秒 | ~3.5 秒 | +1 秒 |
| Gap Analysis 啟動 | T=50ms | T=2500ms | +2450ms |
| 並行效率 | 高 | 中 | -40% |

### 準確性提升
| 評估項目 | V3 | V4 | 改善 |
|----------|-----|-----|------|
| 使用真實相似度 | ❌ | ✅ | 100% |
| 匹配度判斷準確性 | 低 | 高 | 顯著提升 |
| 時程建議合理性 | 粗略 | 精確 | 大幅改善 |
| 用戶信任度 | 中 | 高 | 提升 |

## 🎯 相似度分數門檻值

### 最終確定的門檻（2025-08-13 更新）

| 相似度範圍 | 匹配等級 | 評估描述 | 建議時程 |
|-----------|---------|----------|----------|
| **80%+** | Strong Match | 幾乎理想匹配 | 1-2 天履歷優化 |
| **70-79%** | Good Potential | 有競爭力的候選人 | 1-2 週針對性改進 |
| **60-70%** | Good Alignment | 相關經驗豐富 | 1-2 個月提升 |
| **50-60%** | Moderate Alignment | 有基礎但需學習 | 2-3 個月發展 |
| **40-50%** | Limited Match | 基礎技能存在 | 3-6 個月系統學習 |
| **<40%** | Poor Match | 領域差異大 | 6-12 個月或考慮其他職位 |

### 門檻設計理由

- **40% 分界線**：區分「同領域但技能不足」vs「不同領域」
- **50-70% 寬區間**：涵蓋大多數候選人，細分為技能導向和呈現導向
- **70% 以上**：已是合格候選人，主要是優化問題

## 🚀 部署與回滾策略

### 部署步驟
1. 程式碼推送到 GitHub
2. CI/CD 自動建置 Docker 映像
3. Azure Container Apps 自動部署
4. 健康檢查驗證

### 回滾方案
如果發現問題，可以快速回滾到 V3：
```bash
# 使用 GitHub Actions 回滾
gh workflow run rollback.yml

# 或手動切換到先前版本
az containerapp revision set-mode \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --mode single \
  --revision <previous-revision-name>
```

## 📈 監控指標

### 關鍵指標追蹤
- **回應時間**: 預期從 2.5s → 3.5s
- **相似度分數分布**: 監控各區間的分布情況
- **用戶滿意度**: 追蹤評估準確性回饋

### 日誌範例
```log
INFO: V2 Index calculation completed: similarity=72%
INFO: Gap Analysis using real similarity score: 72%
INFO: Overall assessment: Good potential candidate
```

## 🤔 設計決策理由

### 為什麼選擇 V4（準確性優先）？

1. **用戶體驗**
   - 準確的評估比快 1 秒更重要
   - 錯誤的期望管理會損害用戶信任

2. **商業價值**
   - 精確的匹配度評估提升平台可信度
   - 合理的時程建議增加用戶黏性

3. **技術考量**
   - 3.5 秒仍在可接受範圍內
   - 未來可通過快取等方式優化

## 📝 未來優化方向

1. **智能快取**
   - 快取常見 JD 的 embeddings
   - 減少重複計算

2. **漸進式回應**
   - 先返回關鍵字匹配結果
   - 逐步更新相似度和評估

3. **混合模式**
   - 簡單查詢使用 V3（快速）
   - 詳細分析使用 V4（準確）

## 📚 相關文檔

- [Prompt 版本管理](../prompt-version-management.md)
- [Gap Analysis v2.1.1 Prompt](../../src/prompts/gap_analysis/v2.1.1.yaml)
- [API 文檔](../API.md)

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-13  
**作者**: AI Resume Advisor Team  
**狀態**: 已部署生產環境