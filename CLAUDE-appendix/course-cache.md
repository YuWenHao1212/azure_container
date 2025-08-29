# 動態課程快取系統

## 系統概述 🚀
為解決 Gap Analysis API 返回假課程 ID 的問題，實作了高效能動態快取系統。

### 核心特性
- **精確快取**: 基於完整 embedding text 的 MD5 hash，不再依賴簡單 skill_name
- **TTL 過期**: 30 分鐘自動過期，確保資料新鮮度
- **LRU 淘汰**: 智能記憶體管理，最多快取 1000 項目 (~30-50MB)
- **執行緒安全**: AsyncIO 保護的並發存取
- **優雅降級**: 快取失效時自動回退到資料庫查詢

### 效能提升
| 指標 | 實作前 | 實作後 | 改善 |
|------|--------|--------|------|
| 快取命中回應時間 | 350ms | < 1ms | 99.7% ↓ |
| 混合場景 (70% 命中) | 350ms | 105ms | 70% ↓ |
| 資料庫查詢量 | 100% | 30% | 70% ↓ |

### 監控與管理
```bash
# 快取狀態查詢
GET /api/v1/debug/course-cache/stats

# 健康檢查
GET /api/v1/debug/course-cache/health

# 手動清理過期項目
POST /api/v1/debug/course-cache/cleanup

# 緊急清空快取 (慎用)
POST /api/v1/debug/course-cache/clear
```

### 技術實作
- **檔案位置**: `src/services/dynamic_course_cache.py`
- **整合點**: `src/services/course_availability.py`
- **監控 API**: `src/api/monitoring/cache_dashboard.py`
- **背景任務**: 自動啟動，每小時清理過期項目

**📖 詳細技術文檔**: `docs/issues/course_details_batch/`