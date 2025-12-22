# Deployment Rollback Procedure

## Overview
This runbook provides step-by-step instructions for rolling back a problematic deployment.

## When to Rollback
- Error rate exceeds 5%
- P99 latency exceeds 2x normal
- Critical functionality broken
- Data corruption detected
- Security vulnerability discovered

## Pre-Rollback Checklist
- [ ] Confirm issue is deployment-related
- [ ] Identify the problematic deployment version
- [ ] Verify previous stable version is available
- [ ] Notify stakeholders of impending rollback
- [ ] Prepare rollback verification plan

## Rollback Steps

### 1. Identify Current and Target Versions
```bash
# Check current version
kubectl get deployment <service> -o jsonpath='{.spec.template.spec.containers[0].image}'

# List available versions
kubectl rollout history deployment/<service>
```

### 2. Execute Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/<service>

# Or rollback to specific revision
kubectl rollout undo deployment/<service> --to-revision=<N>
```

### 3. Monitor Rollback
```bash
# Watch rollback progress
kubectl rollout status deployment/<service>
```

### 4. Verify Recovery
- Check error rates returning to normal
- Verify latency metrics improving
- Test critical user flows
- Monitor for 15 minutes post-rollback

## Post-Rollback Actions
1. Create incident report
2. Analyze root cause of failed deployment
3. Update deployment pipeline if needed
4. Schedule post-mortem meeting

## Emergency Contacts
- On-call SRE: See PagerDuty
- Platform Team: #platform-help
- Service Owners: See service catalog
