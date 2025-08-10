# 履歷客製化功能 (v2.1.0-simplified)

## 功能概述

運用 AI 技術根據特定職缺要求客製化履歷內容，在保持真實性的前提下，優化表達方式以提高匹配度。

**v2.1.0-simplified 最新優化** 🚀
- **兩階段架構**：Instruction Compiler (GPT-4.1 mini) + Resume Writer (GPT-4)
- **智能 Gap 分類處理**：根據 [Skill Gap] 和 [Presentation Gap] 採用不同優化策略
- **Prompt 簡化**：從 717 行減少到 380 行（減少 47%）
- **成本優化**：降低 API 成本 40%+ (token 使用量減少 44%)
- **效能提升**：P50 < 4.0秒，比 v2.0.0 更快

## API 端點

`POST /api/v1/tailor-resume`

## 核心功能

### 1. 智能改寫
- **關鍵字融入**：自然嵌入職缺關鍵字
- **經驗強調**：突顯相關工作經歷
- **成就量化**：加入具體數據支撐
- **語氣調整**：符合公司文化

### 2. 結構優化
- **段落重組**：調整內容優先順序
- **篇幅控制**：保持適當長度
- **重點突出**：強調匹配項目
- **邏輯流暢**：確保連貫性

### 3. 多種強調等級
- **低度強調**：微調用詞
- **中度強調**：調整重點
- **高度強調**：重構內容

## 技術實作

### v2.0.0 兩階段架構

#### Stage 1: Instruction Compiler (GPT-4.1 mini)
- **目的**：分析 Gap Analysis 結果，生成結構化優化指令
- **模型**：GPT-4.1 mini（成本降低 200x）
- **處理時間**：~280ms
- **輸出**：JSON 格式的優化指令

#### Stage 2: Resume Writer (GPT-4)
- **目的**：根據指令執行履歷優化
- **模型**：GPT-4 (gpt4o-2)
- **處理時間**：~2100ms
- **輸出**：優化後的 HTML 履歷

### 處理流程
```python
1. 接收 Gap Analysis 結果（外部 API 提供）
2. Stage 1: Instruction Compiler
   - 分析 [Skill Gap] 和 [Presentation Gap]
   - 生成針對性優化指令
   - Fallback 機制確保穩定性
3. Stage 2: Resume Writer
   - 執行指令優化履歷
   - 整合缺失關鍵字
   - 強化現有技能呈現
4. 後處理與驗證
5. 返回優化結果與 metadata
```

### 品質控制
- 事實一致性檢查
- 關鍵字覆蓋驗證
- 語法錯誤檢測
- 重複內容過濾

## 使用範例

### 請求範例 (v2.1.0-simplified)
```python
import requests

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/tailor-resume",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        "job_description": "Senior Backend Engineer needed with Python, Kubernetes...",  # 最少 200 字元
        "original_resume": "<html><body><h2>Experience</h2>...</body></html>",  # 最少 200 字元
        "gap_analysis": {  # 必填 - 來自 Gap Analysis API 的結果
            "core_strengths": ["Python expertise", "API development"],
            "key_gaps": [
                "[Skill Gap] Kubernetes orchestration - No experience",
                "[Presentation Gap] Machine Learning - Has experience but not highlighted"
            ],
            "quick_improvements": ["Add ML projects to resume", "Take Kubernetes course"],
            "covered_keywords": ["Python", "API", "Docker"],
            "missing_keywords": ["Kubernetes", "ML", "GraphQL"],
            "coverage_percentage": 75,  # 選填 - 來自 Index Calculation API
            "similarity_percentage": 80  # 選填 - 來自 Index Calculation API
        },
        "options": {
            "language": "en"
        }
    }
)
```

### 回應範例 (v2.1.0-simplified)
```json
{
  "success": true,
  "data": {
    "optimized_resume": "<h2>John Smith</h2>
<p>Senior Backend Engineer with 8+ years Python expertise...</p>",
    "applied_improvements": [
      "[Presentation Gap] Machine Learning - Added ML project details to experience section",
      "[Skill Gap] Kubernetes - Positioned Docker experience as foundation for container orchestration",
      "Quantified Python experience (8+ years)",
      "Added 3 missing keywords naturally",
      "Enhanced achievement metrics (40% performance improvement)"
    ],
    "gap_analysis_insights": {
      "presentation_gaps_addressed": 1,
      "skill_gaps_positioned": 1,
      "total_gaps_processed": 2,
      "keywords_integrated": 3
    },
    "stage_timings": {
      "instruction_compilation_ms": 285,
      "resume_writing_ms": 2150,
      "total_processing_ms": 2435
    },
    "metadata": {
      "version": "v2.1.0-simplified",
      "pipeline": "two-stage",
      "models": {
        "instruction_compiler": "gpt41-mini",
        "resume_writer": "gpt4o-2"
      }
    }
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

## 改寫策略

### Gap 類型處理策略 (v2.1.0-simplified)
| Gap 類型 | 處理策略 | 範例 |
|----------|----------|------|
| [Presentation Gap] | 強化現有技能呈現 | "Has Python" → "8+ years Python expertise" |
| [Skill Gap] | 策略性定位相關技能 | "No K8s" → "Docker experience, ready for orchestration" |

### 強調等級說明
| 等級 | 說明 | 改動程度 | 適用情況 |
|------|------|----------|----------|
| low | 微調優化 | 10-20% | 已高度匹配 |
| medium | 適度調整 | 30-50% | 部分匹配 |
| high | 大幅改寫 | 60-80% | 需要轉型 |

### 改寫原則
1. **真實性優先**：不虛構經歷
2. **相關性導向**：聚焦匹配項目
3. **價值展現**：量化成就
4. **個性保留**：維持個人特色

## 關鍵技術

### Instruction Compiler (Stage 1)
```json
{
  "purpose": "分析 Gap 並生成優化指令",
  "input": "Gap Analysis 結果 (包含 [Skill Gap] 和 [Presentation Gap])",
  "output": {
    "summary": {
      "action": "CREATE/MODIFY",
      "keywords_to_integrate": ["keyword1", "keyword2"]
    },
    "skills": {
      "presentation_gaps_to_surface": ["hidden skill"],
      "skill_gaps_to_imply": ["skill to position"]
    },
    "optimization_strategy": {
      "presentation_gaps_count": 2,
      "skill_gaps_count": 1,
      "priority_keywords": ["top keywords"]
    }
  }
}
```

### Resume Writer (Stage 2)
```yaml
系統提示:
  角色: 專業履歷優化專家
  任務: 根據指令優化履歷
  限制:
    - 保持事實準確
    - 不添加虛假資訊
    - 自然整合關鍵字
    - 強化現有技能呈現
```

### 後處理優化
- 關鍵字密度檢查
- 段落長度平衡
- 重複詞彙替換
- 格式一致性

## 效能指標

### v2.1.0-simplified 處理效能
- **P50 處理時間**：3.85 秒（目標 < 4.0秒）✅
- **P95 處理時間**：6.50 秒（目標 < 7.0秒）✅
- **成功率**：> 99.9%
- **Token 使用減少**：44%（比 v2.0.0）
- **成本降低**：40%+（每次請求節省 $0.20+）

### 階段時間分配
| 階段 | 平均時間 | 佔比 |
|------|----------|------|
| Instruction Compiler | 280ms | 12% |
| Resume Writer | 2100ms | 88% |
| 總處理時間 | 2380ms | 100% |

## 最佳實踐

### 使用建議
1. 提供完整的原始履歷
2. 使用詳細的職缺描述
3. 選擇適當的強調等級
4. 檢查並微調結果

### 注意事項
1. 改寫後仍需人工審核
2. 確保所有資訊真實
3. 保持個人風格
4. 適度使用關鍵字

## 進階功能

### 版本比較
- 改寫前後對比
- 變更追蹤顯示
- 關鍵指標提升

### 多輪優化
- 遞進式改進
- A/B 測試支援
- 個人化調整

## 限制與風險

### 技術限制
- 單次處理上限 3000 字
- 需要足夠的原始內容
- 僅支援文字格式

### 使用風險
- 過度優化可能失真
- 需要人工最終審核
- 不同 HR 偏好差異

## 未來發展

### v2.1.0-simplified 已實現
- ✅ 兩階段架構（Instruction Compiler + Resume Writer）
- ✅ Gap 分類處理（[Skill Gap] vs [Presentation Gap]）
- ✅ Prompt 簡化（717行 → 380行，減少 47%）
- ✅ 成本優化（Token 使用減少 44%）
- ✅ 效能提升（P50 < 4.0秒）
- ✅ JSON 輸出格式標準化
- ✅ CSS 類別規範（opt-modified, opt-placeholder, opt-new）

### 短期改進
- 支援更多文件格式（PDF、DOCX）
- 增加行業特定模板
- 實作結果快取機制
- 強化 Fallback 機制

### 長期規劃
- 多輪對話式優化
- 個人寫作風格學習
- 整合面試準備建議
- 實時協作編輯

## 相關功能

- [關鍵字提取](keyword_extraction.md)
- [差距分析](gap_analysis.md)
- [履歷格式化](resume_format.md)