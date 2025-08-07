#!/bin/bash
# SessionStart hook: 顯示專案狀態
# 在每個新對話開始時執行

echo "🚀 Azure Container API Project"
echo "📂 Dir: $(pwd)"
echo ""
echo "⚠️  IMPORTANT: Initialize Serena MCP"
echo "   1. Use: mcp__serena__activate_project(\"azure_container\")"
echo "   2. If fails, use: mcp__serena__activate_project(\".\")"