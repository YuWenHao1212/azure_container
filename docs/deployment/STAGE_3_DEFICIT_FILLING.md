# Stage 3: Enable Deficit Filling Mechanism

## Overview

Stage 3 enables the intelligent deficit filling mechanism that was implemented in Stage 2. This feature ensures optimal course diversity by:

1. Applying category-specific quotas (SKILL, FIELD, DEFAULT)
2. Using reserve pools to fill deficits when specific course types are lacking
3. Re-sorting all courses by similarity after filling

## Prerequisites

- ✅ Stage 1 deployed (configurable thresholds)
- ✅ Stage 2 deployed (deficit filling mechanism implemented)
- Azure CLI installed and logged in
- Production API key for testing

## Configuration

### Environment Variable to Enable

```bash
ENABLE_DEFICIT_FILLING=true
```

### Current Thresholds (Conservative)

| Category | Threshold | Target |
|----------|-----------|--------|
| SKILL | 0.35 | 0.40 |
| FIELD | 0.30 | 0.35 |
| DEFAULT | 0.35 | 0.40 |
| MIN | 0.30 | 0.35 |

### Quota System (When Enabled)

#### Original Quotas (Target Distribution)
| Category | course | project | certification | specialization | degree |
|----------|--------|---------|---------------|----------------|--------|
| SKILL | 15 | 5 | 2 | 2 | 1 |
| FIELD | 5 | 1 | 2 | 12 | 4 |
| DEFAULT | 10 | 3 | 2 | 5 | 2 |

#### Extended Quotas (With Reserves)
| Category | course | project | certification | specialization | degree |
|----------|--------|---------|---------------|----------------|--------|
| SKILL | 25 (+10) | 5 | 2 | 2 | 1 |
| FIELD | 15 (+10) | 1 | 2 | 12 | 4 |
| DEFAULT | 20 (+10) | 3 | 2 | 5 | 2 |

## Deployment Steps

### Option 1: Using the Script (Recommended)

```bash
# Run the enable script
./scripts/enable-deficit-filling.sh
```

The script will:
1. Check Azure login status
2. Show current configuration
3. Enable deficit filling
4. Wait for deployment
5. Verify the new configuration

### Option 2: Manual Azure CLI

```bash
# Login to Azure
az login

# Enable deficit filling
az containerapp update \
    --name airesumeadvisor-api-production \
    --resource-group airesumeadvisorfastapi \
    --set-env-vars ENABLE_DEFICIT_FILLING=true

# Verify the change
az containerapp show \
    --name airesumeadvisor-api-production \
    --resource-group airesumeadvisorfastapi \
    --query "properties.template.containers[0].env[?name=='ENABLE_DEFICIT_FILLING'].value" \
    -o tsv
```

### Option 3: Azure Portal

1. Navigate to the Container App in Azure Portal
2. Go to "Containers" → "Edit and deploy"
3. Select the container
4. Add/Update environment variable:
   - Name: `ENABLE_DEFICIT_FILLING`
   - Value: `true`
5. Save and deploy

## Verification

### 1. Run the Test Script

```bash
python test/scripts/test_production_deficit_filling.py
```

Expected indicators of success:
- Skills returning 25 courses (maximum quota)
- Course type heavily dominant (>70%)
- Average courses per SKILL > 20

### 2. Check Application Logs

Look for these log messages:
```
Course Availability Thresholds - ... Deficit Filling: Enabled
[CourseAvailability] Applying deficit filling for SKILL
[CourseAvailability] SKILL - Supplemented N courses from reserve pool
```

### 3. Manual API Test

Test with a job requiring many skills the candidate lacks:

```python
{
    "resume": "<div>Basic junior developer skills</div>",
    "job_description": "Senior role requiring Python, Docker, AWS, etc.",
    "keywords": ["Python", "Docker", "AWS", "Kubernetes"],
    "language": "en"
}
```

## Expected Behavior Changes

### Before (Deficit Filling Disabled)
- Simple sorting by similarity
- Maximum 25 courses total
- No type diversity guarantees
- May return only "course" type

### After (Deficit Filling Enabled)
- Applies quotas per course type
- Uses reserves to fill deficits
- Ensures type diversity
- Re-sorts by similarity after filling

## Monitoring

### Key Metrics to Watch

1. **Course Count Distribution**
   - SKILL category: Should average 20-25 courses
   - FIELD category: Should show more specializations
   - DEFAULT: Balanced distribution

2. **Type Diversity**
   - Should see multiple course types
   - Course type should be 60-80% (not 100%)

3. **Response Times**
   - Minimal impact expected (<5ms additional)

## Rollback

If issues occur, disable deficit filling immediately:

```bash
# Quick rollback
az containerapp update \
    --name airesumeadvisor-api-production \
    --resource-group airesumeadvisorfastapi \
    --set-env-vars ENABLE_DEFICIT_FILLING=false
```

## Success Criteria

✅ Stage 3 is successful when:
- Deficit filling is enabled in production
- API continues returning courses normally
- Course diversity improves (multiple types)
- No performance degradation
- Logs show deficit filling activity

## Next Steps

After successful verification:
- **Stage 4**: Gradually increase thresholds toward targets
- **Stage 5**: Enable monitoring and optimization

## Troubleshooting

### Issue: No courses returned after enabling
- **Cause**: Thresholds might be too restrictive with deficit filling
- **Solution**: Keep deficit filling but maintain conservative thresholds

### Issue: Only "course" type returned
- **Cause**: Deficit filling not actually active
- **Solution**: Verify ENABLE_DEFICIT_FILLING=true in environment

### Issue: Performance degradation
- **Cause**: Additional processing overhead
- **Solution**: Monitor and consider disabling if >100ms impact

## References

- [Course Availability Decision Tree](../issues/index-cal-gap-analysis-evolution/features/COURSE_AVAILABILITY_DECISION_TREE.md)
- [Stage 1 Documentation](./STAGE_1_CONFIGURABLE_THRESHOLDS.md)
- [Stage 2 Documentation](./STAGE_2_IMPLEMENT_MECHANISM.md)