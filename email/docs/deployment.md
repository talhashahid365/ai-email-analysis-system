# Deployment & Operations Guide

This guide covers local development, Docker Compose orchestration, production configuration, and background processing options for the **AI Email Intelligence & Smart Reply System**.

---

## 🛠 Prerequisites

- **Python**: 3.12+
- **Node.js**: 20+ (with `npm`)
- **Docker & Docker Compose**: (Optional for containerized setup)
- **Database**: SQLite (default for dev/testing) or PostgreSQL 15+ (production)
- **Redis**: Optional (used for Celery task broker)

---

## 🚀 Deployment Options

### Option 1: Docker Compose (Recommended for Full Stack)

Run the entire application stack (FastAPI backend, Celery worker, PostgreSQL, Redis, and Next.js frontend) with a single command:

```bash
# Clone repository and set environment variables
export GEMINI_API_KEY="your-gemini-api-key"

# Build and start all services
docker-compose up --build -d
```

#### Services Started:
- **Frontend UI**: `http://localhost:3000`
- **FastAPI REST API**: `http://localhost:8000/api`
- **API Interactive Documentation**: `http://localhost:8000/api/docs`
- **PostgreSQL Database**: `localhost:5432`
- **Redis Cache/Broker**: `localhost:6379`
- **Celery Background Worker**: In-container worker

---

### Option 2: Manual Local Development

#### 1. Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed 100 benchmark emails and default test users
python datasets/seed_data.py --demo

# Start FastAPI server
python app/main.py
```

#### 2. Frontend Setup (Next.js)

```bash
cd frontend

# Install Node dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## ⚙️ Configuration & Environment Variables

Create `.env` files in `backend/` and `frontend/` or pass variables via shell environment:

### Backend Variables (`backend/.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `dev-insecure-secret...` | JWT signing key (must set 32+ chars in prod) |
| `DATABASE_URL` | `sqlite:///./email_intelligence.db` | SQLAlchemy DB connection string |
| `LLM_PROVIDER` | `auto` | `auto`, `gemini`, `openai`, `anthropic`, `heuristic` |
| `GEMINI_API_KEY` | `""` | Google Gemini API key |
| `OPENAI_API_KEY` | `""` | OpenAI API key |
| `ANTHROPIC_API_KEY` | `""` | Anthropic Claude API key |
| `PROCESSING_MODE` | `background` | `sync`, `background` (in-process thread), or `celery` |
| `CELERY_BROKER_URL` | `""` | e.g., `redis://localhost:6379/0` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins |

### Frontend Variables (`frontend/.env.local`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api` | API Base URL |

---

## 🧪 Verification & Automated Testing

Run the full pytest suite to verify backend endpoints, security rules, multi-tenant isolation, and 100-email benchmark evaluation:

```bash
cd backend
pytest tests/ -v
```

Generate the Section 27 evaluation report (independent 90-email dataset, with expected results):

```bash
cd backend && python tests/eval_standard.py
```

Output files produced: `backend/tests/standard_results.json` and `backend/tests/standard_results.md`.
Run it once with no API key (rule-based engine) and once with an LLM key, and report both honestly.
