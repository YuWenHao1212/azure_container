#!/bin/bash
# UserPromptSubmit hook: Commit 前的完整檢查
# 當使用者提到 commit 時觸發

# 確保在正確的工作目錄
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# 檢查 Python 版本的檢查腳本是否存在
if [ ! -f "test/scripts/pre_commit_check_advanced.py" ]; then
    echo "❌ 錯誤: pre_commit_check_advanced.py 不存在"
    echo ""
    echo "Pre-commit hook 需要 Python 檢查腳本才能運行。"
    echo "請確認檔案存在於: test/scripts/pre_commit_check_advanced.py"
    echo ""
    echo "如果檔案遺失，請聯繫開發團隊或從版本控制系統還原。"
    exit 1
fi

# 執行 Python 進階版 pre-commit 檢查
echo "使用 Python 進階版 pre-commit 檢查..."
python test/scripts/pre_commit_check_advanced.py
exit $?