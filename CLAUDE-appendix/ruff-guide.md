# Ruff 程式碼品質完整指南

## 執行檢查
```bash
# 檢查程式碼
ruff check src/ test/ --line-length=120

# 自動修復可修復的問題
ruff check src/ test/ --fix --line-length=120

# 檢查並修復 (包含較不安全的修復)
ruff check src/ test/ --fix --unsafe-fixes --line-length=120
```

## 主要規則
1. **行長度限制**: 120 字元 (設定在 pyproject.toml)
2. **Import 排序**: 使用 isort 規則，自動分組和排序
3. **命名規範**: 遵循 PEP8 (類別用 PascalCase，函數用 snake_case)
4. **型別註解**: 必要時使用 ClassVar for mutable class attributes
5. **例外處理**: 使用 "raise ... from e" 進行例外鏈結
6. **程式碼風格**: 使用三元運算子、合併 if 條件等

## 常見錯誤與解決
- **E501**: 行太長 → 分行或重構
- **F401**: 未使用 import → 移除或加到 __all__
- **B904**: 例外鏈結缺失 → 使用 "from e"
- **RUF012**: 可變類別屬性 → 使用 ClassVar
- **I001**: Import 順序錯誤 → 重新排序
- **SIM102/108**: 可簡化的條件 → 使用三元運算子

## 任務完成檢查清單
- [ ] 功能實作完成
- [ ] **🚨 執行 `ruff check src/ test/ --line-length=120` 通過 (0 errors)**
- [ ] 相關測試通過
- [ ] 文檔更新完成
- [ ] 才可回報任務完成