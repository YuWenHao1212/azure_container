"""
Course Availability Check Service for Gap Analysis
Checks if courses are available for identified skill gaps
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import asyncpg

from src.core.monitoring_service import monitoring_service
from src.services.llm_factory import get_embedding_client

logger = logging.getLogger(__name__)

# Similarity thresholds by skill category (Configurable via environment variables)
# Default values are conservative to ensure courses are returned
# Production can override via environment variables for fine-tuning
SIMILARITY_THRESHOLDS = {
    "SKILL": float(os.getenv("COURSE_THRESHOLD_SKILL", "0.35")),    # Default: 0.35, Target: 0.40
    "FIELD": float(os.getenv("COURSE_THRESHOLD_FIELD", "0.30")),    # Default: 0.30, Target: 0.35
    "DEFAULT": float(os.getenv("COURSE_THRESHOLD_DEFAULT", "0.35"))  # Default: 0.35, Target: 0.40
}

# Minimum threshold for initial query (optimization)
MIN_SIMILARITY_THRESHOLD = float(os.getenv("COURSE_MIN_THRESHOLD", "0.30"))  # Default: 0.30, Target: 0.35

# Feature toggle for deficit filling mechanism
# When enabled, the system will apply intelligent quota management and deficit filling
# When disabled, it will simply return top courses by similarity
ENABLE_DEFICIT_FILLING = os.getenv("ENABLE_DEFICIT_FILLING", "false").lower() == "true"

# Log the active thresholds on module load
logger.info(f"Course Availability Thresholds - SKILL: {SIMILARITY_THRESHOLDS['SKILL']}, "
           f"FIELD: {SIMILARITY_THRESHOLDS['FIELD']}, "
           f"DEFAULT: {SIMILARITY_THRESHOLDS['DEFAULT']}, "
           f"MIN: {MIN_SIMILARITY_THRESHOLD}, "
           f"Deficit Filling: {'Enabled' if ENABLE_DEFICIT_FILLING else 'Disabled'}")

# Original quotas for deficit calculation (before reserve pool expansion)
ORIGINAL_QUOTAS = {
    "SKILL": {
        "course": 15,          # Basic allocation before reserves
        "project": 5,          # Target quota for projects
        "certification": 2,    # Target quota for certifications
        "specialization": 2,   # Target quota for specializations
        "degree": 1           # Target quota for degrees
    },
    "FIELD": {
        "specialization": 12,  # Target quota for specializations
        "degree": 4,          # Target quota for degrees
        "course": 5,          # Basic allocation before reserves
        "certification": 2,    # Target quota for certifications
        "project": 1          # Target quota for projects
    },
    "DEFAULT": {
        "course": 10,         # Basic allocation before reserves
        "specialization": 5,   # Target quota for specializations
        "project": 3,         # Target quota for projects
        "certification": 2,    # Target quota for certifications
        "degree": 2           # Target quota for degrees
    }
}

# Extended quotas for SQL query (includes reserve pools)
COURSE_TYPE_QUOTAS = {
    "SKILL": {
        "course": 25,          # 15 basic + 10 reserve for supplementation
        "project": 5,          # No change (specific type)
        "certification": 2,    # No change (specific type)
        "specialization": 2,   # No change (specific type)
        "degree": 1           # No change (specific type)
    },
    "FIELD": {
        "specialization": 12,  # No change (primary for FIELD)
        "degree": 4,          # No change (specific type)
        "course": 15,          # 5 basic + 10 reserve for supplementation
        "certification": 2,    # No change (specific type)
        "project": 1          # No change (specific type)
    },
    "DEFAULT": {
        "course": 20,         # 10 basic + 10 reserve for supplementation
        "specialization": 5,   # No change (specific type)
        "project": 3,         # No change (specific type)
        "certification": 2,    # No change (specific type)
        "degree": 2           # No change (specific type)
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
        1 - (embedding <=> $1::vector) as similarity,
        provider_standardized,
        description
    FROM courses
    WHERE platform = 'coursera'
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) >= $2  -- MIN_SIMILARITY_THRESHOLD
    ORDER BY similarity DESC
    LIMIT 80  -- Get enough candidates for diversity
),
filtered_candidates AS (
    -- Step 2: Apply category-specific threshold filtering
    SELECT * FROM initial_candidates
    WHERE
        -- SKILL category requires moderate threshold
        ($3 = 'SKILL' AND similarity >= $4) OR
        -- FIELD category uses lower threshold
        ($3 = 'FIELD' AND similarity >= $5) OR
        -- DEFAULT uses SKILL threshold
        ($3 NOT IN ('SKILL', 'FIELD') AND similarity >= $6)
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
    -- Step 4: Apply dynamic quotas based on category (with reserve pools)
    SELECT * FROM type_ranked
    WHERE
        ($3 = 'SKILL' AND (
            (course_type_standard = 'course' AND type_rank <= LEAST(25, type_count)) OR
            (course_type_standard = 'project' AND type_rank <= LEAST(5, type_count)) OR
            (course_type_standard = 'certification' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'specialization' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'degree' AND type_rank <= LEAST(1, type_count))
        )) OR
        ($3 = 'FIELD' AND (
            (course_type_standard = 'specialization' AND type_rank <= LEAST(12, type_count)) OR
            (course_type_standard = 'degree' AND type_rank <= LEAST(4, type_count)) OR
            (course_type_standard = 'course' AND type_rank <= LEAST(15, type_count)) OR
            (course_type_standard = 'certification' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'project' AND type_rank <= LEAST(1, type_count))
        )) OR
        -- DEFAULT category uses balanced quotas (with reserves)
        ($3 NOT IN ('SKILL', 'FIELD') AND (
            (course_type_standard = 'course' AND type_rank <= LEAST(20, type_count)) OR
            (course_type_standard = 'specialization' AND type_rank <= LEAST(5, type_count)) OR
            (course_type_standard = 'project' AND type_rank <= LEAST(3, type_count)) OR
            (course_type_standard = 'certification' AND type_rank <= LEAST(2, type_count)) OR
            (course_type_standard = 'degree' AND type_rank <= LEAST(2, type_count))
        ))
)
-- Step 5: Final selection with aggregated results (SIMPLIFIED FOR TESTING)
SELECT
    COUNT(*) > 0 as has_courses,
    COUNT(*) as total_count,
    COUNT(DISTINCT course_type_standard) as type_diversity,
    array_agg(DISTINCT course_type_standard) as course_types,
    -- SIMPLIFIED: Return course IDs directly like the old version (limited to 25)
    (array_agg(id ORDER BY similarity DESC))[1:25] as course_ids,
    -- Also keep course_data for backward compatibility (limited to 25)
    (array_agg(
        json_build_object(
            'id', id,
            'similarity', similarity,
            'type', course_type_standard
        ) ORDER BY similarity DESC
    ))[1:25] as course_data,
    -- NEW: Return detailed course information for resume enhancement
    -- Fixed: Use JSON_AGG instead of array_agg for better stability
    COALESCE(
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'id', id,
                'name', COALESCE(REGEXP_REPLACE(name, '[\\x00-\\x1F\\x7F]', '', 'g'), ''),
                'type', COALESCE(course_type_standard, 'course'),
                'provider_standardized', COALESCE(provider_standardized, 'Coursera'),
                'description', COALESCE(
                    REGEXP_REPLACE(LEFT(description, 200), '[\\x00-\\x1F\\x7F]', '', 'g'),
                    ''
                ),
                'similarity', similarity
            )
            ORDER BY similarity DESC
        ) FILTER (WHERE id IS NOT NULL),
        '[]'::json
    ) as course_details
FROM (
    SELECT * FROM quota_applied
    ORDER BY similarity DESC
    LIMIT 25
) AS top_courses;
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

        # Initialize connection pool if not provided
        if not self._connection_pool:
            # Try to get the pool from CourseSearchService singleton
            from src.services.course_search import get_course_search_service

            course_search = get_course_search_service()
            if not course_search._connection_pool:
                await course_search.initialize()
            self._connection_pool = course_search._connection_pool

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
                        skill["course_details"] = []  # Also provide empty list for course details

                        # Send alert to Operations
                        monitoring_service.track_event("CourseAvailabilityCheckFailed", {
                            "skill": skill['skill_name'],
                            "error": str(result),
                            "severity": "MEDIUM"
                        })
                    else:
                        # Success: update skill and cache result
                        skill["has_available_courses"] = result["has_courses"]
                        skill["course_count"] = result.get("total_count", 0)
                        skill["available_course_ids"] = result.get("course_ids", [])
                        # NEW: Store course details for resume enhancement
                        skill["course_details"] = result.get("course_details", [])

                        # DEBUG: Verify course_details was stored
                        course_count = len(skill['course_details'])
                        skill_name = skill['skill_name']
                        logger.info(
                            f"[ENHANCEMENT_DEBUG] Stored {course_count} course_details "
                            f"for skill '{skill_name}'"
                        )

                        # Add diversity metrics (v2.0)
                        if result.get("type_diversity") is not None:
                            skill["type_diversity"] = result["type_diversity"]
                            skill["course_types"] = result.get("course_types", [])

                        # Cache the result for future use (if cache enabled)
                        if self._cache_enabled and self._dynamic_cache and cache_key:
                            cache_data = {
                                "has_available_courses": result["has_courses"],
                                "course_count": result.get("total_count", 0),
                                "available_course_ids": result.get("course_ids", []),
                                "type_diversity": result.get("type_diversity", 0),
                                "course_types": result.get("course_types", []),
                                "course_details": result.get("course_details", [])  # NEW: Cache course details
                            }
                            await self._dynamic_cache.set(cache_key, cache_data)

                            # DEBUG: Verify cache data includes course_details
                            course_count = len(cache_data['course_details'])
                            skill_name = skill['skill_name']
                            logger.info(
                                f"[ENHANCEMENT_DEBUG] Cached {course_count} course_details "
                                f"for skill '{skill_name}'"
                            )

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

            # Build enhancement data from all skills
            enhancement_project, enhancement_certification = self._build_enhancement_data(
                skill_queries, skill_queries
            )

            # Log enhancement data for debugging
            logger.info(
                f"[CourseAvailability] Enhancement data built: "
                f"projects={len(enhancement_project)}, "
                f"certifications={len(enhancement_certification)}"
            )

            # DEBUG: More detailed enhancement data logging
            logger.info("[ENHANCEMENT_DEBUG] Enhancement data details:")
            # enhancement_project and enhancement_certification are now lists
            if isinstance(enhancement_project, list):
                proj_preview = [p.get("id", "") for p in enhancement_project[:5]] if enhancement_project else 'Empty'
            else:
                # Fallback for dict (shouldn't happen but just in case)
                proj_preview = list(enhancement_project.keys())[:5] if enhancement_project else 'Empty'
            logger.info(f"  - Projects: {proj_preview}")

            if isinstance(enhancement_certification, list):
                cert_preview = [c.get("id", "") for c in enhancement_certification[:5]] if enhancement_certification else 'Empty'
            else:
                # Fallback for dict (shouldn't happen but just in case)
                cert_preview = list(enhancement_certification.keys())[:5] if enhancement_certification else 'Empty'
            logger.info(f"  - Certifications: {cert_preview}")

            # Add enhancement data to the first skill for backward compatibility
            # This ensures the data is accessible from the API response
            if skill_queries:
                skill_queries[0]["resume_enhancement_project"] = enhancement_project
                skill_queries[0]["resume_enhancement_certification"] = enhancement_certification
                logger.info(
                    "[CourseAvailability] Enhancement data added to first skill query"
                )

                # DEBUG: Verify the data was actually added
                logger.info("[ENHANCEMENT_DEBUG] Verifying first skill after adding enhancement:")
                has_project = 'resume_enhancement_project' in skill_queries[0]
                has_cert = 'resume_enhancement_certification' in skill_queries[0]
                proj_count = len(skill_queries[0].get('resume_enhancement_project', []))
                cert_count = len(skill_queries[0].get('resume_enhancement_certification', []))

                logger.info(f"  - First skill has resume_enhancement_project: {has_project}")
                logger.info(f"  - First skill has resume_enhancement_certification: {has_cert}")
                logger.info(f"  - Project count in first skill: {proj_count}")
                logger.info(f"  - Certification count in first skill: {cert_count}")

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
                skill["course_details"] = []  # Also provide empty list for course details

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
                    logger.info("🔍 [CourseAvailability] No connection pool, attempting initialization...")
                    try:
                        # Fallback: try to get from CourseSearchSingleton
                        from src.services.course_search_singleton import get_course_search_service
                        course_service = await get_course_search_service()
                        self._connection_pool = course_service._connection_pool

                        if self._connection_pool:
                            logger.info(
                                f"✅ [CourseAvailability] Got connection pool from Singleton: "
                                f"{id(self._connection_pool)}"
                            )
                        else:
                            logger.warning("⚠️ [CourseAvailability] Singleton returned None connection pool")
                    except Exception as e:
                        logger.error(f"❌ [CourseAvailability] Failed to get connection pool: {e}")
                        self._connection_pool = None

                if not self._connection_pool:
                    # Return empty result instead of raising exception
                    logger.error("❌ [CourseAvailability] No database connection available, returning empty result")
                    return {
                        "has_courses": False,
                        "total_count": 0,  # Changed from "count" to "total_count"
                        "type_diversity": 0,
                        "course_types": [],
                        "course_ids": [],
                        "course_details": []  # Return empty course details
                    }

                async with self._connection_pool.acquire() as conn:
                    # pgvector already registered in connection pool init
                    # No need to register again - saves 607ms per query!

                    # Use minimum threshold for initial query (optimization)
                    # The actual filtering happens in the SQL based on skill_category
                    min_threshold = MIN_SIMILARITY_THRESHOLD

                    # Execute availability check query with quota-based diversity
                    # DEBUG: Log query parameters (using INFO for production visibility)
                    logger.info("[COURSE_DEBUG] SQL Query parameters:")
                    logger.info(f"  - embedding length: {len(embedding) if embedding else 0}")
                    logger.info(f"  - min_threshold: {min_threshold}")
                    logger.info(f"  - skill_category: {skill_category}")
                    skill_threshold = SIMILARITY_THRESHOLDS.get('SKILL', SIMILARITY_THRESHOLDS['DEFAULT'])
                    logger.info(f"  - SKILL threshold: {skill_threshold}")

                    result = await conn.fetchrow(
                        AVAILABILITY_QUERY,
                        embedding,                                              # $1
                        min_threshold,                                          # $2 = 0.30
                        skill_category,                                         # $3
                        SIMILARITY_THRESHOLDS.get("SKILL", SIMILARITY_THRESHOLDS["DEFAULT"]),    # $4 = 0.35
                        SIMILARITY_THRESHOLDS.get("FIELD", SIMILARITY_THRESHOLDS["DEFAULT"]),    # $5 = 0.30
                        SIMILARITY_THRESHOLDS.get("DEFAULT", SIMILARITY_THRESHOLDS["DEFAULT"])  # $6 = 0.35
                    )

                    # DEBUG: Log raw SQL result (using INFO for production visibility)
                    if result:
                        logger.info(f"[COURSE_DEBUG] SQL result keys: {list(result.keys())}")
                        course_ids = result.get('course_ids', [])
                        course_details = result.get('course_details', [])
                        logger.info(f"[COURSE_DEBUG] course_ids count: {len(course_ids) if course_ids else 0}")
                        logger.info(f"[COURSE_DEBUG] course_details type: {type(course_details)}")
                        details_count = len(course_details) if course_details else 0
                        logger.info(f"[COURSE_DEBUG] course_details count: {details_count}")
                        if course_details and len(course_details) > 0:
                            logger.info(f"[COURSE_DEBUG] First course_detail: {course_details[0]}")
                        # NEW DEBUG: Check if course_details is None vs empty list
                        logger.info(f"[ENHANCEMENT_DEBUG] course_details is None: {course_details is None}")
                        empty_status = not course_details if course_details is not None else 'N/A'
                        logger.info(f"[ENHANCEMENT_DEBUG] course_details empty: {empty_status}")
                    else:
                        logger.warning("[ENHANCEMENT_DEBUG] SQL query returned None result")

                    # Process course data - SIMPLIFIED VERSION FOR TESTING
                    # First check if we have course_ids directly (like old version)
                    # course_ids already extracted above for debugging

                    # Check if course_ids is not None and not empty
                    if course_ids is not None and len(course_ids) > 0 and course_ids[0] is not None:
                        # Use direct course_ids if available
                        final_course_ids = course_ids[:25]
                    else:
                        # Fallback to course_data processing
                        course_data = result.get("course_data", [])

                        # Ensure course_data is not None and filter out invalid entries
                        if course_data is None:
                            course_data = []
                        # Filter out None values and non-dict entries for robustness
                        course_data = [c for c in course_data if c and isinstance(c, dict)]

                        # If no valid courses found, return empty result
                        if not course_data:
                            return {
                                "has_courses": False,
                                "total_count": 0,  # Fixed: Use total_count instead of count
                                "type_diversity": 0,
                                "course_types": [],
                                "course_ids": [],
                                "course_details": []  # Return empty course details
                            }

                        # Check if deficit filling is enabled
                        if ENABLE_DEFICIT_FILLING:
                            # Apply deficit filling mechanism with quotas and reserves
                            logger.debug(f"[CourseAvailability] Applying deficit filling for {skill_category}")
                            final_course_ids = self._apply_deficit_filling(course_data, skill_category)
                        else:
                            # Simple processing: Sort by similarity and take top 25
                            course_data.sort(key=lambda x: x.get('similarity', 0), reverse=True)
                            final_course_ids = [c['id'] for c in course_data[:25]]

                    # Get diversity metrics
                    type_diversity = result.get("type_diversity", 0)
                    course_types = result.get("course_types", [])

                    # NEW: Get course details for resume enhancement
                    course_details = result.get("course_details", [])

                    # Handle JSON_AGG string result (convert to list if needed)
                    if isinstance(course_details, str):
                        import json
                        try:
                            course_details = json.loads(course_details)
                        except (json.JSONDecodeError, TypeError):
                            course_details = []

                    # Filter out None values
                    if course_details:
                        course_details = [c for c in course_details if c and isinstance(c, dict)]

                    # FALLBACK: If course_details is empty but we have course_data, build basic details
                    if not course_details and result.get("course_data"):
                        logger.warning(
                            f"[ENHANCEMENT_FALLBACK] course_details empty for '{skill_name}', "
                            f"using course_data fallback"
                        )
                        course_data = result.get("course_data", [])
                        if course_data and isinstance(course_data, list):
                            # Build basic course details from course_data
                            course_details = []
                            for item in course_data[:25]:  # Limit to 25 items
                                if item and isinstance(item, dict) and item.get("id"):
                                    course_details.append({
                                        "id": item["id"],
                                        "name": "",  # Name not available in course_data
                                        "type": item.get("type", "course"),
                                        "provider_standardized": "Coursera",
                                        "description": "",  # Description not available
                                        "similarity": item.get("similarity", 0)
                                    })
                            logger.info(
                                f"[ENHANCEMENT_FALLBACK] Built {len(course_details)} basic course_details "
                                f"from course_data for '{skill_name}'"
                            )

                    # DEBUG: Log course details before returning
                    logger.info(
                        f"[ENHANCEMENT_DEBUG] _check_single_skill returning "
                        f"{len(course_details)} course_details for skill '{skill_name}'"
                    )
                    if course_details and len(course_details) > 0:
                        logger.info(f"[ENHANCEMENT_DEBUG] Sample course detail: {course_details[0]}")

                    # Return enhanced result with diversity metrics
                    return {
                        "has_courses": len(final_course_ids) > 0,
                        "total_count": len(final_course_ids),  # Changed from "count" to "total_count"
                        "type_diversity": type_diversity,
                        "course_types": course_types,
                        "course_ids": final_course_ids,
                        "course_details": course_details  # NEW: Include course details
                    }

        except TimeoutError:
            logger.warning(f"[CourseAvailability] Timeout checking '{skill_name}'")
            raise
        except Exception as e:
            logger.error(f"[CourseAvailability] Error checking '{skill_name}': {e}")
            raise

    def _apply_deficit_filling(
        self,
        course_data: list[dict[str, Any]],
        skill_category: str
    ) -> list[str]:
        """
        Apply deficit filling logic with course reserves and re-sort by similarity

        Args:
            course_data: List of course dictionaries with id, similarity, type
            skill_category: SKILL, FIELD, or DEFAULT

        Returns:
            List of course IDs after deficit filling and resorting
        """
        if not course_data:
            return []

        # Get the appropriate quotas for this category
        original_quotas = ORIGINAL_QUOTAS.get(skill_category, ORIGINAL_QUOTAS["DEFAULT"])

        # Group courses by type
        courses_by_type = {}
        for course in course_data:
            course_type = course['type']
            if course_type not in courses_by_type:
                courses_by_type[course_type] = []
            courses_by_type[course_type].append(course)

        # Separate course type into basic and reserve pools
        course_list = courses_by_type.get('course', [])
        basic_course_quota = original_quotas.get('course', 10)

        # Split courses into basic allocation and reserves
        basic_courses = course_list[:basic_course_quota]
        reserve_courses = course_list[basic_course_quota:]

        # Collect courses up to original quotas for non-course types
        final_courses = []
        total_deficit = 0

        # Process non-course types first
        for type_name, quota in original_quotas.items():
            if type_name == 'course':
                # Handle courses separately after calculating deficits
                continue

            type_courses = courses_by_type.get(type_name, [])
            actual_count = len(type_courses)

            # Take up to quota
            final_courses.extend(type_courses[:quota])

            # Calculate deficit
            deficit = max(0, quota - actual_count)
            total_deficit += deficit

            if deficit > 0:
                logger.debug(
                    f"[CourseAvailability] {skill_category} - {type_name}: "
                    f"quota={quota}, actual={actual_count}, deficit={deficit}"
                )

        # Add basic course allocation
        final_courses.extend(basic_courses)

        # Fill deficits from reserve pool if available
        if total_deficit > 0 and reserve_courses:
            supplement_count = min(total_deficit, len(reserve_courses))
            supplement = reserve_courses[:supplement_count]
            final_courses.extend(supplement)
            logger.debug(
                f"[CourseAvailability] {skill_category} - Supplemented {supplement_count} "
                f"courses from reserve pool (deficit was {total_deficit})"
            )

        # Sort all courses by similarity (highest first)
        final_courses.sort(key=lambda x: x['similarity'], reverse=True)

        # Limit to 25 courses maximum
        final_courses = final_courses[:25]

        # Extract and return course IDs
        return [course['id'] for course in final_courses]

    def _build_enhancement_data(
        self,
        enhanced_skills: list[dict],
        skill_queries: list[dict]
    ) -> tuple[list, list]:
        """
        Build resume enhancement data structure (v3.1.0 array format)

        Args:
            enhanced_skills: Skills with course availability data
            skill_queries: Original skill queries with names

        Returns:
            Tuple of (resume_enhancement_project[], resume_enhancement_certification[])
        """
        projects = []
        certifications = []

        # DEBUG: Log input data
        logger.info(f"[ENHANCEMENT_DEBUG] _build_enhancement_data called with {len(enhanced_skills)} skills")

        for idx, skill in enumerate(enhanced_skills):
            if idx >= len(skill_queries):
                continue

            skill_name = skill_queries[idx].get("skill_name", "")
            course_details = skill.get("course_details", [])

            # DEBUG: Log each skill's course details
            logger.info(f"[ENHANCEMENT_DEBUG] Skill {idx} '{skill_name}':")
            logger.info(f"  - course_details type: {type(course_details)}")
            logger.info(f"  - course_details is None: {course_details is None}")
            logger.info(f"  - course_details count: {len(course_details) if course_details else 0}")
            if course_details and len(course_details) > 0:
                logger.info(f"  - First course: {course_details[0]}")

            if not course_details:
                logger.info(f"  - Skipping skill '{skill_name}' - no course_details")
                continue

            # Process courses by type with quotas
            project_count = 0
            cert_count = 0

            for course in course_details:
                if not course or not isinstance(course, dict):
                    logger.info(f"  - Skipping invalid course: {course}")
                    continue

                course_id = course.get("id")
                course_type = course.get("type", "")
                course_name = course.get("name", "")

                # DEBUG: Log each course being processed
                course_display_name = course_name[:50] if course_name else 'N/A'
                logger.info(
                    f"  - Processing course: id={course_id}, "
                    f"type={course_type}, name={course_display_name}"
                )

                if not course_id:
                    logger.info("  - Skipping course without ID")
                    continue

                # Projects: max 2 per skill
                if course_type == "project" and project_count < 2:
                    projects.append({
                        "id": course_id,
                        "name": course.get("name", ""),
                        "provider": course.get("provider_standardized", "Coursera"),
                        "description": course.get("description", "")[:200],
                        "related_skill": skill_name
                    })
                    project_count += 1
                    logger.info(f"    - Added project: {course_id[:20]}")

                # Certifications and Specializations: max 4 per skill
                elif course_type in ["certification", "specialization"] and cert_count < 4:
                    certifications.append({
                        "id": course_id,
                        "name": course.get("name", ""),
                        "provider": course.get("provider_standardized", "Coursera"),
                        "description": course.get("description", "")[:200],
                        "related_skill": skill_name
                    })
                    cert_count += 1
                    logger.info(f"    - Added certification: {course_id[:20]}")

                # Skip regular courses - only project/certification/specialization allowed
                # Based on specification requirement

        # Return empty array [] if no courses found (v3.1.0 format)
        result_projects = projects if projects else []
        result_certifications = certifications if certifications else []

        # DEBUG: Log final enhancement data
        logger.info("[ENHANCEMENT_DEBUG] _build_enhancement_data returning:")
        logger.info(f"  - Projects count: {len(result_projects)}")
        logger.info(f"  - Certifications count: {len(result_certifications)}")
        if result_projects:
            # result_projects is now a list, not a dict
            logger.info(f"  - Sample project: {result_projects[0] if result_projects else 'None'}")
        if result_certifications:
            # result_certifications is now a list, not a dict
            sample_cert = result_certifications[0] if result_certifications else 'None'
            logger.info(f"  - Sample certification: {sample_cert}")

        return result_projects, result_certifications


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
        # Get connection pool from CourseSearchService singleton
        from src.services.course_search import get_course_search_service

        course_search = get_course_search_service()
        if not course_search._connection_pool:
            await course_search.initialize()

        # Create checker with the properly initialized connection pool
        _checker_instance = CourseAvailabilityChecker(
            connection_pool=course_search._connection_pool
        )

        # Also initialize embedding client
        await _checker_instance.initialize()

    return await _checker_instance.check_course_availability(skill_queries)
