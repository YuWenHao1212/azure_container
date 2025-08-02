#!/bin/bash

# Log utilities for test scripts
# Provides common functions for log management

# Function to clean old log files (keep only latest 6)
clean_old_logs() {
    local log_dir=$1
    local log_pattern=$2
    
    if [ -z "$log_dir" ] || [ -z "$log_pattern" ]; then
        echo "Usage: clean_old_logs <log_dir> <log_pattern>"
        return 1
    fi
    
    # Find matching log files, sort by modification time, and keep only latest 6
    find "$log_dir" -name "$log_pattern" -type f 2>/dev/null | \
        xargs -r ls -t | \
        tail -n +7 | \
        xargs -r rm -f
}

# Function to ensure log directory and clean old logs
prepare_log_dir() {
    local log_dir=$1
    local log_pattern=$2
    
    # Create directory if it doesn't exist
    mkdir -p "$log_dir"
    
    # Clean old logs if pattern provided
    if [ -n "$log_pattern" ]; then
        clean_old_logs "$log_dir" "$log_pattern"
    fi
}

# Function to get project root
get_project_root() {
    # Works in both local and CI environments
    echo "${GITHUB_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
}

# Function to get standard log directory
get_log_dir() {
    echo "$(get_project_root)/test/logs"
}

# Export functions for use in other scripts
export -f clean_old_logs
export -f prepare_log_dir
export -f get_project_root
export -f get_log_dir