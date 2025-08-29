# 安全最佳實踐

## 安全檢查清單

### 容器安全
- ✅ 非 root 用戶運行容器
- ✅ 最小化基礎映像
- ✅ 定期更新基礎映像

### 秘密管理
- ✅ 敏感資料使用 Azure 秘密管理
- ✅ 環境變數不包含秘密
- ✅ .env 檔案加入 .gitignore

### API 安全
- ✅ API Key 認證保護端點
- ✅ CORS 設定限制來源網域
- ✅ 輸入驗證與清理
- ✅ Rate limiting 保護

### 日誌安全
- ✅ 錯誤日誌不包含敏感資訊
- ✅ 不記錄 API keys 或 tokens
- ✅ 不記錄個人識別資訊

### 網路安全
- ✅ 使用 HTTPS
- ✅ 適當的 TLS 版本
- ✅ 安全的 header 設定

## 安全相關環境變數
- `JWT_SECRET_KEY` - JWT 簽名密鑰
- `CONTAINER_APP_API_KEY` - API 認證密鑰
- `AZURE_OPENAI_API_KEY` - Azure OpenAI 存取密鑰

## 安全事件回應
1. 立即撤銷受影響的密鑰
2. 審查存取日誌
3. 更新並輪換所有密鑰
4. 通知相關團隊