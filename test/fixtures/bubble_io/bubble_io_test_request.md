# Bubble.io API Connector 測試資料

## Resume Tailoring v3.1.0 測試請求

在 Bubble.io API Connector 中使用以下資料進行測試：

### 完整 JSON 請求（複製此內容到 Body）

```json
{
  "job_description": "We are seeking an experienced Senior Software Engineer to join our innovative team. The ideal candidate will have strong expertise in Python, Django, and cloud technologies. You will be responsible for designing scalable microservices, implementing RESTful APIs, and optimizing database performance. Experience with Docker, Kubernetes, and AWS is essential. The role involves collaborating with cross-functional teams, mentoring junior developers, and contributing to architectural decisions. Strong problem-solving skills and experience with agile methodologies are required. This is an excellent opportunity for a passionate engineer looking to make a significant impact in a fast-growing technology company.",
  "original_resume": "<html><body><div><h1>Software Engineer</h1><p>Experienced Python developer with 5 years of experience in building web applications. Proficient in Django framework and REST API development. Strong background in database design and optimization. Familiar with agile development methodologies and version control systems. Excellent problem-solving abilities and team collaboration skills. Previous experience includes developing e-commerce platforms and data analytics tools.</p></div></body></html>",
  "original_index": {
    "core_strengths": "<ul><li>Strong Python and Django expertise</li><li>5 years of web development experience</li><li>Database optimization skills</li></ul>",
    "key_gaps": "<ul><li>[Skill Gap] No mentioned experience with Docker or containerization</li><li>[Skill Gap] Missing AWS cloud platform experience</li><li>[Skill Gap] No Kubernetes orchestration experience</li></ul>",
    "quick_improvements": "<ul><li>Add Docker containerization projects to portfolio</li><li>Highlight any cloud deployment experience</li><li>Include microservices architecture experience if applicable</li></ul>",
    "covered_keywords": ["Python", "Django", "REST API", "database", "agile"],
    "missing_keywords": ["Docker", "Kubernetes", "AWS", "microservices", "cloud"],
    "coverage_percentage": 50,
    "similarity_percentage": 65
  },
  "options": {
    "language": "en",
    "include_visual_markers": true
  }
}
```

### 重要提醒

1. **確保沒有換行符號**：在 Bubble.io 中貼上時，確保 JSON 是單行或正確格式化
2. **API Key**：記得在 Header 中設定 `X-API-Key`
3. **Content-Type**：必須是 `application/json`

### 預期回應

成功時會返回：
- `success`: true
- `data.optimized_resume`: 優化後的 HTML 履歷
- `data.applied_improvements`: 應用的改進清單
- `data.Keywords`: 關鍵字追蹤資訊
- `data.similarity`: 相似度指標

### Bubble.io 設定提醒

1. **Initialize Call**: 使用上述 JSON 進行初始化
2. **Data Types**: 確保設定正確的資料類型
   - job_description: Text
   - original_resume: Text
   - original_index: 展開為個別欄位
   - options: 展開為個別欄位
3. **Response**: 設定為 "Use as Data"
4. **Return values**: 選擇需要的回應欄位

### 測試步驟

1. 在 API Connector 中建立新的 API Call
2. 設定 Method 為 POST
3. 設定 URL 為 `https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/tailor-resume`
4. 加入 Header: `X-API-Key: [Your API Key]`
5. 加入 Header: `Content-Type: application/json`
6. 將上述 JSON 貼到 Body
7. 點擊 "Initialize Call"
8. 檢查回應是否正確