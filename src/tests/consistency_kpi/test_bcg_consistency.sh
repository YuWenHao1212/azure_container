#!/bin/bash

# BCG 長文本一致性測試腳本
# 測試長文本 (~5,898 字符) 的關鍵字提取一致性
# 由於 Claude 有 2 分鐘的 Bash 執行時間限制，自動分批處理

TEST_COUNT=${1:-50}
API_URL="http://localhost:8000/api/v1/extract-jd-keywords"
BATCH_SIZE=25

echo "=== BCG Lead Data Scientist 一致性測試 ==="
echo "測試時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "測試次數: $TEST_COUNT"
echo "批次大小: $BATCH_SIZE"

# BCG 職位描述
JOB_DESC_FILE="/tmp/bcg_job_desc_kpi.txt"
cat > "$JOB_DESC_FILE" << 'EOF'
What you'll do

We are seeking a strong candidate with advanced analytics experience to fill an exciting Lead Data Scientist (LDS) position within BCG X. The LDS is a valuable expert in Data Science and will design and build analytics methodologies, solutions, and products to deliver value to BCG's clients in collaboration with case teams. Exceptional candidates will also show an analytical curiosity, going beyond the immediate requirements of the project to find deep insights that others have missed. They will ask questions about outliers, seek to understand the fundamental drivers of advantage and look for clues that may change the basis of competition. The LDS will be involved in all aspects of advanced analytics, from helping to create relevant products and service offerings by working with priority global Practice Areas, to leading and executing analytics work and continuing to expand the analytical foundation and competitive value proposition. The LDS will collaborate directly client and wider BCG case teams and will manage the analytics components of client deliverables. The LDS is responsible for clarifying initial objectives, setting up analytics work plan and methodology, organizing the data scientist members of the team, quality assurance, and managing scope and work planning throughout the project. The LDS is expected to provide mentoring, coaching, and career development to data scientist team members on both a formal and informal basis.


Who You Are

We are looking for talented individuals with a passion for data science, statistics, operations research and transforming organizations into AI led innovative companies.
Deep Technical and Data Science Expertise: You will have a wealth of experience with applying advanced analytics to a variety of business situations, such that you can efficiently and effectively advise multiple teams on the best path to uncovering critical insights for clients.
Experience in core analytics methods (one or more of the following): Statistics (t-tests, ANOVA), variable reduction (FA, PCA), Segmentation/clustering techniques, Geographic cluster recognition and manipulation techniques, Predictive modeling: e.g. logistic regression, linear regression, Network analysis (location-allocation, travelling sales person, vehicle routing problem), Time series analysis: e.g. ARIMA, VAR, etc., Machine learning: e.g. LCA, Random Forest, neural networks, Spatio-temporal analysis, Time series analysis (ARIMA, VAR, etc.), Text mining & unstructured data analytics, Simulation: e.g. MC, dynamic, discrete event, Optimization: e.g. linear programming, heuristic
Familiarity with a broad base of analytics tools (one or more of the following): Data management: e.g. Excel, SQL, PostGRESql, Hadoop/Hive, Alteryx, Analytics platforms: e.g. SAS, R, RapidMiner, SPSS, Data visualization: e.g. Tableau, GIS toolkits (ESRI, Quantum GIS, MapInfo or similar), ESRI Network Analyst, RouteSmart, RoadNet or similar, GPS data analysis a plus, Programming and/or scripting experience: e.g. Python, C#, VBA, Java, Perl, etc.
Experience in applied analytics for business problem solving (one or more of the following): Pricing and promotional effectiveness, Delivery fleet consolidation, Loyalty program effectiveness, Network real estate reorganization, Customer segmentation and targeting, Delivery footprint/territory expansion (or reduction), Customer LTV maximization, Cost modeling of transportation & logistics operations, Churn prevention, Strong project management skills.
Analytical and Conceptual thinking: You will be able to conceptualize business problems and drive frameworks. The LDS will produce leading edge business models and must be able to work in a hypothesis-based environment where inductive rather than deductive thinking is the norm.
Engagement Management and Work with Case Teams: You will have demonstrated ability to manage engagements, client relationships, provide "thought leadership" to teams and able to act as a full member of a BCG project team. They must own analytical modules from work planning to creating impact. He/she must scope, manage and lead work for data science teams, providing expertise on methodology of advanced analytics. Strong presence, strong collaborator and leadership skills and ability to operate effectively in a matrix organization are a must.
Client Relationship Management: The candidate with have a demonstrated ability to communicate effectively and professionally with clients, delivering impactful solutions and presenting work in a concise and thoughtful manner, while demonstrating technical expertise (fluency in both Mandarin and English is required). Strong business focus with experience with 80/20 approaches.
Analytics Innovation: Must be an autonomous self starter with a passion for analytics and problem solving. He/she will help build new Analytics service offerings that grow our portfolio of products and will captures proprietary content as well as analytics insights to the knowledge infrastructure. The candidate will support the creation of proposal/selling documents and provide perspective on relevant Analytics value propositions.


You Bring (Experience & Qualifications)

8+ years of relevant industry work experience providing advanced analytics solutions, or 5+ years consulting experience
PhD or other Advanced degree required in a field linked to business analytics, statistics or geo-statistics, operations research, geography, applied mathematics, computer science, engineering, or related field
Looking for individuals with deep technical and data science expertise, acute strategic and analytical skills, ability to lead and persuade, drive and energy, and desire to work in a project based environment on strategic issues.
Strong record of professional accomplishment and leadership.
Demonstrated ability to lead and manage projects and teams.
EOF

JOB_DESC=$(cat "$JOB_DESC_FILE")

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASE_DIR="bcg_consistency_test_${TIMESTAMP}"
mkdir -p "$BASE_DIR"

# 計算批次數
BATCHES=$(( ($TEST_COUNT + $BATCH_SIZE - 1) / $BATCH_SIZE ))

echo "將執行 $BATCHES 個批次..."
echo ""

# 執行批次測試
for batch in $(seq 1 $BATCHES); do
    start=$(( ($batch - 1) * $BATCH_SIZE + 1 ))
    end=$(( $batch * $BATCH_SIZE ))
    if [ $end -gt $TEST_COUNT ]; then
        end=$TEST_COUNT
    fi
    
    echo "批次 $batch: 測試 $start-$end"
    BATCH_DIR="${BASE_DIR}/batch${batch}"
    mkdir -p "$BATCH_DIR"
    
    for i in $(seq $start $end); do
        printf "\r進度: [%3d/$TEST_COUNT]" $i
        
        # 創建請求JSON文件
        cat > "${BATCH_DIR}/request_${i}.json" << EOJSON
{
    "job_description": $(echo "$JOB_DESC" | jq -Rs .),
    "max_keywords": 20,
    "prompt_version": "v1.2.0"
}
EOJSON
        
        # 使用文件進行請求
        response=$(curl -s -X POST "$API_URL" \
            -H "Content-Type: application/json" \
            -d @"${BATCH_DIR}/request_${i}.json")
        
        # 保存響應
        echo "$response" > "${BATCH_DIR}/response_${i}.json"
        
        # 提取關鍵字
        echo "$response" | jq -r '.data.keywords[]' 2>/dev/null | sort > "${BATCH_DIR}/keywords_${i}.txt"
        
        # 提取統計信息
        echo "$response" | jq '.data.intersection_stats' 2>/dev/null > "${BATCH_DIR}/stats_${i}.json"
        
        sleep 0.5
    done
    echo ""
done

echo ""
echo "合併批次結果..."

# 合併所有批次結果
MERGED_DIR="${BASE_DIR}/merged"
mkdir -p "$MERGED_DIR"

for batch in $(seq 1 $BATCHES); do
    cp "${BASE_DIR}/batch${batch}"/*.json "$MERGED_DIR/" 2>/dev/null
    cp "${BASE_DIR}/batch${batch}"/*.txt "$MERGED_DIR/" 2>/dev/null
done

# 生成報告
./generate_consistency_report.sh "$MERGED_DIR" "BCG Lead Data Scientist" "5,898"

echo "測試完成！結果保存在: $BASE_DIR"

# 清理
rm -f "$JOB_DESC_FILE"