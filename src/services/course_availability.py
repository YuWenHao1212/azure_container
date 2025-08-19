"""
Course Availability Check Service for Gap Analysis
Checks if courses are available for identified skill gaps
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

import asyncpg

from src.core.monitoring_service import monitoring_service
from src.services.llm_factory import get_embedding_client

logger = logging.getLogger(__name__)

# Similarity thresholds by skill category
SIMILARITY_THRESHOLDS = {
    "SKILL": 0.30,  # Higher threshold for technical skills
    "FIELD": 0.25,  # Lower threshold for domain knowledge
    "DEFAULT": 0.30  # Default threshold
}

# Popular skills cache (preloaded at startup)
POPULAR_SKILLS_CACHE = {
    # Technical Skills (SKILL category) - with sample course IDs
    "Python": {
        "has_courses": True,
        "count": 10,
        # Course IDs removed - will be fetched from database
    },
    "JavaScript": {
        "has_courses": True,
        "count": 10,
        # Course IDs removed - will be fetched from database
    },
    "React": {
        "has_courses": True,
        "count": 10,
        # Course IDs removed - will be fetched from database
    },
    "Docker": {
        "has_courses": True,
        "count": 8,
        # Course IDs removed - will be fetched from database
    },
    "Kubernetes": {
        "has_courses": True,
        "count": 6,
        # Course IDs removed - will be fetched from database
    },
    "AWS": {
        "has_courses": True,
        "count": 10,
        # Course IDs removed - will be fetched from database
    },
    "Azure": {
        "has_courses": True,
        "count": 10,
        # Course IDs removed - will be fetched from database
    },
    "Machine Learning": {
        "has_courses": True,
        "count": 10,
        # Course IDs removed - will be fetched from database
    },
    "TypeScript": {"has_courses": True, "count": 10},
    "Node.js": {"has_courses": True, "count": 10},
    "Java": {"has_courses": True, "count": 10},
    "SQL": {"has_courses": True, "count": 10},
    "Git": {"has_courses": True, "count": 10},

    # Domain Knowledge (FIELD category)
    "Computer Science": {"has_courses": True, "count": 10},
    "Data Science": {"has_courses": True, "count": 10},
    "Product Management": {"has_courses": True, "count": 10},
    "UX Design": {"has_courses": True, "count": 10},
    "Project Management": {"has_courses": True, "count": 10},
    "Digital Marketing": {"has_courses": True, "count": 10},
    "Business Analysis": {"has_courses": True, "count": 10},
}

# SQL query for checking course availability with course type prioritization
AVAILABILITY_QUERY = """
WITH ranked_courses AS (
    SELECT
        id,
        course_type_standard,
        name,
        1 - (embedding <=> $1::vector) as similarity,
        CASE
            -- SKILL category preferences
            WHEN $3 = 'SKILL' THEN
                CASE course_type_standard
                    WHEN 'course' THEN 3         -- Highest priority
                    WHEN 'project' THEN 2        -- Second priority
                    WHEN 'certification' THEN 1  -- Third priority
                    ELSE 0  -- Other types still included
                END
            -- FIELD category preferences
            WHEN $3 = 'FIELD' THEN
                CASE course_type_standard
                    WHEN 'specialization' THEN 3  -- Highest priority
                    WHEN 'degree' THEN 2           -- Second priority
                    WHEN 'certification' THEN 1    -- Third priority
                    ELSE 0  -- Other types still included
                END
            ELSE 0
        END as priority_score
    FROM courses
    WHERE platform = 'coursera'
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) >= $2
    ORDER BY priority_score DESC, similarity DESC
    LIMIT 25  -- Limit to collect up to 25 course IDs
)
SELECT
    COUNT(*) > 0 as has_courses,
    COUNT(*) as total_count,
    SUM(CASE WHEN priority_score > 0 THEN 1 ELSE 0 END) as preferred_count,
    SUM(CASE WHEN priority_score = 0 THEN 1 ELSE 0 END) as other_count,
    array_agg(id ORDER BY priority_score DESC, similarity DESC) as course_ids
FROM ranked_courses;
"""


class CourseAvailabilityChecker:
    """Service for checking course availability for skills"""

    def __init__(self, connection_pool: asyncpg.Pool | None = None):
        """
        Initialize the course availability checker

        Args:
            connection_pool: Optional shared connection pool from CourseSearchService
        """
        self._connection_pool = connection_pool
        self._embedding_client = None

    def _generate_embedding_text(self, skill_query: dict[str, Any]) -> str:
        """
        Generate optimized embedding text based on skill category

        Args:
            skill_query: Skill query with name, category, and description

        Returns:
            Optimized text for embedding generation
        """
        skill_name = skill_query.get('skill_name', '')
        description = skill_query.get('description', '')
        category = skill_query.get('skill_category', 'DEFAULT')

        if category == "SKILL":
            # For technical skills: emphasize course, project, certificate
            # Targets: course (69.4%), project (7.2%), certification (1.8%)
            text = f"{skill_name} course project certificate. {description}"
        elif category == "FIELD":
            # For domain knowledge: emphasize specialization, degree
            # Targets: specialization (16.7%), degree (5.0%)
            text = f"{skill_name} specialization degree. {description}"
        else:
            # Default: balanced approach
            text = f"{skill_name} {description}"

        return text

    async def initialize(self):
        """Initialize the service"""
        if not self._embedding_client:
            # Use course embedding client (embedding-3-small)
            self._embedding_client = get_embedding_client(api_name="course_search")

    async def check_course_availability(
        self,
        skill_queries: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Batch check course availability for skills

        Args:
            skill_queries: List of skill queries from Gap Analysis (3-6 skills)

        Returns:
            Enhanced skill queries with has_available_courses and course_count
        """
        if not skill_queries:
            return []

        start_time = datetime.now()

        try:
            # Initialize service
            await self.initialize()

            # 1. Check cache for popular skills
            cached_results = self._check_cache(skill_queries)
            uncached = [s for s in skill_queries if s["skill_name"] not in cached_results]

            if uncached:
                # 2. Batch generate embeddings (single API call)
                # Generate optimized texts based on skill category
                query_texts = [
                    self._generate_embedding_text(skill)
                    for skill in uncached
                ]

                logger.debug(f"[CourseAvailability] Generating embeddings for {len(query_texts)} skills")
                embeddings = await self._embedding_client.create_embeddings(query_texts)

                # 3. Parallel query for each skill (support up to 20 parallel tasks)
                tasks = [
                    self._check_single_skill(
                        emb,
                        skill['skill_name'],
                        skill.get('skill_category', 'DEFAULT')
                    )
                    for emb, skill in zip(embeddings, uncached, strict=False)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 4. Process results and errors
                for skill, result in zip(uncached, results, strict=False):
                    if isinstance(result, Exception):
                        # Error handling - Graceful Degradation
                        logger.error(f"[CourseAvailability] Failed for {skill['skill_name']}: {result}")
                        skill["has_available_courses"] = False
                        skill["course_count"] = 0
                        skill["available_course_ids"] = []  # Always provide empty list on error

                        # Send alert to Operations
                        monitoring_service.track_event("CourseAvailabilityCheckFailed", {
                            "skill": skill['skill_name'],
                            "error": str(result),
                            "severity": "MEDIUM"
                        })
                    else:
                        skill["has_available_courses"] = result["has_courses"]
                        skill["course_count"] = result["count"]
                        # Always provide course IDs (empty list if none available)
                        skill["available_course_ids"] = result.get("course_ids", [])
                        # Add breakdown if available
                        if result.get("preferred_count") is not None:
                            skill["preferred_courses"] = result["preferred_count"]
                            skill["other_courses"] = result["other_count"]

            # 5. Record performance metrics
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            cache_hit_rate = len(cached_results) / len(skill_queries) if skill_queries else 0

            monitoring_service.track_event("CourseAvailabilityCheck", {
                "skill_count": len(skill_queries),
                "duration_ms": duration_ms,
                "cache_hit_rate": cache_hit_rate,
                "cached_count": len(cached_results),
                "uncached_count": len(uncached)
            })

            logger.info(
                f"[CourseAvailability] Checked {len(skill_queries)} skills in {duration_ms}ms "
                f"(cache hit rate: {cache_hit_rate:.1%})"
            )

            return skill_queries

        except Exception as e:
            # Overall failure - mark all as false
            logger.error(f"[CourseAvailability] System error: {e}")
            monitoring_service.track_event("CourseAvailabilitySystemError", {
                "error": str(e),
                "severity": "HIGH"
            })

            for skill in skill_queries:
                skill["has_available_courses"] = False
                skill["course_count"] = 0

            return skill_queries

    def _check_cache(self, skill_queries: list[dict]) -> dict[str, dict]:
        """
        Check cache for popular skills

        Args:
            skill_queries: List of skill queries

        Returns:
            Dictionary of cached results
        """
        cached = {}
        for skill in skill_queries:
            name = skill['skill_name']
            if name in POPULAR_SKILLS_CACHE:
                cached[name] = POPULAR_SKILLS_CACHE[name]
                skill["has_available_courses"] = cached[name]["has_courses"]
                skill["course_count"] = cached[name]["count"]
                # Always provide available_course_ids field
                # Since we removed fake IDs from cache, return empty list for now
                # TODO: Implement real-time cache with actual course IDs
                skill["available_course_ids"] = []
                logger.debug(f"[CourseAvailability] Cache hit for '{name}'")
        return cached

    async def _check_single_skill(
        self,
        embedding: list[float],
        skill_name: str,
        skill_category: str = "DEFAULT",
        timeout: float = 3.0
    ) -> dict[str, Any]:
        """
        Check availability for a single skill

        Args:
            embedding: Skill embedding vector
            skill_name: Name of the skill
            timeout: Query timeout in seconds

        Returns:
            Dictionary with has_courses and count
        """
        try:
            async with asyncio.timeout(timeout):
                # Get connection from pool
                if not self._connection_pool:
                    logger.info("🔍 [CourseAvailability] No connection pool, fetching from Singleton...")
                    # Fallback: try to get from CourseSearchSingleton
                    from src.services.course_search_singleton import get_course_search_service
                    course_service = await get_course_search_service()
                    self._connection_pool = course_service._connection_pool
                    logger.info(
                        f"✅ [CourseAvailability] Got connection pool from Singleton: "
                        f"{id(self._connection_pool) if self._connection_pool else 'None'}"
                    )

                if not self._connection_pool:
                    raise Exception("No database connection pool available")

                async with self._connection_pool.acquire() as conn:
                    # pgvector already registered in connection pool init
                    # No need to register again - saves 607ms per query!

                    # Get similarity threshold based on category
                    threshold = SIMILARITY_THRESHOLDS.get(skill_category, SIMILARITY_THRESHOLDS["DEFAULT"])

                    # Execute availability check query with prioritization
                    result = await conn.fetchrow(
                        AVAILABILITY_QUERY,
                        embedding,
                        threshold,
                        skill_category
                    )

                    # Get course IDs (limit to 25 for response size)
                    course_ids = result.get("course_ids", []) or []
                    if course_ids and len(course_ids) > 25:
                        course_ids = course_ids[:25]

                    # Return enhanced result with breakdown and course IDs
                    return {
                        "has_courses": result["has_courses"],
                        "count": min(result["total_count"], 25),  # Update cap to match query
                        "preferred_count": result.get("preferred_count", 0),
                        "other_count": result.get("other_count", 0),
                        "course_ids": course_ids
                    }

        except TimeoutError:
            logger.warning(f"[CourseAvailability] Timeout checking '{skill_name}'")
            raise
        except Exception as e:
            logger.error(f"[CourseAvailability] Error checking '{skill_name}': {e}")
            raise


# Global instance
_checker_instance: CourseAvailabilityChecker | None = None


async def check_course_availability(
    skill_queries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Convenience function to check course availability

    Args:
        skill_queries: List of skill queries from Gap Analysis

    Returns:
        Enhanced skill queries with availability information
    """
    global _checker_instance

    if not _checker_instance:
        _checker_instance = CourseAvailabilityChecker()

    return await _checker_instance.check_course_availability(skill_queries)
