# Deployment Runbook

## First Deployment

### Prerequisites
- Docker and Docker Compose installed
- `.env` file created from `backend/.env.example`
- PostgreSQL database provisioned

### Steps
1. Clone the repository
2. Copy env file: `cp backend/.env.example backend/.env`
3. Edit `.env` with production values (real SECRET_KEY, DATABASE_URL, etc.)
4. Start services: `docker-compose up -d`
5. Run migrations: `docker-compose exec backend alembic upgrade head`
6. Seed data (optional): `docker-compose exec backend python datasets/seed_data.py --demo`
7. Verify health: `curl http://localhost:8000/api/health`

## Rollback
1. Identify last working image tag from CI/CD logs
2. Update docker-compose.yml to pin previous image tag
3. Run: `docker-compose up -d`
4. If migration rollback needed: `docker-compose exec backend alembic downgrade -1`

## Environment Variables
See `backend/.env.example` for all required variables.
