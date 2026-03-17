# Operations & Recovery Procedures

Guide for maintaining and troubleshooting the N-Tier Intelligence platform.

## 1. Outbox Recovery Procedure

The Outbox pattern ensures atomicity between PostgreSQL and Neo4j. If the Neo4j instance is unreachable, events accumulate in `outbox_events` with a `failed` or `pending` status.

### Automatic Retries
- Events are retried automatically with **Exponential Backoff**.
- Max retries: 5.

### Manual Recovery
If an event permanently fails (status: `failed`), it must be manually reset for reprocessing once the downstream issue is resolved:

```sql
-- Reset all failed events for retry
UPDATE outbox_events 
SET status = 'pending', retries = 0, next_retry_at = NOW() 
WHERE status = 'failed';
```

## 2. Troubleshooting Connectivity

### Neo4j (7687/7474)
- **Problem**: `ServiceUnavailable` errors.
- **Check**: `bolt` protocol connection to `settings.neo4j_uri`.
- **Action**: Verify Neo4j Docker container status and credentials.

### Redis (6379)
- **Problem**: Cache misses or Rate limiting lag.
- **Action**: Check `redis-cli ping`. Ensure `REDIS_URL` mapping is correct.

## 3. Celery Worker (Upload Processing)
- **Problem**: PDF uploads stuck in "pending".
- **Action**: Check Celery worker logs. Restart worker:
  ```bash
  celery -A core.celery_app worker --loglevel=info
  ```
