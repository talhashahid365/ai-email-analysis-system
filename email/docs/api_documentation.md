# Smart Email Intelligence — REST API Documentation

This document provides complete documentation for the REST API endpoints provided by the FastAPI backend.

---

## 🔐 Base URL & Authentication

**Base URL**: `http://localhost:8000/api/v1`

### Authentication Headers
All protected endpoints require a JWT Bearer Token in the HTTP `Authorization` header:
```http
Authorization: Bearer <access_token>
```

---

## 🔑 1. Authentication Endpoints (`/auth`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register new user account | ❌ No |
| `POST` | `/auth/login` | Authenticate user & return JWT token + jti | ❌ No |
| `POST` | `/auth/logout` | Revoke active JWT token and logout session | ✅ Yes |
| `POST` | `/auth/forgot-password` | Email a password reset link (the link is only ever sent by email) | ❌ No |
| `POST` | `/auth/reset-password` | Reset password using valid reset token | ❌ No |
| `GET` | `/auth/verify-email` | Verify email address using verification token | ❌ No |
| `GET` | `/auth/me` | Fetch currently logged in user profile | ✅ Yes |
| `PATCH`| `/auth/me` | Update full name or profile preferences | ✅ Yes |

---

## 📧 2. Email Ingestion & Management (`/emails`, `/threads`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/emails` | Query/list user emails with filtering & pagination | ✅ Yes |
| `POST` | `/emails` | Ingest single email manually | ✅ Yes |
| `POST` | `/emails/upload` | Upload `.eml` or `.txt` raw RFC822 file | ✅ Yes |
| `POST` | `/emails/import-file` | Batch upload `.json` or `.csv` files | ✅ Yes |
| `POST` | `/emails/import-batch`| Import JSON array of emails | ✅ Yes |
| `GET` | `/emails/{id}` | Get detailed email record & AI analysis | ✅ Yes |
| `PATCH`| `/emails/{id}/read` | Mark email as read / unread | ✅ Yes |
| `PATCH`| `/emails/{id}/toggle-star` | Toggle starred / favorited flag | ✅ Yes |
| `PATCH`| `/emails/{id}/toggle-archive`| Toggle archived state | ✅ Yes |
| `DELETE`| `/emails/{id}` | Delete email record | ✅ Yes |
| `GET` | `/threads` | List email conversation threads | ✅ Yes |
| `GET` | `/threads/{id}` | Get full thread message history | ✅ Yes |

---

## 🤖 3. AI Analysis & Smart Reply (`/emails/{id}/...`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/emails/{id}/reprocess` | Re-run the whole AI pipeline for one email | ✅ Yes |
| `POST` | `/emails/{id}/classify` | Re-run classification only (category, intent, priority, sentiment, reply/action required) | ✅ Yes |
| `POST` | `/emails/{id}/summarize?mode=short\|detailed` | Re-run summarisation only | ✅ Yes |
| `POST` | `/emails/{id}/extract` | Re-run information extraction only | ✅ Yes |
| `POST` | `/emails/{id}/reply` | Generate a smart reply draft (`tone`, optional `custom_instructions`) | ✅ Yes |
| `POST` | `/emails/{id}/reply/{reply_id}/approve` | Approve a draft (optionally with `edited_body`) and record the outbound reply | ✅ Yes |
| `POST` | `/emails/{id}/reply/{reply_id}/reject` | Reject a draft with a reason | ✅ Yes |
| `POST` | `/search/ai` | Ask the AI assistant a question about your emails | ✅ Yes |

`GET /emails` also accepts: `category`, `priority`, `sentiment`, `unread_only`, `reply_required_only`,
`action_required_only`, `starred_only`, `archived`, `search_text`, `sender`, and `date_preset`
(`today`, `yesterday`, `this_week`, `this_month`, `last_month`, `last_7_days`, ...). Filters combine with AND.

--- | :--- | :--- | :--- |
| `POST` | `/ai/analyze` | Trigger manual AI analysis on text | ✅ Yes |
| `POST` | `/ai/smart-reply` | Generate 6-tone smart reply with thread context | ✅ Yes |
| `POST` | `/ai/smart-reply/approve`| Approve smart reply draft and record outbound reply | ✅ Yes |
| `POST` | `/ai/smart-reply/reject` | Reject draft with reason feedback for learning | ✅ Yes |

---

## 🔍 4. Vector Search & RAG Assistant (`/search`, `/assistant`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/search` | Structured search across subject, body, sender, dates | ✅ Yes |
| `POST` | `/assistant/chat` | RAG query processing with vector embeddings & memory | ✅ Yes |

---

## 📋 5. Actions, Tasks & Deadlines (`/actions`, `/deadlines`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/actions` | List extracted action items | ✅ Yes |
| `PATCH`| `/actions/{id}` | Update action item status (pending/completed) | ✅ Yes |
| `GET` | `/deadlines` | List extracted temporal deadlines | ✅ Yes |

---

## 📊 6. Analytics & Performance (`/analytics`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/analytics/overview` | Fetch SLA metrics, category & sentiment breakdown | ✅ Yes |

---

## 🛡️ 7. Admin & Security Governance (`/admin`)

| Method | Endpoint | Description | Required Role |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/stats` | System-wide statistics and active provider info | Admin / Manager |
| `GET` | `/admin/users` | List all registered users | Admin / Manager |
| `PATCH`| `/admin/users/{id}/role` | Change user role (user/manager/admin) | Admin |
| `PATCH`| `/admin/users/{id}/status` | Activate or deactivate user account | Admin |
| `GET` | `/admin/categories` | List email categories | Admin / Manager |
| `POST` | `/admin/categories` | Create custom category | Admin |
| `GET` | `/admin/settings` | Get system configuration settings | Admin / Manager |
| `PUT` | `/admin/settings/{key}` | Update system configuration setting | Admin |
| `POST` | `/admin/emails/{id}/reprocess` | Queue any email for AI re-processing | Admin |
| `POST` | `/admin/emails/retry-failed` | Re-queue emails whose processing failed (`limit`, default 100) | Admin |
| `GET` | `/admin/processing` | Emails per processing status plus recent failures (ids and errors only, no email content) | Admin / Manager |
| `GET` | `/admin/usage` | AI usage: total/failed/24h calls, error rate, latency by operation and provider | Admin / Manager |
| `GET` | `/admin/ai-errors` | Failed AI calls only | Admin / Manager |
| `GET` | `/admin/ai-logs` | View AI execution diagnostic logs | Admin / Manager |
| `GET` | `/admin/audit-logs` | View security audit trail | Admin / Manager |
