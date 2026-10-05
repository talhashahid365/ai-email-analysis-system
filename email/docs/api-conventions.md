# MailNexa AI — API Conventions

## Base URL
- Development: `http://localhost:8000/api`
- API docs (dev only): `http://localhost:8000/api/docs`
- OpenAPI spec: `http://localhost:8000/api/openapi.json`

## Authentication
All protected endpoints require: `Authorization: Bearer <token>`
Obtain token via: `POST /api/auth/login`

## Standard Error Format
```json
{"detail": "Human-readable error message"}
```

## HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 401 | Unauthenticated |
| 403 | Forbidden (role check failed) |
| 404 | Not found or IDOR (resource belongs to another user) |
| 422 | Pydantic validation failed |
| 429 | Rate limit exceeded — check Retry-After header |
| 500 | Internal server error |

## Pagination
List endpoints accept: `?skip=0&limit=50` (max limit: 200)

## Authorization Rules
- All queries filter by `user_id = current_user.id`
- Use `require(user, Action.X)` from `app.permissions` for role checks
- Users get 404 (not 403) when accessing another user's resource

## Rate Limits
| Endpoint Group | Limit |
|----------------|-------|
| Auth (login, register, reset) | 10/min per IP |
| AI endpoints | 30/min per user |
| Upload endpoints | 20/min per user |

## Key Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/register | No | Create account |
| POST | /auth/login | No | Get JWT token |
| GET | /auth/me | Yes | Current user |
| GET | /auth/export-data | Yes | GDPR data export |
| GET | /emails | Yes | List emails |
| POST | /emails | Yes | Ingest email |
| GET | /emails/{id} | Yes | Email detail |
| DELETE | /emails/{id} | Yes | Delete email |
| POST | /ai/analyze/{id} | Yes | Re-analyze |
| POST | /ai/reply/{id} | Yes | Smart reply |
| GET | /analytics/overview | Yes | Dashboard stats |
| GET | /admin/users | Admin | User management |
| GET | /notifications | Yes | Notifications |
| GET | /api/health | No | Health check |
