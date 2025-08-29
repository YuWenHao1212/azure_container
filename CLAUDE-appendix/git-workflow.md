# Git 工作流程

## 推送到 main branch
推送到 main branch 會觸發自動部署，系統會顯示配置並要求確認：

```bash
# 方法 1: 手動確認（預設）
git push origin main
# 系統會顯示配置摘要並要求輸入 'yes' 確認

# 方法 2: 自動確認（自動化友好）
AUTO_CONFIRM_PUSH=yes git push origin main

# 方法 3: CI/CD 環境會自動確認
# 當 CI=true 或 GITHUB_ACTIONS=true 時自動確認
```

## 功能分支工作流程
```bash
# 1. 建立功能分支
git checkout -b feature/new-feature

# 2. 開發並測試
# ...執行對應層級測試

# 3. 提交
git commit -m "feat: add new feature"

# 4. 推送（功能分支不需要確認）
git push origin feature/new-feature
```

## Commit Message 規範
遵循 Conventional Commits：
- `feat:` 新功能
- `fix:` 修復問題
- `docs:` 文檔更新
- `style:` 格式調整
- `refactor:` 重構
- `test:` 測試相關
- `chore:` 維護工作