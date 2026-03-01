# Phase 3: Rename to agentlens-observe

## Context Links
- GitHub repo: https://github.com/tranhoangtu-it/agentlens
- Docker Hub: https://hub.docker.com/r/tranhoangtu/agentlens
- PyPI: https://pypi.org/project/agentlens-observe/ (already correct)
- npm: https://www.npmjs.com/package/agentlens-observe (already correct)

## Overview
- **Priority:** P1 (highest risk)
- **Status:** pending
- **Effort:** 4h
- Rename GitHub repo, Docker image, and all internal references from `agentlens` to `agentlens-observe`

## Key Insights
- **PyPI package already named `agentlens-observe`** — no change needed
- **npm package already named `agentlens-observe`** — no change needed
- **Python import path stays `agentlens`** (wheel maps `agentlens` package to `agentlens-observe` distribution)
- **Primary changes:** GitHub repo name, Docker image name, doc references, docker-compose.yml

## What Changes vs What Stays

| Item | Current | Target | Action |
|------|---------|--------|--------|
| GitHub repo | tranhoangtu-it/agentlens | tranhoangtu-it/agentlens-observe | Rename via GitHub settings |
| Docker image | tranhoangtu/agentlens | tranhoangtu/agentlens-observe | New image name |
| docker-compose.yml | build: . | image: tranhoangtu/agentlens-observe | Update |
| README docker run | tranhoangtu/agentlens:0.5.0 | tranhoangtu/agentlens-observe:0.6.0 | Update |
| PyPI package | agentlens-observe | agentlens-observe | NO CHANGE |
| npm package | agentlens-observe | agentlens-observe | NO CHANGE |
| Python import | `import agentlens` | `import agentlens` | NO CHANGE |
| TS import | `agentlens-observe` | `agentlens-observe` | NO CHANGE |
| pyproject.toml URLs | github.com/.../agentlens | github.com/.../agentlens-observe | Update |
| Docs references | /agentlens | /agentlens-observe | Update selectively |

## Related Code Files

### Files to MODIFY
1. `README.md` — Docker references, any GitHub URLs
2. `Dockerfile` — no change needed (builds from source)
3. `docker-compose.yml` — image name
4. `sdk/pyproject.toml` — project.urls (Homepage, Repository, Issues)
5. `docs/deployment-guide.md` — Docker references
6. `docs/project-overview-pdr.md` — repo URL, Docker references
7. `docs/codebase-summary.md` — repo URL references
8. `docs/project-changelog.md` — Docker references
9. `docs/system-architecture.md` — if Docker image mentioned
10. `examples/README.md` — if Docker image mentioned

### Files that stay the SAME
- `sdk/agentlens/` — all Python SDK files (import path unchanged)
- `sdk-ts/` — all TS SDK files (package name already correct)
- `server/` — all server files (no repo name references in code)
- `dashboard/` — all dashboard files (no repo name references)

## Implementation Steps

### Step 1: Rename GitHub repo
```bash
# Via GitHub CLI
gh repo rename agentlens-observe --repo tranhoangtu-it/agentlens
# GitHub auto-creates redirect from old URL
```

### Step 2: Update local git remote
```bash
git remote set-url origin https://github.com/tranhoangtu-it/agentlens-observe.git
```

### Step 3: Update pyproject.toml URLs
```toml
[project.urls]
Homepage = "https://github.com/tranhoangtu-it/agentlens-observe"
Repository = "https://github.com/tranhoangtu-it/agentlens-observe"
Issues = "https://github.com/tranhoangtu-it/agentlens-observe/issues"
```

### Step 4: Update docker-compose.yml
```yaml
services:
  agentlens:
    image: tranhoangtu/agentlens-observe:latest
    # or build: . for local dev
    ports:
      - "3000:3000"
    volumes:
      - ./data:/data
    environment:
      - AGENTLENS_DB_PATH=/data/agentlens.db
```

### Step 5: Update README.md
Search-replace `tranhoangtu/agentlens:` → `tranhoangtu/agentlens-observe:`
Search-replace `tranhoangtu-it/agentlens` → `tranhoangtu-it/agentlens-observe` (but NOT in import examples)

Careful: Do NOT change:
- `import agentlens` (Python)
- `from agentlens.integrations...` (Python)
- `import * as agentlens from "agentlens-observe"` (already correct)

### Step 6: Update docs/*.md
For each doc file, find-replace GitHub repo URLs and Docker image references.

### Step 7: Update examples/README.md
If it references the Docker image or GitHub URLs.

### Step 8: Grep verification
```bash
# Should find ZERO matches after rename (excluding node_modules, .git, .venv):
grep -r "tranhoangtu/agentlens[^-]" --include="*.md" --include="*.py" --include="*.toml" --include="*.yml" --include="*.json" .
grep -r "tranhoangtu-it/agentlens[^-]" --include="*.md" --include="*.py" --include="*.toml" --include="*.yml" --include="*.json" .
# Note: "agentlens" alone without prefix is fine (it's the Python package name)
```

## Todo List

- [ ] Rename GitHub repo via `gh repo rename`
- [ ] Update git remote URL
- [ ] Update `sdk/pyproject.toml` URLs
- [ ] Update `docker-compose.yml` image name
- [ ] Update `README.md` Docker + GitHub references
- [ ] Update `docs/deployment-guide.md`
- [ ] Update `docs/project-overview-pdr.md`
- [ ] Update `docs/codebase-summary.md`
- [ ] Update `docs/project-changelog.md`
- [ ] Update `examples/README.md`
- [ ] Grep verification: zero stale references
- [ ] Run all tests to confirm no regressions
- [ ] Verify GitHub redirect works (old URL → new URL)

## Success Criteria
- `gh repo view tranhoangtu-it/agentlens-observe` succeeds
- Old URL `github.com/tranhoangtu-it/agentlens` redirects to new URL
- `grep -r "tranhoangtu/agentlens[^-]"` returns zero matches (excluding .git)
- All 86+ server tests + 30 TS SDK tests still pass
- `pip install agentlens-observe` still works (PyPI unchanged)
- `npm install agentlens-observe` still works (npm unchanged)

## Risk Assessment
- **GitHub redirect**: GitHub maintains redirects for renamed repos. Old URLs keep working.
- **Docker Hub**: Old image `tranhoangtu/agentlens` stays available. New image is separate namespace.
- **Broken links**: External sites linking to old GitHub URL → redirect handles it
- **Existing users**: `pip install` and `npm install` unaffected — package names unchanged

## Security Considerations
- No secrets in rename
- Ensure no `.env` or credentials committed during this change
