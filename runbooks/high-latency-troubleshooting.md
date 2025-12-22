# High Latency Troubleshooting Runbook

## Overview
This runbook covers diagnosis and remediation of high latency issues in production services.

## Symptoms
- P99 latency exceeds SLA threshold
- User-reported slowness
- Timeout errors increasing
- Elevated response time metrics

## Common Causes
1. Database query performance degradation
2. External API slowdowns
3. Resource exhaustion (CPU, memory)
4. Network issues
5. Connection pool saturation
6. Garbage collection pauses

## Diagnosis Steps

### 1. Check Metrics Dashboard
```bash
# Query latency metrics
curl -s http://localhost:9090/api/v1/query?query=http_request_duration_seconds_bucket
```

### 2. Identify Slow Endpoints
- Sort endpoints by P99 latency
- Check if issue is isolated or widespread

### 3. Check Resource Utilization
- CPU usage
- Memory pressure
- Disk I/O
- Network saturation

### 4. Review Dependencies
- Check downstream service health
- Verify database response times
- Check external API latencies

## Remediation

### Quick Fixes
1. **Scale horizontally** if CPU-bound
2. **Increase connection pools** if connection-bound
3. **Enable request shedding** if overloaded
4. **Activate fallback caches** for slow dependencies

### Database-Related
- Add missing indexes
- Optimize slow queries
- Enable query caching
- Increase connection pool

### Memory-Related
- Increase heap size
- Tune GC settings
- Check for memory leaks

## Escalation
If latency doesn't improve within 15 minutes:
1. Page on-call SRE
2. Consider partial rollback
3. Enable incident mode
