#!/usr/bin/env python
"""
診斷腳本:詳細分解 Database Query 的時間消耗
目的:理解 pgvector 查詢的各個階段耗時
"""
import asyncio
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DetailedTimeTracker:
    """詳細追蹤各階段時間的工具"""

    def __init__(self):
        self.stages = []
        self.current_stage = None
        self.start_time = None

    def start(self, stage_name: str):
        """開始一個階段"""
        self.current_stage = stage_name
        self.start_time = time.perf_counter()
        return self

    def end(self) -> float:
        """結束當前階段並記錄時間"""
        if self.start_time is None or self.current_stage is None:
            return 0
        elapsed = (time.perf_counter() - self.start_time) * 1000  # 轉換為 ms
        self.stages.append({
            "stage": self.current_stage,
            "duration_ms": round(elapsed, 2)
        })
        self.current_stage = None
        self.start_time = None
        return elapsed


async def analyze_single_db_query(skill_name: str, embedding: list[float], skill_category: str, connection_pool) -> dict:
    """分析單個資料庫查詢的詳細時間"""
    from pgvector.asyncpg import register_vector

    tracker = DetailedTimeTracker()
    result = {
        "skill_name": skill_name,
        "skill_category": skill_category,
        "stages": []
    }

    try:
        # Stage 1: 從連接池獲取連接
        tracker.start("acquire_connection")
        conn_context = connection_pool.acquire()
        conn = await conn_context.__aenter__()
        tracker.end()

        # Stage 2: pgvector 已在連接池初始化時註冊
        # 不需要再註冊 - 省下 607ms!

        # Stage 3: 準備查詢參數
        tracker.start("prepare_query")
        threshold = 0.30 if skill_category == "SKILL" else 0.25
        query = """
        WITH ranked_courses AS (
            SELECT
                course_type_standard,
                name,
                1 - (embedding <=> $1::vector) as similarity,
                CASE
                    WHEN $3 = 'SKILL' THEN
                        CASE course_type_standard
                            WHEN 'course' THEN 3
                            WHEN 'project' THEN 2
                            WHEN 'certification' THEN 1
                            ELSE 0
                        END
                    WHEN $3 = 'FIELD' THEN
                        CASE course_type_standard
                            WHEN 'specialization' THEN 3
                            WHEN 'degree' THEN 2
                            WHEN 'certification' THEN 1
                            ELSE 0
                        END
                    ELSE 0
                END as priority_score
            FROM courses
            WHERE platform = 'coursera'
            AND embedding IS NOT NULL
            AND 1 - (embedding <=> $1::vector) >= $2
            ORDER BY priority_score DESC, similarity DESC
            LIMIT 10
        )
        SELECT
            COUNT(*) > 0 as has_courses,
            COUNT(*) as total_count,
            SUM(CASE WHEN priority_score > 0 THEN 1 ELSE 0 END) as preferred_count,
            SUM(CASE WHEN priority_score = 0 THEN 1 ELSE 0 END) as other_count
        FROM ranked_courses;
        """
        tracker.end()

        # Stage 4: 執行查詢(這是主要耗時)
        tracker.start("execute_query")
        query_result = await conn.fetchrow(query, embedding, threshold, skill_category)
        tracker.end()

        # Stage 5: 處理查詢結果
        tracker.start("process_result")
        processed_result = {
            "has_courses": query_result["has_courses"],
            "count": min(query_result["total_count"], 10),
            "preferred_count": query_result.get("preferred_count", 0),
            "other_count": query_result.get("other_count", 0)
        }
        tracker.end()

        # Stage 6: 釋放連接
        tracker.start("release_connection")
        await conn_context.__aexit__(None, None, None)
        tracker.end()

        # 記錄所有階段
        result["stages"] = tracker.stages
        result["total_ms"] = sum(s["duration_ms"] for s in tracker.stages)
        result["query_result"] = processed_result
        result["success"] = True

    except Exception as e:
        logger.error(f"查詢失敗 {skill_name}: {e}")
        result["error"] = str(e)
        result["success"] = False
        result["stages"] = tracker.stages

    return result


async def analyze_parallel_queries(num_queries: int = 6) -> dict:
    """分析並行查詢的時間分解"""
    import random
    import string

    from src.services.course_search_singleton import get_course_search_service
    from src.services.llm_factory import get_embedding_client

    logger.info("="*80)
    logger.info(f"🔬 分析 {num_queries} 個並行資料庫查詢")
    logger.info("="*80)

    # 初始化服務
    logger.info("\n📍 初始化服務...")
    service = await get_course_search_service()
    connection_pool = service._connection_pool
    embedding_client = get_embedding_client(api_name="course_search")

    # 生成測試技能
    suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
    test_skills = []
    for i in range(num_queries):
        if i % 2 == 0:
            skill = {
                "name": f"TestSkill_{suffix}_{i}",
                "category": "SKILL",
                "text": f"TestSkill_{suffix}_{i} course tutorial project certificate"
            }
        else:
            skill = {
                "name": f"TestField_{suffix}_{i}",
                "category": "FIELD",
                "text": f"TestField_{suffix}_{i} specialization degree track curriculum"
            }
        test_skills.append(skill)

    # 生成 embeddings
    logger.info(f"\n📍 生成 {num_queries} 個 embeddings...")
    start_time = time.perf_counter()
    texts = [s["text"] for s in test_skills]
    embeddings = await embedding_client.create_embeddings(texts)
    embedding_time = (time.perf_counter() - start_time) * 1000
    logger.info(f"✅ Embedding 完成:{embedding_time:.1f}ms")

    # 執行並行查詢
    logger.info(f"\n📍 執行 {num_queries} 個並行查詢...")
    parallel_start = time.perf_counter()

    # 創建查詢任務
    tasks = []
    for skill, embedding in zip(test_skills, embeddings, strict=False):
        task = analyze_single_db_query(
            skill["name"],
            embedding,
            skill["category"],
            connection_pool
        )
        tasks.append(task)

    # 並行執行
    results = await asyncio.gather(*tasks)

    parallel_time = (time.perf_counter() - parallel_start) * 1000
    logger.info(f"✅ 並行查詢完成:{parallel_time:.1f}ms")

    # 分析結果
    analysis = {
        "test_name": "Database Query Breakdown Analysis",
        "timestamp": datetime.now(UTC).isoformat(),
        "num_queries": num_queries,
        "embedding_time_ms": round(embedding_time, 2),
        "total_parallel_time_ms": round(parallel_time, 2),
        "queries": results,
        "stage_summary": {},
        "statistics": {}
    }

    # 統計各階段時間
    stage_times = {}
    for query_result in results:
        if query_result.get("success"):
            for stage in query_result.get("stages", []):
                stage_name = stage["stage"]
                if stage_name not in stage_times:
                    stage_times[stage_name] = []
                stage_times[stage_name].append(stage["duration_ms"])

    # 計算統計
    for stage_name, times in stage_times.items():
        analysis["stage_summary"][stage_name] = {
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "total_ms": round(sum(times), 2),
            "count": len(times)
        }

    # 計算每個查詢的平均時間
    query_times = [r["total_ms"] for r in results if r.get("success")]
    if query_times:
        analysis["statistics"] = {
            "avg_query_time_ms": round(sum(query_times) / len(query_times), 2),
            "min_query_time_ms": round(min(query_times), 2),
            "max_query_time_ms": round(max(query_times), 2),
            "slowest_query": max(results, key=lambda x: x.get("total_ms", 0))["skill_name"],
            "fastest_query": min(results, key=lambda x: x.get("total_ms", float('inf')))["skill_name"]
        }

    return analysis


async def run_detailed_db_analysis():
    """執行詳細的資料庫查詢分析"""

    # 執行 5 輪測試
    all_analyses = []

    for round_num in range(5):
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 第 {round_num + 1}/5 輪測試")
        logger.info(f"{'='*80}")

        analysis = await analyze_parallel_queries(6)
        all_analyses.append(analysis)

        # 打印簡要結果
        logger.info("\n📊 本輪結果:")
        logger.info(f"總並行時間: {analysis['total_parallel_time_ms']:.1f}ms")
        logger.info(f"平均單查詢: {analysis['statistics']['avg_query_time_ms']:.1f}ms")

        logger.info("\n🔍 階段分解(平均):")
        for stage, stats in analysis["stage_summary"].items():
            percentage = (stats["avg_ms"] / analysis['statistics']['avg_query_time_ms']) * 100
            logger.info(f"   {stage}: {stats['avg_ms']:.1f}ms ({percentage:.1f}%)")

        # 短暫延遲
        if round_num < 4:
            await asyncio.sleep(1)

    # 保存詳細報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/yuwenhao/Documents/GitHub/azure_container/test/logs/db_query_breakdown_{timestamp}.json"

    # 計算總體統計
    final_report = {
        "test_name": "Database Query Detailed Breakdown",
        "timestamp": datetime.now(UTC).isoformat(),
        "rounds": all_analyses,
        "overall_statistics": {}
    }

    # 聚合所有輪次的階段統計
    all_stage_times = {}
    for analysis in all_analyses:
        for stage, stats in analysis["stage_summary"].items():
            if stage not in all_stage_times:
                all_stage_times[stage] = []
            all_stage_times[stage].append(stats["avg_ms"])

    # 計算總體平均
    for stage, times in all_stage_times.items():
        final_report["overall_statistics"][stage] = {
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2)
        }

    # 計算總體查詢時間
    all_query_times = []
    for analysis in all_analyses:
        if "statistics" in analysis and "avg_query_time_ms" in analysis["statistics"]:
            all_query_times.append(analysis["statistics"]["avg_query_time_ms"])

    if all_query_times:
        final_report["overall_statistics"]["total_query"] = {
            "avg_ms": round(sum(all_query_times) / len(all_query_times), 2),
            "min_ms": round(min(all_query_times), 2),
            "max_ms": round(max(all_query_times), 2)
        }

    # 保存報告
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    logger.info("\n" + "="*80)
    logger.info("📊 分析完成!")
    logger.info(f"📁 詳細報告已保存到: {output_file}")
    logger.info("="*80)

    # 打印最終統計
    logger.info("\n📈 總體統計(5 輪平均):")
    if "total_query" in final_report["overall_statistics"]:
        logger.info(f"平均查詢時間: {final_report['overall_statistics']['total_query']['avg_ms']:.1f}ms")

    logger.info("\n🔍 階段分解(總體平均):")
    total_avg = final_report["overall_statistics"].get("total_query", {}).get("avg_ms", 0)
    for stage, stats in final_report["overall_statistics"].items():
        if stage != "total_query":
            percentage = (stats["avg_ms"] / total_avg * 100) if total_avg > 0 else 0
            logger.info(f"   {stage}: {stats['avg_ms']:.1f}ms ({percentage:.1f}%)")


if __name__ == "__main__":
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()

    # 執行分析
    asyncio.run(run_detailed_db_analysis())
