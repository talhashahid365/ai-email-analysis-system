# MailNexa AI — System Design

## Problem Statement
Professionals and teams waste 2-3 hours daily managing email. MailNexa AI automates email triage, categorization, priority scoring, and smart reply generation using AI, reducing email management time by 70%.

## User Roles
| Role | Description | Count (Y1 estimate) |
|------|-------------|---------------------|
| User | Individual professional, manages own inbox | Primary users, ~10K |
| Manager | Team lead with oversight of team email analytics | ~1K |
| Admin | System administrator, manages users and settings | ~50 |

## Core User Flows
1. **Email Ingestion**: Upload email → AI categorizes + prioritizes + extracts actions
2. **Inbox Management**: View/filter/search emails by category, priority, sentiment
3. **Smart Reply**: Select email → AI suggests reply → Edit/send
4. **AI Assistant**: Chat with AI about inbox, get summaries, ask questions
5. **Analytics**: View email volume, category breakdown, response time trends

## Functional Requirements
- Email upload (EML/text) and analysis via AI
- Category classification (10+ categories)
- Priority scoring (LOW/MEDIUM/HIGH/CRITICAL)
- Sentiment analysis
- Action item and deadline extraction
- Smart reply generation
- Inbox search and filtering
- Role-based access (User/Manager/Admin)
- Admin: user management, role assignment, system config
- Notifications for urgent emails

## Non-Functional Requirements
| Requirement | Target |
|-------------|--------|
| API response time (p95) | < 500ms (excluding AI calls) |
| AI analysis time | < 5 seconds |
| Uptime | 99.5% |
| Data isolation | Per-user (multi-tenant in roadmap) |
| Security | OWASP Top 10 mitigated |

## Out of Scope (v1)
- Gmail/Outlook OAuth direct integration
- Real-time email sync (IMAP/SMTP)
- Mobile native apps
- Stripe payments / billing
- Multi-org tenancy (planned for v2)

## Open Questions
- [ ] When to add organization_id multi-tenancy?
- [ ] Which LLM provider as default? (currently heuristic fallback)
- [ ] Email sending (SMTP outbound) in scope for v1.5?
