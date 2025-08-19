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

# Similarity thresholds by skill category (Balanced for coverage and quality)
SIMILARITY_THRESHOLDS = {
    "SKILL": 0.35,    # Moderate threshold for technical skills
    "FIELD": 0.30,    # Lower threshold for domain knowledge
    "DEFAULT": 0.35   # Default threshold
}

# Minimum threshold for initial query (optimization)
MIN_SIMILARITY_THRESHOLD = 0.30

# Course type quotas for balanced recommendations
COURSE_TYPE_QUOTAS = {
    "SKILL": {
        "course": 15,          # Single courses for quick learning
        "project": 5,          # Hands-on projects
        "certification": 2,    # Professional certifications
        "specialization": 2,   # Course series
        "degree": 1           # Degree programs
    },
    "FIELD": {
        "specialization": 12,  # Course series for comprehensive learning
        "degree": 4,          # Full degree programs
        "course": 5,          # Supplementary single courses
        "certification": 2,    # Professional certifications
        "project": 1          # Practical projects
    }
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

# SQL query for course availability with quota-based diversity (v2.0)
AVAILABILITY_QUERY = """
WITH initial_candidates AS (
    -- Step 1: Use minimum threshold for initial filtering
    SELECT
        id,
        course_type_standard,
        name,
        1 - (embedding <=> $1::vector) as similarity
    FROM courses
    WHERE platform = 'coursera'
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) >= 0.30  -- MIN_SIMILARITY_THRESHOLD
    ORDER BY similarity DESC
    LIMIT 80  -- Get enough candidates for diversity
),
filtered_candidates AS (
    -- Step 2: Apply category-specific threshold filtering
    SELECT * FROM initial_candidates
    WHERE
        -- SKILL category requires moderate threshold
        ($3 = 'SKILL' AND similarity >= 0.35) OR
        -- FIELD category uses lower threshold
        ($3 = 'FIELD' AND similarity >= 0.30) OR
        -- DEFAULT uses SKILL threshold
        ($3 NOT IN ('SKILL', 'FIELD') AND similarity >= 0.35)
),
type_ranked AS (
    -- Step 3: Rank within each course type and get counts
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY course_type_standard
            ORDER BY similarity DESC
        ) as type_rank,
        COUNT(*) OVER (PARTITION BY course_type_standard) as type_count
    FROM filtered_candidates
),
quota_applied AS (
    -- Step 4: Apply dynamic quotas based on category
    SELECT * FROM type_ranked
    WHERE
        ($3 = 'SKILL' AND (
            (course_type_standard = 'course' AND type_rank <= LEAST(15, type_count)) OR
            (course_type_standard = 'project' AND type_rank <= LEAST(5, type_count)) OR
            (course_type_standard = 'certification' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'specialization' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'degree' AND type_rank <= LEAST(1, type_count))
        )) OR
        ($3 = 'FIELD' AND (
            (course_type_standard = 'specialization' AND type_rank <= LEAST(12, type_count)) OR
            (course_type_standard = 'degree' AND type_rank <= LEAST(4, type_count)) OR
            (course_type_standard = 'course' AND type_rank <= LEAST(5, type_count)) OR
            (course_type_standard = 'certification' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'project' AND type_rank <= LEAST(1, type_count))
        )) OR
        -- DEFAULT category uses balanced quotas
        ($3 NOT IN ('SKILL', 'FIELD') AND (
            (course_type_standard = 'course' AND type_rank <= LEAST(10, type_count)) OR
            (course_type_standard = 'specialization' AND type_rank <= LEAST(5, type_count)) OR
            (course_type_standard = 'project' AND type_rank <= LEAST(3, type_count)) OR
            (course_type_standard = 'certification' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'degree' AND type_rank <= LEAST(2, type_count))
        ))
)
-- Step 5: Final selection ordered by pure similarity
SELECT
    COUNT(*) > 0 as has_courses,
    COUNT(*) as total_count,
    COUNT(DISTINCT course_type_standard) as type_diversity,
    array_agg(DISTINCT course_type_standard) as course_types,
    array_agg(id ORDER BY similarity DESC) as course_ids
FROM quota_applied
ORDER BY similarity DESC
LIMIT 25;
"""


class CourseAvailabilityChecker:
    """Service for checking course availability for skills"""

    def __init__(self, connection_pool: asyncpg.Pool | None = None):
        """
        Initialize the course availability checker

        Args:
            connection_pool: Optional shared connection pool from CourseSearchService
        """
        import os

        self._connection_pool = connection_pool
        self._embedding_client = None

        # Check if cache is enabled via environment variable
        self._cache_enabled = os.getenv("ENABLE_COURSE_CACHE", "true").lower() == "true"

        # Initialize dynamic cache only if enabled
        if self._cache_enabled:
            from src.services.dynamic_course_cache import get_course_cache
            self._dynamic_cache = get_course_cache()
            logger.info("[CourseAvailability] Dynamic cache enabled")
        else:
            self._dynamic_cache = None
            logger.info("[CourseAvailability] Dynamic cache disabled - using direct database queries")

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
        Batch check course availability for skills with dynamic caching

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

            # 1. Check dynamic cache for each skill (if enabled)
            uncached_skills = []
            cache_hits = 0

            if self._cache_enabled and self._dynamic_cache:
                # Cache is enabled - check cache first
                for skill in skill_queries:
                    skill_category = skill.get('skill_category', 'DEFAULT')
                    threshold = SIMILARITY_THRESHOLDS.get(skill_category, SIMILARITY_THRESHOLDS["DEFAULT"])

                    # Generate cache key based on full embedding text
                    cache_key = self._dynamic_cache.generate_cache_key(
                        skill, skill_category, threshold
                    )

                    # Try to get from cache
                    cached_result = await self._dynamic_cache.get(cache_key)

                    if cached_result:
                        # Cache hit: use cached data
                        skill.update(cached_result)
                        cache_hits += 1
                        logger.debug(f"[CourseAvailability] Dynamic cache hit for '{skill['skill_name']}'")
                    else:
                        # Cache miss: add to uncached list
                        skill['_cache_key'] = cache_key  # Store for later caching
                        uncached_skills.append(skill)
            else:
                # Cache is disabled - all skills need to be queried
                uncached_skills = skill_queries

            # 2. Process uncached skills
            if uncached_skills:
                # Batch generate embeddings (single API call)
                query_texts = [
                    self._generate_embedding_text(skill)
                    for skill in uncached_skills
                ]

                logger.debug(f"[CourseAvailability] Generating embeddings for {len(query_texts)} skills")
                embeddings = await self._embedding_client.create_embeddings(query_texts)

                # Parallel query for each skill (support up to 20 parallel tasks)
                tasks = [
                    self._check_single_skill(
                        emb,
                        skill['skill_name'],
                        skill.get('skill_category', 'DEFAULT')
                    )
                    for emb, skill in zip(embeddings, uncached_skills, strict=False)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results and cache them
                for skill, result in zip(uncached_skills, results, strict=False):
                    # Remove temporary cache key if present
                    cache_key = skill.pop('_cache_key', None)

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
                        # Success: update skill and cache result
                        skill["has_available_courses"] = result["has_courses"]
                        skill["course_count"] = result["count"]
                        skill["available_course_ids"] = result.get("course_ids", [])

                        # Add diversity metrics (v2.0)
                        if result.get("type_diversity") is not None:
                            skill["type_diversity"] = result["type_diversity"]
                            skill["course_types"] = result.get("course_types", [])

                        # Cache the result for future use (if cache enabled)
                        if self._cache_enabled and self._dynamic_cache and cache_key:
                            await self._dynamic_cache.set(cache_key, {
                                "has_available_courses": result["has_courses"],
                                "course_count": result["count"],
                                "available_course_ids": result.get("course_ids", []),
                                "type_diversity": result.get("type_diversity", 0),
                                "course_types": result.get("course_types", [])
                            })

            # 3. Record performance metrics
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            cache_hit_rate = cache_hits / len(skill_queries) if skill_queries else 0

            monitoring_service.track_event("CourseAvailabilityCheck", {
                "skill_count": len(skill_queries),
                "duration_ms": duration_ms,
                "cache_hit_rate": cache_hit_rate,
                "cached_count": cache_hits,
                "uncached_count": len(uncached_skills),
                "cache_enabled": self._cache_enabled,
                "cache_type": "dynamic" if self._cache_enabled else "none"
            })

            if self._cache_enabled:
                cache_info = f"(dynamic cache hit rate: {cache_hit_rate:.1%}, hits: {cache_hits})"
            else:
                cache_info = "(cache disabled)"

            logger.info(
                f"[CourseAvailability] Checked {len(skill_queries)} skills in {duration_ms}ms {cache_info}"
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
                skill["available_course_ids"] = []  # Always provide empty list on error

            return skill_queries

    def _check_cache(self, skill_queries: list[dict]) -> dict[str, dict]:
        """
        Legacy cache check method - DEPRECATED

        This method is kept for backward compatibility but is no longer used.
        Dynamic caching is now handled directly in check_course_availability().

        Args:
            skill_queries: List of skill queries

        Returns:
            Empty dictionary (no longer caches using static cache)
        """
        # Return empty dict - all caching now handled by dynamic cache
        logger.debug("[CourseAvailability] Legacy _check_cache called - using dynamic cache instead")
        return {}

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

                    # Use minimum threshold for initial query (optimization)
                    # The actual filtering happens in the SQL based on skill_category
                    min_threshold = MIN_SIMILARITY_THRESHOLD

                    # Execute availability check query with quota-based diversity
                    result = await conn.fetchrow(
                        AVAILABILITY_QUERY,
                        embedding,
                        min_threshold,  # Use minimum threshold
                        skill_category
                    )

                    # Get course IDs (already limited in query)
                    course_ids = result.get("course_ids", []) or []
                    if course_ids and len(course_ids) > 25:
                        course_ids = course_ids[:25]

                    # Get type diversity information
                    type_diversity = result.get("type_diversity", 0)
                    course_types = result.get("course_types", [])

                    # Return enhanced result with diversity metrics
                    return {
                        "has_courses": result["has_courses"],
                        "count": min(result.get("total_count", 0), 25),  # Use get() for safety
                        "type_diversity": type_diversity,  # Number of different course types
                        "course_types": course_types,      # List of course types found
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
