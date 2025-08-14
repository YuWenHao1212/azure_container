# Architecture Design - Resume Structure Integration V4

## Document Information
- **Version**: 4.0.0
- **Date**: 2025-08-14 18:20 CST
- **Author**: Claude Code + WenHao
- **Component**: Index-Cal-Gap-Analysis API Enhancement

## System Architecture

### Component Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    API Endpoint Layer                        │
│            /api/v1/index-cal-and-gap-analysis               │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│             CombinedAnalysisServiceV2                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Parallel Execution Group                 │   │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐ │   │
│  │  │  Keywords  │ │ Embeddings │ │Resume Structure  │ │   │
│  │  │   (50ms)   │ │   (500ms)  │ │    (2000ms)      │ │   │
│  │  └────────────┘ └────────────┘ └──────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                             │                                │
│  ┌──────────────────────────▼────────────────────────────┐  │
│  │            Index Calculation (300ms)                  │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                                │
│  ┌──────────────────────────▼────────────────────────────┐  │
│  │           Gap Analysis (6000-8000ms)                  │  │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │ResumeStructure   │  │      LLM Factory                │  │
│  │   Analyzer       │──│  - GPT-4.1 mini (structure)    │  │
│  └──────────────────┘  │  - GPT-4.1 (gap analysis)      │  │
│                        └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

### Request Flow
```
1. Client Request
   ├── Resume (HTML)
   ├── Job Description
   └── Options

2. Parallel Processing (T=0ms)
   ├── Keyword Extraction ──────→ Keywords (T=50ms)
   ├── Embedding Generation ────→ Embeddings (T=500ms)
   └── Structure Analysis ──────→ Structure (T=2000ms)

3. Sequential Processing
   └── Embeddings Complete (T=500ms)
       └── Index Calculation ────→ Index Score (T=800ms)
           └── Gap Analysis ─────→ Gap Results (T=8800ms)

4. Response Assembly
   ├── Index Score
   ├── Gap Analysis
   ├── Keywords
   └── Resume Structure (NEW)
```

## Class Design

### ResumeStructureAnalyzer Service
```python
class ResumeStructureAnalyzer:
    """
    Analyzes resume HTML to identify section structure.
    Uses GPT-4.1 mini for fast, lightweight processing.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client(api_name="resume_structure")
        self.max_retries = 3
        self.retry_delay = 0.5
        self.timeout = 3.0
    
    async def analyze_structure(
        self, 
        resume_html: str
    ) -> ResumeStructure:
        """
        Identify resume sections with retry mechanism.
        
        Returns:
            ResumeStructure with sections and metadata
        """
```

### Data Models
```python
class ResumeStructure(BaseModel):
    """Resume structure analysis result."""
    standard_sections: StandardSections
    custom_sections: List[str]
    metadata: StructureMetadata
    
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
    total_experience_entries: int
    total_education_entries: int
    has_quantified_achievements: bool
    estimated_length: str
```

## Integration Points

### 1. CombinedAnalysisServiceV2 Modification
```python
async def analyze_combined_v2(self, ...) -> dict:
    # Existing parallel tasks
    keyword_task = asyncio.create_task(...)
    embedding_task = asyncio.create_task(...)
    
    # NEW: Add structure analysis task
    structure_task = None
    if self.enable_structure_analysis:
        structure_task = asyncio.create_task(
            self.structure_analyzer.analyze_structure(resume_html)
        )
    
    # Wait for embeddings (required for index calculation)
    embeddings = await embedding_task
    
    # Get structure result if enabled
    structure = None
    if structure_task:
        try:
            structure = await asyncio.wait_for(
                structure_task, 
                timeout=3.0
            )
        except (asyncio.TimeoutError, Exception):
            structure = self._get_fallback_structure()
```

### 2. API Endpoint Enhancement
```python
@router.post("/api/v1/index-cal-and-gap-analysis")
async def index_cal_and_gap_analysis(
    request: IndexCalGapAnalysisRequest
) -> IndexCalGapAnalysisResponse:
    # Process with enhanced service
    result = await combined_service.analyze_combined_v2(...)
    
    # Build response with optional structure
    response = {
        "index_score": result["index_score"],
        "gap_analysis": result["gap_analysis"],
        "keywords": result["keywords"]
    }
    
    # Add structure if available
    if "resume_structure" in result:
        response["resume_structure"] = result["resume_structure"]
    
    return response
```

## Error Handling Architecture

### Retry Strategy
```python
class RetryableStructureAnalyzer:
    async def analyze_with_retry(self, resume_html: str):
        for attempt in range(self.max_retries):
            try:
                return await self._analyze_once(resume_html)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return self._get_fallback_structure()
                await asyncio.sleep(self.retry_delay)
```

### Fallback Structure
```python
def _get_fallback_structure() -> ResumeStructure:
    """Return basic structure when analysis fails."""
    return ResumeStructure(
        standard_sections=StandardSections(
            summary="Professional Summary",
            skills="Skills",
            experience="Experience",
            education="Education"
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

## Configuration Management

### Environment Variables
```bash
# Feature flag
ENABLE_RESUME_STRUCTURE_ANALYSIS=true

# Performance tuning
STRUCTURE_ANALYSIS_TIMEOUT=3000
STRUCTURE_ANALYSIS_MAX_RETRIES=3
STRUCTURE_ANALYSIS_RETRY_DELAY=500

# Model selection
STRUCTURE_ANALYSIS_MODEL=gpt-4.1-mini
```

### LLM Factory Configuration
```python
API_CONFIG = {
    "resume_structure": {
        "model": "gpt-4.1-mini",
        "temperature": 0.3,
        "max_tokens": 1000,
        "timeout": 3.0
    }
}
```

## Performance Considerations

### Parallel Execution Benefits
1. **Zero Latency Impact**: Structure analysis (2s) completes before Gap Analysis starts (at T=800ms)
2. **Resource Efficiency**: Utilizes idle CPU time during Gap Analysis LLM call
3. **Scalability**: Independent task doesn't affect critical path

### Optimization Strategies
1. **Prompt Engineering**: Minimal, focused prompt for fast response
2. **Token Limits**: Restrict to 1000 tokens for structure analysis
3. **Caching Potential**: Future enhancement for repeated resumes

## Security Considerations

1. **Input Validation**: Sanitize HTML before analysis
2. **Token Limits**: Prevent excessive LLM usage
3. **Error Isolation**: Structure failures don't expose sensitive data
4. **Audit Logging**: Track structure analysis attempts and failures

## Monitoring & Observability

### Metrics to Track
```python
metrics = {
    "structure_analysis_duration_ms": histogram,
    "structure_analysis_success_rate": counter,
    "structure_analysis_retry_count": counter,
    "structure_analysis_fallback_rate": counter,
    "structure_analysis_timeout_rate": counter
}
```

### Logging Strategy
```python
logger.info(
    "Structure analysis completed",
    extra={
        "duration_ms": duration,
        "success": success,
        "retry_count": retries,
        "sections_found": len(sections)
    }
)
```

## Testing Architecture

### Mock Services
```python
class MockStructureAnalyzer:
    """Mock for testing without LLM calls."""
    async def analyze_structure(self, resume_html: str):
        return ResumeStructure(
            standard_sections={...},
            custom_sections=[],
            metadata={...}
        )
```

### Test Coverage Areas
1. **Unit Tests**: Individual component validation
2. **Integration Tests**: End-to-end flow with mocks
3. **Performance Tests**: Parallel execution timing
4. **Error Tests**: Retry and fallback scenarios

## Migration Strategy

### Phase 1: Code Implementation
- Implement ResumeStructureAnalyzer
- Update CombinedAnalysisServiceV2
- Add response models

### Phase 2: Testing & Validation
- Run comprehensive tests
- Validate parallel execution
- Verify error handling

### Phase 3: Deployment
- Enable feature flag
- Monitor metrics
- Gradual rollout

## Conclusion

This architecture design ensures seamless integration of resume structure analysis with zero performance impact through intelligent parallel execution and robust error handling.