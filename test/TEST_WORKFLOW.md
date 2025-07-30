# 測試文檔使用工作流程

## 🎯 實際使用場景

### 場景 1: 新增 API 端點
假設要新增「履歷客製化」功能 (`/api/v1/tailor-resume`)

```bash
# Step 1: 查看編號規則 (TEST_SPEC.md)
# 履歷相關功能編號: 400-499
# 所以測試案例編號為: TEST-TR-401-UNIT

# Step 2: 更新測試矩陣 (TEST_MATRIX.md)
# 在「計劃端點」表格新增一行：
| `/api/v1/tailor-resume` | POST | ⏳ 0/6 | ⏳ 0/2 | ⏳ 0/1 | ⏳ | 規劃中 | 2025-08-30 |

# Step 3: 撰寫測試案例
# 根據 TEST_SPEC.md 模板建立測試
```

### 場景 2: 追蹤測試進度
```bash
# 查看 TEST_MATRIX.md 的統計資訊
# - 目前覆蓋率: 95%
# - 待完成測試: 3 個
# - 下週目標: 100% 覆蓋

# 更新狀態
# ⏳ → 🔄 (開始測試)
# 🔄 → ✅ (測試通過)
# 🔄 → ❌ (測試失敗)
```

### 場景 3: 品質審查
```bash
# 1. 開啟 TEST_STRATEGY.md
# 2. 檢查品質目標:
#    - 單元測試覆蓋率 > 80% ✓
#    - API 回應時間 < 3秒 ✓
#    - 0 個 P0 錯誤 ✓
# 3. 產生報告給主管
```

## 📋 快速檢查清單

### 每日開發
- [ ] 新功能有對應的測試案例編號嗎？
- [ ] 測試案例遵循 TEST_SPEC.md 格式嗎？
- [ ] TEST_MATRIX.md 更新了嗎？

### 每週檢視
- [ ] 檢查 TEST_MATRIX.md 覆蓋率統計
- [ ] 更新測試執行狀態（✅/❌/🔄）
- [ ] 調整下週測試優先級

### 每月評估
- [ ] TEST_STRATEGY.md 的品質目標達成了嗎？
- [ ] 需要調整測試策略嗎？
- [ ] 測試文檔需要版本更新嗎？

## 🔧 自動化整合

### Git Hook (pre-commit)
```bash
#!/bin/bash
# .git/hooks/pre-commit

# 檢查是否有新增 API 但未更新 TEST_MATRIX.md
if git diff --staged --name-only | grep -q "api/"; then
  if ! git diff --staged --name-only | grep -q "TEST_MATRIX.md"; then
    echo "警告: 新增 API 但未更新 TEST_MATRIX.md"
    exit 1
  fi
fi
```

### CI/CD Pipeline
```yaml
# .github/workflows/test-check.yml
name: Test Documentation Check

on: [pull_request]

jobs:
  check-test-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Check TEST_MATRIX.md is updated
        run: |
          # 檢查測試矩陣是否同步更新
          python test/scripts/check_test_matrix_sync.py
```

## 💡 最佳實踐

1. **即時更新** - 開發時就更新，不要等到最後
2. **團隊同步** - 每週團隊會議檢視 TEST_MATRIX.md
3. **版本控制** - 測試文檔與程式碼一起提交
4. **自動提醒** - 設定 CI/CD 檢查文檔同步