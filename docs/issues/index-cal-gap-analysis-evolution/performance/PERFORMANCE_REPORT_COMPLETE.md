# Performance Analysis Report - /api/v1/index-cal-and-gap-analysis

## Executive Summary

This report provides a comprehensive analysis of the performance characteristics of the `/api/v1/index-cal-and-gap-analysis` API endpoint based on real-world testing with production data.

**Test Date**: 2025-08-16  
**Test Environment**: Production (Azure Container Apps - Japan East)  
**Test Cases**: 3 unique job descriptions with 16 keywords each  
**Resume Size**: 6,306 characters

## 📊 Key Performance Metrics

### Response Time Statistics

| Metric | Value | Status |
|--------|-------|--------|
| **P50 (Median)** | 8.34s | ⚠️ Above target |
| **P95** | ~11s | ⚠️ Above target |
| **Average** | 9.27s | ⚠️ Above target |
| **Min** | 8.34s | - |
| **Max** | 11.13s | - |

### Success Rate
- **100%** (3/3 tests successful)
- No errors or timeouts observed

## 🔍 Function Block Performance Analysis

### Timing Breakdown (milliseconds)

| Function | Min | Median | Max | % of Total | Status |
|----------|-----|--------|-----|------------|--------|
| **Structure Analysis** | 8,222 | 8,225 | 10,958 | ~85% | 🔴 Critical Bottleneck |
| **Gap Analysis** | 6,667 | 7,278 | 9,349 | ~75% | 🔴 Critical Bottleneck |
| **Course Availability** | 614 | 1,243 | 1,320 | ~12% | 🟡 Secondary |
| **Index Calculation** | 158 | 160 | 160 | ~1.6% | ✅ Optimal |
| **Embeddings** | 131 | 156 | 171 | ~1.6% | ✅ Optimal |
| **Keyword Matching** | 13 | 14 | 18 | ~0.1% | ✅ Optimal |
| **PGVector Warmup** | 277 | - | - | Hidden | ✅ Parallel |

## 🚨 Critical Findings

### 1. Major Bottlenecks Identified

#### Structure Analysis (85% of total time)
- **Current**: 8-11 seconds
- **Expected**: 1-2 seconds (if truly parallel)
- **Issue**: The timing appears to include wait time from when the task is checked, not actual execution time
- **Impact**: Adds unnecessary 6-9 seconds to total response time

#### Gap Analysis (75% of total time)
- **Current**: 7-9 seconds
- **Expected**: 3-4 seconds with optimization
- **Issue**: Sequential LLM calls without batching
- **Impact**: Primary contributor to high response times

### 2. Parallel Execution Efficiency
- **Reported**: -0.0% efficiency
- **Analysis**: Parallel execution is not working as designed
- **Expected behavior**:
  - Keywords, Embeddings, and Structure Analysis should run in parallel from T=0
  - Index Calculation should start after Embeddings complete
  - Gap Analysis should start after Index Calculation

### 3. Actual vs Expected Timeline

#### Current Execution Pattern (Sequential)
```
T=0     Keywords (13ms)
T=13    Embeddings (156ms)
T=169   Index Calculation (160ms)
T=329   Gap Analysis (7,278ms)
T=7607  Structure Analysis Check (appears as 8,225ms)
T=8832  Course Availability (1,243ms)
T=10075 Complete
```

#### Expected Execution Pattern (Parallel)
```
T=0     Keywords (13ms) | Embeddings (156ms) | Structure Analysis (2,000ms) | PGVector Warmup (277ms)
T=156   Index Calculation (160ms)
T=316   Gap Analysis (7,278ms)
T=7594  Course Availability (1,243ms)
T=8837  Complete
```

**Potential Time Saving**: ~2 seconds with proper parallelization

## 📈 Performance Trends

### By Test Case
1. **TSMC - Senior Data Analyst**: 11.13s (worst)
2. **NVIDIA - Senior Data Scientist**: 8.34s (best)
3. **foodpanda - Data Analyst**: 8.34s (best)

### Variance Analysis
- High variance in Structure Analysis (8.2s - 11s)
- Consistent performance in Index Calculation and Embeddings
- Gap Analysis shows significant variation (6.7s - 9.3s)

## 🎯 Optimization Recommendations

### Priority 1: Fix Structure Analysis Timing (Immediate)
- **Issue**: Recording check time instead of actual execution time
- **Solution**: Already implemented in code fix - needs deployment
- **Expected Impact**: Correct timing visibility, no actual performance change

### Priority 2: Optimize Gap Analysis (High Impact)
- **Current approach**: Sequential processing
- **Recommendations**:
  1. Batch LLM calls where possible
  2. Implement response streaming
  3. Cache common gap patterns
  4. Consider using lighter models for initial analysis
- **Expected Impact**: 30-40% reduction (save 2-3 seconds)

### Priority 3: Ensure True Parallel Execution
- **Current**: Tasks appear to run sequentially
- **Solution**: 
  1. Verify asyncio.create_task is working correctly
  2. Check for blocking operations in parallel tasks
  3. Add detailed timing logs for debugging
- **Expected Impact**: 15-20% reduction (save 1-2 seconds)

### Priority 4: Optimize Course Availability
- **Current**: 600-1,300ms
- **Recommendations**:
  1. Pre-warm database connections
  2. Implement result caching
  3. Batch database queries
- **Expected Impact**: 5% reduction (save 500ms)

## 🚀 Target Performance Goals

### Short Term (1-2 weeks)
- Reduce P50 to **6 seconds**
- Reduce P95 to **8 seconds**
- Achieve 30% parallel efficiency

### Medium Term (1 month)
- Reduce P50 to **4 seconds**
- Reduce P95 to **6 seconds**
- Achieve 50% parallel efficiency

### Long Term (3 months)
- Reduce P50 to **3 seconds**
- Reduce P95 to **4 seconds**
- Achieve 70% parallel efficiency

## 📋 Action Items

1. **Deploy structure_analysis timing fix** (completed in code)
2. **Add detailed execution timeline logging** to production
3. **Profile Gap Analysis LLM calls** to identify optimization opportunities
4. **Implement response streaming** for Gap Analysis
5. **Cache frequently requested skill gaps**
6. **Optimize database queries** in Course Availability
7. **Add performance monitoring dashboard**

## 🔧 Technical Details

### Environment Configuration
- **Deployment**: Azure Container Apps
- **Region**: Japan East
- **Resources**: 1 CPU, 2GB RAM
- **Auto-scaling**: 2-10 instances
- **LLM Models**:
  - Keywords: GPT-4.1-mini
  - Gap Analysis: GPT-4.1
  - Structure Analysis: Internal parser

### Test Methodology
- Real production API calls
- Diverse test data (3 industries)
- 2-second delay between tests to avoid rate limiting
- Consistent resume size (6,306 characters)
- 16 keywords per job description

## 📊 Conclusion

The API is functional with 100% success rate but requires significant performance optimization. The main bottlenecks are:

1. **Structure Analysis timing issue** (measurement problem, not actual performance)
2. **Gap Analysis duration** (7-9 seconds)
3. **Lack of effective parallelization**

With the recommended optimizations, we can achieve a **40-50% reduction** in response times, bringing P50 down from 8.3s to approximately 4-5s.

---

*Report Generated: 2025-08-16*  
*Next Review: After deployment of timing fixes*