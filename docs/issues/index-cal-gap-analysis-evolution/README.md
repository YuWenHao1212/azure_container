# Index Calculation & Gap Analysis Evolution

## 📚 文檔總覽

本專案記錄了 Azure Container API 中 `/api/v1/index-cal-and-gap-analysis` 端點從 V2 到 V4 的完整演進歷程。

### 🏆 當前生產版本
- **版本**: V4 (準確性優先架構)
- **狀態**: ✅ Active in Production
- **特點**: 順序執行，使用真實 similarity_score 進行準確評估

### 📊 快速統計
- **開發週期**: 2025-08-03 ~ 2025-08-16 (13天)
- **架構迭代**: 3次 (V2→V3→V4)
- **測試案例**: 67個核心測試 + 4個特殊測試
- **效能改善**: P50 5.3%, P95 -7.3% (準確性優先)

## 📁 文檔結構

### 核心文檔
| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [DEVELOPMENT_TIMELINE.md](./DEVELOPMENT_TIMELINE.md) | 完整開發歷程 (V2→V3→V4) | ⭐⭐⭐⭐⭐ |
| [CURRENT_ARCHITECTURE.md](./CURRENT_ARCHITECTURE.md) | 當前V4架構詳解 | ⭐⭐⭐⭐⭐ |
| [TEST_SPECIFICATION_COMPLETE.md](./TEST_SPECIFICATION_COMPLETE.md) | 67個測試案例完整規格 | ⭐⭐⭐⭐ |
| [LESSONS_LEARNED_COMPLETE.md](./LESSONS_LEARNED_COMPLETE.md) | 所有經驗教訓彙總 | ⭐⭐⭐⭐⭐ |
| [IMPLEMENTATION_GUIDE_CURRENT.md](./IMPLEMENTATION_GUIDE_CURRENT.md) | 當前實作指南 | ⭐⭐⭐ |

### 特性文檔
| 文檔 | 說明 | 版本 |
|------|------|------|
| [features/GAP_ANALYSIS_V218.md](./features/GAP_ANALYSIS_V218.md) | Gap Analysis v2.1.8 三層技能分類 | v2.1.8 |
| [features/COURSE_AVAILABILITY.md](./features/COURSE_AVAILABILITY.md) | 課程可用性檢查整合 | v1.0.0 |
| [features/RESUME_STRUCTURE_ANALYSIS.md](./features/RESUME_STRUCTURE_ANALYSIS.md) | 履歷結構分析功能 | v4.0.0 |

### 效能分析
| 文檔 | 說明 |
|------|------|
| [performance/PERFORMANCE_ANALYSIS.md](./performance/PERFORMANCE_ANALYSIS.md) | 效能分析總結 |
| [performance/benchmark_results/](./performance/benchmark_results/) | 原始測試數據 |

## 🎯 關鍵洞察

### 架構演進路線
```
V2 (理論設計) → V3 (激進並行) → V4 (準確性優先)
   資源池架構      發現LLM瓶頸      順序執行成功
```

### 重要決策點
1. **V3 並行優化失敗**: Gap Analysis 佔99.9%時間，並行效益有限
2. **V4 準確性優先**: 犧牲1秒換取真實 similarity_score
3. **LLM Factory 強制**: 所有 LLM 調用必須通過統一介面

### 測試覆蓋演進
- **初始規劃**: 20 UT + 14 IT = 34個
- **V2 擴充**: +錯誤處理測試 = 47個
- **V4 最終**: +Course Availability = 67個

## 💡 最重要的經驗教訓

### 1. LLM Factory 使用規範 🚨
```python
# ❌ 絕對禁止 - 會導致 deployment 錯誤
from openai import AsyncAzureOpenAI
from src.services.openai_client import get_azure_openai_client

# ✅ 唯一正確方式
from src.services.llm_factory import get_llm_client
client = get_llm_client(api_name="gap_analysis")
```

### 2. 並行優化的限制
當單一操作（Gap Analysis LLM）佔據 99.9% 時間時，架構層級的並行優化影響極其有限。

### 3. 準確性 vs 速度權衡
V4 選擇犧牲 1 秒回應時間，換取準確的相似度評估，提升用戶信任度。

## 🚀 快速開始

### 查看當前架構
```bash
# 了解 V4 架構
cat docs/issues/index-cal-gap-analysis-evolution/CURRENT_ARCHITECTURE.md

# 查看實作細節
cat src/services/combined_analysis_v2.py
```

### 執行測試
```bash
# 執行所有 67 個測試
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# 執行效能測試
pytest test/performance/test_gap_analysis_v2_performance.py -v
```

### 查看歷史版本
```bash
# V2 原始規劃 (未實施)
ls archive/v2-refactor/

# V3 並行優化實驗
ls archive/v3-refactor/

# V4 最終版本
ls archive/v4-refactor/
```

## 📈 效能數據對比

| 版本 | P50 | P95 | 說明 |
|------|-----|-----|------|
| V1 Baseline | 7.13s | 8.75s | 簡化 Prompt |
| V2 優化 Prompt | 9.54s | 11.15s | 加入 CoT，品質提升 |
| V3 並行執行 | 9.04s | 11.96s | 改善有限 |
| **V4 生產版** | **9.04s** | **11.96s** | **準確評估** |

## 🔗 相關資源

### API 文檔
- [API 端點說明](../../API_REFERENCE.md#index-cal-and-gap-analysis)
- [Swagger 文檔](https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/docs)

### 程式碼位置
- **服務實作**: `src/services/combined_analysis_v2.py`
- **API 端點**: `src/api/v1/index_cal_and_gap_analysis.py`
- **測試檔案**: `test/integration/test_gap_analysis_v2_integration_complete.py`

### Prompt 版本
- **Gap Analysis**: v2.1.8 (Active)
- **Index Calculation**: v2.0.0 (Active)
- **Course Availability**: Embedded in service

## 📝 維護資訊

- **最後更新**: 2025-08-16
- **維護者**: AI Resume Advisor Team
- **文檔版本**: 1.0.0
- **狀態**: Production Ready

---

**提示**: 如果您是新加入的開發者，建議按以下順序閱讀：
1. DEVELOPMENT_TIMELINE.md - 了解歷史
2. CURRENT_ARCHITECTURE.md - 理解現狀
3. LESSONS_LEARNED_COMPLETE.md - 學習經驗
4. TEST_SPECIFICATION_COMPLETE.md - 掌握測試