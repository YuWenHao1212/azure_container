#!/usr/bin/env python
"""
LLM2 Fallback Monitor Tool
用於監控 Resume Tailoring API 中 LLM2 (Additional Manager) 的 fallback 發生率

Tool ID: TOOL-LLM2-MON-01
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

# Configuration
DEFAULT_API_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/tailor-resume"
DEFAULT_API_KEY = os.getenv("CONTAINER_APP_API_KEY", "hUjQoHxaWoUUvqGxD4eMFYpT4dYXyFmgIK0fwtEePFk")

# Test data
ORIGINAL_RESUME = """<h3>Personal Summary:</h3> <p>1. As a Business Administration Manager, I possess extensive experience in data processing, visualization, and interpretation, aiding executive management in making informed decisions. <br>2. With 10 years of hands-on experience in project management, I am proficient in overseeing projects within fast-paced consumer and sophisticated automotive industries. <br>3. My vision is to create value for my community alongside individuals who uphold shared values of respect, freedom, and integrity.</p> <h3>Work Experience:</h3> <p><strong>Business Administration Manager</strong><br><strong>友達光電 </strong><em>, 台灣 Taiwan 新竹市 </em><br><em> Jul 2022- Apr 2025 </em><br>- Execute advanced data processing and visualization tasks with a focus on the Chinese automotive and IT display sectors, providing pivotal support for executive decision-making. This involves a comprehensive review of business unit performance, incorporating in-depth analysis of financial income statements and data outcomes. The integrated approach not only reveals the overall business operations but also aids in strategic decision-making and promotes corporate growth.<br>- Spearheaded data management projects by collaborating with IT and key departments to deepen the company's insights into its business operations. This effort aims to boost operational efficiency, improve performance metrics, and stimulate innovation across the organization.<br><br><strong>Automotive Project Manager, Deputy Manager</strong><br><strong>友達光電 </strong><em>, 台灣 新竹縣市 </em><br><em> May 2019- Jun 2022 </em><br>- RFQ Management and Financial Evaluation: Oversee the Request for Quotation (RFQ) processes for automotive Original Equipment Manufacturers (OEMs), assess project budgets and profit & loss statements, and critically review quotations to guarantee project profitability.<br>- Customer Requirements and Solution Alignment: Manage and align customer requirements with internal solutions, ensuring they meet customer needs. Address and secure customer acceptance for any discrepancies.<br>- Customer Engagement and Project Oversight: Maintain consistent communication with customers through regular meetings, discuss unresolved issues, review risk management strategies, and confirm adherence to project timelines.<br><br><strong>Product Management, Department Manager</strong><br><strong>友達光電 </strong><em>, Taiwan </em><br><em> Jul 2011- Apr 2019 </em><br>- Led a team of seven project managers overseeing the production of mobile display products at LCD manufacturing sites in Taiwan and Singapore.<br>- Designed and implemented a profit and loss (P&L) database and dashboard for mobile products, enabling effective data visualization and strategic presentations to the Vice President.<br>- Managed the new product development process, ensuring the on-time delivery of prototypes and compliance with customer specifications.<br>- Achieved significant success in product development, highlighted by:<br>Launching the Xiaomi 4.7" model, achieving sales of 23 million units.<br>Introducing the OPPO 5.5" model, with 12 million units sold.<br><br><strong>Customer Service Engineer</strong><br><strong>Novatek Microelectronics Corp </strong><em>, Hsin-Chu, Taiwan </em><br><em> Apr 2007- Jan 2011 </em><br>- Led the local customer service team to support major Chinese phone makers (such as Huawei, ZTE, etc.) in designing Novatek's display IC, which has been adopted and mass-produced in millions of pieces per month.<br>- Built and trained the customer service team in Mainland China, resulting in a 50%+ reduction in troubleshooting time and business trips after the local service team was established.<br><br><strong>Customer Service/Circuit Switch - Senior Engineer</strong><br><strong>NOKIA </strong><em> </em><br><em> Aug 2004- Mar 2007 </em><br>As an account customer service engineer, I represented Nokia's technical team in supporting telecommunication customers such as Far EasTone and Chunghwa Telecom.</p> <h3>Education Background:</h3> <p><strong> Master of Science in Decision Analysis</strong> <br><strong>Minerva University </strong>| Decision Analysis <br><em> Sep 2023 - Jun 2025</em><br>Minerva University was named Most Innovative University in the World consecutively in 2022 and 2023. <br>Master of Science in Decision Analysis (MDA) prepares students to make informed, consequential decisions across all disciplines and employment sectors, including science, education, government, technology, and finance.<br><br><strong> Master</strong> <br><strong>National Tsing Hua University </strong>| Engineering and System Science<br><em> Sep 2001 - Jun 2003</em><br>NA<br><br><strong> B.S</strong> <br><strong>National Tsing Hua University </strong>| Engineering and System Science<br><em> Sep 1997 - Jun 2001</em><br>NA</p> <h3>Personal Project:</h3> <p><strong> AI Resume Advisor</strong> <br>This web-based tool uses artificial intelligence to help job seekers optimize their resumes and increase their chances of landing interviews. Key features include:<br>1. Resume-Job Description Compatibility Analysis<br>2. Customized Resume Suggestions<br>3. ATS (Applicant Tracking System) Optimization Tips<br>4. Keyword Recommendation<br>5. Format and Structure Improvement<br>The AI analyzes the user's resume against their target job description, providing actionable insights to tailor their application for maximum impact.</p> <h3>Certification:</h3> <p><strong> Industrial Analyst</strong><em> issued by APIAA</em><br><strong> Microsoft Project</strong><em> issued by Microsoft</em><br><strong> PMP</strong><em> issued by PMI-OC Project Management Institute Orange County Chapter</em></p> <h3>Skill:</h3> <p>KPI Dashboards;Data Analysis;Decision Analysis;Hypothesis Testing;Experimental Design;Statistic;APQP;Profit & Loss Management;MS project;Jira ;Analytic Problem Solving;R;SQL;Negotiation and Communication;P&L Calculation;8D Problem Solving;MySQL;Python;Automotive SPICE (ASPICE);Project Management;Tableau;Data Visualization;JIRA;Microsoft Project;Data Analytics;Rational DOORS;Polarion</p>"""

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


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Monitor LLM2 fallback rate in Resume Tailoring API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run 10 tests with default settings
  %(prog)s -n 100 --delay 1        # Run 100 tests with 1 second delay
  %(prog)s -n 20 --save-responses  # Run 20 tests and save full responses
  %(prog)s --verbose               # Run with detailed output
        """
    )

    parser.add_argument('-n', '--num-tests', type=int, default=10,
                        help='Number of tests to run (default: 10)')
    parser.add_argument('--delay', type=int, default=2,
                        help='Delay in seconds between tests (default: 2)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed output for each test')
    parser.add_argument('--save-responses', action='store_true',
                        help='Save full API responses to separate JSON files')
    parser.add_argument('--api-url', type=str, default=DEFAULT_API_URL,
                        help='API endpoint URL (default: production)')
    parser.add_argument('--api-key', type=str, default=DEFAULT_API_KEY,
                        help='API key for authentication')

    return parser.parse_args()


def make_api_request(api_url, api_key, payload, timeout=60):
    """Make API request with error handling"""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        return response
    except requests.exceptions.RequestException as e:
        return (None, str(e))


def analyze_response(response_json):
    """Analyze API response for LLM2 fallback indicators"""
    if not response_json.get("success") or "data" not in response_json:
        return None

    data = response_json["data"]

    # Check warnings field
    warnings = data.get("warnings", [])
    has_llm2_fallback = any("LLM2" in w or "fallback" in w.lower() for w in warnings)

    # Check for specific fallback message
    for warning in warnings:
        if "Using fallback content from original resume for LLM2 sections" in warning:
            has_llm2_fallback = True
            break

    # Extract sections to check for opt- classes
    # In v3.1, optimized_resume is an HTML string, not a dict
    optimized_resume = data.get("optimized_resume", "")

    # Check for section content in the HTML
    education_content = "Education" in optimized_resume or "education" in optimized_resume
    projects_content = "Project" in optimized_resume or "project" in optimized_resume
    certifications_content = "Certification" in optimized_resume or "certification" in optimized_resume

    # Check if sections have opt- classes (indicating LLM optimization)
    has_opt_classes = {
        "education": education_content and "opt-" in optimized_resume,
        "projects": projects_content and "opt-" in optimized_resume,
        "certifications": certifications_content and "opt-" in optimized_resume
    }

    return {
        "has_llm2_fallback": has_llm2_fallback,
        "warnings": warnings,
        "has_opt_classes": has_opt_classes
    }


def run_monitor(args):
    """Run the monitoring tests"""
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

    # Create output directory for full responses if needed
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"/tmp/llm2_fallback_test_{timestamp}")
    if args.save_responses:
        output_dir.mkdir(exist_ok=True)
        print(f"📁 Full responses will be saved to: {output_dir}")

        # Save test configuration
        config_file = output_dir / "test_config.json"
        with open(config_file, "w") as f:
            json.dump({
                "test_datetime": datetime.now().isoformat(),
                "configuration": {
                    "num_tests": args.num_tests,
                    "delay_seconds": args.delay,
                    "api_url": args.api_url,
                    "verbose": args.verbose
                },
                "test_data": {
                    "job_description_length": len(payload["job_description"]),
                    "original_resume_length": len(payload["original_resume"]),
                    "gap_analysis_keywords_count": len(payload["original_index"]["covered_keywords"]) + len(payload["original_index"]["missing_keywords"]),
                    "options": payload["options"]
                }
            }, f, indent=2)
        print(f"   Configuration saved to: {config_file}")

    print("\n" + "="*80)
    print(f"LLM2 Fallback Monitor - Testing {args.num_tests} consecutive calls")
    print("="*80)
    print(f"API URL: {args.api_url}")
    print(f"Settings: delay={args.delay}s, verbose={args.verbose}")

    results = []
    fallback_count = 0
    full_responses = []

    for i in range(1, args.num_tests + 1):
        print(f"\n🔄 Test #{i}/{args.num_tests}...", end='')

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
            print(f" ❌ API Error: {response.status_code}")
            results.append({
                "test_number": i,
                "error": f"HTTP {response.status_code}"
            })
            continue

        try:
            # Check if response is JSON
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                print(f" ❌ Non-JSON response: {content_type}")
                results.append({
                    "test_number": i,
                    "error": f"Non-JSON response: {content_type}"
                })
                continue

            result = response.json()

            # Save full response if requested
            if args.save_responses:
                response_file = output_dir / f"response_{i:03d}.json"
                # Save both request and response for comparison
                full_data = {
                    "request": {
                        "job_description": payload["job_description"],
                        "original_resume": payload["original_resume"],
                        "original_index": payload["original_index"],
                        "options": payload["options"]
                    },
                    "response": result,
                    "metadata": {
                        "test_number": i,
                        "timestamp": datetime.now().isoformat(),
                        "response_time_seconds": elapsed_time,
                        "api_url": args.api_url
                    }
                }
                with open(response_file, "w") as f:
                    json.dump(full_data, f, indent=2)
                full_responses.append(str(response_file))

            # Analyze response
            analysis = analyze_response(result)

            if analysis:
                results.append({
                    "test_number": i,
                    "has_llm2_fallback": analysis["has_llm2_fallback"],
                    "warnings": analysis["warnings"],
                    "has_opt_classes": analysis["has_opt_classes"],
                    "response_time": elapsed_time,
                    "response_file": str(response_file) if args.save_responses else None
                })

                if analysis["has_llm2_fallback"]:
                    fallback_count += 1
                    print(" ⚠️ LLM2 FALLBACK DETECTED")
                    if args.verbose:
                        print(f"   Warnings: {analysis['warnings']}")
                else:
                    print(" ✅ LLM2 worked properly (no fallback)")
                    if args.verbose:
                        print(f"   Sections with opt- classes: {analysis['has_opt_classes']}")
                        if analysis["warnings"]:
                            print(f"   Other warnings: {analysis['warnings']}")
            else:
                print(" ❌ API returned error or no data")
                results.append({
                    "test_number": i,
                    "error": "API returned error or no data"
                })

        except Exception as e:
            print(f" ❌ Parse error: {e}")
            if args.verbose:
                print(f"   Response type: {type(result) if 'result' in locals() else 'Unknown'}")
                print(f"   Response content: {str(result)[:200] if 'result' in locals() else 'N/A'}")
            results.append({
                "test_number": i,
                "error": str(e)
            })

        # Delay between requests
        if i < args.num_tests:
            time.sleep(args.delay)

    # Generate summary
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)

    successful_tests = [r for r in results if "error" not in r]

    print("\n📊 Test Results:")
    print(f"   Total tests: {args.num_tests}")
    print(f"   Successful: {len(successful_tests)}")
    print(f"   Failed: {args.num_tests - len(successful_tests)}")

    if successful_tests:
        print("\n🔴 LLM2 Fallback Statistics:")
        print(f"   Fallback occurred: {fallback_count}/{len(successful_tests)} times")
        fallback_rate = (fallback_count/len(successful_tests)*100)
        print(f"   Fallback rate: {fallback_rate:.1f}%")

        # Show warning thresholds
        if fallback_rate > 10:
            print("   ⚠️ WARNING: Fallback rate exceeds 10% threshold!")
        elif fallback_rate > 5:
            print("   ⚠️ CAUTION: Fallback rate exceeds 5% warning threshold")
        else:
            print("   ✅ Fallback rate within acceptable range (< 5%)")

        # Show which tests had fallback
        fallback_tests = [r["test_number"] for r in successful_tests if r.get("has_llm2_fallback")]
        if fallback_tests:
            print(f"   Tests with fallback: {fallback_tests}")

        # Performance statistics
        response_times = [r["response_time"] for r in successful_tests]
        avg_time = sum(response_times) / len(response_times)
        p50_time = sorted(response_times)[len(response_times)//2]
        p95_index = int(len(response_times) * 0.95)
        p95_time = sorted(response_times)[min(p95_index, len(response_times)-1)]

        print("\n⏱️ Performance:")
        print(f"   Average response time: {avg_time:.2f}s")
        print(f"   P50 response time: {p50_time:.2f}s")
        print(f"   P95 response time: {p95_time:.2f}s")

    # Save detailed results
    output_file = f"/tmp/llm2_fallback_test_results_{args.num_tests}tests_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump({
            "test_datetime": datetime.now().isoformat(),
            "test_configuration": {
                "num_tests": args.num_tests,
                "delay_seconds": args.delay,
                "verbose": args.verbose,
                "save_responses": args.save_responses,
                "api_url": args.api_url
            },
            "summary": {
                "total_tests": args.num_tests,
                "successful": len(successful_tests),
                "llm2_fallbacks": fallback_count,
                "fallback_rate": f"{fallback_rate:.1f}%" if successful_tests else "N/A"
            },
            "detailed_results": results,
            "response_files": full_responses if args.save_responses else []
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
    if args.save_responses:
        print(f"💾 Full responses saved to: {output_dir}/")
        print(f"   View a specific response: cat {output_dir}/response_001.json")

    # Return exit code based on fallback rate
    if successful_tests and fallback_rate > 10:
        return 1  # Error threshold
    return 0


def main():
    """Main entry point"""
    args = parse_arguments()
    exit_code = run_monitor(args)
    exit(exit_code)


if __name__ == "__main__":
    main()
