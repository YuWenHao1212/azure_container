#!/bin/bash

# TSMC 短文本一致性測試腳本
# 測試短文本 (~1,200 字符) 的關鍵字提取一致性

TEST_COUNT=${1:-50}
API_URL="http://localhost:8000/api/v1/extract-jd-keywords"

echo "=== TSMC Senior Data Analyst 一致性測試 ==="
echo "測試時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "測試次數: $TEST_COUNT"

# TSMC 職位描述
JOB_DESC="Established in 1987 and headquartered in Taiwan, TSMC pioneered the pure-play foundry business model with an exclusive focus on manufacturing its customers' products. In 2023, the company served 528 customers with 11,895 products for high performance computing, smartphones, IoT, automotive, and consumer electronics, and is the world's largest provider of logic ICs with annual capacity of 16 million 12-inch equivalent wafers. TSMC operates fabs in Taiwan as well as manufacturing subsidiaries in Washington State, Japan and China, and its ESMC subsidiary plans to begin construction on a fab in Germany in 2024. In Arizona, TSMC is building three fabs, with the first starting 4nm production in 2025, the second by 2028, and the third by the end of the decade.

The Senior Data Analyst will work across the various departments within TSMC Arizona and be responsible for creating and updating dashboards using SQL, R, Python, and BI tools. The ideal candidate will have strong analytical skills and be able to present findings to both a technical and non-technical audience.

Responsibilities
Design and maintain dashboards and Automated reports for various departments (Quality and Reliability, Operations, Manufacturing)
Write code to connect, extract data from various databases (Oracle SQL, Hadoop)
Analyze data to identify trends and patterns
Present findings to stakeholders in a clear and concise manner
Work with cross-functional teams to identify and solve business problems

Requirements
Master's degree in related discipline or bachelor's degree with 3 years of related work experience
Proficiency in SQL and experience with databases (Oracle, MySQL, etc.)
Experience with BI tools (Tableau, Power BI, Looker, etc.)
Proficiency in Python or R for data manipulation and analysis
Experience with data visualization best practices
Strong analytical and problem-solving skills"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="tsmc_consistency_test_${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

echo "執行 $TEST_COUNT 次測試..."
echo ""

# 執行測試
for i in $(seq 1 $TEST_COUNT); do
    printf "\r進度: [%3d/$TEST_COUNT]" $i
    
    # 創建請求
    request_json=$(cat <<EOF
{
    "job_description": "$JOB_DESC",
    "max_keywords": 20,
    "prompt_version": "v1.2.0"
}
EOF
)
    
    # 發送請求
    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "$request_json")
    
    # 保存響應
    echo "$response" > "${RESULTS_DIR}/response_${i}.json"
    
    # 提取關鍵字
    echo "$response" | jq -r '.data.keywords[]' 2>/dev/null | sort > "${RESULTS_DIR}/keywords_${i}.txt"
    
    # 提取統計信息
    echo "$response" | jq '.data.intersection_stats' 2>/dev/null > "${RESULTS_DIR}/stats_${i}.json"
    
    sleep 0.5
done

echo ""
echo ""

# 生成報告
./generate_consistency_report.sh "$RESULTS_DIR" "TSMC Senior Data Analyst" "~1,200"

echo "測試完成！結果保存在: $RESULTS_DIR"