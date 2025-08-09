#!/usr/bin/env python3
"""
V3 Optimization Timing Analysis Script
Collects detailed timing data from 5 test samples to identify optimization opportunities.
"""

import asyncio
import json
import os
import statistics
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")  # Use local server for testing
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "test-api-key-for-development")
NUM_SAMPLES = 5
RESULTS_DIR = Path("test/logs/v3_timing_analysis")

# Test data (meets minimum 200 character requirement)
TEST_JD = """
Senior Software Engineer Position - Cloud Infrastructure Team

We are seeking an experienced Senior Software Engineer to join our Cloud Infrastructure team. 
The ideal candidate will have strong expertise in Python, AWS services, and container orchestration 
platforms like Kubernetes. You will be responsible for designing and implementing scalable 
microservices architectures, optimizing system performance, and ensuring high availability 
of our cloud-based applications.

Required Skills:
- 5+ years of Python development experience
- Strong knowledge of AWS (EC2, S3, Lambda, RDS)
- Experience with Docker and Kubernetes
- Proficiency in CI/CD pipelines
- Understanding of distributed systems
"""

TEST_RESUME = """
Software Engineer with 6 years of experience

Professional Summary:
Experienced software engineer specializing in backend development and cloud infrastructure.
Proven track record of building scalable applications using Python and modern cloud technologies.
Strong problem-solving skills and ability to work in fast-paced agile environments.

Technical Skills:
- Programming Languages: Python, JavaScript, Go
- Cloud Platforms: AWS (EC2, S3, Lambda), Google Cloud
- Containers: Docker, basic Kubernetes knowledge
- Databases: PostgreSQL, MongoDB, Redis
- Tools: Git, Jenkins, Terraform

Work Experience:
Senior Software Developer at TechCorp (2020-Present)
- Developed microservices using Python and FastAPI
- Implemented CI/CD pipelines using Jenkins
- Optimized database queries improving performance by 40%
"""

TEST_KEYWORDS = [
    "Python", "AWS", "Docker", "Kubernetes", "Microservices",
    "CI/CD", "Cloud", "Backend", "FastAPI", "PostgreSQL"
]


async def make_api_call(session: httpx.AsyncClient, sample_num: int) -> dict:
    """Make a single API call and collect timing data."""
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "resume": TEST_RESUME,
        "job_description": TEST_JD,
        "keywords": TEST_KEYWORDS,
        "analysis_options": {
            "include_skills": True,
            "include_experience": True,
            "include_recommendations": True
        }
    }
    
    print(f"  Sample {sample_num}: Making API call...")
    start_time = time.time()
    
    try:
        response = await session.post(
            f"{API_URL}/api/v1/index-cal-and-gap-analysis",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get("metadata", {})
            
            result = {
                "sample": sample_num,
                "success": True,
                "total_time": elapsed,
                "status_code": response.status_code,
                "phase_timings_ms": metadata.get("phase_timings_ms", {}),
                "detailed_timings_ms": metadata.get("detailed_timings_ms", {}),
                "parallel_efficiency": metadata.get("parallel_efficiency", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"    ✓ Success in {elapsed:.2f}s")
            print(f"    - Embedding: {metadata.get('detailed_timings_ms', {}).get('embedding_time', 'N/A')}ms")
            print(f"    - Index Calc: {metadata.get('detailed_timings_ms', {}).get('index_calculation_time', 'N/A')}ms")
            print(f"    - Gap Analysis: {metadata.get('detailed_timings_ms', {}).get('gap_analysis_time', 'N/A')}ms")
            
            return result
        else:
            print(f"    ✗ Failed with status {response.status_code}")
            return {
                "sample": sample_num,
                "success": False,
                "total_time": elapsed,
                "status_code": response.status_code,
                "error": response.text,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ Error: {str(e)}")
        return {
            "sample": sample_num,
            "success": False,
            "total_time": elapsed,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def run_timing_analysis():
    """Run timing analysis with 5 samples."""
    
    print("=" * 70)
    print("V3 OPTIMIZATION TIMING ANALYSIS")
    print("=" * 70)
    print(f"API URL: {API_URL}")
    print(f"Samples: {NUM_SAMPLES}")
    print("-" * 70)
    
    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect samples
    results = []
    async with httpx.AsyncClient() as session:
        print("\n📊 Collecting timing samples...")
        
        for i in range(1, NUM_SAMPLES + 1):
            # Small delay between requests to avoid rate limiting
            if i > 1:
                await asyncio.sleep(1)
            
            result = await make_api_call(session, i)
            results.append(result)
    
    # Analyze results
    successful_samples = [r for r in results if r.get("success")]
    
    if not successful_samples:
        print("\n❌ No successful samples collected!")
        return
    
    print("\n" + "=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)
    
    # Calculate statistics
    total_times = [r["total_time"] for r in successful_samples]
    
    # Phase timing statistics
    phase_stats = {}
    for phase in ["embedding_time", "index_calculation_time", "gap_analysis_time"]:
        phase_times = []
        for r in successful_samples:
            timing = r.get("detailed_timings_ms", {}).get(phase)
            if timing is not None:
                phase_times.append(timing)
        
        if phase_times:
            phase_stats[phase] = {
                "mean": statistics.mean(phase_times),
                "median": statistics.median(phase_times),
                "min": min(phase_times),
                "max": max(phase_times),
                "stdev": statistics.stdev(phase_times) if len(phase_times) > 1 else 0,
                "samples": len(phase_times)
            }
    
    # Print analysis
    print(f"\n📈 Overall Performance (n={len(successful_samples)}):")
    print(f"  • Mean Response Time: {statistics.mean(total_times):.2f}s")
    print(f"  • Median Response Time: {statistics.median(total_times):.2f}s")
    print(f"  • Min Response Time: {min(total_times):.2f}s")
    print(f"  • Max Response Time: {max(total_times):.2f}s")
    
    if len(total_times) > 1:
        print(f"  • Std Dev: {statistics.stdev(total_times):.2f}s")
    
    print("\n🔍 Phase Breakdown (milliseconds):")
    for phase_name, stats in phase_stats.items():
        phase_label = phase_name.replace("_", " ").title()
        percentage = (stats["mean"] / (statistics.mean(total_times) * 1000)) * 100
        
        print(f"\n  {phase_label}:")
        print(f"    • Mean: {stats['mean']:.1f}ms ({percentage:.1f}%)")
        print(f"    • Median: {stats['median']:.1f}ms")
        print(f"    • Range: {stats['min']:.1f}ms - {stats['max']:.1f}ms")
        if stats['stdev'] > 0:
            print(f"    • Std Dev: {stats['stdev']:.1f}ms")
    
    # Calculate phase percentages
    if phase_stats:
        total_phase_time = sum(s["mean"] for s in phase_stats.values())
        print("\n📊 Phase Time Distribution:")
        for phase_name, stats in phase_stats.items():
            phase_label = phase_name.replace("_", " ").title()
            percentage = (stats["mean"] / total_phase_time) * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            print(f"  {phase_label:20} [{bar}] {percentage:.1f}%")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"timing_analysis_{timestamp}.json"
    
    analysis_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "api_url": API_URL,
            "num_samples": NUM_SAMPLES,
            "successful_samples": len(successful_samples)
        },
        "overall_stats": {
            "mean_response_time_s": statistics.mean(total_times),
            "median_response_time_s": statistics.median(total_times),
            "min_response_time_s": min(total_times),
            "max_response_time_s": max(total_times),
            "stdev_response_time_s": statistics.stdev(total_times) if len(total_times) > 1 else 0
        },
        "phase_stats": phase_stats,
        "raw_samples": results
    }
    
    with open(output_file, "w") as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Optimization recommendations
    print("\n" + "=" * 70)
    print("🎯 OPTIMIZATION RECOMMENDATIONS")
    print("=" * 70)
    
    if phase_stats.get("gap_analysis_time"):
        gap_percentage = (phase_stats["gap_analysis_time"]["mean"] / (statistics.mean(total_times) * 1000)) * 100
        if gap_percentage > 50:
            print(f"\n⚠️  Gap Analysis is the primary bottleneck ({gap_percentage:.1f}% of total time)")
            print("   Recommendations:")
            print("   • Optimize Gap Analysis prompt to reduce token generation")
            print("   • Consider using GPT-4.1-mini for faster response")
            print("   • Implement streaming response for better perceived performance")
    
    if phase_stats.get("embedding_time"):
        embedding_percentage = (phase_stats["embedding_time"]["mean"] / (statistics.mean(total_times) * 1000)) * 100
        if embedding_percentage > 20:
            print(f"\n⚠️  Embedding generation takes {embedding_percentage:.1f}% of total time")
            print("   Recommendations:")
            print("   • Ensure resume and JD embeddings are truly parallel")
            print("   • Consider caching embeddings for repeated content")
    
    # Check parallel efficiency
    efficiency_values = [r.get("parallel_efficiency", 0) for r in successful_samples if r.get("parallel_efficiency")]
    if efficiency_values:
        avg_efficiency = statistics.mean(efficiency_values)
        if avg_efficiency < 50:
            print(f"\n⚠️  Low parallel efficiency detected ({avg_efficiency:.1f}%)")
            print("   The system may not be executing phases in true parallel")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(run_timing_analysis())