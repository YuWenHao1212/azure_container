#!/usr/bin/env python
"""
測試連接池預熱效果
"""
import asyncio
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


async def simulate_warmup():
    """模擬預熱過程"""
    from src.services.course_search_singleton import get_course_search_service

    logger.info("="*80)
    logger.info("🔬 測試連接池預熱效果")
    logger.info("="*80)

    # Step 1: 初始化連接池
    logger.info("\n📍 Step 1: 初始化連接池...")
    start_time = time.perf_counter()
    course_service = await get_course_search_service()
    pool = course_service._connection_pool
    init_time = (time.perf_counter() - start_time) * 1000
    logger.info(f"✅ 連接池初始化完成:{init_time:.1f}ms")

    # Step 2: 執行預熱
    logger.info("\n📍 Step 2: 執行預熱程序...")
    warmup_start = time.perf_counter()

    if pool:
        # 強制創建連接
        connections = []
        num_connections = min(pool._maxsize, 5)
        logger.info(f"   創建 {num_connections} 個連接...")

        for i in range(num_connections):
            conn = await pool.acquire()
            connections.append(conn)
            logger.info(f"   連接 #{i+1} 已創建")

        # 預熱查詢
        logger.info("   執行預熱查詢...")
        test_embedding = [0.1] * 1536

        for i, conn in enumerate(connections[:2]):
            try:
                query_start = time.perf_counter()
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM courses
                    WHERE platform = 'coursera'
                    AND embedding IS NOT NULL
                    AND 1 - (embedding <=> $1::vector) >= 0.01
                    LIMIT 1
                    """,
                    test_embedding
                )
                query_time = (time.perf_counter() - query_start) * 1000
                logger.info(f"   預熱查詢 #{i+1} 完成:{query_time:.1f}ms (找到 {count} 筆)")
            except Exception as e:
                logger.error(f"   預熱查詢 #{i+1} 失敗:{e}")

        # 釋放連接
        for conn in connections:
            await pool.release(conn)

        warmup_time = (time.perf_counter() - warmup_start) * 1000
        logger.info(f"✅ 預熱完成:{warmup_time:.1f}ms")

    # Step 3: 測試預熱後的查詢速度
    logger.info("\n📍 Step 3: 測試預熱後的查詢速度...")
    from src.services.course_availability import CourseAvailabilityChecker

    checker = CourseAvailabilityChecker()
    await checker.initialize()

    # 執行 5 次查詢測試
    query_times = []
    for i in range(5):
        test_skills = [
            {"skill_name": f"Python_{i}", "skill_category": "SKILL", "description": "Programming"},
            {"skill_name": f"JavaScript_{i}", "skill_category": "SKILL", "description": "Web"},
            {"skill_name": f"Docker_{i}", "skill_category": "SKILL", "description": "Container"},
            {"skill_name": f"DataScience_{i}", "skill_category": "FIELD", "description": "Analytics"},
            {"skill_name": f"MachineLearning_{i}", "skill_category": "FIELD", "description": "AI"},
            {"skill_name": f"CloudComputing_{i}", "skill_category": "FIELD", "description": "Cloud"}
        ]

        start = time.perf_counter()
        await checker.check_course_availability(test_skills)
        elapsed = (time.perf_counter() - start) * 1000
        query_times.append(elapsed)
        logger.info(f"   查詢 #{i+1}: {elapsed:.1f}ms")

    # 統計結果
    logger.info("\n📊 查詢速度統計(預熱後):")
    logger.info(f"   第一次查詢: {query_times[0]:.1f}ms")
    logger.info(f"   平均查詢時間: {sum(query_times)/len(query_times):.1f}ms")
    logger.info(f"   最快查詢: {min(query_times):.1f}ms")
    logger.info(f"   最慢查詢: {max(query_times):.1f}ms")

    # 比較有無預熱的差異
    logger.info("\n📈 預熱效果比較:")
    logger.info("   未預熱第一次查詢: ~3000ms (根據之前測試)")
    logger.info(f"   預熱後第一次查詢: {query_times[0]:.1f}ms")
    logger.info(f"   改善: {(1 - query_times[0]/3000) * 100:.1f}%")

    logger.info("\n" + "="*80)
    logger.info("🔬 測試完成")
    logger.info("="*80)


if __name__ == "__main__":
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()

    # 執行測試
    asyncio.run(simulate_warmup())
