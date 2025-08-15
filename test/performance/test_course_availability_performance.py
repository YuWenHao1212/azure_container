"""
Performance tests for Course Availability Check feature
Test ID: CA-001-PT (6-skill performance test with 20 iterations)
"""
import asyncio
import json
import os
import statistics
import time
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.course_availability import CourseAvailabilityChecker


class TestCourseAvailabilityPerformance:
    """Performance tests for Course Availability feature"""

    def _generate_embedding_text(self, skill_query: dict[str, Any]) -> str:
        """
        Generate optimized embedding text based on skill category
        (Same logic as in CourseAvailabilityChecker)
        """
        skill_name = skill_query.get('skill_name', '')
        description = skill_query.get('description', '')
        category = skill_query.get('skill_category', 'DEFAULT')

        if category == "SKILL":
            # For technical skills: emphasize course, project, certificate
            return f"{skill_name} course tutorial project certificate hands-on {description}"
        elif category == "FIELD":
            # For fields: emphasize specialization, degree, track
            return f"{skill_name} specialization degree track curriculum pathway {description}"
        else:
            # Default: balanced approach
            return f"{skill_name} learning {description}"

    class PerformanceTracker:
        """Track detailed performance metrics"""
        def __init__(self):
            self.metrics = {
                "cache_check": [],
                "embedding_generation": [],
                "db_queries": [],
                "total_time": []
            }
            self.current_times = {}

        def start_phase(self, phase: str):
            """Start timing a phase"""
            self.current_times[phase] = time.time()

        def end_phase(self, phase: str):
            """End timing a phase"""
            if phase in self.current_times:
                duration = (time.time() - self.current_times[phase]) * 1000
                if phase not in self.metrics:
                    self.metrics[phase] = []
                self.metrics[phase].append(duration)
                del self.current_times[phase]
                return duration
            return 0

        def get_summary(self) -> dict:
            """Get performance summary"""
            summary = {}
            for phase, times in self.metrics.items():
                if times:
                    summary[phase] = {
                        "p50": statistics.median(times) if len(times) > 1 else times[0],
                        "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                        "avg": statistics.mean(times),
                        "min": min(times),
                        "max": max(times)
                    }
            return summary

    @pytest.fixture
    def checker(self):
        """Create CourseAvailabilityChecker instance"""
        return CourseAvailabilityChecker()


    @pytest.mark.asyncio
    async def test_CA_001_PT_performance(
        self,
        checker
    ):
        """
        Test ID: CA-001-PT
        Scenario: 6-skill performance test with configurable iterations
        Validation: Measure actual performance with P50/P95 metrics using cache avoidance
        Priority: P0
        Note: Requires real Azure API keys and PostgreSQL connection
        """
        import random
        import string

        # Performance Tests always use real API (no environment variable check needed)

        # Initialize with real connections
        await checker.initialize()

        # Get iterations count from environment (default 20, can set to 100 for detailed analysis)
        iterations_count = int(os.getenv("PERFORMANCE_ITERATIONS", "20"))

        print("\n" + "="*80)
        print(f"🚀 Course Availability Performance Test (6 skills, {iterations_count} iterations)")
        print("="*80)
        print("⚠️  Using real Azure Embedding API and PostgreSQL")
        print("🔄 Using randomized skills to minimize cache interference")

        response_times = []
        detailed_results = []

        # Base skill templates for generating unique variations
        skill_templates = [
            # Technical skills
            {"base_name": "Python", "variations": ["Python 3", "Python Development", "Python Programming", "Python Coding", "Advanced Python"], "category": "SKILL", "description": "Programming language"},
            {"base_name": "JavaScript", "variations": ["JavaScript ES6", "Modern JavaScript", "JavaScript Development", "JS Programming", "Frontend JavaScript"], "category": "SKILL", "description": "Web programming"},
            {"base_name": "Docker", "variations": ["Docker Containers", "Docker Deployment", "Docker Orchestration", "Container Docker", "Docker Technology"], "category": "SKILL", "description": "Container technology"},
            {"base_name": "React", "variations": ["React.js", "React Development", "React Framework", "Modern React", "React Components"], "category": "SKILL", "description": "Frontend framework"},
            {"base_name": "Node.js", "variations": ["Node.js Backend", "Server Node.js", "Node.js Development", "Backend Node", "Node.js Runtime"], "category": "SKILL", "description": "Backend runtime"},
            {"base_name": "TypeScript", "variations": ["TypeScript Development", "Typed JavaScript", "TypeScript Programming", "Advanced TypeScript", "TS Development"], "category": "SKILL", "description": "Typed JavaScript"},

            # Field skills
            {"base_name": "Machine Learning", "variations": ["ML Engineering", "Applied Machine Learning", "ML Development", "Machine Learning Systems", "ML Algorithms"], "category": "FIELD", "description": "AI and ML"},
            {"base_name": "Data Science", "variations": ["Applied Data Science", "Data Analytics", "Data Science Engineering", "Statistical Data Science", "Data Science Methods"], "category": "FIELD", "description": "Data analysis"},
            {"base_name": "Cloud Computing", "variations": ["Cloud Architecture", "Cloud Engineering", "Cloud Solutions", "Cloud Infrastructure", "Cloud Development"], "category": "FIELD", "description": "Cloud services"},
            {"base_name": "Cybersecurity", "variations": ["Information Security", "Security Engineering", "Cyber Defense", "Security Architecture", "Security Operations"], "category": "FIELD", "description": "Information security"},
            {"base_name": "DevOps", "variations": ["DevOps Engineering", "DevOps Practices", "CI/CD DevOps", "DevOps Automation", "Platform Engineering"], "category": "FIELD", "description": "Development operations"},
            {"base_name": "Artificial Intelligence", "variations": ["AI Engineering", "Applied AI", "AI Development", "AI Systems", "AI Solutions"], "category": "FIELD", "description": "AI technologies"}
        ]

        print(f"   Running {iterations_count} iterations with randomized skill variations")

        # Run iterations with randomized skill variations
        for iteration in range(iterations_count):
            # Generate 6 unique skills for this iteration (3 SKILL + 3 FIELD)
            skill_templates_copy = skill_templates.copy()
            random.shuffle(skill_templates_copy)

            # Select 3 SKILL and 3 FIELD skills
            selected_skills = []
            skill_count = field_count = 0

            for template in skill_templates_copy:
                if len(selected_skills) >= 6:
                    break

                if template["category"] == "SKILL" and skill_count < 3:
                    # Pick a random variation for this skill
                    skill_name = random.choice(template["variations"])  # noqa: S311
                    # Add small random suffix to ensure uniqueness
                    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=2))  # noqa: S311
                    unique_skill_name = f"{skill_name} {random_suffix}"

                    selected_skills.append({
                        "skill_name": unique_skill_name,
                        "skill_category": "SKILL",
                        "description": f"{template['description']} (variation {iteration+1})"
                    })
                    skill_count += 1

                elif template["category"] == "FIELD" and field_count < 3:
                    # Pick a random variation for this field
                    skill_name = random.choice(template["variations"])  # noqa: S311
                    # Add small random suffix to ensure uniqueness
                    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=2))  # noqa: S311
                    unique_skill_name = f"{skill_name} {random_suffix}"

                    selected_skills.append({
                        "skill_name": unique_skill_name,
                        "skill_category": "FIELD",
                        "description": f"{template['description']} (variation {iteration+1})"
                    })
                    field_count += 1

            # Ensure we have exactly 6 skills
            if len(selected_skills) != 6:
                # Fill remaining slots with completely random skills
                while len(selected_skills) < 6:
                    category = "SKILL" if len([s for s in selected_skills if s["skill_category"] == "SKILL"]) < 3 else "FIELD"
                    random_name = f"RandomSkill_{iteration}_{len(selected_skills)}_{''.join(random.choices(string.ascii_lowercase, k=4))}"  # noqa: S311
                    selected_skills.append({
                        "skill_name": random_name,
                        "skill_category": category,
                        "description": f"Generated random skill for cache avoidance (iteration {iteration+1})"
                    })

            start_time = time.time()
            result = await checker.check_course_availability(selected_skills)
            total_time = (time.time() - start_time) * 1000
            response_times.append(total_time)

            # Record iteration result with enhanced details
            iteration_result = {
                "iteration": iteration + 1,
                "total_time_ms": total_time,
                "timestamp": datetime.now().isoformat(),
                "cache_avoidance_strategy": "Randomized skill variations with unique suffixes",
                "results": []
            }

            # Add detailed skill information
            for i, skill in enumerate(result):
                original_skill = selected_skills[i]
                skill_result = {
                    "skill": skill["skill_name"],
                    "category": skill.get("skill_category", "SKILL"),
                    "description": original_skill.get("description", ""),
                    "has_courses": skill.get("has_available_courses", False),
                    "count": skill.get("course_count", 0),
                    "embedding_text": self._generate_embedding_text(original_skill)
                }
                iteration_result["results"].append(skill_result)
            detailed_results.append(iteration_result)

            # Verify correctness
            assert len(result) == 6, f"Expected 6 results, got {len(result)}"
            assert all("has_available_courses" in skill for skill in result)

            # Progress indicator (adaptive based on iteration count)
            progress_interval = max(5, iterations_count // 10)  # Show progress every 10% or minimum every 5 iterations
            if (iteration + 1) % progress_interval == 0:
                print(f"  Completed {iteration + 1}/{iterations_count} iterations... (randomized cache avoidance)")

            # Small delay between iterations to avoid rate limiting
            if iteration < iterations_count - 1:
                await asyncio.sleep(0.1)  # Reduced delay for randomized skills

        # Calculate statistics
        p50 = statistics.median(response_times)
        p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
        avg = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        min_time = min(response_times)
        max_time = max(response_times)

        # Print results
        print(f"\n📊 Performance Results ({iterations_count} iterations with randomized cache avoidance):")
        print(f"  📈 P50: {p50:.1f}ms")
        print(f"  📈 P95: {p95:.1f}ms")
        print(f"  📊 Average: {avg:.1f}ms (±{std_dev:.1f}ms)")
        print(f"  ⬇️  Min: {min_time:.1f}ms")
        print(f"  ⬆️  Max: {max_time:.1f}ms")

        # Analyze cache effectiveness
        consistent_responses = sum(1 for times in [response_times[i:i+5] for i in range(0, len(response_times), 5)]
                                 if len(times) == 5 and max(times) - min(times) < 50)  # Within 50ms variation
        cache_effectiveness = (consistent_responses * 5 / len(response_times)) * 100 if response_times else 0

        print(f"  🎯 Cache effectiveness: {cache_effectiveness:.1f}% (lower is better for true performance testing)")

        # Generate detailed performance report
        report = {
            "test_name": "Course Availability Performance Test (6 skills)",
            "test_id": "CA-001-PT",
            "timestamp": datetime.now().isoformat(),
            "api_type": "REAL",
            "configuration": {
                "skill_count": 6,
                "iterations": iterations_count,
                "skill_mix": "3 SKILL + 3 FIELD per iteration",
                "cache_avoidance": "Randomized skill variations with unique suffixes",
                "cache_effectiveness_percent": cache_effectiveness
            },
            "statistics": {
                "p50_ms": p50,
                "p95_ms": p95,
                "avg_ms": avg,
                "std_dev_ms": std_dev,
                "min_ms": min_time,
                "max_ms": max_time
            },
            "iterations": detailed_results
        }

        # Save detailed JSON report
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f"test/logs/performance_CA-001-PT_{timestamp_str}.json"
        os.makedirs("test/logs", exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📝 Detailed report saved to: {report_path}")

        # Performance assertions (adjusted for real uncached API performance)
        # With effective cache avoidance, we expect higher and more variable response times
        assert p50 < 2000, f"P50 ({p50:.1f}ms) exceeds 2000ms target (adjusted for uncached performance)"
        assert p95 < 5000, f"P95 ({p95:.1f}ms) exceeds 5000ms target (adjusted for uncached performance)"

        if cache_effectiveness < 20:  # Less than 20% cache hits indicates good cache avoidance
            print("✅ Effective cache avoidance achieved - measuring true uncached performance")
        else:
            print(f"⚠️  High cache effectiveness ({cache_effectiveness:.1f}%) - some cache influence still present")

        print("✅ Real API performance test completed with cache avoidance")


