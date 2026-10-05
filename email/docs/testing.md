# Testing Strategy

## Levels
1. **Unit tests** — `backend/tests/test_unit.py` — test individual service functions
2. **Integration tests** — `backend/tests/test_security.py` — test API endpoints with real DB
3. **AI Evaluation** — `backend/tests/eval_standard.py` scores the engine on `datasets/standard_test_dataset.json` (90 emails, 9 categories x 10, with expected results); `test_standard_dataset.py` enforces regression floors. Regenerate the dataset with `python datasets/build_standard_dataset.py`; write a report with `python tests/eval_standard.py`. (`test_ai_eval.py` is the older sample set; its expected values are not independent, so treat it as a smoke test only.)
4. **E2E tests** — Playwright (TODO for v1.1)

## What to Mock
- External LLM APIs (OpenAI, Anthropic) — use fixtures
- SMTP email sending — mock the mailer
- **Never mock**: our database, our auth checks

## Critical Flows (must not break)
1. User signup + email verification
2. Login + JWT token flow
3. Email upload + AI analysis
4. Smart reply generation
5. Admin: grant role to user

## Coverage Target
- Business logic in `/services`: 70%+
- API endpoints: 100% happy path + common error cases
- Auth/permission checks: 100%

## Running Tests
```bash
cd backend
pytest tests/ -v                    # all tests
pytest tests/test_unit.py -v        # unit only
pytest tests/test_security.py -v    # integration only
pytest tests/ --cov=app --cov-report=html  # with coverage
```
