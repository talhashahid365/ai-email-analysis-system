# Monitoring Plan

## Uptime Checks
Set up at UptimeRobot (free) or Better Stack:
- Homepage: `https://yourdomain.com/`
- Health API: `https://yourdomain.com/api/health`
- Login page: `https://yourdomain.com/login`

## Technical Metrics
| Metric | Tool | Alert Threshold |
|--------|------|----------------|
| Error rate | Sentry | > 1% of requests |
| API p95 latency | Sentry Performance | > 2000ms |
| DB connections | PostgreSQL logs | > 80% of pool |
| Celery queue depth | Redis CLI | > 100 pending jobs |
| Disk usage | Host monitoring | > 80% |

## Business Metrics (check weekly)
- New signups per day
- Active users (last 7 days)
- Emails analyzed per day
- AI engine success rate
- Smart reply usage rate

## Alert Runbooks
- High error rate → see /docs/runbooks/high-error-rate.md
- Database down → see /docs/runbooks/database-down.md
- High latency → see /docs/runbooks/high-latency.md

## Status Page
Set up free status page at: https://statsig.com or https://uptimerobot.com
