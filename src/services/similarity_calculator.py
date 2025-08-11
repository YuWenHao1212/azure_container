"""
Similarity calculation service for comparing resume content before and after optimization.
"""

import re
from collections import Counter

from bs4 import BeautifulSoup


class SimilarityCalculator:
    """Calculate semantic similarity between job description and resume."""

    @staticmethod
    def calculate_similarity(
        job_description: str,
        resume_html: str,
        keywords: list[str] | None = None
    ) -> float:
        """
        Calculate similarity score between JD and resume.

        Uses a weighted approach:
        - 50% keyword overlap (Jaccard similarity)
        - 30% skill matching
        - 20% term frequency similarity (cosine similarity)

        Args:
            job_description: The job description text
            resume_html: The resume in HTML format
            keywords: Optional list of important keywords to weight higher

        Returns:
            Similarity score between 0-100
        """
        # Extract text from HTML
        if resume_html.strip().startswith('<'):
            soup = BeautifulSoup(resume_html, 'html.parser')
            resume_text = soup.get_text(separator=' ', strip=True)
        else:
            resume_text = resume_html

        # Normalize texts
        jd_normalized = SimilarityCalculator._normalize_text(job_description)
        resume_normalized = SimilarityCalculator._normalize_text(resume_text)

        # Calculate different similarity metrics
        keyword_score = SimilarityCalculator._keyword_overlap_score(
            jd_normalized, resume_normalized, keywords
        )

        skill_score = SimilarityCalculator._skill_matching_score(
            jd_normalized, resume_normalized
        )

        cosine_score = SimilarityCalculator._cosine_similarity(
            jd_normalized, resume_normalized
        )

        # Weighted average
        similarity = (
            keyword_score * 0.5 +
            skill_score * 0.3 +
            cosine_score * 0.2
        )

        # Return as percentage (0-100)
        return min(100, round(similarity * 100, 1))

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text

    @staticmethod
    def _keyword_overlap_score(
        jd_text: str,
        resume_text: str,
        important_keywords: list[str] | None = None
    ) -> float:
        """
        Calculate keyword overlap using Jaccard similarity.
        Important keywords are weighted 2x.
        """
        # Extract words
        jd_words = set(jd_text.split())
        resume_words = set(resume_text.split())

        # Calculate base intersection
        intersection = jd_words & resume_words
        union = jd_words | resume_words

        if not union:
            return 0.0

        # Weight important keywords
        if important_keywords:
            important_set = set(kw.lower() for kw in important_keywords)
            # Count important keywords in intersection as double
            important_found = intersection & important_set
            weighted_intersection_size = len(intersection) + len(important_found)
        else:
            weighted_intersection_size = len(intersection)

        # Jaccard similarity with weighting
        return weighted_intersection_size / len(union)

    @staticmethod
    def _skill_matching_score(jd_text: str, resume_text: str) -> float:
        """
        Match technical skills and tools.
        """
        # Common technical skills and tools
        tech_patterns = [
            r'\bpython\b', r'\bjava\b', r'\bjavascript\b', r'\btypescript\b',
            r'\breact\b', r'\bvue\b', r'\bangular\b', r'\bnode\b',
            r'\bdocker\b', r'\bkubernetes\b', r'\baws\b', r'\bazure\b',
            r'\bsql\b', r'\bmongodb\b', r'\bpostgresql\b', r'\bmysql\b',
            r'\bgit\b', r'\bci\W*cd\b', r'\bagile\b', r'\bscrum\b',
            r'\bmachine learning\b', r'\bdeep learning\b', r'\bai\b', r'\bml\b',
            r'\bapi\b', r'\brest\b', r'\bgraphql\b', r'\bmicroservices\b',
        ]

        jd_skills = set()
        resume_skills = set()

        for pattern in tech_patterns:
            if re.search(pattern, jd_text):
                jd_skills.add(pattern)
            if re.search(pattern, resume_text):
                resume_skills.add(pattern)

        if not jd_skills:
            return 1.0  # No skills required, perfect match

        # Calculate skill coverage
        matched_skills = jd_skills & resume_skills
        return len(matched_skills) / len(jd_skills)

    @staticmethod
    def _cosine_similarity(text1: str, text2: str) -> float:
        """
        Calculate cosine similarity based on term frequency.
        """
        # Create word frequency vectors
        words1 = text1.split()
        words2 = text2.split()

        # Get word counts
        counter1 = Counter(words1)
        counter2 = Counter(words2)

        # Get all unique words
        all_words = set(counter1.keys()) | set(counter2.keys())

        # Create vectors
        vec1 = [counter1.get(word, 0) for word in all_words]
        vec2 = [counter2.get(word, 0) for word in all_words]

        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def calculate_improvement(
        jd: str,
        original_resume: str,
        optimized_resume: str,
        keywords: list[str] | None = None
    ) -> tuple[float, float, float]:
        """
        Calculate similarity before and after optimization.

        Returns:
            Tuple of (before_score, after_score, improvement)
        """
        before = SimilarityCalculator.calculate_similarity(jd, original_resume, keywords)
        after = SimilarityCalculator.calculate_similarity(jd, optimized_resume, keywords)
        improvement = after - before

        return before, after, improvement
