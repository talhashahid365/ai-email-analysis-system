# MailNexa AI — Threat Model

## Assets
- User email data (confidential business communications)
- Authentication credentials (passwords, tokens)
- AI API keys (financial cost)
- User account data (PII)

## Entry Points
| Entry Point | OWASP Risk | Mitigation Status |
|-------------|-----------|------------------|
| POST /auth/login | A7 Brute Force | ✅ Rate limited (10/min) |
| POST /auth/register | A7 Spam | ⚠️ Rate limited, no CAPTCHA |
| POST /emails/ (upload) | A4 File injection | ✅ Type validated |
| GET /emails/{id} | A1 IDOR | ✅ Filtered by user_id |
| All endpoints | A2 Broken Auth | ✅ JWT required |
| AI endpoints | Cost abuse | ✅ Rate limited |
| Admin endpoints | A5 Broken Access | ✅ role=admin required |

## Mitigations Missing
- [ ] CAPTCHA on signup (A7)
- [ ] CSP headers (A3 XSS)
- [ ] Dependency vulnerability scanning (A6)
- [ ] Penetration test
- [ ] GDPR data export endpoint
