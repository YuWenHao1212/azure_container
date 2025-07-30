# 履歷格式化功能

## 功能概述

智能格式化履歷內容，突顯與職缺相關的關鍵字，提升履歷的視覺吸引力和 ATS（申請者追蹤系統）友善度。

## API 端點

`POST /api/v1/format-resume`

## 核心功能

### 1. 關鍵字標記
- **高亮顯示**：標記匹配的關鍵字
- **樣式選項**：粗體、底線、顏色
- **智能匹配**：同義詞和變體識別
- **上下文保留**：維持語句流暢性

### 2. 格式優化
- **段落結構**：清晰的章節劃分
- **項目符號**：統一的列表格式
- **間距調整**：適當的留白設計
- **字體建議**：ATS 友善字型

### 3. HTML 輸出
- **語意標籤**：使用適當的 HTML5 標籤
- **CSS 樣式**：內嵌可自訂樣式
- **響應式設計**：適配不同裝置
- **列印友善**：優化列印效果

## 技術實作

### 標記演算法
```python
def mark_keywords(text, keywords):
    # 1. 建立關鍵字模式
    patterns = create_patterns(keywords)
    
    # 2. 智能匹配
    matches = find_matches(text, patterns)
    
    # 3. 應用標記
    marked_text = apply_markup(text, matches)
    
    return marked_text
```

### 格式化流程
1. 解析履歷結構
2. 識別關鍵字位置
3. 應用格式化規則
4. 生成 HTML 輸出
5. 優化顯示效果

### 樣式系統
- 預設樣式模板
- 自訂樣式選項
- TinyMCE 整合支援
- Bubble.io 相容性

## 使用範例

### 請求範例
```python
import requests

response = requests.post(
    "https://airesumeadvisor-fastapi.azurewebsites.net/api/v1/format-resume",
    params={"code": "YOUR_HOST_KEY"},
    json={
        "resume": "專業技能：Python、JavaScript、React...",
        "keywords": ["Python", "JavaScript", "React", "API"],
        "format_options": {
            "highlight_style": "bold",
            "include_summary": True
        }
    }
)
```

### 回應範例
```json
{
  "success": true,
  "data": {
    "formatted_resume": "<div class='resume-container'><section class='skills'><h3>專業技能</h3><p><strong>Python</strong>、<strong>JavaScript</strong>、<strong>React</strong>...</p></section></div>",
    "highlighted_keywords": ["Python", "JavaScript", "React"],
    "keyword_frequency": {
      "Python": 5,
      "JavaScript": 3,
      "React": 4,
      "API": 2
    },
    "formatting_stats": {
      "total_keywords": 14,
      "unique_keywords": 4,
      "coverage_percentage": 85.7
    }
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

## 格式化選項

### 高亮樣式
| 樣式 | 說明 | HTML 範例 |
|------|------|-----------|
| bold | 粗體標記 | `<strong>keyword</strong>` |
| underline | 底線標記 | `<u>keyword</u>` |
| color | 顏色標記 | `<mark>keyword</mark>` |
| combined | 組合樣式 | `<strong><mark>keyword</mark></strong>` |

### 結構選項
- **章節標題**：H2/H3 標籤
- **列表項目**：有序/無序列表
- **技能標籤**：標籤雲樣式
- **時間軸**：經歷時序排列

## 與前端整合

### Bubble.io 整合
```javascript
// 在 Page is loaded 工作流程中
function applyResumeFormatting() {
    // 1. 獲取格式化內容
    const formattedContent = bubble_fn_formatted_resume();
    
    // 2. 注入到 TinyMCE
    if (tinymce.activeEditor) {
        tinymce.activeEditor.setContent(formattedContent);
    }
}
```

### TinyMCE 設定
- 保留 HTML 格式
- 自訂工具列
- 樣式選擇器
- 即時預覽

## 效能優化

### 處理速度
- 1000 字履歷：< 0.5 秒
- 3000 字履歷：< 1 秒
- 5000 字履歷：< 1.5 秒

### 輸出品質
- HTML 大小：最小化
- 樣式效率：內聯優化
- 渲染速度：即時顯示

## 最佳實踐

### 履歷準備
1. 使用標準段落格式
2. 明確區分章節
3. 保持一致的格式
4. 避免特殊字元

### 關鍵字選擇
1. 使用職缺中的原始關鍵字
2. 包含同義詞變體
3. 注意大小寫差異
4. 涵蓋縮寫全稱

## ATS 優化建議

### 友善格式
- 避免表格排版
- 使用標準字體
- 簡單的項目符號
- 清晰的章節標題

### 關鍵字密度
- 自然分布：2-3%
- 避免堆砌
- 上下文相關
- 多樣化表達

## 限制與注意事項

### 輸入限制
- 純文字格式
- UTF-8 編碼
- 最大 5000 字元

### 輸出限制
- HTML 格式
- 內聯樣式
- 基本標籤集

## 未來改進

### 短期計畫
- PDF 輸出支援
- 更多樣式選項
- 自動段落優化

### 長期計畫
- AI 排版建議
- 多語言模板
- 個人化風格

## 相關功能

- [關鍵字提取](keyword_extraction.md)
- [履歷客製化](resume_tailoring.md)
- [匹配指數計算](index_calculation.md)