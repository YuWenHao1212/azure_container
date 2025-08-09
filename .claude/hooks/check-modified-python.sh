#!/bin/bash
# PostToolUse hook: 使用新的智能延遲 Ruff 檢查系統 v2
# 支援 Sub Agent 自動觸發和滾動計時器

# Debug: 記錄執行資訊
echo "[$(date)] PostToolUse hook v2 executed" >> /tmp/claude_hook_debug.log

# 確保在正確的工作目錄
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# 調用新的智能 Ruff 檢查器 v2
if [ -f ".claude/hooks/smart-ruff-checker-v2.sh" ]; then
    bash .claude/hooks/smart-ruff-checker-v2.sh
    
    # 檢查是否有 Sub Agent 觸發請求
    local latest_trigger=$(ls -t /tmp/claude_ruff_trigger_*.json 2>/dev/null | head -1)
    
    if [ -n "$latest_trigger" ] && [ -f "$latest_trigger" ]; then
        # 讀取觸發請求的時間戳
        local trigger_time=$(jq -r '.timestamp' "$latest_trigger" 2>/dev/null || echo "")
        local current_time=$(date -Iseconds)
        
        # 如果觸發請求是最近 1 分鐘內的，可能需要等待 Claude Code 處理
        if [ -n "$trigger_time" ]; then
            echo "[$(date)] Found recent Sub Agent trigger request: $latest_trigger" >> /tmp/claude_hook_debug.log
        fi
    fi
else
    echo "[$(date)] Smart ruff checker v2 not found" >> /tmp/claude_hook_debug.log
fi

# PostToolUse: 不阻塞，檢查器在背景運行
exit 0