# Performance Test Fixtures

這個目錄包含 20 組測試數據，用於 `/api/v1/index-cal-and-gap-analysis` API 的性能測試。

## 📁 目錄結構

```
performance_test_data/
├── resumes/
│   └── wenhao_resume.html              # 測試用履歷 (用戶提供)
├── job_descriptions/
│   ├── jd_001_tsmc.txt                 # TSMC Senior Data Analyst (真實)
│   ├── jd_002_nvidia.txt               # NVIDIA Senior Data Scientist (真實)
│   ├── jd_003_foodpanda.txt            # foodpanda Data Analyst (真實)
│   ├── jd_004_apple.txt                # Apple Senior Business Analyst (生成)
│   └── ... (共 20 個 JD)
├── keywords/
│   ├── keywords_001_tsmc.json          # 對應的關鍵字列表
│   └── ... (共 20 個關鍵字文件)
├── test_data_registry.json             # 測試數據索引和元數據
└── README.md                           # 使用說明
```

## 🎯 測試數據設計原則

### 多樣性保證
- **行業覆蓋**: 11 個不同行業 (科技、金融、顧問、製造等)
- **職位層級**: 涵蓋 Analyst、Manager、Lead 等不同層級
- **難度分布**: 低難度 1 個、中難度 13 個、高難度 6 個
- **匹配度範圍**: 45%-85% 預期匹配度，確保測試多樣性

### 技術規格
- **字符數量**: 2,622 - 4,282 字符 (平均 3,338)
- **關鍵字數量**: 16 個關鍵字 (所有測試案例統一)
- **格式要求**: 所有 JD 都超過 200 字符 (API 最小要求)
- **唯一性**: 每個 JD 內容足夠不同，避免 cache hits

### 測試覆蓋範圍
1. **真實數據** (3個): TSMC、NVIDIA、foodpanda
2. **生成數據** (17個): 基於用戶履歷特色設計的相關職位

## 📊 統計資訊

| 類別 | 數量 |
|------|------|
| 總測試案例 | 20 |
| 真實 JD | 3 |
| 生成 JD | 17 |
| 涵蓋行業 | 11 |
| 關鍵字總數 | 340+ |

## 🚀 使用方法

### Performance Testing 腳本使用
```python
import json

# 載入測試數據索引
with open('test_data_registry.json', 'r') as f:
    registry = json.load(f)

# 遍歷所有測試案例
for test_case in registry['test_cases']:
    jd_file = test_case['job_description_file']
    keywords_file = test_case['keywords_file']
    
    # 讀取 JD 內容
    with open(jd_file, 'r') as f:
        job_description = f.read()
    
    # 讀取關鍵字
    with open(keywords_file, 'r') as f:
        keywords = json.load(f)
    
    # 執行 API 測試
    # ...
```

### 避免 Cache 影響
- 每個 JD 內容都是唯一的
- 關鍵字組合各不相同
- 測試順序可以隨機化
- 建議在測試間加入小延遲 (1-2秒)

## 📈 Performance Testing 目標

這些測試數據設計用於：
1. **20次 API 調用** - 測量 P50、P95、worst case
2. **Function Block Timing** - 詳細分解各階段執行時間
3. **Gantt Chart 分析** - 視覺化並行執行和相依關係
4. **Cache 影響驗證** - 確保每次都是真實冷啟動測試
5. **負載測試** - 模擬真實使用場景下的性能表現

## 🔍 數據品質檢驗

所有測試數據已通過以下驗證：
- ✅ 字符數量檢查 (全部 > 200 字符)
- ✅ JSON 格式驗證 (所有關鍵字文件)
- ✅ 關鍵字數量檢查 (15-18 個)
- ✅ 內容唯一性驗證
- ✅ 行業多樣性確認

## 📝 更新記錄

- **2025-01-17**: 初始版本，20 組測試數據完成
- 基於用戶履歷和 3 個真實 JD 樣本生成
- 涵蓋多個行業和職位類型
- 通過所有品質檢驗