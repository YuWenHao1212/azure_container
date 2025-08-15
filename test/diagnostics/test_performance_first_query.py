#!/usr/bin/env python
"""
診斷腳本:模擬效能測試的第一次查詢
目的:找出為什麼第一次查詢需要 1547ms
"""
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def simulate_performance_test():
    """模擬效能測試的第一次查詢"""
    logger.info("="*80)
    logger.info("🔬 模擬效能測試的第一次查詢")
    logger.info("="*80)

    # Step 1: 預初始化 Singleton(模擬 main.py 啟動)
    logger.info("\n📍 Step 1: 預初始化 CourseSearchSingleton(模擬應用程式啟動)")
    from src.services.course_search_singleton import get_course_search_service

    start_time = time.time()
    service = await get_course_search_service()
    init_time = (time.time() - start_time) * 1000
    logger.info(f"✅ Singleton 初始化完成,耗時: {init_time:.1f}ms")
    logger.info(f"   Service ID: {id(service)}")
    logger.info(f"   Pool ID: {id(service._connection_pool) if service._connection_pool else 'None'}")

    # Step 2: 建立新的 CourseAvailabilityChecker(模擬測試)
    logger.info("\n📍 Step 2: 建立新的 CourseAvailabilityChecker(模擬測試環境)")
    from src.services.course_availability import CourseAvailabilityChecker

    checker = CourseAvailabilityChecker()
    await checker.initialize()
    logger.info(f"   Checker pool (初始): {id(checker._connection_pool) if checker._connection_pool else 'None'}")

    # Step 3: 執行第一次查詢(使用隨機技能)
    logger.info("\n📍 Step 3: 執行第一次查詢(隨機技能)")
    test_skills = [
        {"skill_name": "RandomSkill_001", "skill_category": "SKILL", "description": "Test 1"},
        {"skill_name": "RandomSkill_002", "skill_category": "SKILL", "description": "Test 2"},
        {"skill_name": "RandomSkill_003", "skill_category": "SKILL", "description": "Test 3"},
        {"skill_name": "RandomField_001", "skill_category": "FIELD", "description": "Test 4"},
        {"skill_name": "RandomField_002", "skill_category": "FIELD", "description": "Test 5"},
        {"skill_name": "RandomField_003", "skill_category": "FIELD", "description": "Test 6"}
    ]

    start_time = time.time()
    try:
        await checker.check_course_availability(test_skills)
        query_time = (time.time() - start_time) * 1000
        logger.info(f"✅ 第一次查詢完成,耗時: {query_time:.1f}ms")
        logger.info(f"   Checker pool (查詢後): {id(checker._connection_pool) if checker._connection_pool else 'None'}")

        # 檢查是否與 Singleton 共享連接池
        if checker._connection_pool and service._connection_pool:
            if id(checker._connection_pool) == id(service._connection_pool):
                logger.info("✅ 連接池被正確共享")
            else:
                logger.error("❌ 連接池沒有被共享!")
    except Exception as e:
        logger.error(f"❌ 查詢失敗: {e}")

    # Step 4: 執行第二次查詢(驗證是否快速)
    logger.info("\n📍 Step 4: 執行第二次查詢(驗證速度)")
    test_skills2 = [
        {"skill_name": "RandomSkill_004", "skill_category": "SKILL", "description": "Test 7"},
        {"skill_name": "RandomSkill_005", "skill_category": "SKILL", "description": "Test 8"},
        {"skill_name": "RandomSkill_006", "skill_category": "SKILL", "description": "Test 9"},
        {"skill_name": "RandomField_004", "skill_category": "FIELD", "description": "Test 10"},
        {"skill_name": "RandomField_005", "skill_category": "FIELD", "description": "Test 11"},
        {"skill_name": "RandomField_006", "skill_category": "FIELD", "description": "Test 12"}
    ]

    start_time = time.time()
    try:
        await checker.check_course_availability(test_skills2)
        query_time = (time.time() - start_time) * 1000
        logger.info(f"✅ 第二次查詢完成,耗時: {query_time:.1f}ms")
    except Exception as e:
        logger.error(f"❌ 查詢失敗: {e}")

    logger.info("\n" + "="*80)
    logger.info("🔬 診斷完成")
    logger.info("="*80)

async def simulate_cold_start():
    """模擬冷啟動(沒有預初始化)"""
    logger.info("\n" + "="*80)
    logger.info("🧊 模擬冷啟動(沒有預初始化)")
    logger.info("="*80)

    # 直接建立 CourseAvailabilityChecker,不預初始化 Singleton
    from src.services.course_availability import CourseAvailabilityChecker

    checker = CourseAvailabilityChecker()
    await checker.initialize()

    test_skills = [
        {"skill_name": "ColdStart_001", "skill_category": "SKILL", "description": "Cold 1"},
        {"skill_name": "ColdStart_002", "skill_category": "SKILL", "description": "Cold 2"},
        {"skill_name": "ColdStart_003", "skill_category": "SKILL", "description": "Cold 3"},
        {"skill_name": "ColdStart_004", "skill_category": "FIELD", "description": "Cold 4"},
        {"skill_name": "ColdStart_005", "skill_category": "FIELD", "description": "Cold 5"},
        {"skill_name": "ColdStart_006", "skill_category": "FIELD", "description": "Cold 6"}
    ]

    start_time = time.time()
    try:
        await checker.check_course_availability(test_skills)
        query_time = (time.time() - start_time) * 1000
        logger.info(f"🧊 冷啟動查詢完成,耗時: {query_time:.1f}ms")

        if query_time > 1000:
            logger.warning(f"⚠️ 冷啟動確實很慢: {query_time:.1f}ms")

    except Exception as e:
        logger.error(f"❌ 查詢失敗: {e}")

if __name__ == "__main__":
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()

    # 執行診斷
    asyncio.run(simulate_performance_test())

    # 執行冷啟動測試
    # 重要:需要重新啟動 Python 進程才能真正模擬冷啟動
    # asyncio.run(simulate_cold_start())
