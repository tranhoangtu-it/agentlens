---
title: "Multi-tenant Auth"
description: "Add user accounts, JWT sessions, API key auth, and tenant isolation to AgentLens"
status: pending
priority: P1
effort: 16h
branch: kai/feat/multi-tenant-auth
tags: [auth, multi-tenant, security, backend, frontend]
created: 2026-02-28
---

# Multi-tenant Auth — Implementation Plan

## Problem

AgentLens currently has zero authentication — all data is globally visible. For multi-user deployments, each user/org must see only their own traces and alerts.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth library | `PyJWT` + `bcrypt` | Minimal deps, stdlib-friendly, well-maintained |
| Tenant model | User-level (v1) | Simpler; orgs can be added later via `tenant_id` FK |
| API key format | Prefixed `al_` + 32 hex | Self-identifying, easy to grep in logs |
| Session transport | JWT via `Authorization: Bearer` header | SPA-friendly, no CSRF issues |
| Migration | Existing data → "default" tenant | Non-destructive, backward-compatible |

## Phases

| # | Phase | Status | Effort | Files |
|---|-------|--------|--------|-------|
| 1 | [Auth models & storage](phase-01-auth-models-and-storage.md) | pending | 3h | 4 new server files |
| 2 | [Auth middleware](phase-02-auth-middleware.md) | pending | 3h | 3 new + 1 modified server files |
| 3 | [Tenant isolation](phase-03-tenant-isolation.md) | pending | 3h | 5 modified server files |
| 4 | [Dashboard auth UI](phase-04-auth-dashboard-ui.md) | pending | 3h | 6 new + 3 modified TS files |
| 5 | [Migration & seeding](phase-05-migration-and-seeding.md) | pending | 2h | 2 new + 1 modified server files |
| 6 | [Testing](phase-06-testing.md) | pending | 2h | 2 new test files |

## Dependencies

- Phase 1 must complete first (tables needed by all others)
- Phases 2-3 can be done in sequence after Phase 1
- Phase 4 depends on Phase 2 (needs login endpoint)
- Phase 5 depends on Phases 1+3 (needs models + tenant_id column)
- Phase 6 depends on all prior phases

## New Dependencies (requirements.txt)

```
PyJWT>=2.9.0
bcrypt>=4.2.0
```

## Env Vars

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENTLENS_JWT_SECRET` | auto-generated | JWT signing key |
| `AGENTLENS_ADMIN_EMAIL` | `admin@agentlens.local` | Seeded admin email |
| `AGENTLENS_ADMIN_PASSWORD` | `changeme` | Seeded admin password |

## Out of Scope (v1)

- OAuth / SSO providers
- Organization-level tenancy
- Role-based access control (RBAC)
- Password reset / email verification
- Rate limiting on login
