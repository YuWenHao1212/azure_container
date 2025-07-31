#!/bin/bash

# Precommit Log Viewer
# Provides utilities to view and analyze precommit test logs

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/test/logs"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  list         List all precommit logs"
    echo "  latest       Show the latest log"
    echo "  view <file>  View a specific log file"
    echo "  stats        Show statistics from all logs"
    echo "  failures     Show only failed test runs"
    echo "  clean        Remove old logs (keep last 5 pairs)"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 latest"
    echo "  $0 view precommit_20250731_143022.txt"
    echo "  $0 stats"
}

# Function to list all logs
list_logs() {
    echo "======================================"
    echo "Precommit Logs"
    echo "======================================"
    echo ""
    
    local txt_files=($(ls -t "$LOG_DIR"/precommit_*.txt 2>/dev/null))
    
    if [ ${#txt_files[@]} -eq 0 ]; then
        echo "No precommit logs found."
        return
    fi
    
    echo "Found ${#txt_files[@]} log(s):"
    echo ""
    
    for file in "${txt_files[@]}"; do
        local basename=$(basename "$file")
        local timestamp=${basename#precommit_}
        timestamp=${timestamp%.txt}
        
        # Check if corresponding JSON exists
        local json_file="${file%.txt}.json"
        if [ -f "$json_file" ]; then
            # Parse status from JSON
            local status=$(grep '"status":' "$json_file" | tail -1 | cut -d'"' -f4)
            local duration=$(grep '"total_duration":' "$json_file" | cut -d':' -f2 | tr -d ' ,')
            
            if [ "$status" = "passed" ]; then
                echo -e "${GREEN}✅${NC} $timestamp - ${GREEN}PASSED${NC} (${duration}s)"
            else
                echo -e "${RED}❌${NC} $timestamp - ${RED}FAILED${NC} (${duration}s)"
            fi
        else
            echo "   $timestamp (JSON missing)"
        fi
    done
}

# Function to view latest log
view_latest() {
    local latest_txt=$(ls -t "$LOG_DIR"/precommit_*.txt 2>/dev/null | head -1)
    
    if [ -z "$latest_txt" ]; then
        echo "No precommit logs found."
        return
    fi
    
    echo "======================================"
    echo "Latest Precommit Log"
    echo "======================================"
    echo ""
    
    cat "$latest_txt"
    
    # Also show JSON summary if exists
    local json_file="${latest_txt%.txt}.json"
    if [ -f "$json_file" ]; then
        echo ""
        echo "======================================"
        echo "JSON Summary"
        echo "======================================"
        jq '.' "$json_file" 2>/dev/null || cat "$json_file"
    fi
}

# Function to view specific log
view_log() {
    local filename=$1
    
    # Add .txt extension if not present
    if [[ ! "$filename" =~ \.txt$ ]]; then
        filename="${filename}.txt"
    fi
    
    # Add precommit_ prefix if not present
    if [[ ! "$filename" =~ ^precommit_ ]]; then
        filename="precommit_${filename}"
    fi
    
    local filepath="$LOG_DIR/$filename"
    
    if [ ! -f "$filepath" ]; then
        echo "Log file not found: $filepath"
        return 1
    fi
    
    cat "$filepath"
}

# Function to show statistics
show_stats() {
    echo "======================================"
    echo "Precommit Test Statistics"
    echo "======================================"
    echo ""
    
    local json_files=($(ls "$LOG_DIR"/precommit_*.json 2>/dev/null))
    
    if [ ${#json_files[@]} -eq 0 ]; then
        echo "No JSON logs found for analysis."
        return
    fi
    
    local total_runs=${#json_files[@]}
    local passed_runs=0
    local failed_runs=0
    local total_duration=0
    local min_duration=999999
    local max_duration=0
    
    for file in "${json_files[@]}"; do
        local status=$(grep '"status":' "$file" | tail -1 | cut -d'"' -f4)
        local duration=$(grep '"total_duration":' "$file" | cut -d':' -f2 | tr -d ' ,')
        
        if [ "$status" = "passed" ]; then
            passed_runs=$((passed_runs + 1))
        else
            failed_runs=$((failed_runs + 1))
        fi
        
        if [ -n "$duration" ]; then
            total_duration=$((total_duration + duration))
            if [ $duration -lt $min_duration ]; then
                min_duration=$duration
            fi
            if [ $duration -gt $max_duration ]; then
                max_duration=$duration
            fi
        fi
    done
    
    local avg_duration=0
    if [ $total_runs -gt 0 ]; then
        avg_duration=$((total_duration / total_runs))
    fi
    
    local pass_rate=0
    if [ $total_runs -gt 0 ]; then
        pass_rate=$((passed_runs * 100 / total_runs))
    fi
    
    echo "Total runs: $total_runs"
    echo -e "Passed: ${GREEN}$passed_runs${NC}"
    echo -e "Failed: ${RED}$failed_runs${NC}"
    echo "Pass rate: ${pass_rate}%"
    echo ""
    echo "Duration statistics:"
    echo "  Average: ${avg_duration}s"
    echo "  Minimum: ${min_duration}s"
    echo "  Maximum: ${max_duration}s"
    echo ""
    
    # Show duration trend
    echo "Recent duration trend (last 5 runs):"
    local recent_files=($(ls -t "$LOG_DIR"/precommit_*.json 2>/dev/null | head -5))
    for file in "${recent_files[@]}"; do
        local timestamp=$(basename "$file" | sed 's/precommit_//; s/.json//')
        local duration=$(grep '"total_duration":' "$file" | cut -d':' -f2 | tr -d ' ,')
        local status=$(grep '"status":' "$file" | tail -1 | cut -d'"' -f4)
        
        if [ "$duration" -gt 90 ]; then
            echo -e "  $timestamp: ${YELLOW}${duration}s${NC} (exceeded target)"
        else
            echo -e "  $timestamp: ${GREEN}${duration}s${NC}"
        fi
    done
}

# Function to show failures
show_failures() {
    echo "======================================"
    echo "Failed Precommit Runs"
    echo "======================================"
    echo ""
    
    local json_files=($(ls "$LOG_DIR"/precommit_*.json 2>/dev/null))
    local found_failures=0
    
    for file in "${json_files[@]}"; do
        local status=$(grep '"status":' "$file" | tail -1 | cut -d'"' -f4)
        
        if [ "$status" != "passed" ]; then
            found_failures=1
            local timestamp=$(basename "$file" | sed 's/precommit_//; s/.json//')
            local txt_file="${file%.json}.txt"
            
            echo -e "${RED}Failed run: $timestamp${NC}"
            
            if [ -f "$txt_file" ]; then
                # Extract failure details
                echo "Details:"
                grep -A 5 "FAILED\|ERROR" "$txt_file" | head -20
                echo "..."
                echo ""
            fi
        fi
    done
    
    if [ $found_failures -eq 0 ]; then
        echo -e "${GREEN}No failures found!${NC}"
    fi
}

# Function to clean old logs
clean_logs() {
    echo "Cleaning old logs (keeping last 5 pairs)..."
    
    # Get all log files sorted by timestamp (newest first)
    local txt_files=($(ls -t "$LOG_DIR"/precommit_*.txt 2>/dev/null))
    local json_files=($(ls -t "$LOG_DIR"/precommit_*.json 2>/dev/null))
    
    # Remove old text logs
    if [ ${#txt_files[@]} -gt 5 ]; then
        for ((i=5; i<${#txt_files[@]}; i++)); do
            echo "  Removing: $(basename "${txt_files[$i]}")"
            rm -f "${txt_files[$i]}"
        done
    fi
    
    # Remove old JSON logs
    if [ ${#json_files[@]} -gt 5 ]; then
        for ((i=5; i<${#json_files[@]}; i++)); do
            echo "  Removing: $(basename "${json_files[$i]}")"
            rm -f "${json_files[$i]}"
        done
    fi
    
    echo "Done."
}

# Main script logic
case "${1:-help}" in
    list)
        list_logs
        ;;
    latest)
        view_latest
        ;;
    view)
        if [ -z "$2" ]; then
            echo "Error: Please specify a log file to view"
            echo "Usage: $0 view <filename>"
            exit 1
        fi
        view_log "$2"
        ;;
    stats)
        show_stats
        ;;
    failures)
        show_failures
        ;;
    clean)
        clean_logs
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac