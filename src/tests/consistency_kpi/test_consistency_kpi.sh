#!/bin/bash

# 關鍵字提取 API 一致性 KPI 測試腳本
# 這是重要的商業 KPI 測試，用於驗證 API 輸出的一致性
# Author: Claude Code
# Date: 2025-07-01

echo "=== 關鍵字提取一致性 KPI 測試 ==="
echo "測試時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

API_URL="http://localhost:8000/api/v1/extract-jd-keywords"
TEST_COUNT=50
PROMPT_VERSION="v1.2.0"

# 檢查 API 是否運行
echo "檢查 API 狀態..."
if ! curl -s "$API_URL" > /dev/null; then
    echo "錯誤: API 無法連接，請確保服務正在運行"
    exit 1
fi

# 顯示測試配置
echo "測試配置:"
echo "- API URL: $API_URL"
echo "- 測試次數: $TEST_COUNT"
echo "- Prompt 版本: $PROMPT_VERSION"
echo "- 最大返回關鍵字: 16"
echo ""

# 選擇測試類型
echo "請選擇測試類型:"
echo "1) 短文本測試 (TSMC - ~1,200 字符)"
echo "2) 長文本測試 (BCG - ~5,898 字符)"
echo "3) 兩者都測試"
read -p "選擇 (1-3): " choice

case $choice in
    1)
        echo "執行短文本測試..."
        ./test_tsmc_consistency.sh $TEST_COUNT
        ;;
    2)
        echo "執行長文本測試..."
        ./test_bcg_consistency.sh $TEST_COUNT
        ;;
    3)
        echo "執行完整測試套件..."
        ./test_tsmc_consistency.sh $TEST_COUNT
        echo ""
        ./test_bcg_consistency.sh $TEST_COUNT
        ;;
    *)
        echo "無效選擇"
        exit 1
        ;;
esac

echo ""
echo "測試完成！"
echo "請查看生成的報告以了解詳細結果。"