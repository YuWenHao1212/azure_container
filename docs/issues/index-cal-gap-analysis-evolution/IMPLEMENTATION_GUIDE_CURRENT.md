# 當前實作指南 - Index Cal & Gap Analysis V4

**文檔版本**: 1.0.0  
**最後更新**: 2025-08-16  
**狀態**: Production Ready

## 📌 快速參考

### API 端點
```
POST /api/v1/index-cal-and-gap-analysis
```

### 核心服務
- **主服務**: `src/services/combined_analysis_v2.py`
- **Gap Analysis**: `src/services/gap_analysis_v2.py`
- **Index Calculation**: `src/services/index_calculation_v2.py`
- **Course Availability**: `src/services/course_availability.py`

## 🏗️ 當前架構 (V4)

### 執行流程
```python
async def _execute_parallel_analysis(self, ...):
    # Step 1: 並行執行 Keywords & Embeddings
    keywords_task = self._quick_keyword_match(...)
    embeddings_task = self._generate_embeddings_parallel_with_timing(...)
    
    # Step 2: 等待兩者完成
    keywords_result = await keywords_task
    embeddings = await embeddings_task
    
    # Step 3: 執行 Index Calculation (包含真實 similarity_score)
    index_result = await self.index_service.calculate_index(
        resume=resume,
        job_description=job_description,
        keywords=keywords_result["keywords"],
        embeddings=embeddings
    )
    
    # Step 4: 執行 Gap Analysis (使用真實 similarity_score)
    gap_result = await self.gap_service.analyze_with_context(
        index_result=index_result,  # 包含真實相似度！
        resume=resume,
        job_description=job_description,
        language=language,
        covered_keywords=keywords_result["covered_keywords"],
        missing_keywords=keywords_result["missing_keywords"],
        coverage_percentage=keywords_result["keyword_coverage"]
    )
    
    # Step 5: 增強技能建議 (Course Availability)
    if gap_result and "SkillSearchQueries" in gap_result:
        enhanced_skills = await check_course_availability(
            gap_result["SkillSearchQueries"]
        )
        gap_result["SkillSearchQueries"] = enhanced_skills
    
    return index_result, gap_result
```

## 🔑 關鍵配置

### 環境變數
```bash
# 必須設定
USE_V2_IMPLEMENTATION=true          # 使用 V2 實作
ENABLE_PARTIAL_RESULTS=false        # V4 不支援部分結果

# LLM 模型配置
LLM_MODEL_GAP_ANALYSIS=gpt-4.1     # Gap Analysis 使用完整模型
LLM_MODEL_KEYWORDS=gpt-4.1-mini    # Keywords 使用輕量模型

# Prompt 版本
GAP_ANALYSIS_PROMPT_VERSION=2.1.8   # 三層技能分類系統
```

### LLM Factory 配置 🚨
```python
# 必須使用 LLM Factory！
from src.services.llm_factory import get_llm_client

# ✅ 正確方式
client = get_llm_client(api_name="gap_analysis")

# ❌ 絕對禁止
from openai import AsyncAzureOpenAI  # 不要直接使用！
```

## 📊 相似度門檻配置

Gap Analysis v2.1.8 使用以下門檻值：

```python
SIMILARITY_THRESHOLDS = {
    "strong_match": 80,      # 幾乎理想匹配
    "good_potential": 70,    # 有競爭力
    "good_alignment": 60,    # 相關經驗豐富
    "moderate": 50,          # 有基礎但需學習
    "limited": 40,           # 基礎技能存在
    # < 40: 領域差異大
}
```

## 🧪 測試執行

### 單元測試 + 整合測試 (67個)
```bash
# 執行所有測試
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# 單獨執行 Gap Analysis 測試
pytest test/unit/services/test_gap_analysis_v2.py -v
pytest test/integration/test_gap_analysis_v2_integration_complete.py -v

# 單獨執行 Course Availability 測試
pytest test/unit/services/test_course_availability.py -v
pytest test/integration/test_course_availability_integration.py -v
```

### 效能測試
```bash
# 需要真實 API keys
pytest test/performance/test_gap_analysis_v2_performance.py -v
```

### E2E 測試
```bash
./test/scripts/run_e2e_standalone.sh
```

## 🚀 部署流程

### 1. 本地測試
```bash
# 確保所有測試通過
./test/scripts/run_complete_test_suite.sh

# 檢查 Ruff
ruff check src/ --line-length=120
```

### 2. 推送到 GitHub
```bash
git add .
git commit -m "feat: implement V4 architecture"
git push origin main
# 會觸發 pre-push hook 顯示配置
```

### 3. CI/CD 自動部署
- GitHub Actions 自動建置 Docker 映像
- 推送到 Azure Container Registry
- 部署到 Container Apps

### 4. 驗證部署
```bash
# 檢查健康狀態
curl https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/health

# 查看日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --follow
```

## 🐛 常見問題診斷

### 問題 1: "deployment does not exist" 錯誤
**原因**: 未使用 LLM Factory  
**解決**: 確保所有 LLM 調用通過 `get_llm_client()`

### 問題 2: Gap Analysis 不準確
**原因**: 使用了假的 similarity_score  
**解決**: 確保 V4 架構順序執行

### 問題 3: 測試失敗
**原因**: 環境變數未正確設定  
**解決**: 檢查 `USE_V2_IMPLEMENTATION=true`

## 📈 效能監控

### 關鍵指標
- **P50 響應時間**: ~9.04s
- **P95 響應時間**: ~11.96s
- **Gap Analysis 時間**: ~9.2s (99.9%)
- **其他操作**: ~0.4s (0.1%)

### 監控端點
```python
# 獲取服務統計
GET /api/v1/monitoring/stats

# 回應範例
{
  "total_requests": 1234,
  "success_rate": 99.5,
  "average_response_time": 9.2,
  "p95_response_time": 11.96
}
```

## 🔄 版本管理

### Prompt 版本
- **Gap Analysis**: v2.1.8 (Active)
- **Index Calculation**: v2.0.0 (Active)
- **Keywords Extraction**: v1.4.0 (Active)

### 切換版本
```bash
# 臨時切換 (會被 CI/CD 覆蓋)
az containerapp update \
  --name airesumeadvisor-api-production \
  --set-env-vars GAP_ANALYSIS_PROMPT_VERSION=2.1.7

# 永久切換
vim .github/workflows/ci-cd-main.yml
# 修改 GAP_VERSION 預設值
```

## 📚 相關資源

### 程式碼
- [CombinedAnalysisServiceV2](../../src/services/combined_analysis_v2.py)
- [GapAnalysisServiceV2](../../src/services/gap_analysis_v2.py)
- [IndexCalculationServiceV2](../../src/services/index_calculation_v2.py)

### 文檔
- [架構詳解](./CURRENT_ARCHITECTURE.md)
- [開發歷程](./DEVELOPMENT_TIMELINE.md)
- [測試規格](./TEST_SPECIFICATION_COMPLETE.md)
- [經驗教訓](./LESSONS_LEARNED_COMPLETE.md)

### Prompt 檔案
- `src/prompts/gap_analysis/v2.1.8.yaml`
- `src/prompts/index_calculation/v2.0.0.yaml`

---

**提示**: 如需修改架構，請先閱讀 [LESSONS_LEARNED_COMPLETE.md](./LESSONS_LEARNED_COMPLETE.md) 了解過去的教訓。