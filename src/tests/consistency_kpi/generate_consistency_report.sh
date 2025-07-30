#!/bin/bash

# 通用一致性報告生成腳本
# 用於分析測試結果並生成詳細報告

RESULTS_DIR="$1"
JOB_TITLE="$2"
TEXT_LENGTH="$3"

if [ -z "$RESULTS_DIR" ]; then
    echo "用法: $0 <結果目錄> <職位名稱> <文本長度>"
    exit 1
fi

REPORT_FILE="${RESULTS_DIR}/consistency_report.md"

echo "生成一致性分析報告..."

# 開始報告
cat > "$REPORT_FILE" << EOF
# ${JOB_TITLE} 關鍵字提取一致性分析報告

**測試日期**: $(date '+%Y-%m-%d %H:%M:%S')  
**API版本**: v1.2.0  
**限制返回**: 最多16個關鍵字  
**職位**: ${JOB_TITLE}
**職位描述長度**: ${TEXT_LENGTH} 字符

---

## 1. 執行摘要

| 指標 | 數值 | 說明 |
|------|------|------|
EOF

# 計算統計數據
total_tests=0
total_intersection=0
min_intersection=100
max_intersection=0

for stats_file in "${RESULTS_DIR}"/stats_*.json; do
    if [ -f "$stats_file" ]; then
        intersection=$(jq -r '.intersection_count' "$stats_file" 2>/dev/null)
        if [ -n "$intersection" ] && [ "$intersection" != "null" ]; then
            total_tests=$((total_tests + 1))
            total_intersection=$((total_intersection + intersection))
            if [ $intersection -lt $min_intersection ]; then
                min_intersection=$intersection
            fi
            if [ $intersection -gt $max_intersection ]; then
                max_intersection=$intersection
            fi
        fi
    fi
done

if [ $total_tests -gt 0 ]; then
    avg_intersection=$(echo "scale=1; $total_intersection / $total_tests" | bc)
else
    avg_intersection=0
fi

# 計算唯一結果集
hash_file="${RESULTS_DIR}/hashes.txt"
> "$hash_file"

for keywords_file in "${RESULTS_DIR}"/keywords_*.txt; do
    if [ -f "$keywords_file" ] && [ -s "$keywords_file" ]; then
        md5sum "$keywords_file" | awk '{print $1}' >> "$hash_file"
    fi
done

unique_sets=$(sort "$hash_file" | uniq | wc -l)
most_common=$(sort "$hash_file" | uniq -c | sort -nr | head -1)
most_common_count=$(echo "$most_common" | awk '{print $1}')
consistency_rate=$(awk "BEGIN {printf \"%.1f\", $most_common_count / $total_tests * 100}")

# 寫入摘要
echo "| 測試次數 | $total_tests | 成功執行次數 |" >> "$REPORT_FILE"
echo "| 平均交集數 | $avg_intersection | 兩輪之間的平均交集 |" >> "$REPORT_FILE"
echo "| 交集範圍 | $min_intersection-$max_intersection | 最小到最大交集數 |" >> "$REPORT_FILE"
echo "| 返回關鍵字數 | 16 | 每次固定返回 |" >> "$REPORT_FILE"
echo "| 唯一結果集數 | $unique_sets | 不同的關鍵字組合數 |" >> "$REPORT_FILE"
echo "| 最高一致率 | ${consistency_rate}% | 最常見組合的出現頻率 |" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 關鍵字頻率分析
echo "## 2. 關鍵字頻率分析（Top 20）" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| 排名 | 關鍵字 | 出現次數 | 出現率 |" >> "$REPORT_FILE"
echo "|------|--------|----------|--------|" >> "$REPORT_FILE"

# 統計所有關鍵字
all_keywords="${RESULTS_DIR}/all_keywords.txt"
> "$all_keywords"
for keywords_file in "${RESULTS_DIR}"/keywords_*.txt; do
    if [ -f "$keywords_file" ]; then
        cat "$keywords_file" >> "$all_keywords"
    fi
done

# 顯示前20個最常見的關鍵字
rank=1
cat "$all_keywords" | sort | uniq -c | sort -nr | head -20 | while read count keyword; do
    if [ -n "$keyword" ]; then
        percentage=$(awk "BEGIN {printf \"%.0f\", $count / $total_tests * 100}")
        echo "| $rank | $keyword | $count/$total_tests | ${percentage}% |" >> "$REPORT_FILE"
        rank=$((rank + 1))
    fi
done

echo "" >> "$REPORT_FILE"

# 集合分組統計
echo "## 3. 一致性分析" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "共有 **${unique_sets}** 個不同的關鍵字組合。" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 顯示最常見的組合
echo "### 最常見的關鍵字組合（出現${most_common_count}次，佔${consistency_rate}%）" >> "$REPORT_FILE"
most_common_hash=$(echo "$most_common" | awk '{print $2}')
for keywords_file in "${RESULTS_DIR}"/keywords_*.txt; do
    if [ -f "$keywords_file" ]; then
        if [ "$(md5sum "$keywords_file" | awk '{print $1}')" = "$most_common_hash" ]; then
            echo '```' >> "$REPORT_FILE"
            cat "$keywords_file" | tr '\n' ', ' | sed 's/,$//' >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            break
        fi
    fi
done

echo "" >> "$REPORT_FILE"

# 交集分布
echo "## 4. 交集分布分析" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "交集數量分布：" >> "$REPORT_FILE"

# 統計交集分布
for stats_file in "${RESULTS_DIR}"/stats_*.json; do
    if [ -f "$stats_file" ]; then
        jq -r '.intersection_count' "$stats_file" 2>/dev/null
    fi
done | grep -v null | sort -n | uniq -c | while read count value; do
    bar=$(printf '█%.0s' $(seq 1 $count))
    printf "%2d個交集: %-30s (%2d次)\n" $value "$bar" $count >> "$REPORT_FILE"
done

echo '```' >> "$REPORT_FILE"

# 結論
echo "" >> "$REPORT_FILE"
echo "## 5. KPI 達成情況" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 判斷是否達標
if [ "$TEXT_LENGTH" = "~1,200" ]; then
    target_rate=70
    warning_rate=60
else
    target_rate=50
    warning_rate=40
fi

echo "| KPI 指標 | 目標值 | 實測值 | 狀態 |" >> "$REPORT_FILE"
echo "|----------|--------|--------|------|" >> "$REPORT_FILE"

if (( $(echo "$consistency_rate >= $target_rate" | bc -l) )); then
    status="✅ 達標"
elif (( $(echo "$consistency_rate >= $warning_rate" | bc -l) )); then
    status="⚠️ 警戒"
else
    status="❌ 未達標"
fi

echo "| 一致率 | ≥${target_rate}% | ${consistency_rate}% | $status |" >> "$REPORT_FILE"
echo "| 核心關鍵字穩定性 | 100% | 見頻率分析 | - |" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "**報告生成時間**: $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"

echo "報告已生成: $REPORT_FILE"