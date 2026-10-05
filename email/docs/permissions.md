# MailNexa AI — Permissions Matrix

All permission checks use the central `can(user, action)` function in `app/permissions.py`.

## Role × Action Matrix

| Action | User | Manager | Admin |
|--------|------|---------|-------|
| email:read | ✅ | ✅ | ✅ |
| email:create | ✅ | ✅ | ✅ |
| email:delete | ✅ (own only) | ✅ (own only) | ✅ (any) |
| ai:analyze | ✅ | ✅ | ✅ |
| ai:reply | ✅ | ✅ | ✅ |
| analytics:read | ✅ (own) | ✅ (team) | ✅ (all) |
| analytics:advanced | ❌ | ✅ | ✅ |
| manager:team | ❌ | ✅ | ✅ |
| admin:users | ❌ | ❌ | ✅ |
| admin:settings | ❌ | ❌ | ✅ |
| admin:audit | ❌ | ❌ | ✅ |

## Authorization Rules
1. Every endpoint checks authentication (401 if no token)
2. Every endpoint checks role permission (403 if insufficient role)
3. Every resource fetch filters by `user_id` (404 if not owner)
4. Users always get 404 (not 403) when accessing another user's resource by ID
5. Frontend hides actions the user can't take, but server is source of truth
