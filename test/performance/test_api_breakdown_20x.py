#!/usr/bin/env python
"""
Performance test for /api/v1/index-cal-and-gap-analysis endpoint
Run 20 iterations with different JD/Resume combinations
Track detailed time breakdown for each functional block
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API configuration
API_URL = "http://localhost:8000/api/v1/index-cal-and-gap-analysis"
ITERATIONS = 20

def generate_test_case(iteration: int) -> dict[str, Any]:
    """Generate unique test case for each iteration"""

    # Different job descriptions
    job_descriptions = [
        # Backend Engineer
        """We are looking for a Senior Backend Engineer with strong experience in:
        - Python and FastAPI for building scalable APIs
        - Docker and Kubernetes for containerization and orchestration
        - PostgreSQL and Redis for data management
        - AWS cloud services and infrastructure
        - Microservices architecture and design patterns
        - CI/CD pipelines and DevOps practices
        - RESTful API design and GraphQL
        - Message queuing systems (RabbitMQ, Kafka)""",

        # Data Scientist
        """Seeking a Data Scientist to join our AI team. Requirements:
        - Python programming and data manipulation (pandas, numpy)
        - Machine Learning frameworks (TensorFlow, PyTorch, scikit-learn)
        - Statistical analysis and hypothesis testing
        - Big data technologies (Spark, Hadoop)
        - SQL and NoSQL databases
        - Data visualization (Matplotlib, Seaborn, Tableau)
        - Deep learning and neural networks
        - Natural language processing and computer vision""",

        # Frontend Developer
        """Looking for a Senior Frontend Developer with expertise in:
        - React.js and modern JavaScript/TypeScript
        - State management (Redux, MobX, Context API)
        - CSS preprocessors and CSS-in-JS solutions
        - Webpack, Babel, and build optimization
        - Testing frameworks (Jest, React Testing Library)
        - Performance optimization and PWA development
        - Responsive design and accessibility
        - GraphQL and REST API integration""",

        # DevOps Engineer
        """We need a DevOps Engineer with experience in:
        - Infrastructure as Code (Terraform, CloudFormation)
        - Container orchestration (Kubernetes, Docker Swarm)
        - CI/CD pipelines (Jenkins, GitLab CI, GitHub Actions)
        - Cloud platforms (AWS, Azure, GCP)
        - Monitoring and logging (Prometheus, Grafana, ELK)
        - Configuration management (Ansible, Puppet)
        - Security best practices and compliance
        - Scripting (Bash, Python, Go)""",

        # Full Stack Developer
        """Hiring a Full Stack Developer with skills in:
        - Node.js and Express.js backend development
        - React or Vue.js frontend frameworks
        - MongoDB and PostgreSQL databases
        - RESTful API design and implementation
        - Authentication and authorization (OAuth, JWT)
        - WebSocket and real-time communication
        - Microservices and serverless architecture
        - Testing and debugging across the stack"""
    ]

    # Different resumes
    resumes = [
        # Backend-focused resume
        """<h2>Experience</h2>
        <p>Senior Backend Engineer with 5 years experience</p>
        <ul>
        <li>Developed scalable APIs using Python and Django REST Framework</li>
        <li>Implemented microservices architecture with Docker and Kubernetes</li>
        <li>Optimized PostgreSQL queries reducing response time by 60%</li>
        <li>Built event-driven systems using RabbitMQ and Celery</li>
        </ul>
        <h2>Skills</h2>
        <p>Python, Django, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git</p>""",

        # Data Science resume
        """<h2>Experience</h2>
        <p>Data Scientist with 4 years of machine learning experience</p>
        <ul>
        <li>Built predictive models using TensorFlow and scikit-learn</li>
        <li>Analyzed large datasets with PySpark and Hadoop</li>
        <li>Created data pipelines for real-time analytics</li>
        <li>Developed NLP models for sentiment analysis</li>
        </ul>
        <h2>Skills</h2>
        <p>Python, TensorFlow, PyTorch, Pandas, NumPy, SQL, Spark, Tableau, Statistics</p>""",

        # Frontend-focused resume
        """<h2>Experience</h2>
        <p>Senior Frontend Developer with 6 years experience</p>
        <ul>
        <li>Developed responsive SPAs using React and TypeScript</li>
        <li>Implemented state management with Redux and Context API</li>
        <li>Optimized web performance achieving 95+ Lighthouse scores</li>
        <li>Led migration from JavaScript to TypeScript</li>
        </ul>
        <h2>Skills</h2>
        <p>JavaScript, TypeScript, React, Redux, CSS, Webpack, Jest, Node.js, GraphQL</p>""",

        # DevOps resume
        """<h2>Experience</h2>
        <p>DevOps Engineer with 5 years of cloud infrastructure experience</p>
        <ul>
        <li>Managed AWS infrastructure using Terraform and CloudFormation</li>
        <li>Implemented CI/CD pipelines with Jenkins and GitLab CI</li>
        <li>Orchestrated containers using Kubernetes in production</li>
        <li>Set up monitoring with Prometheus and Grafana</li>
        </ul>
        <h2>Skills</h2>
        <p>AWS, Terraform, Kubernetes, Docker, Jenkins, Python, Bash, Ansible, Monitoring</p>""",

        # Full Stack resume
        """<h2>Experience</h2>
        <p>Full Stack Developer with 4 years experience</p>
        <ul>
        <li>Built end-to-end features using Node.js and React</li>
        <li>Designed RESTful APIs and GraphQL schemas</li>
        <li>Implemented real-time features using WebSockets</li>
        <li>Managed MongoDB and PostgreSQL databases</li>
        </ul>
        <h2>Skills</h2>
        <p>JavaScript, Node.js, React, Express, MongoDB, PostgreSQL, GraphQL, Docker, AWS</p>"""
    ]

    # Keywords matching each job description
    keywords_sets = [
        ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "Redis", "AWS", "Microservices"],
        ["Python", "Machine Learning", "TensorFlow", "Data Analysis", "SQL", "Statistics", "Deep Learning", "Spark"],
        ["React", "JavaScript", "TypeScript", "Redux", "CSS", "Testing", "Performance", "GraphQL"],
        ["Terraform", "Kubernetes", "CI/CD", "AWS", "Monitoring", "Docker", "Security", "Ansible"],
        ["Node.js", "React", "MongoDB", "PostgreSQL", "API", "WebSocket", "Microservices", "Testing"]
    ]

    # Select based on iteration to ensure variety
    idx = iteration % 5

    # Add variation to avoid caching
    suffix = f"_iter{iteration}"

    return {
        "resume": resumes[idx] + f"\n<!-- Iteration {iteration} -->",
        "job_description": job_descriptions[idx] + f"\n<!-- Test iteration {iteration} -->",
        "keywords": [k + suffix if i % 2 == 0 else k for i, k in enumerate(keywords_sets[idx])],
        "language": "en"
    }

async def call_api(session: aiohttp.ClientSession, test_case: dict[str, Any], iteration: int) -> dict[str, Any]:
    """Call the API and extract timing information"""

    start_time = time.time()

    # Add API key header for development
    headers = {
        "X-API-Key": "your-api-key-here"  # Use the configured API key
    }

    try:
        async with session.post(API_URL, json=test_case, headers=headers) as response:
            end_time = time.time()
            total_time = (end_time - start_time) * 1000  # Convert to ms

            if response.status == 200:
                result = await response.json()

                # Extract timing breakdown from metadata if available
                metadata = result.get("metadata", {})
                timing_breakdown = metadata.get("detailed_timings_ms", {})

                return {
                    "iteration": iteration,
                    "success": True,
                    "status_code": response.status,
                    "total_time_ms": round(total_time, 2),
                    "server_processing_time_ms": metadata.get("processing_time_ms", 0),
                    "timing_breakdown": {
                        "keyword_matching": timing_breakdown.get("keyword_matching_time", 0),
                        "embedding_generation": timing_breakdown.get("embedding_time", 0),
                        "index_calculation": timing_breakdown.get("index_calculation_time", 0),
                        "gap_analysis": timing_breakdown.get("gap_analysis_time", 0),
                        "course_availability": timing_breakdown.get("course_availability_time", 0),
                        "structure_analysis": timing_breakdown.get("structure_analysis_time", 0),
                        "pgvector_warmup": timing_breakdown.get("pgvector_warmup_time", 0),
                        "total_api_time": timing_breakdown.get("total_time", 0)
                    },
                    "api_response": {
                        "similarity_percentage": result.get("data", {}).get("similarity_percentage", 0),
                        "keyword_coverage": result.get("data", {}).get("keyword_coverage", {}).get("coverage_percentage", 0),
                        "skills_count": len(result.get("data", {}).get("gap_analysis", {}).get("SkillSearchQueries", [])),
                        "has_course_availability": any(
                            skill.get("has_available_courses", False)
                            for skill in result.get("data", {}).get("gap_analysis", {}).get("SkillSearchQueries", [])
                        )
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                error_text = await response.text()
                return {
                    "iteration": iteration,
                    "success": False,
                    "status_code": response.status,
                    "total_time_ms": round(total_time, 2),
                    "error": error_text,
                    "timestamp": datetime.now().isoformat()
                }

    except Exception as e:
        return {
            "iteration": iteration,
            "success": False,
            "error": str(e),
            "total_time_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }

async def run_performance_test():
    """Run the performance test with 20 iterations"""

    logger.info(f"Starting performance test with {ITERATIONS} iterations")
    logger.info(f"API endpoint: {API_URL}")

    results = []

    async with aiohttp.ClientSession() as session:
        for i in range(1, ITERATIONS + 1):
            logger.info(f"Running iteration {i}/{ITERATIONS}")

            # Generate test case
            test_case = generate_test_case(i)

            # Call API
            result = await call_api(session, test_case, i)
            results.append(result)

            # Log brief summary
            if result["success"]:
                logger.info(f"  ✅ Success - Total: {result['total_time_ms']:.1f}ms, "
                          f"Server: {result.get('server_processing_time_ms', 0):.1f}ms")

                # Log breakdown
                breakdown = result.get("timing_breakdown", {})
                if breakdown:
                    logger.info(f"     Keywords: {breakdown.get('keyword_matching', 0):.1f}ms, "
                              f"Embeddings: {breakdown.get('embedding_generation', 0):.1f}ms, "
                              f"Index: {breakdown.get('index_calculation', 0):.1f}ms, "
                              f"Gap: {breakdown.get('gap_analysis', 0):.1f}ms, "
                              f"Courses: {breakdown.get('course_availability', 0):.1f}ms")
            else:
                logger.error(f"  ❌ Failed - {result.get('error', 'Unknown error')}")

            # Small delay between requests
            await asyncio.sleep(0.5)

    return results

def analyze_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze and summarize the performance results"""

    successful_results = [r for r in results if r.get("success", False)]

    if not successful_results:
        return {"error": "No successful results to analyze"}

    # Extract timing data
    total_times = [r["total_time_ms"] for r in successful_results]
    server_times = [r.get("server_processing_time_ms", 0) for r in successful_results]

    # Extract breakdown times
    breakdown_keys = ["keyword_matching", "embedding_generation", "index_calculation",
                     "gap_analysis", "course_availability", "structure_analysis", "pgvector_warmup"]

    breakdown_stats = {}
    for key in breakdown_keys:
        times = [r.get("timing_breakdown", {}).get(key, 0) for r in successful_results]
        times = [t for t in times if t > 0]  # Filter out zeros
        if times:
            breakdown_stats[key] = {
                "avg_ms": round(np.mean(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
                "p50_ms": round(np.percentile(times, 50), 2),
                "p95_ms": round(np.percentile(times, 95), 2),
                "std_ms": round(np.std(times), 2)
            }

    return {
        "summary": {
            "total_iterations": len(results),
            "successful": len(successful_results),
            "failed": len(results) - len(successful_results),
            "success_rate": round(len(successful_results) / len(results) * 100, 1)
        },
        "overall_performance": {
            "total_time": {
                "avg_ms": round(np.mean(total_times), 2),
                "min_ms": round(min(total_times), 2),
                "max_ms": round(max(total_times), 2),
                "p50_ms": round(np.percentile(total_times, 50), 2),
                "p95_ms": round(np.percentile(total_times, 95), 2),
                "std_ms": round(np.std(total_times), 2)
            },
            "server_processing_time": {
                "avg_ms": round(np.mean(server_times), 2),
                "min_ms": round(min(server_times), 2),
                "max_ms": round(max(server_times), 2),
                "p50_ms": round(np.percentile(server_times, 50), 2),
                "p95_ms": round(np.percentile(server_times, 95), 2),
                "std_ms": round(np.std(server_times), 2)
            }
        },
        "function_block_breakdown": breakdown_stats,
        "course_availability_coverage": {
            "iterations_with_courses": sum(1 for r in successful_results
                                          if r.get("api_response", {}).get("has_course_availability", False)),
            "coverage_percentage": round(
                sum(1 for r in successful_results
                    if r.get("api_response", {}).get("has_course_availability", False)) /
                len(successful_results) * 100, 1
            )
        }
    }

async def main():
    """Main function"""

    # Create logs directory if it doesn't exist
    log_dir = Path("test/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filenames with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = log_dir / f"api_breakdown_20x_{timestamp}.json"
    log_file = log_dir / f"api_breakdown_20x_{timestamp}.log"

    # Set up file logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    logger.info("="*80)
    logger.info("API Performance Test - 20 Iterations with Time Breakdown")
    logger.info("="*80)

    # Run the test
    start_time = time.time()
    results = await run_performance_test()
    end_time = time.time()

    # Analyze results
    analysis = analyze_results(results)

    # Create comprehensive report
    report = {
        "test_name": "API Performance Test - /api/v1/index-cal-and-gap-analysis",
        "iterations": ITERATIONS,
        "timestamp": datetime.now().isoformat(),
        "total_test_duration_seconds": round(end_time - start_time, 2),
        "api_endpoint": API_URL,
        "analysis": analysis,
        "detailed_results": results
    }

    # Save JSON report
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Log summary
    logger.info("")
    logger.info("="*80)
    logger.info("PERFORMANCE TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Total iterations: {ITERATIONS}")
    logger.info(f"Successful: {analysis['summary']['successful']}")
    logger.info(f"Failed: {analysis['summary']['failed']}")
    logger.info(f"Success rate: {analysis['summary']['success_rate']}%")
    logger.info("")

    logger.info("Overall Performance:")
    total_stats = analysis['overall_performance']['total_time']
    logger.info(f"  Average: {total_stats['avg_ms']:.1f}ms")
    logger.info(f"  P50: {total_stats['p50_ms']:.1f}ms")
    logger.info(f"  P95: {total_stats['p95_ms']:.1f}ms")
    logger.info(f"  Min: {total_stats['min_ms']:.1f}ms")
    logger.info(f"  Max: {total_stats['max_ms']:.1f}ms")
    logger.info("")

    logger.info("Function Block Breakdown (Average):")
    for block, stats in analysis['function_block_breakdown'].items():
        logger.info(f"  {block}: {stats['avg_ms']:.1f}ms (P95: {stats['p95_ms']:.1f}ms)")
    logger.info("")

    logger.info(f"Course Availability Coverage: {analysis['course_availability_coverage']['coverage_percentage']}%")
    logger.info("")

    logger.info(f"📊 JSON report saved to: {json_file}")
    logger.info(f"📝 Log file saved to: {log_file}")
    logger.info("="*80)

    print("\n✅ Test completed successfully!")
    print(f"📊 JSON report: {json_file}")
    print(f"📝 Log file: {log_file}")

if __name__ == "__main__":
    asyncio.run(main())
