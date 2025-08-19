# Course Availability Threshold Adjustment - Stage 2

## 📊 Adjustment Summary

**Date**: 2025-08-20  
**Stage**: Stage 2 - Moderate Strictness  
**Purpose**: Improve course recommendation quality by increasing similarity thresholds

## 🎯 Threshold Changes

### Similarity Thresholds

| Category | Old Value | New Value | Change |
|----------|-----------|-----------|--------|
| SKILL | 0.35 | 0.40 | +14% |
| FIELD | 0.30 | 0.35 | +17% |
| DEFAULT | 0.35 | 0.40 | +14% |
| MIN_THRESHOLD | 0.30 | 0.35 | +17% |

### Course Type Quotas Adjustments

#### SKILL Category
| Type | Old Quota | New Quota | Reason |
|------|-----------|-----------|--------|
| course | 15 | 18 | Compensate for stricter filtering |
| project | 5 | 3 | Focus on highest quality projects |
| certification | 2 | 3 | Slightly increase professional certs |
| specialization | 2 | 3 | More comprehensive learning paths |
| degree | 1 | 1 | Keep focused on most relevant |

#### FIELD Category
| Type | Old Quota | New Quota | Reason |
|------|-----------|-----------|--------|
| specialization | 12 | 15 | More high-quality course series |
| degree | 4 | 3 | Slightly reduced but substantial |
| course | 5 | 6 | Slight increase for variety |
| certification | 2 | 2 | Maintain professional certs |
| project | 1 | 1 | Focus on best practical project |

## 🔧 Implementation Details

### Environment Variable Support

The following environment variables can be used to override thresholds without redeployment:

```bash
# Threshold overrides
export COURSE_THRESHOLD_SKILL=0.40      # Default: 0.40
export COURSE_THRESHOLD_FIELD=0.35      # Default: 0.35
export COURSE_THRESHOLD_DEFAULT=0.40    # Default: 0.40
export COURSE_MIN_THRESHOLD=0.35        # Default: 0.35
```

### Code Changes

**File**: `src/services/course_availability.py`

Key changes:
1. Updated `SIMILARITY_THRESHOLDS` dictionary with new values
2. Updated `MIN_SIMILARITY_THRESHOLD` constant
3. Added environment variable support with `os.getenv()`
4. Added logging to display active thresholds on module load
5. Adjusted `COURSE_TYPE_QUOTAS` to compensate for stricter filtering

## 📈 Expected Impact

### Positive Effects
- **Higher Precision**: Courses more closely match requested skills
- **Reduced Noise**: Fewer marginally relevant courses
- **Better UX**: More focused, actionable recommendations
- **Quality Focus**: Top 10-15 most relevant courses per skill

### Potential Concerns
- **Fewer Results**: Some skills might have fewer or no courses
- **Coverage Gaps**: Niche skills might not meet threshold
- **Monitoring Needed**: Watch for skills with zero results

## 📊 Success Metrics

Monitor these metrics after deployment:

1. **Average courses per skill**: Target 10-15 (was ~20-25)
2. **Skills with courses percentage**: Target 70-90% (was ~95%)
3. **Unique course IDs returned**: Should decrease by ~20-30%
4. **User engagement**: Track click-through rates on courses

## 🧪 Testing

### Test Script
Use `test_threshold_adjustment.py` to verify the effects:

```bash
python test_threshold_adjustment.py
```

### Manual Testing
Test with various skill levels:
- Common skills (Python, JavaScript) - should still have many courses
- Specialized skills (MLOps, Kubernetes) - should have focused results
- Niche skills - might have fewer or no results

## 🔄 Rollback Plan

If issues occur, rollback options:

### Option 1: Environment Variables (No Deployment)
```bash
# Revert to original values via Container Apps config
COURSE_THRESHOLD_SKILL=0.35
COURSE_THRESHOLD_FIELD=0.30
COURSE_THRESHOLD_DEFAULT=0.35
COURSE_MIN_THRESHOLD=0.30
```

### Option 2: Git Revert
```bash
git revert ffb4da3
git push origin main
```

## 📝 Notes

- Thresholds based on cosine similarity (0.0 = orthogonal, 1.0 = identical)
- pgvector uses `1 - (embedding <=> vector)` for similarity calculation
- Higher thresholds mean stricter matching requirements
- Consider A/B testing for user satisfaction

## 🚀 Deployment

**Commit**: ffb4da3  
**Pipeline**: CI/CD Pipeline - Main  
**Target**: airesumeadvisor-api-production  
**Region**: Japan East  

## 📞 Support

For issues or adjustments:
1. Check logs: `az containerapp logs show --name airesumeadvisor-api-production`
2. Monitor metrics in Application Insights
3. Adjust via environment variables if needed
4. Contact: DevOps team for deployment issues

---

*Document created: 2025-08-20*  
*Author: Claude Code + WenHao*