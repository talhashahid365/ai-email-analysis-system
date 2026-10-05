# ADR 0002: Custom JWT Authentication

## Context
Needed authentication for the API. Options: Clerk, Supabase Auth, Auth.js, or custom JWT.

## Decision
Custom JWT using python-jose and passlib (bcrypt). Includes token revocation via DB denylist and password-change invalidation.

## Alternatives Considered
- **Clerk**: Best DX but vendor lock-in, cost at scale
- **Supabase Auth**: Tied to Supabase database

## Consequences
- Full control over auth flow
- Must maintain security ourselves (bcrypt, token expiry, revocation)
- Consider migrating to Clerk/Auth.js if team grows
