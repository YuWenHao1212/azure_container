#!/bin/bash
# Unified Ruff Trigger System
# 統一的 Ruff 觸發系統，整合自動觸發和手動觸發

# 配置
TRIGGER_MANAGER=".claude/scripts/trigger_manager.py"
LOG_FILE="/tmp/claude_unified_trigger.log"

# 日誌函數
log_info() {
    echo "[$(date '+%H:%M:%S')] Unified Trigger: $1" >> "$LOG_FILE"
}

# 檢查觸發管理器是否可用
check_trigger_manager() {
    if [ ! -f "$TRIGGER_MANAGER" ]; then
        log_info "Error: Trigger manager not found at $TRIGGER_MANAGER"
        return 1
    fi
    
    if [ ! -x "$TRIGGER_MANAGER" ]; then
        chmod +x "$TRIGGER_MANAGER" 2>/dev/null || true
    fi
    
    return 0
}

# 處理自動觸發
handle_auto_trigger() {
    log_info "Handling auto trigger request"
    
    if ! check_trigger_manager; then
        return 1
    fi
    
    local result=$(python "$TRIGGER_MANAGER" --auto 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_info "Auto trigger successful: $result"
        
        # 顯示簡潔的成功訊息
        echo ""
        echo "✅ Smart Ruff Auto-Check Completed"
        echo "   Result: $(echo "$result" | tail -1)"
        echo ""
    else
        log_info "Auto trigger failed: $result"
        
        # 顯示錯誤訊息
        echo ""
        echo "⚠️  Smart Ruff Auto-Check Failed"
        echo "   Error: $(echo "$result" | tail -1)"
        echo ""
    fi
    
    return $exit_code
}

# 處理手動觸發
handle_manual_trigger() {
    local files="$*"
    log_info "Handling manual trigger request: $files"
    
    if ! check_trigger_manager; then
        return 1
    fi
    
    local result
    if [ -n "$files" ]; then
        result=$(python "$TRIGGER_MANAGER" --manual $files 2>&1)
    else
        result=$(python "$TRIGGER_MANAGER" --manual 2>&1)
    fi
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_info "Manual trigger successful: $result"
        echo "✅ Manual Ruff check completed successfully"
    else
        log_info "Manual trigger failed: $result"
        echo "⚠️  Manual Ruff check failed: $(echo "$result" | tail -1)"
    fi
    
    return $exit_code
}

# 顯示狀態
show_status() {
    if check_trigger_manager; then
        python "$TRIGGER_MANAGER" --status
    else
        echo "❌ Trigger manager unavailable"
    fi
}

# 主函數
main() {
    case "${1:-auto}" in
        "--auto"|"auto")
            handle_auto_trigger
            ;;
        "--manual"|"manual")
            shift
            handle_manual_trigger "$@"
            ;;
        "--status"|"status")
            show_status
            ;;
        "--help"|"help")
            echo "Usage: $0 [auto|manual [files...]|status|help]"
            echo "  auto    - Process automatic trigger requests (default)"
            echo "  manual  - Process manual trigger request"
            echo "  status  - Show trigger system status"
            echo "  help    - Show this help message"
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# 執行主函數
main "$@"