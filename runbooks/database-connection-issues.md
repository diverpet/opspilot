# Database Connection Issues Runbook

## Overview
This runbook covers troubleshooting database connection issues including timeouts, connection pool exhaustion, and connection failures.

## Symptoms
- Connection timeout errors in logs
- High latency on database-dependent endpoints
- Connection pool exhausted errors
- Circuit breaker open for database connections

## Diagnosis Steps

### 1. Check Connection Pool Status
```bash
# Check current connection pool usage
curl http://localhost:8080/metrics | grep db_pool
```

### 2. Review Recent Changes
- Check for recent deployments that might have changed connection pool settings
- Review any configuration changes to database connection parameters

### 3. Check Database Server
- Verify database server is healthy
- Check database server connection limits
- Review slow query logs

## Remediation Steps

### Immediate Actions
1. **If connection pool exhausted**: Increase pool size temporarily
2. **If database slow**: Identify and kill long-running queries
3. **If circuit breaker open**: Wait for half-open test or force reset

### Configuration Changes
```yaml
# Recommended connection pool settings
pool:
  max_size: 100
  min_size: 10
  timeout_ms: 5000
  max_lifetime_ms: 1800000
```

### Rollback Procedure
If recent deployment caused issues:
1. Identify the problematic deployment
2. Rollback to previous stable version
3. Monitor for recovery

## Prevention
- Set up connection pool monitoring alerts
- Implement connection pool metrics dashboard
- Add canary testing for configuration changes
