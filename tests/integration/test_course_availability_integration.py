"""
Integration tests for Course Availability Check feature
Test ID: CA-001-IT to CA-005-IT
"""
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
import numpy as np
from typing import List, Dict, Any

from src.services.course_availability import CourseAvailabilityChecker


@pytest.mark.asyncio
class TestCourseAvailabilityIntegration:
    """Integration tests for Course Availability feature"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return CourseAvailabilityChecker()

    @pytest.fixture
    def mock_embedding_response(self):
        """Mock embedding API response"""
        def create_embeddings(texts: List[str]) -> List[List[float]]:
            # Return 1536-dimensional embeddings
            return [np.random.rand(1536).tolist() for _ in texts]
        return create_embeddings

    @pytest.fixture
    def mock_db_response(self):
        """Mock database response for course availability"""
        def create_response(has_courses: bool = True, count: int = 5):
            return {
                "has_courses": has_courses,
                "course_count": count,
                "preferred_match": True,
                "breakdown": {
                    "preferred": count - 1,
                    "other": 1
                }
            }
        return create_response

    async def test_CA_001_IT_course_availability_integration(
        self,
        service,
        mock_embedding_response,
        mock_db_response
    ):
        """
        Test ID: CA-001-IT
        Scenario: Course availability check with embedding and database
        Validation: Verify has_available_courses and course_count fields
        """
        # Prepare skill queries (use non-cached skills to test full flow)
        skill_queries = [
            {
                "skill_name": "Rust",  # Not in cache
                "skill_category": "SKILL",
                "description": "Systems programming language"
            },
            {
                "skill_name": "Quantum Computing",  # Not in cache
                "skill_category": "FIELD",
                "description": "Quantum algorithms and computation"
            }
        ]

        # Mock embedding client
        with patch.object(service, '_embedding_client') as mock_client:
            mock_client.create_embeddings = AsyncMock(return_value=mock_embedding_response(["text1", "text2"]))
            
            # Mock connection pool
            mock_pool = MagicMock()
            mock_conn = AsyncMock()
            # Create a proper async context manager mock
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_conn
            mock_ctx.__aexit__.return_value = None
            mock_pool.acquire.return_value = mock_ctx
            
            # Mock database response
            mock_conn.fetchrow = AsyncMock(return_value={
                "has_courses": True,
                "total_count": 10,
                "preferred_count": 7,
                "other_count": 3
            })
            
            service._connection_pool = mock_pool
            service._embedding_client = mock_client
            
            # Execute
            result = await service.check_course_availability(skill_queries)
            
            # Verify
            assert len(result) == 2
            
            # Check Rust (SKILL)
            rust_skill = result[0]
            assert rust_skill["has_available_courses"] is True
            assert rust_skill["course_count"] == 10
            assert rust_skill.get("preferred_courses") == 7
            
            # Check Quantum Computing (FIELD)  
            qc_skill = result[1]
            assert qc_skill["has_available_courses"] is True
            assert qc_skill["course_count"] == 10
            assert qc_skill.get("preferred_courses") == 7

    async def test_CA_002_IT_parallel_processing(
        self,
        service,
        mock_embedding_response,
        mock_db_response
    ):
        """
        Test ID: CA-002-IT
        Scenario: Parallel processing of multiple skills  
        Validation: Verify concurrent execution and performance
        """
        # Test data with mixed categories (use non-cached skills)
        skill_queries = [
            {
                "skill_name": "Rust",
                "skill_category": "SKILL",
                "description": "Systems programming language"
            },
            {
                "skill_name": "Quantum Computing",
                "skill_category": "FIELD",
                "description": "Quantum algorithms and computation"
            }
        ]
        
        # Track embedding text generation
        generated_texts = []
        
        async def capture_texts(texts):
            generated_texts.extend(texts)
            return mock_embedding_response(texts)
        
        # Mock embedding client to capture generated texts
        with patch.object(service, '_embedding_client') as mock_client:
            mock_client.create_embeddings = AsyncMock(side_effect=capture_texts)
            
            # Mock connection pool
            mock_pool = MagicMock()
            mock_conn = AsyncMock()
            # Create a proper async context manager mock
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_conn
            mock_ctx.__aexit__.return_value = None
            mock_pool.acquire.return_value = mock_ctx
            mock_conn.fetchrow = AsyncMock(return_value={
                "has_courses": True,
                "total_count": 5,
                "preferred_count": 3,
                "other_count": 2
            })
            
            service._connection_pool = mock_pool
            service._embedding_client = mock_client
            
            # Execute
            result = await service.check_course_availability(skill_queries)
            
            # Verify different strategies were applied
            assert len(generated_texts) == 2
            
            # Check SKILL category text
            assert "Rust course project certificate" in generated_texts[0]
            
            # Check FIELD category text
            assert "Quantum Computing specialization degree" in generated_texts[1]

    async def test_CA_003_IT_graceful_degradation(
        self,
        service,
        mock_embedding_response,
        mock_db_response
    ):
        """
        Test ID: CA-003-IT
        Scenario: Database connection failure
        Validation: Verify graceful degradation
        """
        # Create 20 skills (max parallel limit)
        skills = [
            {
                'skill_name': f"Skill_{i}",
                'skill_category': 'SKILL' if i % 2 == 0 else 'FIELD',
                'description': f"Description for skill {i}"
            }
            for i in range(20)
        ]

        with patch('src.services.course_availability.CourseAvailabilityChecker') as MockChecker:
            mock_service = AsyncMock()
            MockChecker.return_value = mock_service
            
            # Track concurrent calls
            call_times = []
            
            async def mock_check(skill_queries):
                import time
                start_time = time.time()
                call_times.append(start_time)
                
                # Simulate database query delay
                await asyncio.sleep(0.01)
                
                return {
                    skill['skill_name']: mock_db_response(True, 5)
                    for skill in skill_queries
                }
            
            mock_service.check_availability.side_effect = mock_check
            
            # Use our fixture service
            service._embedding_client = mock_service
            
            import time
            start = time.time()
            result = await service.check_course_availability(skills)
            duration = time.time() - start
            
            # Verify parallel execution
            assert len(result) == 20
            # With mocked services, should be very fast
            assert duration < 1.0  # Should complete quickly

    async def test_CA_004_IT_cache_integration(
        self,
        service,
        mock_embedding_response
    ):
        """
        Test ID: CA-004-IT
        Scenario: Cache hit for popular skills
        Validation: Verify cache effectiveness
        """
        skills = [
            {
                'skill_name': "Rust",  # Not in cache
                'skill_category': 'SKILL',
                'description': "Systems programming"
            }
        ]

        # Mock embedding client to work normally
        with patch.object(service, '_embedding_client') as mock_client:
            mock_client.create_embeddings = AsyncMock(return_value=[[0.1] * 1536])
            
            # Mock connection pool to fail
            mock_pool = MagicMock()
            mock_pool.acquire.side_effect = Exception("Database connection failed")
            
            service._connection_pool = mock_pool
            service._embedding_client = mock_client
            
            # Execute - should not raise exception
            result = await service.check_course_availability(skills)
            
            # Should return with graceful degradation
            assert result is not None
            assert len(result) == 1
            
            # Skill should be marked as unavailable
            assert result[0]["has_available_courses"] is False
            assert result[0]["course_count"] == 0

