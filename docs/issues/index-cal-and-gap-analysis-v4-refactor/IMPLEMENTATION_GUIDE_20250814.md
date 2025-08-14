# Implementation Guide - Resume Structure Integration V4

## Document Information
- **Version**: 4.0.0
- **Date**: 2025-08-14 18:20 CST
- **Author**: Claude Code + WenHao
- **Purpose**: Step-by-step implementation guide

## Implementation Checklist

### Phase 1: Service Implementation
- [ ] Create ResumeStructureAnalyzer service
- [ ] Add YAML prompt configuration
- [ ] Update LLM Factory configuration
- [ ] Implement retry mechanism
- [ ] Add fallback structure logic

### Phase 2: API Integration
- [ ] Update CombinedAnalysisServiceV2
- [ ] Modify API response models
- [ ] Add feature flag support
- [ ] Update API endpoint handler

### Phase 3: Testing
- [ ] Write 5 unit tests (RS-001-UT to RS-005-UT)
- [ ] Write 5 integration tests (RS-001-IT to RS-005-IT)
- [ ] Update test specifications
- [ ] Update pre-commit checks

### Phase 4: Documentation
- [ ] Update API documentation
- [ ] Add code comments with test IDs
- [ ] Update CLAUDE.md if needed
- [ ] Create release notes

## Step-by-Step Implementation

### Step 1: Create Prompt Configuration
**File**: `src/prompts/resume_structure_analyzer.yaml`

```yaml
system: |
  You are a Resume Structure Analyzer. Your role is to quickly identify the resume structure.
  
  ## Your Task
  Analyze the resume HTML and identify:
  1. Which sections exist and their actual titles
  2. Count basic statistics
  3. Note structural observations
  
  ## Output Format
  Return JSON with this exact structure:
  {
    "standard_sections": {
      "summary": "actual title or null",
      "skills": "actual title or null",
      "experience": "actual title or null",
      "education": "actual title or null",
      "certifications": "actual title or null",
      "projects": "actual title or null"
    },
    "custom_sections": ["section1", "section2"],
    "metadata": {
      "total_experience_entries": number,
      "total_education_entries": number,
      "has_quantified_achievements": boolean,
      "estimated_length": "1 page|2 pages|3+ pages"
    }
  }

user: |
  Analyze this resume structure:
  
  {resume_html}
  
  Provide structural analysis in the specified JSON format.
```

### Step 2: Create ResumeStructureAnalyzer Service
**File**: `src/services/resume_structure_analyzer.py`

```python
"""
Resume Structure Analyzer Service
Identifies resume sections using GPT-4.1 mini for fast processing.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.services.llm_factory import get_llm_client
from src.services.error_handler import UnifiedErrorHandler
from src.utils.prompt_loader import load_prompt_from_yaml

logger = logging.getLogger(__name__)
error_handler = UnifiedErrorHandler()


class StandardSections(BaseModel):
    """Standard resume section mappings."""
    summary: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    certifications: Optional[str] = None
    projects: Optional[str] = None


class StructureMetadata(BaseModel):
    """Resume structure metadata."""
    total_experience_entries: int = 0
    total_education_entries: int = 0
    has_quantified_achievements: bool = False
    estimated_length: str = "unknown"


class ResumeStructure(BaseModel):
    """Resume structure analysis result."""
    standard_sections: StandardSections
    custom_sections: list[str] = []
    metadata: StructureMetadata


class ResumeStructureAnalyzer:
    """
    Analyzes resume HTML to identify section structure.
    Uses GPT-4.1 mini for fast, lightweight processing.
    """
    
    def __init__(self):
        """Initialize with GPT-4.1 mini client."""
        self.llm_client = get_llm_client(api_name="resume_structure")
        self.max_retries = 3
        self.retry_delay = 0.5
        self.timeout = 3.0
        self.prompt_template = load_prompt_from_yaml(
            "resume_structure_analyzer.yaml"
        )
        logger.info("ResumeStructureAnalyzer initialized with GPT-4.1 mini")
    
    async def analyze_structure(
        self, 
        resume_html: str
    ) -> ResumeStructure:
        """
        Analyze resume structure with retry mechanism.
        
        Test IDs:
        - RS-001-UT: Basic structure analysis
        - RS-004-UT: Retry mechanism validation
        - RS-005-UT: Fallback structure generation
        
        Args:
            resume_html: Resume content in HTML format
            
        Returns:
            ResumeStructure with identified sections
        """
        for attempt in range(self.max_retries):
            try:
                # Test ID: RS-001-UT - Basic analysis
                result = await self._analyze_once(resume_html)
                logger.info(
                    f"Structure analysis succeeded on attempt {attempt + 1}"
                )
                return result
                
            except Exception as e:
                # Test ID: RS-004-UT - Retry logic
                logger.warning(
                    f"Structure analysis attempt {attempt + 1} failed: {e}"
                )
                
                if attempt == self.max_retries - 1:
                    # Test ID: RS-005-UT - Fallback activation
                    logger.error(
                        "All structure analysis attempts failed, using fallback"
                    )
                    return self._get_fallback_structure()
                
                await asyncio.sleep(self.retry_delay)
    
    async def _analyze_once(self, resume_html: str) -> ResumeStructure:
        """
        Single attempt at structure analysis.
        
        Test ID: RS-003-UT - JSON parsing validation
        """
        start_time = time.time()
        
        try:
            # Prepare prompt
            user_prompt = self.prompt_template["user"].format(
                resume_html=resume_html[:10000]  # Limit input size
            )
            
            messages = [
                {"role": "system", "content": self.prompt_template["system"]},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call LLM with timeout
            response = await asyncio.wait_for(
                self.llm_client.chat_completion(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1000,
                    top_p=0.1
                ),
                timeout=self.timeout
            )
            
            # Parse response
            content = response["choices"][0]["message"]["content"]
            
            # Clean JSON if needed
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # Test ID: RS-003-UT - Parse and validate
            data = json.loads(content.strip())
            
            # Convert to model
            structure = ResumeStructure(
                standard_sections=StandardSections(**data.get("standard_sections", {})),
                custom_sections=data.get("custom_sections", []),
                metadata=StructureMetadata(**data.get("metadata", {}))
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Structure analysis completed in {duration_ms}ms")
            
            return structure
            
        except json.JSONDecodeError as e:
            error_handler.log_error(
                error_type="STRUCTURE_PARSE_ERROR",
                error_message=f"Failed to parse structure JSON: {e}",
                context={"response_preview": content[:500] if 'content' in locals() else None}
            )
            raise
            
        except asyncio.TimeoutError:
            error_handler.log_error(
                error_type="STRUCTURE_TIMEOUT",
                error_message=f"Structure analysis timed out after {self.timeout}s",
                context={"resume_length": len(resume_html)}
            )
            raise
            
        except Exception as e:
            error_handler.log_error(
                error_type="STRUCTURE_ANALYSIS_ERROR",
                error_message=str(e),
                context={"attempt_duration_ms": int((time.time() - start_time) * 1000)}
            )
            raise
    
    def _get_fallback_structure(self) -> ResumeStructure:
        """
        Return basic structure when analysis fails.
        
        Test ID: RS-005-UT - Fallback structure validation
        """
        return ResumeStructure(
            standard_sections=StandardSections(
                summary="Professional Summary",
                skills="Skills",
                experience="Experience",
                education="Education",
                certifications=None,
                projects=None
            ),
            custom_sections=[],
            metadata=StructureMetadata(
                total_experience_entries=0,
                total_education_entries=0,
                has_quantified_achievements=False,
                estimated_length="unknown"
            )
        )
```

### Step 3: Update LLM Factory
**File**: `src/services/llm_factory.py` (Add configuration)

```python
# Add to API_CONFIG dictionary
"resume_structure": {
    "model": "gpt-4.1-mini",  # Fast, lightweight model
    "deployment": "gpt-4-1-mini-japaneast",
    "temperature": 0.3,
    "max_tokens": 1000,
    "top_p": 0.1,
    "timeout": 3.0,
    "description": "Resume structure analysis"
}
```

### Step 4: Update CombinedAnalysisServiceV2
**File**: `src/services/combined_analysis_v2.py` (Modifications)

```python
# Add import
from src.services.resume_structure_analyzer import (
    ResumeStructureAnalyzer,
    ResumeStructure
)

# Add to __init__
self.structure_analyzer = ResumeStructureAnalyzer()
self.enable_structure_analysis = os.getenv(
    "ENABLE_RESUME_STRUCTURE_ANALYSIS", "true"
).lower() == "true"

# Modify analyze_combined_v2 method
async def analyze_combined_v2(self, ...):
    """
    Test IDs:
    - RS-001-IT: Parallel execution timing
    - RS-003-IT: Error handling flow
    """
    # Create parallel tasks
    keyword_task = asyncio.create_task(...)
    embedding_task = asyncio.create_task(...)
    
    # NEW: Add structure analysis task
    structure_task = None
    if self.enable_structure_analysis:
        # Test ID: RS-001-IT - Parallel execution
        structure_task = asyncio.create_task(
            self.structure_analyzer.analyze_structure(resume_html)
        )
    
    # ... existing code ...
    
    # Get structure result
    resume_structure = None
    if structure_task:
        try:
            # Test ID: RS-003-IT - Error handling
            resume_structure = await asyncio.wait_for(
                structure_task,
                timeout=3.0
            )
        except Exception as e:
            logger.warning(f"Structure analysis failed: {e}")
            resume_structure = self.structure_analyzer._get_fallback_structure()
    
    # Add to result
    if resume_structure:
        result["resume_structure"] = resume_structure.dict()
```

### Step 5: Update API Response Models
**File**: `src/api/v1/models/index_cal_gap_analysis.py`

```python
# Add new response field
class IndexCalGapAnalysisResponse(BaseModel):
    """
    Test ID: RS-002-IT - API response format validation
    """
    index_score: float
    gap_analysis: Dict[str, Any]
    keywords: Dict[str, Any]
    resume_structure: Optional[Dict[str, Any]] = None  # NEW field
```

### Step 6: Create Unit Tests
**File**: `test/unit/test_resume_structure_analyzer.py`

```python
"""
Unit tests for Resume Structure Analyzer
Test IDs: RS-001-UT to RS-005-UT
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.services.resume_structure_analyzer import (
    ResumeStructureAnalyzer,
    ResumeStructure,
    StandardSections
)


class TestResumeStructureAnalyzer:
    """Unit tests for resume structure analysis."""
    
    @pytest.mark.asyncio
    async def test_RS_001_UT_basic_structure_analysis(self):
        """Test ID: RS-001-UT - Basic structure analysis."""
        analyzer = ResumeStructureAnalyzer()
        
        # Mock LLM response
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "standard_sections": {
                            "summary": "Professional Summary",
                            "experience": "Work Experience"
                        },
                        "custom_sections": ["Languages"],
                        "metadata": {
                            "total_experience_entries": 3,
                            "total_education_entries": 1,
                            "has_quantified_achievements": True,
                            "estimated_length": "2 pages"
                        }
                    })
                }
            }]
        }
        
        with patch.object(analyzer.llm_client, 'chat_completion', 
                         return_value=mock_response):
            result = await analyzer.analyze_structure("<html>Resume</html>")
            
            assert isinstance(result, ResumeStructure)
            assert result.standard_sections.summary == "Professional Summary"
            assert len(result.custom_sections) == 1
    
    @pytest.mark.asyncio  
    async def test_RS_002_UT_prompt_template_validation(self):
        """Test ID: RS-002-UT - Prompt template validation."""
        analyzer = ResumeStructureAnalyzer()
        
        assert "system" in analyzer.prompt_template
        assert "user" in analyzer.prompt_template
        assert "{resume_html}" in analyzer.prompt_template["user"]
    
    @pytest.mark.asyncio
    async def test_RS_003_UT_json_parsing_validation(self):
        """Test ID: RS-003-UT - JSON parsing and validation."""
        analyzer = ResumeStructureAnalyzer()
        
        # Test with malformed JSON
        mock_response = {
            "choices": [{
                "message": {"content": "```json\n{invalid json}```"}
            }]
        }
        
        with patch.object(analyzer.llm_client, 'chat_completion',
                         return_value=mock_response):
            with pytest.raises(json.JSONDecodeError):
                await analyzer._analyze_once("<html>Resume</html>")
    
    @pytest.mark.asyncio
    async def test_RS_004_UT_retry_mechanism(self):
        """Test ID: RS-004-UT - Retry mechanism validation."""
        analyzer = ResumeStructureAnalyzer()
        analyzer.retry_delay = 0.01  # Speed up test
        
        # Mock to fail twice, succeed on third
        call_count = 0
        async def mock_analyze(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return ResumeStructure(
                standard_sections=StandardSections(),
                custom_sections=[],
                metadata=StructureMetadata()
            )
        
        with patch.object(analyzer, '_analyze_once', side_effect=mock_analyze):
            result = await analyzer.analyze_structure("<html>Resume</html>")
            
            assert call_count == 3
            assert isinstance(result, ResumeStructure)
    
    @pytest.mark.asyncio
    async def test_RS_005_UT_fallback_structure_generation(self):
        """Test ID: RS-005-UT - Fallback structure generation."""
        analyzer = ResumeStructureAnalyzer()
        analyzer.retry_delay = 0.01
        
        # Mock to always fail
        with patch.object(analyzer, '_analyze_once',
                         side_effect=Exception("Permanent failure")):
            result = await analyzer.analyze_structure("<html>Resume</html>")
            
            assert isinstance(result, ResumeStructure)
            assert result.standard_sections.summary == "Professional Summary"
            assert result.metadata.estimated_length == "unknown"
```

### Step 7: Create Integration Tests
**File**: `test/integration/test_resume_structure_integration.py`

```python
"""
Integration tests for Resume Structure in API
Test IDs: RS-001-IT to RS-005-IT
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import time

from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2


class TestResumeStructureIntegration:
    """Integration tests for resume structure feature."""
    
    @pytest.mark.asyncio
    async def test_RS_001_IT_parallel_execution_timing(self):
        """Test ID: RS-001-IT - Verify parallel execution timing."""
        service = CombinedAnalysisServiceV2()
        
        # Mock all services with different delays
        async def mock_keywords(*args):
            await asyncio.sleep(0.05)
            return {"keywords": []}
        
        async def mock_embeddings(*args):
            await asyncio.sleep(0.5)
            return {"embeddings": []}
        
        async def mock_structure(*args):
            await asyncio.sleep(2.0)  # Longest task
            return Mock(dict=lambda: {"sections": {}})
        
        with patch.multiple(service,
                          extract_keywords=mock_keywords,
                          generate_embeddings=mock_embeddings):
            with patch.object(service.structure_analyzer, 
                            'analyze_structure', mock_structure):
                
                start = time.time()
                result = await service.analyze_combined_v2(
                    resume_html="<html></html>",
                    job_description="JD"
                )
                duration = time.time() - start
                
                # Should complete in ~2s (structure time), not 2.55s (sum)
                assert duration < 2.5
                assert "resume_structure" in result
    
    @pytest.mark.asyncio
    async def test_RS_002_IT_api_response_format(self):
        """Test ID: RS-002-IT - Validate API response format."""
        from src.api.v1.models.index_cal_gap_analysis import (
            IndexCalGapAnalysisResponse
        )
        
        response_data = {
            "index_score": 0.85,
            "gap_analysis": {"gaps": []},
            "keywords": {"covered": [], "missing": []},
            "resume_structure": {
                "standard_sections": {
                    "summary": "Professional Summary",
                    "skills": None
                },
                "custom_sections": ["Languages"],
                "metadata": {
                    "total_experience_entries": 3,
                    "total_education_entries": 1,
                    "has_quantified_achievements": True,
                    "estimated_length": "2 pages"
                }
            }
        }
        
        # Should validate without errors
        response = IndexCalGapAnalysisResponse(**response_data)
        assert response.resume_structure is not None
        assert response.resume_structure["standard_sections"]["summary"] == "Professional Summary"
    
    @pytest.mark.asyncio
    async def test_RS_003_IT_error_handling_flow(self):
        """Test ID: RS-003-IT - Error handling and fallback."""
        service = CombinedAnalysisServiceV2()
        
        # Mock structure analyzer to fail
        with patch.object(service.structure_analyzer, 'analyze_structure',
                         side_effect=Exception("LLM Error")):
            
            result = await service.analyze_combined_v2(
                resume_html="<html></html>",
                job_description="JD"
            )
            
            # Should have fallback structure
            assert "resume_structure" in result
            structure = result["resume_structure"]
            assert structure["metadata"]["estimated_length"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_RS_004_IT_feature_flag_behavior(self):
        """Test ID: RS-004-IT - Feature flag enable/disable."""
        service = CombinedAnalysisServiceV2()
        
        # Test with feature disabled
        with patch.dict('os.environ', 
                       {'ENABLE_RESUME_STRUCTURE_ANALYSIS': 'false'}):
            service.__init__()  # Reinitialize with new env
            
            result = await service.analyze_combined_v2(
                resume_html="<html></html>",
                job_description="JD"
            )
            
            assert "resume_structure" not in result
        
        # Test with feature enabled
        with patch.dict('os.environ',
                       {'ENABLE_RESUME_STRUCTURE_ANALYSIS': 'true'}):
            service.__init__()
            
            with patch.object(service.structure_analyzer, 'analyze_structure',
                            return_value=Mock(dict=lambda: {"sections": {}})):
                result = await service.analyze_combined_v2(
                    resume_html="<html></html>",
                    job_description="JD"
                )
                
                assert "resume_structure" in result
    
    @pytest.mark.asyncio
    async def test_RS_005_IT_end_to_end_with_mocks(self):
        """Test ID: RS-005-IT - Complete flow with mock services."""
        service = CombinedAnalysisServiceV2()
        
        # Mock all external services
        mock_structure = Mock(dict=lambda: {
            "standard_sections": {
                "summary": "Executive Summary",
                "experience": "Professional Experience"
            },
            "custom_sections": ["Publications"],
            "metadata": {
                "total_experience_entries": 5,
                "total_education_entries": 2,
                "has_quantified_achievements": True,
                "estimated_length": "3+ pages"
            }
        })
        
        with patch.object(service.structure_analyzer, 'analyze_structure',
                         return_value=mock_structure):
            
            result = await service.analyze_combined_v2(
                resume_html="<html>Full Resume</html>",
                job_description="Senior Engineer Role"
            )
            
            # Verify complete response
            assert result["resume_structure"]["standard_sections"]["summary"] == "Executive Summary"
            assert "Publications" in result["resume_structure"]["custom_sections"]
            assert result["resume_structure"]["metadata"]["total_experience_entries"] == 5
```

### Step 8: Update Test Specifications
**File**: `docs/issues/index-cal-and-gap-analysis-refactor/test-spec-index-cal-gap-analysis.md`

Add the following section:

```markdown
## Resume Structure Analysis Tests (V4)

### Unit Tests (RS-xxx-UT)

| Test ID | Test Name | Description | Priority |
|---------|-----------|-------------|----------|
| RS-001-UT | Basic Structure Analysis | Verify resume structure identification | P0 |
| RS-002-UT | Prompt Template Validation | Validate prompt configuration | P1 |
| RS-003-UT | JSON Parsing Validation | Test JSON parsing and error handling | P0 |
| RS-004-UT | Retry Mechanism | Verify 3-attempt retry logic | P0 |
| RS-005-UT | Fallback Structure | Test fallback structure generation | P0 |

### Integration Tests (RS-xxx-IT)

| Test ID | Test Name | Description | Priority |
|---------|-----------|-------------|----------|
| RS-001-IT | Parallel Execution Timing | Verify parallel task execution | P0 |
| RS-002-IT | API Response Format | Validate response structure | P0 |
| RS-003-IT | Error Handling Flow | Test error recovery and fallback | P0 |
| RS-004-IT | Feature Flag Behavior | Test enable/disable functionality | P1 |
| RS-005-IT | End-to-End Mock Flow | Complete flow with mock services | P0 |
```

### Step 9: Update Pre-commit Check
**File**: `test/pre_commit_check_advanced.py`

Add test IDs to the registry:

```python
# Add to TEST_ID_REGISTRY
"RS-001-UT": "test_RS_001_UT_basic_structure_analysis",
"RS-002-UT": "test_RS_002_UT_prompt_template_validation",
"RS-003-UT": "test_RS_003_UT_json_parsing_validation",
"RS-004-UT": "test_RS_004_UT_retry_mechanism",
"RS-005-UT": "test_RS_005_UT_fallback_structure_generation",
"RS-001-IT": "test_RS_001_IT_parallel_execution_timing",
"RS-002-IT": "test_RS_002_IT_api_response_format",
"RS-003-IT": "test_RS_003_IT_error_handling_flow",
"RS-004-IT": "test_RS_004_IT_feature_flag_behavior",
"RS-005-IT": "test_RS_005_IT_end_to_end_with_mocks",
```

## Testing Commands

### Run Unit Tests
```bash
pytest test/unit/test_resume_structure_analyzer.py -v
```

### Run Integration Tests
```bash
pytest test/integration/test_resume_structure_integration.py -v
```

### Run Specific Test
```bash
pytest test/unit/test_resume_structure_analyzer.py::TestResumeStructureAnalyzer::test_RS_001_UT_basic_structure_analysis -v
```

### Run with Coverage
```bash
pytest test/unit/test_resume_structure_analyzer.py --cov=src.services.resume_structure_analyzer --cov-report=term-missing
```

## Deployment Checklist

### Pre-deployment
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Performance validated

### Deployment Steps
1. Set environment variable: `ENABLE_RESUME_STRUCTURE_ANALYSIS=true`
2. Deploy to staging environment
3. Run smoke tests
4. Monitor metrics for 30 minutes
5. Deploy to production

### Post-deployment
- [ ] Verify feature flag working
- [ ] Check error rates
- [ ] Monitor response times
- [ ] Validate structure quality

## Troubleshooting Guide

### Common Issues

#### 1. Structure Analysis Timeout
**Symptom**: Timeout errors in logs
**Solution**: Increase `STRUCTURE_ANALYSIS_TIMEOUT` or optimize prompt

#### 2. High Fallback Rate
**Symptom**: >5% fallback activation
**Solution**: Check LLM availability, review prompt effectiveness

#### 3. Slow Response Times
**Symptom**: Structure analysis >3s
**Solution**: Ensure GPT-4.1 mini deployment, check token limits

#### 4. JSON Parsing Failures
**Symptom**: Parse errors in logs
**Solution**: Review prompt format requirements, add validation

## Performance Benchmarks

### Expected Performance
- **P50 Duration**: <1500ms
- **P95 Duration**: <2500ms
- **P99 Duration**: <3000ms
- **Success Rate**: >95%
- **Fallback Rate**: <5%

### Monitoring Queries
```sql
-- Success rate
SELECT 
    COUNT(CASE WHEN success = true THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM structure_analysis_logs
WHERE timestamp > NOW() - INTERVAL '1 hour';

-- Performance percentiles
SELECT
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99
FROM structure_analysis_logs
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

## Conclusion

This implementation guide provides a complete roadmap for integrating resume structure analysis into the index-cal-gap-analysis API with comprehensive testing and monitoring.