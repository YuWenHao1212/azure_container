# 部署環境配置

## 生產環境 (目前開發中使用)
- **URL**: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **鏡像**: `airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:20250730-100726-3530cfd`
- **資源**: 1 CPU, 2GB RAM, 4GB 暫存空間
- **狀態**: ✅ 活躍使用中 - 所有開發測試都在此環境進行

## 開發環境 (未來規劃)
- **URL**: https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **鏡像**: `airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:dev-secure`
- **狀態**: ⏸️ 暫未使用 - 預留給未來測試需求

## 效能優化比較

### Container Apps vs Functions
| 指標 | Functions | Container Apps | 改善 |
|------|-----------|----------------|------|
| 總回應時間 | 6.0s | 2.8s | -53% |
| 架構開銷 | 3.2s | 0s | -100% |
| 冷啟動時間 | 2-3s | 0.1-0.5s | -80% |
| 並發能力 | < 0.5 QPS | 20-50 QPS | 40-100x |

### 優化策略
- **模型選擇**: 關鍵字提取使用 GPT-4.1 mini (更快)
- **輕量監控**: 預設啟用輕量級監控，生產關閉重度監控
- **資源配置**: 1 CPU + 2GB RAM，自動擴展 2-10 實例

## Azure Resources
- **Subscription**: 5396d388-8261-464e-8ee4-112770674fba
- **Resource Group**: airesumeadvisorfastapi  
- **Container Registry**: airesumeadvisorregistry
- **Container Environment**: Japan East

## 部署流程
1. 建立並測試 Docker 鏡像
2. 推送到 Azure Container Registry
3. 更新 Container Apps 配置
4. 驗證部署與健康檢查
5. 監控效能指標