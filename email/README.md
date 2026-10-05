# MailNexa AI

> **Intelligent Email Command Center** — AI-powered SaaS for email analysis, smart reply, and team management with role-based access.

[![CI](https://github.com/your-username/mailnexa-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mailnexa-ai/actions/workflows/ci.yml)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 AI Analysis | Auto-categorizes, prioritizes, sentiment scoring |
| ✍️ Smart Reply | AI-generated reply drafts with tone control |
| 🧠 Neural Assistant | Chat with AI about your inbox |
| 📊 Analytics | Email trends, category breakdowns, SLA metrics |
| 🔐 Role Portals | User / Manager / Admin with separate dashboards |
| 🛡️ Security | JWT + bcrypt, token revocation, rate limiting |
| 📋 Task Tracking | Action items and deadlines extracted from emails |

## 🏗 Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.12) + SQLAlchemy + Alembic |
| Database | PostgreSQL 16 (SQLite for local dev) |
| Cache/Jobs | Redis + Celery |
| Auth | Custom JWT (bcrypt + token revocation denylist) |
| AI | Heuristic engine + LLM fallback (OpenAI/Gemini/Anthropic) |
| Error Tracking | Sentry (optional) |
| CI/CD | GitHub Actions |
| Containers | Docker Compose |

## 🚀 Quick Start

### Prerequisites
- Python 3.12+, Node.js 20+
- (Optional) Redis for distributed rate limiting

### 1. Backend setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # Edit SECRET_KEY at minimum
python -m app.main            # Starts on http://localhost:8000
```

### 2. Frontend setup
```bash
cd frontend
npm install
npm run dev                   # Starts on http://localhost:3000
```

### 3. (Optional) Load demo data
The app starts **empty**: sign up, then add your own emails (upload, paste, import or create). Only if you want sample
users and 100 sample emails for a demo, run this explicitly:
```bash
cd backend && python datasets/seed_data.py --demo
```

### 4. Open the app
- **App:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/docs

## 🔑 Demo accounts (only exist if you ran the `--demo` seed above)

| Role | Email | Password |
|------|-------|----------|
| Admin | talha@example.com | password123 |
| Manager | manager@example.com | password123 |
| User | user@example.com | password123 |

> The login page no longer pre-fills any credentials. Change or delete these accounts before any real deployment.

## 🐳 Docker Compose (Full Stack)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your SECRET_KEY and optionally LLM API keys
docker-compose up -d
```

Includes: PostgreSQL 16, Redis, FastAPI backend, Celery worker, Next.js frontend.
Backend auto-runs `alembic upgrade head` on startup.

## 🛠 Commands Reference

```bash
# Backend
cd backend
python -m app.main                               # Dev server (auto-reload)
pytest tests/ -v                                 # Run all tests
pytest tests/ --cov=app --cov-report=html        # Tests + coverage
alembic upgrade head                             # Apply DB migrations
alembic revision --autogenerate -m "description" # New migration

# Frontend
cd frontend
npm run dev                                      # Dev server
npm run build                                    # Production build
npx tsc --noEmit                                 # Type check only

# Testing
cd backend && pytest tests/ -v                   # Unit + integration
npx playwright install && npx playwright test \  # E2E tests
  --config tests/e2e/playwright.config.ts
k6 run tests/load/k6_load_test.js               # Load test (needs k6)
```

## 📁 Project Structure

```
mailnexa-ai/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers (thin layer)
│   │   ├── services/       # Business logic
│   │   ├── workers/        # Celery background tasks
│   │   ├── permissions.py  # Central can() / require()
│   │   ├── middleware.py   # Security headers + Request ID
│   │   ├── ratelimit.py    # Redis-backed rate limiter
│   │   ├── logging_config.py # Structured JSON logging
│   │   └── main.py         # App entry point
│   ├── alembic/            # DB migrations
│   ├── tests/              # pytest unit + integration tests
│   └── datasets/           # Seed data, standard 90-email test dataset, older 93-email sample
├── frontend/src/
│   ├── app/                # Next.js App Router pages
│   └── components/         # Shared UI components
├── tests/
│   ├── e2e/                # Playwright tests
│   └── load/               # k6 load tests
├── docs/                   # Architecture, API conventions, runbooks
├── .github/workflows/      # CI + CD pipelines
├── docker-compose.yml      # Full stack containers
├── CLAUDE.md               # Agent memory / coding rules
└── README.md
```

## 🔐 Security Architecture

- **Auth:** JWT (HS256) + bcrypt password hashing + token revocation denylist
- **Rate limiting:** Redis sliding-window (10/min auth, 30/min AI, 20/min upload)
- **IDOR protection:** All queries filter by `user_id`; cross-user access returns 404
- **Security headers:** X-Frame-Options, HSTS, X-Content-Type-Options, Permissions-Policy
- **Production checks:** Rejects SQLite, insecure SECRET_KEY, exposed dev tokens
- **Logging:** Structured JSON, sensitive fields redacted, request ID correlation

See [docs/security/threat-model.md](docs/security/threat-model.md)

## 👥 Role-Based Access

| Action | User | Manager | Admin |
|--------|------|---------|-------|
| Email inbox & AI | ✅ | ✅ | ✅ |
| Smart reply | ✅ | ✅ | ✅ |
| Basic analytics | ✅ | ✅ | ✅ |
| Advanced team analytics | ❌ | ✅ | ✅ |
| User management | ❌ | ❌ | ✅ |
| System settings | ❌ | ❌ | ✅ |

See [docs/permissions.md](docs/permissions.md) for the complete matrix.

## 📖 Documentation

| Doc | Description |
|-----|-------------|
| [CLAUDE.md](CLAUDE.md) | Agent rules and coding conventions |
| [docs/architecture.md](docs/architecture.md) | System architecture and decisions |
| [docs/system-design.md](docs/system-design.md) | Requirements and user flows |
| [docs/permissions.md](docs/permissions.md) | Role × action permission matrix |
| [docs/api-conventions.md](docs/api-conventions.md) | API standards and conventions |
| [docs/monitoring.md](docs/monitoring.md) | Monitoring and alerts plan |
| [docs/runbooks/](docs/runbooks/) | Deploy, rollback, backup procedures |
| [docs/security/threat-model.md](docs/security/threat-model.md) | OWASP threat model |

## 🤝 Contributing

1. Branch: `git checkout -b feature/your-feature`
2. Follow [Conventional Commits](https://www.conventionalcommits.org/)
3. Tests must pass: `pytest tests/ -v`
4. Open PR — CI runs automatically

See [CLAUDE.md](CLAUDE.md) for agent coding rules.

## 📄 License

MIT
