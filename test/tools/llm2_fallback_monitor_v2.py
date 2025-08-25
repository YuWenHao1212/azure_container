"""
LLM2 Fallback Monitor Tool V2 - Enhanced Detection
用於更準確地監控 Resume Tailoring API 中 LLM2 的 fallback 發生率

Tool ID: TOOL-LLM2-MON-02
Version: 2.0
Changes:
- 增強了fallback檢測邏輯
- 檢測空內容觸發的fallback
- 比對原始簡歷內容
- 更詳細的診斷輸出
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configuration
DEFAULT_API_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/tailor-resume"
DEFAULT_API_KEY = os.getenv("CONTAINER_APP_API_KEY", "hUjQoHxaWoUUvqGxD4eMFYpT4dYXyFmgIK0fwtEePFk")

# Test data - 使用前端相同的測試資料
ORIGINAL_RESUME = """<h3>Personal Summary:</h3> <p>1. As a Business Administration Manager, I possess extensive experience in data processing, visualization, and interpretation, aiding executive management in making informed decisions. <br>2. With 10 years of hands-on experience in project management, I am proficient in overseeing projects within fast-paced consumer and sophisticated automotive industries. <br>3. My vision is to create value for my community alongside individuals who uphold shared values of respect, freedom, and integrity.</p> <h3>Work Experience:</h3> <p><strong>Business Administration Manager</strong><br><strong>友達光電 </strong><em>, 台灣 Taiwan 新竹市 </em><br><em> Jul 2022- Apr 2025 </em><br>- Execute advanced data processing and visualization tasks with a focus on the Chinese automotive and IT display sectors, providing pivotal support for executive decision-making. This involves a comprehensive review of business unit performance, incorporating in-depth analysis of financial income statements and data outcomes. The integrated approach not only reveals the overall business operations but also aids in strategic decision-making and promotes corporate growth.<br>- Spearheaded data management projects by collaborating with IT and key departments to deepen the company's insights into its business operations. This effort aims to boost operational efficiency, improve performance metrics, and stimulate innovation across the organization.<br><br><strong>Automotive Project Manager, Deputy Manager</strong><br><strong>友達光電 </strong><em>, 台灣 新竹縣市 </em><br><em> May 2019- Jun 2022 </em><br>- RFQ Management and Financial Evaluation: Oversee the Request for Quotation (RFQ) processes for automotive Original Equipment Manufacturers (OEMs), assess project budgets and profit &amp; loss statements, and critically review quotations to guarantee project profitability.<br>- Customer Requirements and Solution Alignment: Manage and align customer requirements with internal solutions, ensuring they meet customer needs. Address and secure customer acceptance for any discrepancies.<br>- Customer Engagement and Project Oversight: Maintain consistent communication with customers through regular meetings, discuss unresolved issues, review risk management strategies, and confirm adherence to project timelines.<br><br><strong>Product Management, Department Manager</strong><br><strong>友達光電 </strong><em>, Taiwan </em><br><em> Jul 2011- Apr 2019 </em><br>- Led a team of seven project managers overseeing the production of mobile display products at LCD manufacturing sites in Taiwan and Singapore.<br>- Designed and implemented a profit and loss (P&amp;L) database and dashboard for mobile products, enabling effective data visualization and strategic presentations to the Vice President.<br>- Managed the new product development process, ensuring the on-time delivery of prototypes and compliance with customer specifications.<br>- Achieved significant success in product development, highlighted by:<br>Launching the Xiaomi 4.7" model, achieving sales of 23 million units.<br>Introducing the OPPO 5.5" model, with 12 million units sold.<br><br><strong>Customer Service Engineer</strong><br><strong>Novatek Microelectronics Corp </strong><em>, Hsin-Chu, Taiwan </em><br><em> Apr 2007- Jan 2011 </em><br>- Led the local customer service team to support major Chinese phone makers (such as Huawei, ZTE, etc.) in designing Novatek's display IC, which has been adopted and mass-produced in millions of pieces per month.<br>- Built and trained the customer service team in Mainland China, resulting in a 50%+ reduction in troubleshooting time and business trips after the local service team was established.<br><br><strong>Customer Service/Circuit Switch - Senior Engineer</strong><br><strong>NOKIA </strong><em> </em><br><em> Aug 2004- Mar 2007 </em><br>As an account customer service engineer, I represented Nokia's technical team in supporting telecommunication customers such as Far EasTone and Chunghwa Telecom.</p> <h3>Education Background:</h3> <p><strong> Master of Science in Decision Analysis</strong> <br><strong>Minerva University </strong>| Decision Analysis <br><em> Sep 2023 - Jun 2025</em><br>Minerva University was named Most Innovative University in the World consecutively in 2022 and 2023. <br>Master of Science in Decision Analysis (MDA) prepares students to make informed, consequential decisions across all disciplines and employment sectors, including science, education, government, technology, and finance.<br><br><strong> Master</strong> <br><strong>National Tsing Hua University </strong>| Engineering and System Science<br><em> Sep 2001 - Jun 2003</em><br>NA<br><br><strong> B.S</strong> <br><strong>National Tsing Hua University </strong>| Engineering and System Science<br><em> Sep 1997 - Jun 2001</em><br>NA</p> <h3>Personal Project:</h3> <p><strong> AI Resume Advisor</strong> <br>This web-based tool uses artificial intelligence to help job seekers optimize their resumes and increase their chances of landing interviews. Key features include:<br>1. Resume-Job Description Compatibility Analysis<br>2. Customized Resume Suggestions<br>3. ATS (Applicant Tracking System) Optimization Tips<br>4. Keyword Recommendation<br>5. Format and Structure Improvement<br>The AI analyzes the user's resume against their target job description, providing actionable insights to tailor their application for maximum impact.</p> <h3>Certification:</h3> <p><strong> Industrial Analyst</strong><em> issued by APIAA</em><br><strong> Microsoft Project</strong><em> issued by Microsoft</em><br><strong> PMP</strong><em> issued by PMI-OC Project Management Institute Orange County Chapter</em></p> <h3>Skill:</h3> <p>KPI Dashboards;Data Analysis;Decision Analysis;Hypothesis Testing;Experimental Design;Statistic;APQP;Profit &amp; Loss Management;MS project;Jira ;Analytic Problem Solving;R;SQL;Negotiation and Communication;P&amp;L Calculation;8D Problem Solving;MySQL;Python;Automotive SPICE (ASPICE);Project Management;Tableau;Data Visualization;JIRA;Microsoft Project;Data Analytics;Rational DOORS;Polarion</p>"""

JOB_DESCRIPTION = """Established in 1987 and headquartered in Taiwan, TSMC pioneered the pure-play foundry business model with an exclusive focus on manufacturing its customers' products. In 2023, the company served 528 customers with 11,895 products for high performance computing, smartphones, IoT, automotive, and consumer electronics, and is the world's largest provider of logic ICs with annual capacity of 16 million 12-inch equivalent wafers. TSMC operates fabs in Taiwan as well as manufacturing subsidiaries in Washington State, Japan and China, and its ESMC subsidiary plans to begin construction on a fab in Germany in 2024. In Arizona, TSMC is building three fabs, with the first starting 4nm production in 2025, the second by 2028, and the third by the end of the decade. The Sr. HR Data Analyst will be responsible for analyzing large sets of HR data in order to provide insights and recommendations to the HR team and senior management independently or with other HR analysts across global HR team. The role will require a high level of technical expertise in data visualization and analysis, as well as a deep understanding of HR processes and policies.
Job Responsibilities:
1. Act as a Tableau data visualization expert and develop strategic HR dashboards with other domain experts in cross-team projects that enables data-informed decisions to stakeholders.2. Provide guidance, training plans and technical support to other analysts in HR team for Tableau skills development.3. Translate business needs into technical data requirements and work with IT data platform engineers for data preparation.4. Create trust and maintain strong relationships with key stakeholders across the organization.5. Stay up-to-date with industry trends and new analytics features as a technical advocate.
Job Qualifications:
1. Master's degree in HR, Business, Statistics, CS or related field.2. Minimum 5 years of experience in data analysis, with a proven track record of delivering actionable business insights and recommendations.3. Strong technical skills in data analysis tools such as Tableau, Power BI, Superset and SQL.4. Excellent communication skills with the ability to effectively communicate complex data insights to non-technical stakeholders.5. Strong problem-solving skills with the ability to think critically and creatively to solve complex business problems.6. Ability to work independently and manage multiple projects simultaneously.7. Strong attention to details and accuracy.8. Experience in leading and mentoring junior analysts is a plus."""

# Gap Analysis data
GAP_ANALYSIS = {
    "core_strengths": [
        "🏆 Top Match: Demonstrated expertise in Tableau and advanced data visualization, with direct experience building KPI dashboards and strategic presentations for executive stakeholders.",
        "⭐ Key Strength: Robust background in data analysis and decision science, evidenced by a Master's in Decision Analysis and hands-on use of statistical methods, hypothesis testing, and experimental design.",
        "⭐ Key Strength: Proven track record leading cross-functional teams and managing complex projects in automotive and IT industries, showcasing strong project management and stakeholder engagement.",
        "💡 Differentiator: Experience designing and implementing profit and loss databases and dashboards, translating business needs into technical data requirements and collaborating with IT for data preparation.",
        "✓ Additional Asset: History of training and building teams (e.g., customer service team in China), indicating mentoring capability and ability to support analyst development."
    ],
    "key_gaps": [
        "🔧 Power BI & Superset Tools: Not evident in resume. If experienced, add immediately. Otherwise, budget 2-3 months to learn Power BI and Superset for HR analytics.",
        "📚 Formal Data Analyst Role Experience: Absent from current resume. Possibly overlooked? Add it, or plan 2-3 months to develop direct HR data analyst experience."
    ],
    "quick_improvements": [
        "🔧 Add \"Data Preparation\" to Skills Section: Your experience collaborating with IT and managing data projects implies strong data preparation skills. Add \"Data Preparation for analytics and dashboard development\" to your skills section.",
        "💼 Highlight \"Critical Thinking & Creativity\": Your decision analysis education and analytic problem-solving can be reframed as \"Applied critical thinking and creative solutions for business decision-making\" in your summary or experience bullets.",
        "💼 Mentoring Evidence: Expand on your experience building and training teams (e.g., Novatek and Product Management roles) by adding \"Mentored and developed junior analysts and engineers, fostering skill growth and team performance.\"",
        "💼 Stakeholder Engagement: Reword your project management bullets to explicitly state \"Engaged key stakeholders across business units to align project goals and ensure successful outcomes.\""
    ],
    "covered_keywords": ["SQL", "Tableau", "Data Visualization", "Dashboards", "Insights", "Communication", "Problem Solving", "Project Management"],
    "missing_keywords": ["Power BI", "Superset", "Data Analyst", "Critical Thinking", "Creativity", "Mentoring", "Stakeholder Engagement", "Data Preparation"],
    "coverage_percentage": 47,
    "similarity_percentage": 65
}


def extract_original_sections(html_content: str) -> dict[str, str]:
    """從原始簡歷中提取各個section的內容"""
    soup = BeautifulSoup(html_content, 'html.parser')
    sections = {}

    # 定義section標記和對應的關鍵字
    section_markers = {
        'education': ['Education Background:', 'Education:', 'Academic'],
        'projects': ['Personal Project:', 'Projects:', 'Side Projects:'],
        'certifications': ['Certification:', 'Certifications:', 'Certificates:']
    }

    for section_name, markers in section_markers.items():
        for marker in markers:
            # 尋找包含標記的元素
            for elem in soup.find_all(string=re.compile(marker, re.IGNORECASE)):
                parent = elem.parent
                if parent:
                    # 獲取該section的內容
                    content = []
                    current = parent
                    while current and current.next_sibling:
                        current = current.next_sibling
                        if hasattr(current, 'text'):
                            text = current.text.strip()
                            if text and not any(m in text for markers_list in section_markers.values() for m in markers_list):
                                content.append(text)
                            elif any(m in text for markers_list in section_markers.values() for m in markers_list):
                                break  # 遇到下一個section標記就停止

                    if content:
                        sections[section_name] = ' '.join(content)
                        break

    return sections


def detect_content_similarity(original_text: str, optimized_html: str, threshold: float = 0.8) -> float:
    """
    改進的相似度檢測, 考慮格式變化、CSS classes 和新增內容
    Returns:
        0.0 - 完全不同(有優化)
        0.3 - 部分相似但有明顯改變(格式變化)
        0.6 - 內容相似但有新增或修改
        1.0 - 完全相同(真正的 fallback)
    """
    if not original_text or not optimized_html:
        return 0.0

    # 1. 最重要: 檢查是否有 opt-* CSS classes (表示 LLM2 已優化)
    if 'opt-new' in optimized_html or 'opt-modified' in optimized_html or 'opt-' in optimized_html:
        # 有優化標記, 絕對不是 fallback
        return 0.0

    # 2. 檢查 HTML 結構是否改變 (格式優化的重要指標)
    # 原始簡歷通常使用 <p> 標籤, 優化後常用 <ul><li>
    original_has_p = '<p>' in original_text
    original_has_list = '<ul>' in original_text or '<li>' in original_text
    optimized_has_p = '<p>' in optimized_html
    optimized_has_list = '<ul>' in optimized_html or '<li>' in optimized_html

    # 如果格式從段落變成列表, 或反之, 表示有優化
    if (original_has_p and not original_has_list) and (optimized_has_list and not optimized_has_p):
        # 格式明顯改變, 最多返回 0.3
        return 0.3

    # 3. 清理 HTML 標籤進行內容比較
    soup_orig = BeautifulSoup(original_text, 'html.parser')
    soup_opt = BeautifulSoup(optimized_html, 'html.parser')

    original_clean = soup_orig.get_text().strip()
    optimized_clean = soup_opt.get_text().strip()

    # 4. 檢查是否有新增內容 (長度增加 20% 以上通常表示有新增)
    if len(optimized_clean) > len(original_clean) * 1.2:
        # 有明顯新增內容, 不太可能是 fallback
        return 0.4

    # 5. 精確比較: 使用更嚴格的相似度算法
    # 分割成短語進行比較
    original_phrases = list(filter(None, [p.strip().lower() for p in re.split(r'[;.\n•]', original_clean)]))
    optimized_phrases = list(filter(None, [p.strip().lower() for p in re.split(r'[;.\n•]', optimized_clean)]))

    if not optimized_phrases:
        return 0.0

    # 計算精確匹配的短語數量
    exact_matches = 0
    partial_matches = 0

    for opt_phrase in optimized_phrases:
        if len(opt_phrase) < 10:  # 忽略太短的短語
            continue

        found_exact = False
        found_partial = False

        for orig_phrase in original_phrases:
            if len(orig_phrase) < 10:
                continue

            # 完全匹配
            if opt_phrase == orig_phrase:
                exact_matches += 1
                found_exact = True
                break
            # 部分匹配(原始短語是優化短語的子串)
            elif len(orig_phrase) > 20 and orig_phrase in opt_phrase:
                partial_matches += 1
                found_partial = True
                break

        # 如果某個短語完全沒有匹配, 表示是新內容
        if not found_exact and not found_partial:
            # 有新內容, 降低相似度
            return max(0.5, (exact_matches + partial_matches * 0.5) / len(optimized_phrases))

    # 6. 計算最終相似度分數
    # 只有當大部分內容完全匹配時, 才可能是 fallback
    total_phrases = len([p for p in optimized_phrases if len(p) >= 10])
    if total_phrases == 0:
        return 0.0

    # 精確匹配佔比
    exact_ratio = exact_matches / total_phrases if total_phrases > 0 else 0
    # 部分匹配佔比(權重較低)
    partial_ratio = partial_matches / total_phrases if total_phrases > 0 else 0

    # 綜合分數: 精確匹配權重高, 部分匹配權重低
    similarity_score = exact_ratio * 1.0 + partial_ratio * 0.3

    # 7. 最終判斷: 只有相似度極高且無格式變化時才可能是 fallback
    return min(similarity_score, 1.0)


def analyze_response_enhanced(response_json: dict, original_resume: str) -> dict:
    """增強的API響應分析, 包含多種fallback檢測方法"""
    if not response_json.get("success") or "data" not in response_json:
        return None

    data = response_json["data"]

    # 1. 檢查warnings字段(原始方法)
    warnings = data.get("warnings", [])
    has_warning_fallback = any("LLM2" in w or "fallback" in w.lower() for w in warnings)

    # 2. 檢查optimized_resume內容
    optimized_resume = data.get("optimized_resume", "")

    # 提取原始簡歷的sections
    original_sections = extract_original_sections(original_resume)

    # 3. 檢測各section的相似度
    section_similarities = {}
    sections_with_fallback = []

    # 解析優化後的HTML
    soup = BeautifulSoup(optimized_resume, 'html.parser')

    # 檢查Education section
    education_elem = soup.find('h2', string=re.compile('Education', re.IGNORECASE))
    if education_elem:
        education_content = []
        current = education_elem.next_sibling
        while current and (not hasattr(current, 'name') or current.name != 'h2'):
            if hasattr(current, 'text'):
                education_content.append(current.text)
            current = current.next_sibling if hasattr(current, 'next_sibling') else None

        education_text = ' '.join(education_content)
        if original_sections.get('education'):
            similarity = detect_content_similarity(original_sections['education'], education_text)
            section_similarities['education'] = similarity
            if similarity > 0.9:  # 90%以上相似度才認為是fallback(更嚴格)
                sections_with_fallback.append('education')

    # 檢查Projects section
    projects_elem = soup.find('h2', string=re.compile('Project', re.IGNORECASE))
    if projects_elem:
        projects_content = []
        current = projects_elem.next_sibling
        while current and (not hasattr(current, 'name') or current.name != 'h2'):
            if hasattr(current, 'text'):
                projects_content.append(current.text)
            current = current.next_sibling if hasattr(current, 'next_sibling') else None

        projects_text = ' '.join(projects_content)
        if original_sections.get('projects'):
            similarity = detect_content_similarity(original_sections['projects'], projects_text)
            section_similarities['projects'] = similarity
            if similarity > 0.9:  # 提高門檻到 90%
                sections_with_fallback.append('projects')

    # 檢查Certifications section
    cert_elem = soup.find('h2', string=re.compile('Certification', re.IGNORECASE))
    if cert_elem:
        cert_content = []
        current = cert_elem.next_sibling
        while current and (not hasattr(current, 'name') or current.name != 'h2'):
            if hasattr(current, 'text'):
                cert_content.append(current.text)
            current = current.next_sibling if hasattr(current, 'next_sibling') else None

        cert_text = ' '.join(cert_content)
        if original_sections.get('certifications'):
            similarity = detect_content_similarity(original_sections['certifications'], cert_text)
            section_similarities['certifications'] = similarity
            if similarity > 0.9:  # 提高門檻到 90%
                sections_with_fallback.append('certifications')

    # 4. 檢查是否缺少opt-classes(表示沒有優化)
    has_opt_classes = "opt-" in optimized_resume

    # 5. 綜合判斷是否使用了fallback(改進的邏輯)
    # 只有當有明確的警告, 或者相似度極高且無優化標記時, 才判定為 fallback
    has_llm2_fallback = False

    # 條件1: 有明確的 fallback 警告
    if has_warning_fallback or len(sections_with_fallback) >= 2 and not has_opt_classes or any(sim >= 1.0 for sim in section_similarities.values()) and not has_opt_classes:
        has_llm2_fallback = True

    return {
        "has_llm2_fallback": has_llm2_fallback,
        "fallback_indicators": {
            "warning_based": has_warning_fallback,
            "content_similarity": sections_with_fallback,
            "missing_opt_classes": not has_opt_classes,
            "section_similarities": section_similarities
        },
        "warnings": warnings,
        "sections_analyzed": list(section_similarities.keys())
    }


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Enhanced LLM2 fallback monitor with better detection',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-n', '--num-tests', type=int, default=10,
                        help='Number of tests to run (default: 10)')
    parser.add_argument('--delay', type=int, default=2,
                        help='Delay in seconds between tests (default: 2)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed output for each test')
    parser.add_argument('--save-responses', action='store_true',
                        help='Save full API responses to files')
    parser.add_argument('--api-url', type=str, default=DEFAULT_API_URL,
                        help='API endpoint URL')
    parser.add_argument('--api-key', type=str, default=DEFAULT_API_KEY,
                        help='API key for authentication')

    return parser.parse_args()


def make_api_request(api_url: str, api_key: str, payload: dict, timeout: int = 60) -> requests.Response:
    """Make API request with error handling"""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        return response
    except requests.exceptions.RequestException as e:
        return None, str(e)


def run_monitor(args):
    """Run the enhanced monitoring tests"""
    # Prepare payload
    payload = {
        "job_description": JOB_DESCRIPTION,
        "original_resume": ORIGINAL_RESUME,
        "original_index": GAP_ANALYSIS,
        "options": {
            "language": "en",
            "include_visual_markers": True,
            "format_version": "v3"
        }
    }

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"/tmp/llm2_fallback_test_v2_{timestamp}")
    if args.save_responses:
        output_dir.mkdir(exist_ok=True)
        print(f"📁 Responses will be saved to: {output_dir}")

    print("\n" + "="*80)
    print(f"🔍 Enhanced LLM2 Fallback Monitor V2 - Running {args.num_tests} tests")
    print("="*80)
    print(f"API URL: {args.api_url}")
    print("Detection methods: Warnings + Content Similarity + CSS Classes")
    print("")

    results = []
    fallback_count = 0

    # Track fallback types
    fallback_types = {
        "warning_based": 0,
        "content_similarity": 0,
        "missing_opt_classes": 0
    }

    section_fallback_counts = {
        "education": 0,
        "projects": 0,
        "certifications": 0
    }

    for i in range(1, args.num_tests + 1):
        print(f"🔄 Test #{i}/{args.num_tests}...", end='')

        start_time = time.time()
        response = make_api_request(args.api_url, args.api_key, payload)
        elapsed_time = time.time() - start_time

        if isinstance(response, tuple):  # Error occurred
            print(f" ❌ Exception: {response[1]}")
            results.append({
                "test_number": i,
                "error": response[1]
            })
            continue

        if response.status_code != 200:
            print(f" ❌ HTTP {response.status_code}")
            results.append({
                "test_number": i,
                "error": f"HTTP {response.status_code}"
            })
            continue

        try:
            result_json = response.json()

            # Save response if requested
            if args.save_responses:
                response_file = output_dir / f"response_{i:03d}.json"
                with open(response_file, "w") as f:
                    json.dump({
                        "request": payload,
                        "response": result_json,
                        "metadata": {
                            "test_number": i,
                            "response_time": elapsed_time
                        }
                    }, f, indent=2)

            # Analyze with enhanced detection
            analysis = analyze_response_enhanced(result_json, ORIGINAL_RESUME)

            if analysis and analysis["has_llm2_fallback"]:
                fallback_count += 1
                print(f" ⚠️ FALLBACK DETECTED ({elapsed_time:.1f}s)")

                # Track fallback types
                indicators = analysis["fallback_indicators"]
                if indicators["warning_based"]:
                    fallback_types["warning_based"] += 1
                if indicators["content_similarity"]:
                    fallback_types["content_similarity"] += 1
                    for section in indicators["content_similarity"]:
                        section_fallback_counts[section] += 1
                if indicators["missing_opt_classes"]:
                    fallback_types["missing_opt_classes"] += 1

                if args.verbose:
                    print("   📊 Fallback details:")
                    print(f"      - Warning-based: {indicators['warning_based']}")
                    print(f"      - Content similarity: {indicators['content_similarity']}")
                    print(f"      - Section similarities: {indicators['section_similarities']}")
                    print(f"      - Missing opt-classes: {indicators['missing_opt_classes']}")
            else:
                print(f" ✅ No fallback ({elapsed_time:.1f}s)")

            results.append({
                "test_number": i,
                "has_llm2_fallback": analysis["has_llm2_fallback"] if analysis else False,
                "response_time": elapsed_time,
                "analysis": analysis
            })

        except Exception as e:
            print(f" ❌ Analysis error: {e}")
            results.append({
                "test_number": i,
                "error": str(e)
            })

        # Delay between tests
        if i < args.num_tests:
            time.sleep(args.delay)

    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    successful_tests = [r for r in results if "error" not in r]
    print(f"Total tests: {args.num_tests}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {args.num_tests - len(successful_tests)}")

    if successful_tests:
        fallback_rate = (fallback_count / len(successful_tests)) * 100
        print(f"\n🎯 LLM2 Fallback Rate: {fallback_rate:.1f}% ({fallback_count}/{len(successful_tests)})")

        print("\n📈 Fallback Detection Methods:")
        print(f"   - Warning-based: {fallback_types['warning_based']} occurrences")
        print(f"   - Content similarity: {fallback_types['content_similarity']} occurrences")
        print(f"   - Missing opt-classes: {fallback_types['missing_opt_classes']} occurrences")

        print("\n📑 Section-specific Fallbacks:")
        for section, count in section_fallback_counts.items():
            if count > 0:
                section_rate = (count / len(successful_tests)) * 100
                print(f"   - {section.capitalize()}: {count} times ({section_rate:.1f}%)")

        # Average response time
        avg_time = sum(r["response_time"] for r in successful_tests) / len(successful_tests)
        print(f"\n⏱️ Average response time: {avg_time:.2f}s")

    # Save summary
    if args.save_responses:
        summary_file = output_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump({
                "test_datetime": datetime.now().isoformat(),
                "configuration": {
                    "num_tests": args.num_tests,
                    "delay_seconds": args.delay,
                    "api_url": args.api_url
                },
                "summary": {
                    "total_tests": args.num_tests,
                    "successful": len(successful_tests),
                    "llm2_fallbacks": fallback_count,
                    "fallback_rate": f"{fallback_rate:.1f}%" if successful_tests else "N/A",
                    "fallback_types": fallback_types,
                    "section_fallbacks": section_fallback_counts
                },
                "detailed_results": results
            }, f, indent=2)
        print(f"\n💾 Summary saved to: {summary_file}")


if __name__ == "__main__":
    args = parse_arguments()
    run_monitor(args)
