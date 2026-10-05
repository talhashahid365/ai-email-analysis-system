# Project Status

**Last updated:** 1 October 2026

An honest snapshot against `Email_intelligence_system.pdf`. Numbers below are measured, not targets.

## Working
- Auth (sign up, login/logout with token revocation, verify email, forgot/reset password, profile), RBAC, per-user data isolation.
- Ingestion: `.eml` / `.txt` upload, pasted text, JSON/CSV import, manual creation, de-duplication, thread grouping.
- Rule-based AI engine: category, intent, priority + reason, sentiment, summaries, extraction, action items, deadlines.
- Smart reply with 6 tones and approve/reject lifecycle (never auto-sends); notifications; analytics; admin panel.
- Per-email AI endpoints: `POST /emails/{id}/reprocess|classify|summarize|extract`; admin reprocess and retry-failed.
- Deadline notifications run hourly (API-process scheduler, Celery beat task, and refreshed when notifications are listed).
- Dashboard charts (activity, category distribution), Support KPI, average response time, upcoming deadlines.
- Inbox filters that combine: unread, reply required, action required, category, priority, sentiment, date, sender.

## Measured: rule-based engine on `datasets/standard_test_dataset.json` (90 emails, 10 per category)
No LLM key is configured, so these are rule-based results only. Full report: `backend/tests/standard_results.md`.

| Metric | Result |
|---|---|
| Category | 68.9% |
| Priority (exact / within one level) | 58.9% / 93.3% |
| Sentiment | 48.9% |
| Reply required | 88.9% |
| Action required | 78.9% |
| Extraction fields | 85.9% |
| Deadlines | 81.5% |
| Reply mentions expected key terms (template replies) | 32.4% |

The dataset was written independently of the engine and must not be used to tune it.
`tests/test_standard_dataset.py` holds regression floors a few points below these numbers.

## Not done / known gaps
- **No LLM has ever run.** All API keys are blank. Provider code exists but is untested against a real model.
- **"Embeddings" are term-frequency vectors**, not semantic embeddings; the assistant is weak on open questions
  such as "Which customers are waiting for a response?".
- Smart replies from the heuristic engine are generic templates.
- No deployed URL, no demo video (script only), no frontend unit tests; e2e covers auth only.
- `pytest tests/ -v` (30 passed) and `npm run build` (type check + lint + 19 pages) both pass as of 2 October 2026.

## Update 4 (this revision)
- Dashboard and Analytics pages rewritten: **every number and chart now comes from the signed-in user's own emails**.
  All hardcoded demo values (fake trend, heatmap, category bars, KPI fallbacks like 100/97/28, fake benchmark simulator) are removed.
  A new user sees an empty-state card with an "Add your first email" button.
- New backend data for the dashboard (`/analytics/overview`): 14-day activity, sentiment trend, weekday x time heatmap,
  response-status split, critical queue with confidence, recent emails, recent AI actions. Deleted emails are no longer counted.
- Login page: replaced the three fake "portals" (which ignored the Manager ID / 2FA fields and sent hard-coded passwords) with one real
  email + password form. No credentials are pre-filled. The role comes from the server.
- Add-email form no longer pre-fills a sample refund email.
- `datasets/seed_data.py` now needs `--demo`; the app starts empty by default.
- Removed the circular evaluation artifacts (`generate_test_report.py`, `test_results_report.*`, `enhance_*`, `align_sentiments.py`).
  The only trustworthy numbers are the ones from the independent `standard_test_dataset.json`, listed above.
- Syntax-checked only (no pytest / `next build` possible in the sandbox). Run both before relying on this.

## Frontend layout fixes (3 October 2026)
- Fixed the header overlapping page content on Tasks: `md:p-6` was overriding `pt-16`, so content started under the fixed header.
- Header offset (`left-72`) did not match the 256px sidebar, leaving a 32px gap. Header, sidebar and page content now all use the `lg` breakpoint and a 256px sidebar.
- Sidebar now slides off-canvas below `lg` and opens from a hamburger button (it previously covered the page on small screens).
- Tasks & Deadlines page rebuilt: uses `AppLayout`, deadlines grouped by Overdue / Within 7 days / Later / Completed, search, filter counts, optimistic toggles, links to the source email, loading and error states.
- Removed leftover "Extej Crypto Wallet" page title and the hardcoded "Zubair Tahir" name (now the signed-in user's name).
- Syntax-checked only; still needs `npm run build` and a visual check.


## Verification and inbox fix (2 October 2026)
- Backend `pytest tests/ -v`: 30 passed. Frontend `tsc --noEmit` and `npm run build`: pass. Rule-based eval reproduces the numbers above.
- Inbox page now uses `AppLayout` (mobile hamburger works), no longer shows fake sidebar counts (`142` total / `5` urgent fallbacks), and shows an "Add your first email" empty state for new users, separate from the "no match for filters" message.
- Still not checked visually: email detail, tasks and notifications in a browser (code review found no hardcoded demo data; both detail and notifications use `AppLayout`).

## Spec gap fixes (2 October 2026, later)
- **Migration bug fixed:** `revoked_tokens.updated_at` was in the model but not in Alembic (logout would fail on a migrated Postgres DB). Added migration `003`, plus `tests/test_migrations.py`, which runs `alembic upgrade head` and fails if any model table/column is missing (verified it fails without 003).
- **Inbox (spec section 4):** every row now shows unread dot/bold, date and time, AI status, and has star, mark read/unread, archive and delete buttons. Added Inbox / Starred / Archived views and a "Mark unread" button on the detail page.
- **Admin (spec section 23):** new Email Processing tab (status counts, failed emails, Retry all / Reprocess for admins), AI Usage tab (calls, error rate, latency by operation and provider), Errors tab, and the audit tab is now labelled System Activity. New endpoints `GET /admin/processing` and `GET /admin/usage` (no email content exposed). Fixed a bug where the AI log "Task" column was blank (`action` vs `operation`).
- Documented `REQUIRE_EMAIL_VERIFICATION` in `.env.example`.
- Tests: 36 backend tests pass; `tsc` and `next build` pass.

## Still open (needs things only you can provide)
- **LLM key**: add one, then run `python tests/eval_standard.py` and `python -m pytest tests/` and update the table above.
- **Semantic embeddings / RAG**: needs an embeddings provider (or a new dependency, which CLAUDE.md says to ask about first).
- **Email verification in production**: needs SMTP credentials and `REQUIRE_EMAIL_VERIFICATION=true`.
- **Celery + Redis path**: code exists, never run against a real Redis.
- **Deployment URL and demo video**: need your hosting account and a recording.
- **Browser check** of the new inbox actions and admin tabs, and frontend unit tests (not added: new dependency).


## Admin role management (v9)
- Admins can set anyone to user / manager / admin from Users & RBAC and suspend or re-activate accounts.
- The system always keeps at least one active admin: demoting or suspending the last admin is rejected.
- The sidebar re-reads the role from the server on every page, and always shows an "Admin Panel (Users & RBAC)" link to admins.
- `ADMIN_EMAILS` promotes at login only when no active admin exists (recovery), so it never overrides an admin's choices.
- Password reset works only through the emailed link (see `.env.example` SMTP settings).
- New tests: `tests/test_admin_roles.py`, `tests/test_password_reset_email_only.py` (not yet run in the build sandbox).
