#!/bin/bash
# Smart Ruff Checker v2: 使用 Sub Agent 的智能延遲 Ruff 檢查系統
# 新版本使用 Claude Code Task tool 觸發 ruff-checker Sub Agent

# 配置參數
DELAY_SECONDS=30                                    # 延遲檢查時間（秒）
PENDING_FILES="/tmp/claude_ruff_pending_v2.txt"    # 待檢查檔案清單
LOCK_FILE="/tmp/claude_ruff_checker_v2.lock"       # 程序鎖檔案
CHECKER_PID_FILE="/tmp/claude_ruff_checker_v2.pid" # 檢查器 PID 檔案
TIMER_FILE="/tmp/claude_ruff_timer_v2.txt"         # 計時器狀態檔案
MAX_FILES_IMMEDIATE=3                               # 立即檢查的檔案數量閾值

# 日誌函數
log_debug() {
    echo "[$(date '+%H:%M:%S')] Smart Ruff v2: $1" >> /tmp/claude_hook_debug.log
}

# 清理函數
cleanup_timer() {
    rm -f "$CHECKER_PID_FILE" "$TIMER_FILE"
    log_debug "Timer cleanup completed"
}

# 檢查是否有正在運行的計時器
get_running_timer() {
    if [ -f "$CHECKER_PID_FILE" ]; then
        local pid=$(cat "$CHECKER_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        else
            # PID 檔案存在但程序已死亡，清理
            rm -f "$CHECKER_PID_FILE"
        fi
    fi
    return 1
}

# 重置滾動計時器
reset_rolling_timer() {
    # 殺死現有的計時器程序
    local existing_pid=$(get_running_timer)
    if [ -n "$existing_pid" ]; then
        kill "$existing_pid" 2>/dev/null
        log_debug "Reset timer: killed existing PID $existing_pid"
    fi
    
    # 記錄計時器重置時間
    echo "$(date +%s)" > "$TIMER_FILE"
    
    # 啟動新的計時器
    start_rolling_timer
}

# 啟動滾動計時器
start_rolling_timer() {
    # 在背景啟動計時器程序
    (
        # 儲存 PID
        echo $$ > "$CHECKER_PID_FILE"
        local start_time=$(date +%s)
        log_debug "Started rolling timer (PID: $$, delay: ${DELAY_SECONDS}s)"
        
        # 等待延遲時間
        sleep "$DELAY_SECONDS"
        
        # 檢查是否被重置
        if [ -f "$TIMER_FILE" ]; then
            local reset_time=$(cat "$TIMER_FILE" 2>/dev/null || echo "$start_time")
            if [ "$reset_time" -gt "$start_time" ]; then
                log_debug "Timer was reset during wait, exiting"
                cleanup_timer
                exit 0
            fi
        fi
        
        # 執行 Sub Agent 檢查
        execute_subagent_check
        
        # 清理
        cleanup_timer
    ) &
    
    local new_pid=$!
    echo "$new_pid" > "$CHECKER_PID_FILE"
    log_debug "Rolling timer started with PID: $new_pid"
}

# 執行 Sub Agent 檢查
execute_subagent_check() {
    local files_to_check=""
    
    # 取得並清空待檢查檔案清單 (macOS compatible)
    local lock_attempts=0
    while [ $lock_attempts -lt 10 ]; do
        if mkdir "$LOCK_FILE.dir" 2>/dev/null; then
            # 成功取得鎖
            if [ -f "$PENDING_FILES" ]; then
                files_to_check=$(cat "$PENDING_FILES")
                rm -f "$PENDING_FILES"
            fi
            # 釋放鎖
            rmdir "$LOCK_FILE.dir" 2>/dev/null || true
            break
        else
            # 等待鎖釋放
            sleep 0.1
            lock_attempts=$((lock_attempts + 1))
        fi
    done
    
    if [ -z "$files_to_check" ]; then
        log_debug "No files to check"
        return 0
    fi
    
    # 過濾存在的檔案
    local existing_files=""
    for file in $files_to_check; do
        if [ -f "$file" ]; then
            existing_files="$existing_files $file"
        fi
    done
    
    if [ -z "$existing_files" ]; then
        log_debug "No existing files to check"
        return 0
    fi
    
    local file_count=$(echo $existing_files | wc -w)
    log_debug "Triggering Sub Agent for $file_count files: $existing_files"
    
    # 創建觸發檔案，通知 Claude Code 需要執行 Sub Agent
    local trigger_file="/tmp/claude_ruff_trigger_$(date +%s).json"
    cat > "$trigger_file" << EOF
{
    "action": "trigger_subagent",
    "subagent": "ruff-checker",
    "timestamp": "$(date -Iseconds)",
    "files": [$(echo "$existing_files" | sed 's/[^ ]*/\"&\"/g' | sed 's/ /, /g')],
    "file_count": $file_count,
    "trigger_reason": "delayed_batch_check"
}
EOF
    
    # 輸出 Sub Agent 觸發建議
    echo ""
    echo "🤖 Smart Ruff Auto-Trigger Ready"
    echo "═══════════════════════════════════════════════════════════════"
    echo "📊 Detected $file_count Python files with potential issues"
    echo "🎯 Recommendation: Trigger @Ruff-checker for detailed analysis"
    echo ""
    echo "💡 Manual trigger command: @Ruff-checker"
    echo "📁 Or run quick check: python .claude/scripts/ruff_checker.py"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # 記錄詳細資訊到結果檔案
    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "🤖 Sub Agent Trigger Request - $(date '+%H:%M:%S')"
        echo "═══════════════════════════════════════════════════════════════"
        echo "🎯 Target: ruff-checker Sub Agent"
        echo "📊 Files to check: $file_count"
        echo ""
        echo "📁 File list:"
        for file in $existing_files; do
            echo "   • $file"
        done
        echo ""
        echo "⏰ Trigger reason: delayed_batch_check (${DELAY_SECONDS}s delay)"
        echo "🗂️  Trigger data: $trigger_file"
        echo "═══════════════════════════════════════════════════════════════"
    } > "/tmp/claude_last_ruff_trigger.txt"
    
    log_debug "Sub Agent trigger completed: $file_count files, trigger saved to $trigger_file"
}

# 添加檔案到待檢查清單 (macOS compatible)
add_files_to_pending() {
    local files="$1"
    
    if [ -n "$files" ]; then
        # 簡單的檔案鎖定機制（無 flock）
        local lock_attempts=0
        while [ $lock_attempts -lt 10 ]; do
            if mkdir "$LOCK_FILE.dir" 2>/dev/null; then
                # 成功取得鎖
                {
                    [ -f "$PENDING_FILES" ] && cat "$PENDING_FILES"
                    echo "$files" | tr ' ' '
'
                } | sort -u | grep -v "^$" > "${PENDING_FILES}.tmp"
                
                mv "${PENDING_FILES}.tmp" "$PENDING_FILES" 2>/dev/null || true
                
                local file_count=$(wc -l < "$PENDING_FILES" 2>/dev/null || echo "0")
                log_debug "Added files to pending (total: $file_count files)"
                
                # 釋放鎖
                rmdir "$LOCK_FILE.dir" 2>/dev/null || true
                break
            else
                # 等待鎖釋放
                sleep 0.1
                lock_attempts=$((lock_attempts + 1))
            fi
        done
    fi
}

# 主函數：處理新的檔案修改
process_file_changes() {
    local modified_files="$1"
    
    if [ -z "$modified_files" ]; then
        return 0
    fi
    
    local file_count=$(echo $modified_files | wc -w)
    log_debug "Processing $file_count modified files"
    
    # 添加檔案到待檢查清單
    add_files_to_pending "$modified_files"
    
    # 重置滾動計時器（這會殺死現有計時器並啟動新的）
    reset_rolling_timer
}

# 獲取修改的檔案清單
get_modified_python_files() {
    local modified_py=$(git diff --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
    local staged_py=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
    local untracked_py=$(git ls-files --others --exclude-standard 2>/dev/null | grep "\.py$" || true)
    
    # 合併並去重
    echo -e "$modified_py\n$staged_py\n$untracked_py" | sort -u | grep -v "^$" || true
}

# 狀態查詢函數
show_timer_status() {
    echo "🔄 Rolling Timer Status"
    echo "═══════════════════════════════════════════════════════════════"
    
    local running_pid=$(get_running_timer)
    if [ -n "$running_pid" ]; then
        echo "⏰ Status: ACTIVE (PID: $running_pid)"
        if [ -f "$TIMER_FILE" ]; then
            local start_time=$(cat "$TIMER_FILE")
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            local remaining=$((DELAY_SECONDS - elapsed))
            if [ "$remaining" -gt 0 ]; then
                echo "⏱️  Time remaining: ${remaining}s"
            else
                echo "⏱️  Time remaining: 0s (should trigger soon)"
            fi
        fi
    else
        echo "⏰ Status: INACTIVE"
    fi
    
    if [ -f "$PENDING_FILES" ]; then
        local pending_count=$(wc -l < "$PENDING_FILES" 2>/dev/null || echo "0")
        echo "📋 Pending files: $pending_count"
        if [ "$pending_count" -gt 0 ]; then
            echo "📁 Files:"
            head -5 "$PENDING_FILES" | while read -r file; do
                echo "   • $file"
            done
            if [ "$pending_count" -gt 5 ]; then
                echo "   ... and $((pending_count - 5)) more"
            fi
        fi
    else
        echo "📋 Pending files: 0"
    fi
    
    echo "═══════════════════════════════════════════════════════════════"
}

# 主執行邏輯
main() {
    # 如果傳入 --status 參數，顯示狀態
    if [ "$1" = "--status" ]; then
        show_timer_status
        return 0
    fi
    
    # 如果傳入 --force-trigger 參數，立即觸發
    if [ "$1" = "--force-trigger" ]; then
        log_debug "Force trigger requested"
        execute_subagent_check
        return 0
    fi
    
    # 正常的檔案修改處理
    local modified_files=$(get_modified_python_files)
    
    if [ -n "$modified_files" ]; then
        process_file_changes "$modified_files"
    else
        log_debug "No modified Python files detected"
    fi
}

# 執行主函數
main "$@"