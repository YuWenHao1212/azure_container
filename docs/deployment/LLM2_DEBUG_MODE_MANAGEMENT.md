# LLM2 Debug Mode 管理指南

## 概述
LLM2_DEBUG_MODE 是用於診斷 Resume Tailoring API v3.1 中 LLM2 (Additional Manager) fallback 問題的環境變數。

## 設定方式

### 方法 1: 通過 CI/CD 部署時設定（推薦）
在 `.github/workflows/ci-cd-main.yml` 中設定：
```yaml
LLM2_DEBUG_MODE=false  # 生產環境建議設為 false
```

優點：
- 每次部署時自動設定
- 版本控制追蹤變更
- 不需要額外操作

### 方法 2: 使用 Azure CLI 手動更新
部署後使用提供的腳本：
```bash
# 啟用 debug mode
./scripts/update-llm2-debug-mode.sh true

# 關閉 debug mode（生產環境）
./scripts/update-llm2-debug-mode.sh false
```

優點：
- 即時生效，不需要重新部署
- 適合臨時診斷問題

### 方法 3: 使用 GitHub Secrets（未來考慮）
可以創建 GitHub Secret `LLM2_DEBUG_MODE`，然後在 CI/CD 中引用：
```yaml
LLM2_DEBUG_MODE=${{ secrets.LLM2_DEBUG_MODE }}
```

優點：
- 更安全
- 可以在 GitHub UI 中管理
- 不需要修改程式碼

## 建議配置

| 環境 | 建議值 | 原因 |
|------|--------|------|
| 本地開發 | `true` | 方便開發時診斷 |
| CI/CD 測試 | `false` | 測試生產行為 |
| 生產環境 | `false` | 避免洩露內部邏輯 |
| 診斷問題時 | `true` | 臨時啟用以收集資訊 |

## Debug Mode 效果

當 `LLM2_DEBUG_MODE=true` 時：
- LLM2 返回空內容時顯示診斷 HTML
- 包含詳細的 fallback 原因
- 顯示相關的 metadata 和設定

當 `LLM2_DEBUG_MODE=false` 時：
- 使用原始履歷內容（正常 fallback）
- 不顯示任何診斷資訊
- 適合生產環境

## 監控 Debug 輸出

使用監控工具檢查 debug 輸出：
```bash
# 測試 API 並檢查 debug 訊息
python test/tools/llm2_fallback_monitor_v2.py \
    --api-url https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/tailor-resume \
    --verbose
```

## 注意事項

1. **生產環境謹慎使用**：Debug mode 會洩露內部邏輯，只在需要診斷時啟用
2. **記得關閉**：診斷完成後記得關閉 debug mode
3. **版本控制**：修改 CI/CD 設定時記得提交變更