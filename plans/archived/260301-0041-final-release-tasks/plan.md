---
title: "Final Release Tasks — Test Coverage, Security, Rename, Publish, Landing Page"
description: "6-phase plan: 100% test coverage, security audit, rename to agentlens-observe, publish Docker/npm, improve GitHub repo, deploy Cloudflare Pages landing + docs"
status: pending
priority: P1
effort: 20h
branch: main
tags: [release, testing, security, rename, deploy, docs]
created: 2026-03-01
---

# Final Release Tasks

## Phases

| # | Phase | Effort | Status | Depends On |
|---|-------|--------|--------|------------|
| 1 | [100% Test Coverage](phase-01-test-coverage.md) | 5h | pending | - |
| 2 | [Security Audit](phase-02-security-audit.md) | 3h | pending | - |
| 3 | [Rename to agentlens-observe](phase-03-rename-agentlens-observe.md) | 4h | pending | 1, 2 |
| 4 | [Push to npm & Docker Hub](phase-04-publish-packages.md) | 2h | pending | 3 |
| 5 | [Improve GitHub Repo Page](phase-05-github-repo-page.md) | 2h | pending | 3 |
| 6 | [Cloudflare Pages — Landing + Docs](phase-06-cloudflare-landing-docs.md) | 4h | pending | 3, 5 |

## Dependency Graph

```
Phase 1 (tests) ──┐
                   ├──> Phase 3 (rename) ──┬──> Phase 4 (publish)
Phase 2 (security)┘                        ├──> Phase 5 (github)──> Phase 6 (cloudflare)
                                           └──> Phase 6 (cloudflare)
```

## Key Risks
- **Rename (Phase 3)**: Highest risk — touches every reference across all packages/docs/Docker
- **Publish (Phase 4)**: Docker Hub/npm namespace must be available
- **Cloudflare (Phase 6)**: Domain config TBD, may need DNS setup

## Key Decisions
- Python import path stays `agentlens` (wheel package name `agentlens-observe`, import `agentlens`)
- TS import stays `agentlens-observe` (unchanged)
- GitHub repo rename: `tranhoangtu-it/agentlens` -> `tranhoangtu-it/agentlens-observe`
- Docker: `tranhoangtu/agentlens-observe:0.6.0` and `:latest`
