# 關鍵字提取一致性 KPI 測試工具

本目錄包含用於測試關鍵字提取 API 一致性的測試腳本，這是重要的商業 KPI。

## 測試腳本說明

### 主測試腳本
- `test_consistency_kpi.sh` - 主入口腳本，提供互動式選單

### 專門測試腳本
- `test_tsmc_consistency.sh` - TSMC 短文本（~1,200字符）一致性測試
- `test_bcg_consistency.sh` - BCG 長文本（~5,898字符）一致性測試，自動分批處理

### 報告生成腳本
- `generate_consistency_report.sh` - 通用報告生成工具

## 使用方法

### 1. 確保 API 服務正在運行
```bash
cd /Users/yuwenhao/Documents/GitHub/azure_fastapi
uvicorn src.main:app --reload
```

### 2. 執行測試
```bash
cd src/tests/consistency_kpi
chmod +x *.sh  # 首次使用時設置執行權限

# 互動式測試
./test_consistency_kpi.sh

# 或直接執行特定測試
./test_tsmc_consistency.sh 50  # 執行50次TSMC測試
./test_bcg_consistency.sh 50   # 執行50次BCG測試
```

### 3. 查看報告
測試完成後，報告會保存在帶時間戳的目錄中：
- `tsmc_consistency_test_YYYYMMDD_HHMMSS/consistency_report.md`
- `bcg_consistency_test_YYYYMMDD_HHMMSS/merged/consistency_report.md`

## KPI 目標值

| 測試類型 | 文本長度 | 一致率目標 | 警戒值 |
|---------|---------|-----------|--------|
| 短文本（TSMC） | ~1,200 字符 | ≥70% | <60% |
| 長文本（BCG） | ~5,898 字符 | ≥50% | <40% |

## 基準測試結果（2025-07-01）

### TSMC 短文本
- 一致率：78.1%（✅ 超過目標）
- 唯一結果集：4個
- 核心關鍵字穩定性：100%

### BCG 長文本
- 一致率：60.0%（✅ 超過目標）
- 唯一結果集：8個
- 核心關鍵字穩定性：100%

### 統計分析
- 兩次測試得到相同結果的機率：39.84%
- 95% 信賴區間：[26.3%, 53.4%]

## 注意事項

1. **批次處理**：BCG測試會自動分批執行（每批25次），以避免超時
2. **測試間隔**：每次API調用間隔0.5秒，避免過載
3. **文件大小**：BCG測試使用臨時文件處理長文本，避免命令行限制

## 定期執行建議

建議每週執行一次完整測試套件，監控以下指標：
1. 一致率是否維持在目標值以上
2. 唯一結果集數量是否增加
3. 核心關鍵字穩定性是否維持100%

## 相關文檔

- 測試計畫：`/docs/published/test_plans/TEST_CONSISTENCY_KPI_20250701.md`
- API 設計文檔：`/docs/published/design/DESIGN_2ROUND_20250628.md`
- Work Items：Azure DevOps #350-353