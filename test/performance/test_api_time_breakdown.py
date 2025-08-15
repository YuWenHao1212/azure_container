#!/usr/bin/env python
"""
Performance Test: API Time Breakdown Analysis
測試 /api/v1/index-cal-and-gap-analysis API 的效能和時間分解
執行 10 次不同的請求，分析各功能區塊的時間消耗
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ENDPOINT = "http://localhost:8000/api/v1/index-cal-and-gap-analysis"
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "test-api-key")
NUM_TESTS = 10


def generate_test_cases() -> list[dict[str, Any]]:
    """生成 10 個不同的測試案例，涵蓋不同產業和職位"""
    test_cases = [
        {
            "id": 1,
            "title": "Senior Backend Engineer",
            "industry": "Tech",
            "job_description": """
                We are looking for a Senior Backend Engineer to join our team.
                Requirements:
                - 5+ years of experience with Python and FastAPI
                - Strong knowledge of PostgreSQL and Redis
                - Experience with Docker, Kubernetes, and AWS
                - Expertise in microservices architecture
                - Experience with message queues (RabbitMQ, Kafka)
                - Understanding of CI/CD pipelines
                - Strong problem-solving skills
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Backend Developer at TechCorp (3 years)</p>
                <ul>
                    <li>Developed RESTful APIs using Python and Django</li>
                    <li>Managed PostgreSQL databases</li>
                    <li>Implemented basic Docker containers</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Python</li>
                    <li>Django</li>
                    <li>PostgreSQL</li>
                    <li>Git</li>
                    <li>Linux</li>
                </ul>
            """,
            "keywords": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS", "Microservices", "RabbitMQ", "CI/CD"]
        },
        {
            "id": 2,
            "title": "Data Scientist",
            "industry": "AI/ML",
            "job_description": """
                Seeking a Data Scientist for our AI team.
                Requirements:
                - PhD or Master's in Computer Science or related field
                - Expert in Python, TensorFlow, and PyTorch
                - Experience with NLP and Computer Vision
                - Strong knowledge of statistics and machine learning
                - Experience with big data tools (Spark, Hadoop)
                - Cloud platform experience (GCP, AWS)
                - Published research papers is a plus
            """,
            "resume": """
                <h2>Education</h2>
                <p>Master's in Data Science, University XYZ</p>
                <h2>Experience</h2>
                <p>Junior Data Analyst at DataCo (2 years)</p>
                <ul>
                    <li>Performed data analysis using Python and R</li>
                    <li>Created visualizations with Tableau</li>
                    <li>Built basic ML models with scikit-learn</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Python</li>
                    <li>R</li>
                    <li>SQL</li>
                    <li>Tableau</li>
                    <li>Statistics</li>
                    <li>scikit-learn</li>
                </ul>
            """,
            "keywords": ["Python", "TensorFlow", "PyTorch", "NLP", "Computer Vision", "Machine Learning", "Spark", "Hadoop", "GCP", "AWS"]
        },
        {
            "id": 3,
            "title": "DevOps Engineer",
            "industry": "Cloud Infrastructure",
            "job_description": """
                Looking for a DevOps Engineer to manage our cloud infrastructure.
                Requirements:
                - 4+ years of DevOps experience
                - Expert in Terraform and Ansible
                - Strong knowledge of Kubernetes and Docker
                - Experience with CI/CD tools (Jenkins, GitLab CI)
                - AWS or Azure certification required
                - Monitoring tools (Prometheus, Grafana)
                - Scripting skills (Bash, Python)
            """,
            "resume": """
                <h2>Experience</h2>
                <p>System Administrator at ITCorp (4 years)</p>
                <ul>
                    <li>Managed Linux servers</li>
                    <li>Automated tasks with Bash scripts</li>
                    <li>Basic experience with Docker</li>
                    <li>Configured Jenkins pipelines</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Linux</li>
                    <li>Bash</li>
                    <li>Docker</li>
                    <li>Jenkins</li>
                    <li>Python</li>
                    <li>Networking</li>
                </ul>
            """,
            "keywords": ["Terraform", "Ansible", "Kubernetes", "Docker", "Jenkins", "GitLab CI", "AWS", "Azure", "Prometheus", "Grafana"]
        },
        {
            "id": 4,
            "title": "Frontend React Developer",
            "industry": "Web Development",
            "job_description": """
                We need a Frontend React Developer for our web team.
                Requirements:
                - 3+ years with React and TypeScript
                - Experience with Next.js and Redux
                - Strong CSS/SASS skills
                - Knowledge of modern build tools (Webpack, Vite)
                - Experience with testing (Jest, Cypress)
                - GraphQL experience preferred
                - Mobile responsive design expertise
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Web Developer at WebAgency (2 years)</p>
                <ul>
                    <li>Built websites with HTML, CSS, JavaScript</li>
                    <li>Basic React components development</li>
                    <li>jQuery for interactive features</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>HTML5</li>
                    <li>CSS3</li>
                    <li>JavaScript</li>
                    <li>React (basic)</li>
                    <li>jQuery</li>
                    <li>Bootstrap</li>
                </ul>
            """,
            "keywords": ["React", "TypeScript", "Next.js", "Redux", "CSS", "SASS", "Webpack", "Jest", "Cypress", "GraphQL"]
        },
        {
            "id": 5,
            "title": "Blockchain Developer",
            "industry": "Blockchain/Crypto",
            "job_description": """
                Seeking a Blockchain Developer for DeFi projects.
                Requirements:
                - 2+ years blockchain development experience
                - Solidity and smart contract expertise
                - Experience with Web3.js or Ethers.js
                - Knowledge of DeFi protocols
                - Understanding of cryptography
                - Experience with Hardhat or Truffle
                - Security best practices
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Full Stack Developer at StartupXYZ (3 years)</p>
                <ul>
                    <li>Node.js backend development</li>
                    <li>React frontend applications</li>
                    <li>MongoDB database management</li>
                    <li>Interest in blockchain technology</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>JavaScript</li>
                    <li>Node.js</li>
                    <li>React</li>
                    <li>MongoDB</li>
                    <li>Express.js</li>
                </ul>
            """,
            "keywords": ["Solidity", "Smart Contracts", "Web3.js", "Ethers.js", "DeFi", "Blockchain", "Hardhat", "Truffle", "Cryptography"]
        },
        {
            "id": 6,
            "title": "Mobile App Developer",
            "industry": "Mobile Development",
            "job_description": """
                Looking for a Mobile App Developer for iOS/Android.
                Requirements:
                - 3+ years mobile development experience
                - React Native or Flutter expertise
                - Native development knowledge (Swift/Kotlin)
                - Experience with mobile CI/CD
                - App Store deployment experience
                - Push notifications and deep linking
                - Performance optimization skills
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Junior Android Developer at AppCo (1.5 years)</p>
                <ul>
                    <li>Basic Android app development with Java</li>
                    <li>Simple UI layouts with XML</li>
                    <li>SQLite database integration</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Java</li>
                    <li>Android Studio</li>
                    <li>XML</li>
                    <li>SQLite</li>
                    <li>Git</li>
                </ul>
            """,
            "keywords": ["React Native", "Flutter", "Swift", "Kotlin", "iOS", "Android", "CI/CD", "App Store", "Push Notifications"]
        },
        {
            "id": 7,
            "title": "Security Engineer",
            "industry": "Cybersecurity",
            "job_description": """
                We need a Security Engineer to protect our infrastructure.
                Requirements:
                - 4+ years in cybersecurity
                - CISSP or similar certification
                - Experience with penetration testing
                - Knowledge of OWASP Top 10
                - Security tools (Metasploit, Burp Suite, Nmap)
                - Cloud security expertise
                - Incident response experience
            """,
            "resume": """
                <h2>Experience</h2>
                <p>IT Support Specialist at TechSupport Inc (3 years)</p>
                <ul>
                    <li>Network troubleshooting</li>
                    <li>Basic firewall configuration</li>
                    <li>User access management</li>
                    <li>Antivirus software maintenance</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Networking</li>
                    <li>Windows Server</li>
                    <li>Active Directory</li>
                    <li>Basic Security</li>
                </ul>
            """,
            "keywords": ["CISSP", "Penetration Testing", "OWASP", "Metasploit", "Burp Suite", "Nmap", "Cloud Security", "Incident Response"]
        },
        {
            "id": 8,
            "title": "Product Manager",
            "industry": "Product Management",
            "job_description": """
                Seeking a Product Manager for our SaaS platform.
                Requirements:
                - 5+ years product management experience
                - Experience with Agile/Scrum methodologies
                - Strong analytical skills
                - User research and A/B testing experience
                - SQL and data analysis skills
                - Experience with Jira and Confluence
                - MBA preferred
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Business Analyst at CorpABC (2 years)</p>
                <ul>
                    <li>Requirements gathering and documentation</li>
                    <li>Basic project coordination</li>
                    <li>Stakeholder communication</li>
                    <li>Process improvement initiatives</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Excel</li>
                    <li>PowerPoint</li>
                    <li>Business Analysis</li>
                    <li>Communication</li>
                    <li>Documentation</li>
                </ul>
            """,
            "keywords": ["Product Management", "Agile", "Scrum", "User Research", "A/B Testing", "SQL", "Jira", "Confluence", "Analytics"]
        },
        {
            "id": 9,
            "title": "Database Administrator",
            "industry": "Database Management",
            "job_description": """
                Looking for a Database Administrator for our data team.
                Requirements:
                - 4+ years DBA experience
                - Expert in PostgreSQL and MySQL
                - Performance tuning and optimization
                - Replication and clustering experience
                - Backup and recovery strategies
                - Experience with NoSQL (MongoDB, Redis)
                - Database security best practices
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Junior Developer at SoftwareInc (2 years)</p>
                <ul>
                    <li>Basic SQL queries and reports</li>
                    <li>Simple database design</li>
                    <li>Data entry and validation</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>SQL</li>
                    <li>MySQL (basic)</li>
                    <li>Excel</li>
                    <li>Python</li>
                    <li>Data Analysis</li>
                </ul>
            """,
            "keywords": ["PostgreSQL", "MySQL", "Performance Tuning", "Replication", "Clustering", "Backup", "MongoDB", "Redis", "Database Security"]
        },
        {
            "id": 10,
            "title": "AI/ML Engineer",
            "industry": "Artificial Intelligence",
            "job_description": """
                We need an AI/ML Engineer for cutting-edge projects.
                Requirements:
                - 3+ years in machine learning
                - Experience with LLMs and transformers
                - Strong Python and deep learning frameworks
                - MLOps and model deployment experience
                - Experience with vector databases
                - Knowledge of RAG architectures
                - GPU optimization skills
            """,
            "resume": """
                <h2>Experience</h2>
                <p>Software Engineer at TechStartup (2 years)</p>
                <ul>
                    <li>Python backend development</li>
                    <li>REST API design</li>
                    <li>Basic data processing</li>
                    <li>Interest in AI technologies</li>
                </ul>
                <h2>Skills</h2>
                <ul>
                    <li>Python</li>
                    <li>Flask</li>
                    <li>SQL</li>
                    <li>Git</li>
                    <li>Linux</li>
                    <li>Basic ML concepts</li>
                </ul>
            """,
            "keywords": ["LLMs", "Transformers", "Deep Learning", "MLOps", "Vector Databases", "RAG", "GPU", "PyTorch", "TensorFlow"]
        }
    ]

    return test_cases


async def make_api_call(session: aiohttp.ClientSession, test_case: dict[str, Any]) -> dict[str, Any]:
    """執行單一 API 調用並記錄時間"""

    # Prepare request payload
    payload = {
        "job_description": test_case["job_description"].strip(),
        "resume": test_case["resume"].strip(),
        "keywords": test_case["keywords"],
        "language": "en"
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    # Record start time
    start_time = time.perf_counter()

    try:
        async with session.post(API_ENDPOINT, json=payload, headers=headers) as response:
            # Record end time
            end_time = time.perf_counter()
            total_time_ms = (end_time - start_time) * 1000

            if response.status == 200:
                result = await response.json()

                # Extract timing information from metadata
                metadata = result.get("metadata", {})
                timing_breakdown = metadata.get("timing_breakdown", {})

                return {
                    "test_id": test_case["id"],
                    "title": test_case["title"],
                    "industry": test_case["industry"],
                    "status": "success",
                    "total_time_ms": round(total_time_ms, 2),
                    "timing_breakdown": timing_breakdown,
                    "index_score": result.get("index_calculation", {}).get("overall_match_percentage"),
                    "gaps_found": len(result.get("gap_analysis", {}).get("gaps", [])),
                    "improvements_count": len(result.get("gap_analysis", {}).get("improvements", []))
                }
            else:
                error_text = await response.text()
                return {
                    "test_id": test_case["id"],
                    "title": test_case["title"],
                    "industry": test_case["industry"],
                    "status": "error",
                    "error": f"HTTP {response.status}: {error_text}",
                    "total_time_ms": round(total_time_ms, 2)
                }

    except Exception as e:
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        return {
            "test_id": test_case["id"],
            "title": test_case["title"],
            "industry": test_case["industry"],
            "status": "error",
            "error": str(e),
            "total_time_ms": round(total_time_ms, 2)
        }


async def run_performance_test():
    """執行完整的效能測試"""

    print("=" * 80)
    print("API Performance Test: /api/v1/index-cal-and-gap-analysis")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint: {API_ENDPOINT}")
    print(f"Number of tests: {NUM_TESTS}")
    print("=" * 80)
    print()

    # Generate test cases
    test_cases = generate_test_cases()

    # Run tests sequentially to avoid overwhelming the server
    results = []

    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"Running test {i}/{NUM_TESTS}: {test_case['title']} ({test_case['industry']})")

            # Add small delay between requests to ensure no caching
            if i > 1:
                await asyncio.sleep(1)

            result = await make_api_call(session, test_case)
            results.append(result)

            # Print immediate result
            if result["status"] == "success":
                print(f"  ✅ Success - Total Time: {result['total_time_ms']:.2f}ms")
                if result.get("timing_breakdown"):
                    breakdown = result["timing_breakdown"]
                    print(f"     - Keyword Matching: {breakdown.get('keyword_matching_time', 'N/A')}ms")
                    print(f"     - Embedding: {breakdown.get('embedding_time', 'N/A')}ms")
                    print(f"     - Structure Analysis: {breakdown.get('structure_analysis_time', 'N/A')}ms")
                    print(f"     - Index Calculation: {breakdown.get('index_calculation_time', 'N/A')}ms")
                    print(f"     - Gap Analysis: {breakdown.get('gap_analysis_time', 'N/A')}ms")
                    print(f"     - Course Availability: {breakdown.get('course_availability_time', 'N/A')}ms")
            else:
                print(f"  ❌ Error: {result.get('error', 'Unknown error')}")
            print()

    # Generate summary report
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    successful_results = [r for r in results if r["status"] == "success"]

    if successful_results:
        # Calculate statistics
        total_times = [r["total_time_ms"] for r in successful_results]
        avg_time = sum(total_times) / len(total_times)
        min_time = min(total_times)
        max_time = max(total_times)

        print("\n📊 Overall Statistics:")
        print(f"  - Successful requests: {len(successful_results)}/{NUM_TESTS}")
        print(f"  - Average response time: {avg_time:.2f}ms")
        print(f"  - Min response time: {min_time:.2f}ms")
        print(f"  - Max response time: {max_time:.2f}ms")

        # Calculate average breakdown
        breakdown_keys = [
            "keyword_matching_time",
            "embedding_time",
            "structure_analysis_time",
            "index_calculation_time",
            "gap_analysis_time",
            "course_availability_time"
        ]

        print("\n⏱️ Average Time Breakdown:")
        for key in breakdown_keys:
            times = [r["timing_breakdown"].get(key, 0) for r in successful_results if r.get("timing_breakdown")]
            if times:
                avg = sum(times) / len(times)
                percentage = (avg / avg_time) * 100 if avg_time > 0 else 0
                print(f"  - {key.replace('_', ' ').title()}: {avg:.2f}ms ({percentage:.1f}%)")

        # Industry-wise breakdown
        print("\n🏭 Performance by Industry:")
        industries = {}
        for r in successful_results:
            industry = r["industry"]
            if industry not in industries:
                industries[industry] = []
            industries[industry].append(r["total_time_ms"])

        for industry, times in industries.items():
            avg = sum(times) / len(times)
            print(f"  - {industry}: {avg:.2f}ms (n={len(times)})")

    else:
        print("❌ No successful requests to analyze")

    # Save detailed results to file
    output_file = f"test/logs/api_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "endpoint": API_ENDPOINT,
            "num_tests": NUM_TESTS,
            "results": results,
            "summary": {
                "successful": len(successful_results),
                "failed": NUM_TESTS - len(successful_results),
                "avg_response_time_ms": avg_time if successful_results else None,
                "min_response_time_ms": min_time if successful_results else None,
                "max_response_time_ms": max_time if successful_results else None
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")

    return results


async def main():
    """Main entry point"""
    try:
        results = await run_performance_test()

        # Return appropriate exit code
        successful = sum(1 for r in results if r["status"] == "success")
        if successful == NUM_TESTS:
            print(f"\n✅ All {NUM_TESTS} tests completed successfully!")
            return 0
        elif successful > 0:
            print(f"\n⚠️ {successful}/{NUM_TESTS} tests completed successfully")
            return 1
        else:
            print("\n❌ All tests failed")
            return 2

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 3


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
