#!/usr/bin/env python3
"""
V3 優化性能測試 - 20 次執行
使用真實 Azure OpenAI API
"""

import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 載入環境變數
load_dotenv()

from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2


async def run_single_test(service, test_num):
    """執行單次測試"""

    # 標準測試數據（與性能測試相同）
    resume = """
    Senior Software Engineer with 10+ years of experience in full-stack development.

    Technical Skills:
    - Programming Languages: Python, JavaScript, TypeScript, Java, Go
    - Frontend: React, Vue.js, Angular, HTML5, CSS3, Redux, GraphQL
    - Backend: Node.js, Django, FastAPI, Spring Boot, Express.js
    - Databases: PostgreSQL, MongoDB, Redis, MySQL, Elasticsearch
    - Cloud & DevOps: AWS, Azure, Docker, Kubernetes, CI/CD, Jenkins, GitHub Actions
    - Architecture: Microservices, REST APIs, Event-driven, Serverless
    - Testing: Jest, Pytest, Selenium, Unit Testing, Integration Testing

    Professional Experience:
    - Led development teams of 5-10 engineers
    - Designed and implemented scalable microservices handling 1M+ requests/day
    - Reduced system latency by 40% through optimization
    - Implemented CI/CD pipelines reducing deployment time by 60%
    - Mentored junior developers and conducted code reviews
    """

    job_description = """
    We are seeking a Senior Full Stack Developer to join our engineering team.

    Required Skills:
    - 8+ years of experience in software development
    - Expert-level Python and JavaScript/TypeScript
    - Strong experience with React and modern frontend frameworks
    - Backend development with Django, FastAPI, or Node.js
    - Database design with PostgreSQL and NoSQL databases
    - Cloud platforms (AWS or Azure) and containerization (Docker, Kubernetes)
    - Microservices architecture and RESTful API design
    - CI/CD pipelines and DevOps practices
    - Agile/Scrum methodologies

    Nice to Have:
    - Machine Learning experience
    - GraphQL
    - Performance optimization
    - Team leadership experience
    """

    keywords = [
        'Python', 'JavaScript', 'React', 'Django', 'FastAPI',
        'PostgreSQL', 'Docker', 'Kubernetes', 'AWS', 'Microservices'
    ]

    print(f"  執行測試 #{test_num}...", end="", flush=True)

    try:
        start_time = time.time()

        result = await service.analyze(
            resume=resume,
            job_description=job_description,
            keywords=keywords,
            language='en'
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 提取詳細時間資訊
        metadata = result.get('metadata', {})
        timings = metadata.get('detailed_timings_ms', {})

        print(f" ✓ {elapsed_time:.2f}s (Keywords: {timings.get('keyword_matching_time', 0):.0f}ms, Gap: {timings.get('gap_analysis_time', 0):.0f}ms)")

        return {
            'test_num': test_num,
            'total_time_s': elapsed_time,
            'total_time_ms': elapsed_time * 1000,
            'keyword_time_ms': timings.get('keyword_matching_time', 0),
            'embedding_time_ms': timings.get('embedding_time', 0),
            'gap_time_ms': timings.get('gap_analysis_time', 0),
            'index_time_ms': timings.get('index_calculation_time', 0),
            'parallel_efficiency': metadata.get('parallel_efficiency', 0)
        }

    except Exception as e:
        print(f" ✗ 錯誤: {e}")
        return None


async def run_performance_test():
    """執行 20 次性能測試"""

    # 確認 API key
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    if not api_key:
        print("錯誤: 未找到 AZURE_OPENAI_API_KEY")
        return

    print("=" * 80)
    print("V3 優化性能測試 - 20 次執行（真實 API）")
    print("=" * 80)
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print()

    # 初始化服務
    service = CombinedAnalysisServiceV2()

    # 執行 20 次測試
    print("開始執行測試...")
    results = []

    for i in range(1, 21):
        result = await run_single_test(service, i)
        if result:
            results.append(result)

        # 避免 API 限流
        if i < 20:
            await asyncio.sleep(1)

    # 計算統計數據
    if results:
        print("\n" + "=" * 80)
        print("測試結果統計")
        print("=" * 80)

        # 提取時間數據
        total_times = [r['total_time_s'] for r in results]
        keyword_times = [r['keyword_time_ms'] for r in results]
        gap_times = [r['gap_time_ms'] for r in results]
        efficiencies = [r['parallel_efficiency'] for r in results]

        # 計算統計值
        total_times_sorted = sorted(total_times)
        p50_index = len(total_times_sorted) // 2
        p95_index = int(len(total_times_sorted) * 0.95)

        stats = {
            'test_count': len(results),
            'success_count': len(results),
            'p50_time_s': total_times_sorted[p50_index],
            'p95_time_s': total_times_sorted[p95_index] if p95_index < len(total_times_sorted) else total_times_sorted[-1],
            'min_time_s': min(total_times),
            'max_time_s': max(total_times),
            'avg_time_s': statistics.mean(total_times),
            'std_dev_s': statistics.stdev(total_times) if len(total_times) > 1 else 0,
            'avg_keyword_ms': statistics.mean(keyword_times),
            'avg_gap_ms': statistics.mean(gap_times),
            'avg_efficiency': statistics.mean(efficiencies)
        }

        # 輸出統計結果
        print("\n📊 性能統計:")
        print(f"  測試次數: {stats['test_count']}")
        print(f"  成功次數: {stats['success_count']}")
        print(f"  成功率: {stats['success_count']/20*100:.1f}%")

        print("\n⏱️ 總執行時間統計:")
        print(f"  P50 (中位數): {stats['p50_time_s']:.2f} 秒")
        print(f"  P95: {stats['p95_time_s']:.2f} 秒")
        print(f"  平均值: {stats['avg_time_s']:.2f} 秒")
        print(f"  最小值: {stats['min_time_s']:.2f} 秒")
        print(f"  最大值: {stats['max_time_s']:.2f} 秒")
        print(f"  標準差: {stats['std_dev_s']:.2f} 秒")

        print("\n📈 階段時間平均值:")
        print(f"  Keywords: {stats['avg_keyword_ms']:.0f} ms")
        print(f"  Gap Analysis: {stats['avg_gap_ms']:.0f} ms")
        print(f"  並行效率: {stats['avg_efficiency']:.1f}%")

        # 保存詳細結果
        output_file = f"v3_performance_test_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_timestamp': datetime.now().isoformat(),
                'test_count': 20,
                'statistics': stats,
                'detailed_results': results,
                'all_times': total_times
            }, f, indent=2, ensure_ascii=False)

        print(f"\n💾 詳細結果已保存至: {output_file}")

        # 與 baseline 對比
        print("\n" + "=" * 80)
        print("與 Baseline 對比")
        print("=" * 80)

        baseline_p50 = 9.54
        baseline_p95 = 11.15

        p50_improvement = (baseline_p50 - stats['p50_time_s']) / baseline_p50 * 100
        p95_improvement = (baseline_p95 - stats['p95_time_s']) / baseline_p95 * 100

        print(f"  Baseline P50: {baseline_p50:.2f}s → V3 P50: {stats['p50_time_s']:.2f}s ({p50_improvement:+.1f}%)")
        print(f"  Baseline P95: {baseline_p95:.2f}s → V3 P95: {stats['p95_time_s']:.2f}s ({p95_improvement:+.1f}%)")

        if p95_improvement > 0:
            print(f"\n✅ V3 優化成功！P95 改善 {p95_improvement:.1f}%")
        else:
            print("\n⚠️ V3 優化效果不明顯，需要進一步優化")

    else:
        print("\n❌ 所有測試都失敗了")


def main():
    """主函數"""
    try:
        asyncio.run(run_performance_test())
    except KeyboardInterrupt:
        print("\n\n測試被中斷")
    except Exception as e:
        print(f"\n錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
