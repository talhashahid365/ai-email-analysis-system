# Project: MailNexa AI
## What this product does
MailNexa AI is an intelligent email management SaaS platform that uses AI to automatically analyze, categorize, prioritize, and generate smart replies for business emails. Target users: professionals and teams who receive high volumes of email.

## Stack (do not change without asking)
- Frontend: Next.js 14 + TypeScript + Tailwind CSS
- Backend: Python 3.12 + FastAPI + SQLAlchemy ORM
- Database: PostgreSQL (production), SQLite (local dev only)
- Auth: Custom JWT with bcrypt (jose + passlib) — token revocation via DB
- Background Jobs: Celery + Redis
- AI Engine: Heuristic classifier + LLM fallback (OpenAI / Anthropic / Gemini)
- Hosting: Docker Compose (self-hosted), Vercel (frontend option)

## Rules
- Never commit secrets. All secrets go in environment variables, documented in backend/.env.example
- Every new API endpoint needs: input validation (Pydantic), auth check, authorization check (use require() from app.permissions), tests
- Every database change goes through an Alembic migration file. Never edit the DB by hand or use create_all() for schema changes.
- Run lint, typecheck and tests before saying a task is done
- Ask before adding a new dependency
- Prefer small, reviewable changes. One feature per branch
- Use the central can(user, action) and require(user, action) from app.permissions for ALL authorization checks
- Every endpoint that returns user-owned data must filter by user_id (or organization_id when multi-tenancy is added)
- Return 404 (not 403) when a user tries to access another user's resource by ID

## Commands
- Backend dev: cd backend && python -m app.main
- Frontend dev: cd frontend && npm run dev
- Backend tests: cd backend && pytest tests/ -v
- Frontend build: cd frontend && npm run build
- DB migrate: cd backend && alembic upgrade head
- DB new migration: cd backend && alembic revision --autogenerate -m "description"
- Seed data: cd backend && python datasets/seed_data.py --demo

## Architecture decisions
See /docs/decisions/ for the log of decisions and why they were made.
