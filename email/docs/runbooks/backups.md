# Backup Runbook

## PostgreSQL Backups

### Automated Backup (Docker)
Add to crontab (runs daily at 2 AM):
```
0 2 * * * docker-compose exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > /backups/mailnexa_$(date +%Y%m%d).sql.gz
```

### Manual Backup
```bash
docker-compose exec postgres pg_dump -U mailnexa mailnexa_prod > backup_$(date +%Y%m%d_%H%M).sql
```

### Restore
```bash
docker-compose exec -T postgres psql -U mailnexa mailnexa_prod < backup_file.sql
```

### Retention
- Daily backups kept for 7 days
- Weekly backups kept for 4 weeks
- Monthly backups kept for 6 months

## Verify Backup
Test restore into a separate database:
```bash
docker-compose exec postgres createdb mailnexa_test_restore -U mailnexa
cat backup.sql | docker-compose exec -T postgres psql -U mailnexa mailnexa_test_restore
```
