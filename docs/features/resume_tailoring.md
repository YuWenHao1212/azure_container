# 履歷客製化功能

## 功能概述

運用 AI 技術根據特定職缺要求客製化履歷內容，在保持真實性的前提下，優化表達方式以提高匹配度。

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

### AI 改寫引擎
- 模型：Azure OpenAI GPT-4o
- 溫度參數：0.7（平衡創意與準確）
- 最大令牌：2000
- 提示版本：v2.1.0

### 處理流程
```python
1. 解析原始履歷結構
2. 分析職缺關鍵需求
3. 計算改寫策略
4. 執行 AI 改寫
5. 驗證改寫品質
6. 輸出最終結果
```

### 品質控制
- 事實一致性檢查
- 關鍵字覆蓋驗證
- 語法錯誤檢測
- 重複內容過濾

## 使用範例

### 請求範例
```python
import requests

response = requests.post(
    "https://airesumeadvisor-fastapi.azurewebsites.net/api/v1/tailor-resume",
    params={"code": "YOUR_HOST_KEY"},
    json={
        "resume": "10年軟體開發經驗，專精網頁開發...",
        "job_description": "徵求資深全端工程師，需要React和Node.js經驗...",
        "keywords": {
            "jd": ["React", "Node.js", "MongoDB", "敏捷開發"],
            "resume": ["JavaScript", "前端開發", "後端開發"]
        },
        "options": {
            "emphasis_level": "medium",
            "preserve_structure": True
        }
    }
)
```

### 回應範例
```json
{
  "success": true,
  "data": {
    "tailored_content": "擁有10年全端開發經驗，專精於React前端框架與Node.js後端開發。在敏捷開發環境中，成功交付20+專案...",
    "modifications": [
      {
        "section": "專業技能",
        "changes": [
          "新增 React 相關專案經驗",
          "強調 Node.js 開發能力",
          "加入敏捷開發方法論"
        ]
      },
      {
        "section": "工作經歷",
        "changes": [
          "量化專案成果（提升效能35%）",
          "突顯團隊協作經驗"
        ]
      }
    ],
    "keyword_coverage": 92.5,
    "improvement_metrics": {
      "keyword_density": "+35%",
      "relevance_score": "+28%",
      "readability": "maintained"
    }
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

## 改寫策略

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

### 提示工程
```yaml
系統提示:
  角色: 專業履歷顧問
  任務: 優化履歷以匹配職缺
  限制:
    - 保持事實準確
    - 不添加虛假資訊
    - 維持專業語氣
    - 控制長度變化±20%
```

### 後處理優化
- 關鍵字密度檢查
- 段落長度平衡
- 重複詞彙替換
- 格式一致性

## 效能指標

### 處理效能
- 平均處理時間：3.5 秒
- P95 處理時間：< 5 秒
- 成功率：> 95%

### 改寫品質
- 關鍵字覆蓋率：> 85%
- 內容相關性：> 90%
- 語法正確率：> 98%

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
- 單次處理上限 5000 字
- 需要足夠的原始內容
- 僅支援文字格式

### 使用風險
- 過度優化可能失真
- 需要人工最終審核
- 不同 HR 偏好差異

## 未來發展

### 短期改進
- 支援更多文件格式
- 增加行業模板
- 優化處理速度

### 長期規劃
- 多輪對話式優化
- 個人寫作風格學習
- 整合面試準備建議

## 相關功能

- [關鍵字提取](keyword_extraction.md)
- [差距分析](gap_analysis.md)
- [履歷格式化](resume_format.md)