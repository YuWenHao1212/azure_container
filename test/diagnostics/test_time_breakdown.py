#!/usr/bin/env python
"""
診斷腳本:詳細分解 Course Availability 查詢的時間消耗
目的:找出每個階段的耗時,理解效能瓶頸
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TimeTracker:
    """追蹤各階段時間的工具"""

    def __init__(self):
        self.stages = []
        self.start_time = None

    def start(self, stage_name: str):
        """開始一個階段"""
        self.start_time = time.perf_counter()
        return self

    def end(self, stage_name: str) -> float:
        """結束一個階段並記錄時間"""
        if self.start_time is None:
            return 0
        elapsed = (time.perf_counter() - self.start_time) * 1000  # 轉換為 ms
        self.stages.append({
            "stage": stage_name,
            "duration_ms": round(elapsed, 2)
        })
        self.start_time = None
        return elapsed

    def get_breakdown(self) -> dict[str, Any]:
        """獲取時間分解報告"""
        total = sum(s["duration_ms"] for s in self.stages)
        return {
            "stages": self.stages,
            "total_ms": round(total, 2)
        }


async def analyze_single_query(iteration: int, use_cached_skills: bool = False) -> dict[str, Any]:
    """分析單次查詢的時間消耗"""
    from src.services.course_availability import CourseAvailabilityChecker
    from src.services.course_search_singleton import get_course_search_service

    tracker = TimeTracker()
    result = {
        "iteration": iteration,
        "timestamp": datetime.now(UTC).isoformat(),
        "use_cached_skills": use_cached_skills
    }

    # 準備測試技能
    if use_cached_skills:
        # 使用可能被快取的熱門技能
        test_skills = [
            {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"},
            {"skill_name": "JavaScript", "skill_category": "SKILL", "description": "Web development"},
            {"skill_name": "Docker", "skill_category": "SKILL", "description": "Containerization"},
            {"skill_name": "Data Science", "skill_category": "FIELD", "description": "Analytics field"},
            {"skill_name": "Machine Learning", "skill_category": "SKILL", "description": "AI/ML"},
            {"skill_name": "React", "skill_category": "SKILL", "description": "Frontend framework"}
        ]
    else:
        # 使用完全隨機的技能(模擬真實場景)
        import random
        import string
        suffix = ''.join(random.choices(string.ascii_lowercase, k=4))  # noqa: S311
        test_skills = [
            {"skill_name": f"UniqueSkill_{suffix}_1", "skill_category": "SKILL", "description": "Unique test 1"},
            {"skill_name": f"UniqueSkill_{suffix}_2", "skill_category": "SKILL", "description": "Unique test 2"},
            {"skill_name": f"UniqueSkill_{suffix}_3", "skill_category": "SKILL", "description": "Unique test 3"},
            {"skill_name": f"UniqueField_{suffix}_1", "skill_category": "FIELD", "description": "Unique test 4"},
            {"skill_name": f"UniqueField_{suffix}_2", "skill_category": "FIELD", "description": "Unique test 5"},
            {"skill_name": f"UniqueField_{suffix}_3", "skill_category": "FIELD", "description": "Unique test 6"}
        ]

    result["skills"] = [s["skill_name"] for s in test_skills]

    try:
        # Stage 1: 獲取 Singleton 實例
        tracker.start("get_singleton")
        await get_course_search_service()
        tracker.end("get_singleton")

        # Stage 2: 創建 CourseAvailabilityChecker
        tracker.start("create_checker")
        checker = CourseAvailabilityChecker()
        tracker.end("create_checker")

        # Stage 3: 初始化 Checker (包含 embedding client 初始化)
        tracker.start("initialize_checker")
        await checker.initialize()
        tracker.end("initialize_checker")

        # 記錄快取檢查的時間
        tracker.start("cache_check")
        cached_results = checker._check_cache(test_skills)
        cache_hit_count = len(cached_results)
        tracker.end("cache_check")

        # 需要查詢的技能
        uncached_skills = [s for s in test_skills if s["skill_name"] not in cached_results]

        if uncached_skills:
            # Stage 4: 生成 embedding 文本
            tracker.start("generate_embedding_text")
            query_texts = [
                checker._generate_embedding_text(skill)
                for skill in uncached_skills
            ]
            tracker.end("generate_embedding_text")

            # Stage 5: 調用 Embedding API
            tracker.start("embedding_api_call")
            embeddings = await checker._embedding_client.create_embeddings(query_texts)
            tracker.end("embedding_api_call")

            # Stage 6: 獲取連接池(如果需要)
            if not checker._connection_pool:
                tracker.start("get_connection_pool")
                from src.services.course_search_singleton import get_course_search_service
                course_service = await get_course_search_service()
                checker._connection_pool = course_service._connection_pool
                tracker.end("get_connection_pool")

            # Stage 7: 並行查詢資料庫
            tracker.start("database_queries")
            tasks = []
            for emb, skill in zip(embeddings, uncached_skills, strict=False):
                tasks.append(checker._check_single_skill(
                    emb,
                    skill['skill_name'],
                    skill.get('skill_category', 'DEFAULT')
                ))

            # 等待所有查詢完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            tracker.end("database_queries")

            # Stage 8: 處理結果
            tracker.start("process_results")
            for skill, query_result in zip(uncached_skills, results, strict=False):
                if isinstance(query_result, Exception):
                    skill["has_available_courses"] = False
                    skill["course_count"] = 0
                else:
                    skill["has_available_courses"] = query_result["has_courses"]
                    skill["course_count"] = query_result["count"]
            tracker.end("process_results")

        # 記錄結果
        result["cache_hit_count"] = cache_hit_count
        result["cache_hit_rate"] = cache_hit_count / len(test_skills) if test_skills else 0
        result["uncached_count"] = len(uncached_skills)
        result["time_breakdown"] = tracker.get_breakdown()
        result["success"] = True

    except Exception as e:
        logger.error(f"查詢失敗: {e}")
        result["error"] = str(e)
        result["success"] = False
        result["time_breakdown"] = tracker.get_breakdown()

    return result


async def run_time_breakdown_analysis():
    """執行時間分解分析"""
    logger.info("="*80)
    logger.info("🔬 Course Availability 時間分解分析")
    logger.info("="*80)

    # 預熱:初始化 Singleton
    logger.info("\n📍 預熱階段:初始化 Singleton...")
    from src.services.course_search_singleton import get_course_search_service
    await get_course_search_service()
    logger.info("✅ Singleton 已初始化")

    # 收集結果
    all_results = []

    # 測試 5 次隨機技能(真實場景)
    logger.info("\n📊 測試隨機技能(模擬真實場景)...")
    for i in range(5):
        logger.info(f"\n🔄 執行第 {i+1}/5 次查詢(隨機技能)...")
        result = await analyze_single_query(i+1, use_cached_skills=False)
        all_results.append(result)

        # 打印簡要結果
        if result["success"]:
            breakdown = result["time_breakdown"]
            logger.info(f"✅ 查詢完成,總時間: {breakdown['total_ms']:.1f}ms")
            for stage in breakdown["stages"]:
                logger.info(f"   - {stage['stage']}: {stage['duration_ms']:.1f}ms")
        else:
            logger.info(f"❌ 查詢失敗: {result.get('error', 'Unknown error')}")

        # 短暫延遲
        await asyncio.sleep(0.5)

    # 測試 5 次快取技能(對比)
    logger.info("\n📊 測試熱門技能(對比快取效果)...")
    for i in range(5):
        logger.info(f"\n🔄 執行第 {i+1}/5 次查詢(熱門技能)...")
        result = await analyze_single_query(i+6, use_cached_skills=True)
        all_results.append(result)

        # 打印簡要結果
        if result["success"]:
            breakdown = result["time_breakdown"]
            logger.info(f"✅ 查詢完成,總時間: {breakdown['total_ms']:.1f}ms")
            logger.info(f"   快取命中率: {result['cache_hit_rate']:.1%}")
            for stage in breakdown["stages"]:
                logger.info(f"   - {stage['stage']}: {stage['duration_ms']:.1f}ms")
        else:
            logger.info(f"❌ 查詢失敗: {result.get('error', 'Unknown error')}")

        # 短暫延遲
        await asyncio.sleep(0.5)

    # 保存詳細結果到 JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/yuwenhao/Documents/GitHub/azure_container/test/logs/time_breakdown_{timestamp}.json"

    # 計算統計資料
    random_times = [r["time_breakdown"]["total_ms"] for r in all_results[:5] if r["success"]]
    cached_times = [r["time_breakdown"]["total_ms"] for r in all_results[5:] if r["success"]]

    report = {
        "test_name": "Course Availability Time Breakdown Analysis",
        "timestamp": datetime.now(UTC).isoformat(),
        "iterations": all_results,
        "summary": {
            "random_skills": {
                "count": len(random_times),
                "avg_ms": round(sum(random_times) / len(random_times), 2) if random_times else 0,
                "min_ms": round(min(random_times), 2) if random_times else 0,
                "max_ms": round(max(random_times), 2) if random_times else 0
            },
            "cached_skills": {
                "count": len(cached_times),
                "avg_ms": round(sum(cached_times) / len(cached_times), 2) if cached_times else 0,
                "min_ms": round(min(cached_times), 2) if cached_times else 0,
                "max_ms": round(max(cached_times), 2) if cached_times else 0
            }
        },
        "stage_analysis": {}
    }

    # 分析各階段平均耗時
    stage_times = {}
    for result in all_results:
        if result["success"] and "time_breakdown" in result:
            for stage in result["time_breakdown"]["stages"]:
                stage_name = stage["stage"]
                if stage_name not in stage_times:
                    stage_times[stage_name] = []
                stage_times[stage_name].append(stage["duration_ms"])

    for stage_name, times in stage_times.items():
        report["stage_analysis"][stage_name] = {
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "occurrences": len(times)
        }

    # 保存報告
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("\n" + "="*80)
    logger.info("📊 分析完成!")
    logger.info(f"📁 詳細報告已保存到: {output_file}")
    logger.info("="*80)

    # 打印總結
    logger.info("\n📈 總結統計:")
    logger.info(f"隨機技能平均耗時: {report['summary']['random_skills']['avg_ms']:.1f}ms")
    logger.info(f"熱門技能平均耗時: {report['summary']['cached_skills']['avg_ms']:.1f}ms")
    logger.info("\n🔍 階段分析:")
    for stage, stats in report["stage_analysis"].items():
        logger.info(f"   {stage}: 平均 {stats['avg_ms']:.1f}ms (最小 {stats['min_ms']:.1f}ms, 最大 {stats['max_ms']:.1f}ms)")


if __name__ == "__main__":
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()

    # 執行分析
    asyncio.run(run_time_breakdown_analysis())
