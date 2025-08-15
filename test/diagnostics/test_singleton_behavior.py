#!/usr/bin/env python
"""
診斷腳本:測試 CourseSearchSingleton 行為
目的:找出為什麼連接池預初始化沒有生效
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_singleton_behavior():
    """測試 Singleton 行為"""
    logger.info("="*80)
    logger.info("🔬 開始診斷 CourseSearchSingleton 行為")
    logger.info("="*80)

    # Step 1: 第一次獲取實例(模擬 main.py 啟動)
    logger.info("\n📍 Step 1: 模擬應用程式啟動時的初始化")
    from src.services.course_search_singleton import get_course_search_service
    service1 = await get_course_search_service()
    logger.info(f"Service 1 ID: {id(service1)}")
    logger.info(f"Connection Pool 1 ID: {id(service1._connection_pool) if service1._connection_pool else 'None'}")

    # Step 2: 第二次獲取實例(模擬 API 請求)
    logger.info("\n📍 Step 2: 模擬 API 請求時的獲取")
    service2 = await get_course_search_service()
    logger.info(f"Service 2 ID: {id(service2)}")
    logger.info(f"Connection Pool 2 ID: {id(service2._connection_pool) if service2._connection_pool else 'None'}")

    # Step 3: 驗證是否為同一實例
    logger.info("\n📍 Step 3: 驗證 Singleton 模式")
    if service1 is service2:
        logger.info("✅ Singleton 正常工作:兩次獲取的是同一實例")
    else:
        logger.error("❌ Singleton 失效:兩次獲取的是不同實例!")

    # Step 4: 模擬 CourseAvailabilityChecker 的行為
    logger.info("\n📍 Step 4: 模擬 CourseAvailabilityChecker 行為")
    from src.services.course_availability import CourseAvailabilityChecker

    checker = CourseAvailabilityChecker()
    logger.info(f"Checker connection pool (初始): {id(checker._connection_pool) if checker._connection_pool else 'None'}")

    # 初始化 checker
    await checker.initialize()
    logger.info(f"Checker connection pool (初始化後): {id(checker._connection_pool) if checker._connection_pool else 'None'}")

    # 模擬查詢(觸發連接池獲取)- 使用未快取的技能
    test_skills = [
        {"skill_name": "RandomSkill_Test_123", "skill_category": "SKILL", "description": "Test skill"}
    ]

    try:
        # 這會觸發 _check_single_skill,進而獲取連接池
        result = await checker.check_course_availability(test_skills)
        logger.info(f"查詢成功,結果: {result}")
        logger.info(f"Checker connection pool (查詢後): {id(checker._connection_pool) if checker._connection_pool else 'None'}")
    except Exception as e:
        logger.error(f"查詢失敗: {e}")

    # Step 5: 驗證連接池是否被共享
    logger.info("\n📍 Step 5: 驗證連接池共享狀態")
    if checker._connection_pool and service1._connection_pool:
        if id(checker._connection_pool) == id(service1._connection_pool):
            logger.info("✅ 連接池被正確共享")
        else:
            logger.error("❌ 連接池沒有被共享!")
            logger.error(f"   Service pool: {id(service1._connection_pool)}")
            logger.error(f"   Checker pool: {id(checker._connection_pool)}")

    logger.info("\n" + "="*80)
    logger.info("🔬 診斷完成")
    logger.info("="*80)

if __name__ == "__main__":
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()

    # 執行診斷
    asyncio.run(test_singleton_behavior())
