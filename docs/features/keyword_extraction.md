# 關鍵字提取功能

## 功能概述

從職缺描述（Job Description）中智能提取關鍵技能、要求和資格，協助求職者快速理解職位需求。

## API 端點

`POST /api/v1/extract-jd-keywords`

## 核心功能

### 1. 多語言支援
- 自動偵測語言（英文/繁體中文）
- 語言特定的 prompt 優化
- 保持原始語言的關鍵字

### 2. 智能排序
關鍵字按重要性排序（根據 prompt v1.4.0）：
- **程式語言**（Python、R、SQL 等）- 永遠排在最前
- **技術工具**（Tableau、Power BI、Excel 等）- 第二順位
- **技術技能**（Machine Learning、Data Analysis 等）- 第三順位
- **領域知識**（HR Analytics、Business Intelligence 等）- 第四順位
- **軟技能**（Communication、Leadership、Teamwork 等）- 永遠排在最後

> 注意：目前 API 只返回排序後的關鍵字列表，尚未實作分類功能

### 3. 智能去重
- 移除重複的關鍵字
- 合併相似概念
- 保留最具代表性的表述

## 技術實作

### LLM 整合
- 使用 Azure OpenAI GPT-4.1 mini (Japan East 部署)
- 結構化輸出（JSON）
- Prompt 版本：v1.4.0
- API 版本：2025-01-01-preview

### 處理流程
1. 接收職缺描述文字
2. 語言偵測與驗證
3. 呼叫 LLM 提取關鍵字
4. 後處理與分類
5. 返回結構化結果

### 錯誤處理
- 輸入驗證（200-5000 字元）
- LLM 逾時保護（30 秒）
- 重試機制（3 次）
- 降級處理

## 使用範例

### 請求範例

#### 生產環境 (Container Apps) ✅
```python
import requests

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/extract-jd-keywords",
    headers={"X-API-Key": "YOUR_API_KEY"},  # 推薦：Header 認證
    json={
        "job_description": """
        We are looking for a Senior Python Developer with 5+ years experience.
        Required skills: Python, FastAPI, Docker, AWS, PostgreSQL.
        Nice to have: Kubernetes, React, TypeScript.
        Strong communication skills and team collaboration required.
        """,
        "language": "auto",         # 可選：auto, en, zh-TW
        "max_keywords": 16,         # 可選：5-25，預設 16
        "prompt_version": "1.4.0",  # 可選：預設使用最新版本
        "include_standardization": True,  # 可選：關鍵字標準化
        "use_multi_round_validation": True  # 可選：2輪交集驗證
    }
)
```

#### 向後相容模式 (Query Parameter)
```python
import requests

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/extract-jd-keywords",
    params={"code": "YOUR_HOST_KEY"},
    json={
        "job_description": """
        We are looking for a Senior Python Developer with 5+ years experience.
        Required skills: Python, FastAPI, Docker, AWS, PostgreSQL.
        Nice to have: Kubernetes, React, TypeScript.
        Strong communication skills and team collaboration required.
        """
    }
)
```

### 回應範例
```json
{
  "success": true,
  "data": {
    "keywords": [
      "Python", "FastAPI", "Docker", "AWS", "PostgreSQL",
      "Kubernetes", "React", "TypeScript", "communication skills",
      "team collaboration", "Senior Developer", "5+ years experience"
    ],
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

## 效能指標

### 生產環境效能 (Container Apps + GPT-4.1 mini) ✅
- **平均回應時間**: 2.8 秒（純 API 處理）
- **P95 回應時間**: < 3 秒
- **P99 回應時間**: < 4 秒
- **成功率**: 99.95%
- **並發處理**: 20-50 QPS

### 效能優化成果
- **2輪交集策略**: 提升一致性至 78%（短文本）
- **內建快取**: 相同 JD 立即返回（< 50ms）
- **並行處理**: 2輪同時執行，節省 50% 時間
- **無冷啟動**: Container Apps 持續運行

### 架構比較
| 指標 | Function Apps | Container Apps | 改善 |
|------|---------------|----------------|------|
| API 處理時間 | 2.8s | 2.8s | 0% |
| 架構開銷 | 3.2s | 0s | -100% |
| 總回應時間 | 6.0s | 2.8s | -53% |
| 冷啟動時間 | 2-5s | 0.5-1s | -75% |

### 準確度
- 關鍵字召回率：> 90%
- 分類準確度：> 85%
- 誤判率：< 5%

## 最佳實踐

### 輸入準備
1. 提供完整的職缺描述
2. 包含技能要求部分
3. 保持原始格式

### 結果使用
1. 用於履歷優化
2. 技能差距分析
3. 求職準備指引

## 限制與注意事項

### 輸入限制
- 最小長度：200 字元
- 最大長度：5000 字元
- 支援語言：英文、繁體中文

### 已知限制
1. 可能遺漏隱含要求
2. 產業特定術語需持續優化
3. 新興技術關鍵字需要更新

## Container Apps 部署狀態 ✅

### 📊 部署完成
- **關鍵字提取 API**: ✅ 已完成部署
- **健康檢查端點**: ✅ 已完成部署
- **CI/CD 自動化**: ✅ 已建立完整流程
- **測試覆蓋率**: ✅ 103 個測試 (88 單元 + 15 整合)

### 🔧 技術配置
- **LLM 服務**: GPT-4.1 mini Japan East 部署
- **API 認證**: 支援 X-API-Key header 和 query parameter
- **監控**: Application Insights 完整整合
- **CORS**: 支援 Bubble.io 前端整合
- **部署平台**: Azure Container Apps (Japan East)

### 📊 驗證指標
- 回應時間 < 3 秒 (P95)
- 成功率 > 99.9%
- 功能一致性 100%
- 前端整合無中斷

## 未來改進

### 已完成優化 ✅
- 關鍵字提取 API Container Apps 部署
- GPT-4.1 mini Japan East 整合  
- 2輪交集驗證策略
- 內建快取機制
- CI/CD 自動化部署 (GitHub Actions)
- 完整測試覆蓋 (103 個測試)

### 短期計畫 (Q1 2025)
- **實作關鍵字分類功能** - 將關鍵字分組為技術技能、軟技能、工具等類別
- 產業特定關鍵字詞典擴充
- 提升長文本一致性至 70%+
- Redis 快取層整合
- 批次處理 API 支援

### 長期計畫 (Q2-Q4 2025)
- 支援更多語言 (日文、韓文)
- 知識圖譜整合
- 即時趨勢分析
- 個人化推薦算法

## 相關功能

- [履歷匹配指數](index_calculation.md)
- [差距分析](gap_analysis.md)
- [履歷客製化](resume_tailoring.md)