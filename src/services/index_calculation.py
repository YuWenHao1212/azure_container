"""
Index calculation service for resume similarity and keyword coverage analysis.
Following FHS architecture principles.
"""
import math
import re
import time
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.core.utils import stable_percentage_round
from src.services.embedding_client import get_azure_embedding_client
from src.services.text_processing import clean_html_text


def sigmoid_transform(x: float, x0: Optional[float] = None, k: Optional[float] = None) -> float:
    """
    Apply sigmoid transformation to similarity score.

    Args:
        x: Raw similarity score (0-1)
        x0: Sigmoid center point (default from config)
        k: Sigmoid steepness (default from config)

    Returns:
        Transformed score (0-1)
    """
    settings = get_settings()
    x0 = x0 or settings.sigmoid_x0
    k = k or settings.sigmoid_k

    try:
        return 1 / (1 + math.exp(-k * (x - x0)))
    except OverflowError:
        return 1.0 if x > x0 else 0.0


def analyze_keyword_coverage(
    resume_text: str,
    keywords: list[str] | str
) -> dict[str, int | list[str]]:
    """
    Analyze keyword coverage in resume text.

    Args:
        resume_text: Resume text (plain text or HTML)
        keywords: List of keywords or comma-separated string

    Returns:
        Dictionary containing:
        - total_keywords: Total number of keywords
        - covered_count: Number of keywords found
        - coverage_percentage: Coverage percentage (0-100)
        - covered_keywords: List of found keywords
        - missed_keywords: List of missing keywords
    """
    # Clean HTML if present
    resume_text = clean_html_text(resume_text)

    # Handle empty inputs
    if not keywords or not resume_text:
        return {
            "total_keywords": 0,
            "covered_count": 0,
            "coverage_percentage": 0,
            "covered_keywords": [],
            "missed_keywords": []
        }

    # Convert keywords to list if string
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    settings = get_settings()

    # Prepare resume text for matching
    resume_search_text = (
        resume_text.lower()
        if not settings.keyword_match_case_sensitive
        else resume_text
    )

    covered = []
    missed = []

    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword:
            continue

        # Prepare keyword for matching
        search_keyword = (
            keyword.lower()
            if not settings.keyword_match_case_sensitive
            else keyword
        )

        # Try exact word boundary match
        found = bool(re.search(rf'\b{re.escape(search_keyword)}\b', resume_search_text))

        # Try plural matching if enabled and not found
        if not found and settings.enable_plural_matching:
            # Check if keyword ends with 's' and try without it
            if search_keyword.endswith('s') and len(search_keyword) > 1:
                singular = search_keyword[:-1]
                found = bool(re.search(rf'\b{re.escape(singular)}\b', resume_search_text))
            # Or check if we can add 's' to match plural
            elif not search_keyword.endswith('s'):
                plural = search_keyword + 's'
                found = bool(re.search(rf'\b{re.escape(plural)}\b', resume_search_text))

        if found:
            covered.append(keyword)
        else:
            missed.append(keyword)

    # Calculate statistics
    total = len([k for k in keywords if k.strip()])
    covered_count = len(covered)
    # Use stable rounding for percentage calculation
    percentage = stable_percentage_round(covered_count / total) if total else 0

    return {
        "total_keywords": total,
        "covered_count": covered_count,
        "coverage_percentage": percentage,
        "covered_keywords": covered,
        "missed_keywords": missed
    }


async def compute_similarity(
    resume_text: str,
    job_description: str
) -> tuple[int, int]:
    """
    Compute similarity between resume and job description using embeddings.

    Args:
        resume_text: Resume text (plain text or HTML)
        job_description: Job description text (plain text or HTML)

    Returns:
        Tuple of (raw_similarity_percentage, transformed_similarity_percentage)
    """
    # Clean HTML if present
    resume_text = clean_html_text(resume_text)
    job_description = clean_html_text(job_description)

    # Check for empty texts
    if not resume_text or not job_description:
        return 0, 0

    # Get embedding client
    embedding_client = get_azure_embedding_client()

    try:
        # Create embeddings for both texts
        embedding_start = time.time()
        embeddings = await embedding_client.create_embeddings([resume_text, job_description])
        embedding_time = time.time() - embedding_start

        # Track embedding performance
        monitoring_service.track_event(
            "EmbeddingPerformance",
            {
                "operation": "index_calculation",
                "text_lengths": {
                    "resume": len(resume_text),
                    "job_description": len(job_description)
                },
                "processing_time_ms": round(embedding_time * 1000, 2),
                "embeddings_count": 2,
                "estimated_tokens": (len(resume_text) + len(job_description)) // 4  # Rough estimate
            }
        )

        if len(embeddings) != 2:
            raise ValueError(f"Expected 2 embeddings, got {len(embeddings)}")

        # Calculate cosine similarity
        resume_embedding = np.array(embeddings[0]).reshape(1, -1)
        job_embedding = np.array(embeddings[1]).reshape(1, -1)

        raw_similarity = float(cosine_similarity(resume_embedding, job_embedding)[0][0])

        # Debug logging for consistency issue
        monitoring_service.track_event(
            "IndexCalculationDebug",
            {
                "resume_length": len(resume_text),
                "job_desc_length": len(job_description),
                "raw_similarity": raw_similarity,
                "embedding_time_ms": round(embedding_time * 1000, 2),
                "resume_embedding_sample": str(resume_embedding[0][:5].tolist()),  # First 5 values
                "job_embedding_sample": str(job_embedding[0][:5].tolist())
            }
        )

        # Apply sigmoid transformation
        transformed_similarity = sigmoid_transform(raw_similarity)

        # Convert to percentages with detailed logging
        raw_similarity_percent = raw_similarity * 100
        transformed_similarity_percent = transformed_similarity * 100

        # Log exact values before rounding
        monitoring_service.track_event(
            "SimilarityRoundingDebug",
            {
                "raw_similarity_exact": raw_similarity,
                "raw_similarity_percent_exact": raw_similarity_percent,
                "transformed_similarity_exact": transformed_similarity,
                "transformed_similarity_percent_exact": transformed_similarity_percent,
                "will_round_raw_to": round(raw_similarity_percent),
                "will_round_transformed_to": round(transformed_similarity_percent)
            }
        )

        raw_percentage = stable_percentage_round(raw_similarity)
        transformed_percentage = stable_percentage_round(transformed_similarity)

        return raw_percentage, transformed_percentage

    finally:
        await embedding_client.close()


class IndexCalculationService:
    """Service class for index calculation operations."""

    def __init__(self):
        """Initialize the service."""
        self.settings = get_settings()

    async def calculate_index(
        self,
        resume: str,
        job_description: str,
        keywords: list[str] | str
    ) -> dict[str, int | dict]:
        """
        Calculate complete index including similarity and keyword coverage.

        Args:
            resume: Resume content (HTML or plain text)
            job_description: Job description (HTML or plain text)
            keywords: Keywords list or comma-separated string

        Returns:
            Dictionary containing:
            - raw_similarity_percentage: Raw cosine similarity (0-100)
            - similarity_percentage: Transformed similarity (0-100)
            - keyword_coverage: Keyword coverage analysis results
        """
        # Calculate similarity scores
        raw_similarity, transformed_similarity = await compute_similarity(
            resume,
            job_description
        )

        # Analyze keyword coverage
        keyword_coverage = analyze_keyword_coverage(resume, keywords)

        return {
            "raw_similarity_percentage": raw_similarity,
            "similarity_percentage": transformed_similarity,
            "keyword_coverage": keyword_coverage
        }
