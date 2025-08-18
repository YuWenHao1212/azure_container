# Course Batch Query API 效能分析資料夾

## 📁 資料夾內容

此資料夾包含 Course Batch Query API (`POST /api/v1/courses/get-by-ids`) 的完整效能分析資料。

### 📄 檔案列表

| 檔案名稱 | 類型 | 描述 |
|---------|------|------|
| `PERFORMANCE_REPORT_COURSE_BATCH.md` | 報告 | 完整效能測試報告與分析 |
| `gantt_chart_20250818_112949.png` | 圖表 | P50 測試 Gantt 時間分解圖 |
| `gantt_chart_20250818_113029.png` | 圖表 | 大批量測試 Gantt 時間分解圖 |
| `performance_report_20250818_112949.json` | 數據 | P50 測試原始數據報告 |
| `performance_report_20250818_113029.json` | 數據 | 大批量測試原始數據報告 |

## 🎯 關鍵效能指標

- **P50 響應時間**: 0.01ms (目標: < 150ms) ✅ **超越 15,000x**
- **冷啟動效能**: 47.79ms (目標: < 500ms) ✅ **超越 10.4x**
- **快取命中效能**: 0.18ms (目標: < 100ms) ✅ **超越 555x**
- **快取效能提升**: 260.4x 速度提升

## 🔄 如何重新生成圖表

```bash
# 重新生成所有效能圖表
pytest test/performance/test_course_batch_performance.py::TestCourseBatchPerformance::test_generate_gantt_chart -v

# 執行完整效能測試套件
pytest test/performance/test_course_batch_performance.py -v
```

## 📊 圖表說明

### Gantt 圖表展示內容
- **時間分解**: 準備、快取、資料庫、處理階段的詳細耗時
- **並行處理**: TaskGroup 並行執行效率視覺化
- **快取影響**: 快取命中與未命中的效能差異對比
- **批次處理**: 不同批次大小的處理時間分析

### JSON 報告包含數據
- 詳細的時間測量數據
- 每個階段的精確耗時
- 快取命中率統計
- 記憶體使用情況

## 📝 維護說明

- 靜態檔案（此資料夾）：作為文檔參考保存
- 動態檔案（`test/performance/charts/`）：已加入 `.gitignore`，每次測試重新生成
- 測試執行時會自動更新動態圖表，但不會影響此文檔資料夾

---

**建立日期**: 2025-08-18  
**API 版本**: Course Batch Query v1.0.0  
**測試環境**: Mock Database (10-50ms latency)