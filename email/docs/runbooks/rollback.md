# Rollback Runbook

## Application Rollback
1. Identify the last working git commit: `git log --oneline`
2. Check out previous release tag: `git checkout tags/v1.x.x`
3. Rebuild and restart: `docker-compose up -d --build`

## Database Migration Rollback
1. Check current migration: `alembic current`
2. Roll back one step: `alembic downgrade -1`
3. Roll back to specific revision: `alembic downgrade <revision_id>`

## Emergency: Restore from Backup
1. Stop application: `docker-compose stop backend`
2. Restore database from backup (see backups.md)
3. Start application: `docker-compose start backend`
