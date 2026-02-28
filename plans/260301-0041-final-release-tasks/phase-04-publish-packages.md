# Phase 4: Push to npm & Docker Hub

## Context Links
- Docker Hub: https://hub.docker.com/r/tranhoangtu/agentlens-observe (new name)
- npm: https://www.npmjs.com/package/agentlens-observe
- PyPI: https://pypi.org/project/agentlens-observe/
- Dockerfile: `Dockerfile` (multi-stage: node build + python runtime)

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 2h
- Build and push Docker image with new name, bump versions if code changed, publish to registries

## Key Insights
- Docker image changes from `tranhoangtu/agentlens` to `tranhoangtu/agentlens-observe`
- Version bump to 0.6.0 across board (new name = new release)
- PyPI: only publish if SDK code changed (security fixes in Phase 2 may touch server only)
- npm: only publish if TS SDK code changed
- Docker: always publish (includes server + dashboard)

## Requirements

### Functional
- Docker image `tranhoangtu/agentlens-observe:0.6.0` and `:latest` available
- All packages at consistent version references in docs

### Non-functional
- Docker image size stays reasonable (<500MB)
- No secrets baked into Docker image

## Implementation Steps

### Step 1: Version bumps

#### Server — no version file, version lives in docs only
Update `docs/project-changelog.md` with v0.6.0 entry.

#### Python SDK (if changes made)
```bash
# sdk/pyproject.toml
version = "0.4.0"  # bump from 0.3.0
```

#### TypeScript SDK (if changes made)
```bash
# sdk-ts/package.json
"version": "0.2.0"  # bump from 0.1.0
```

### Step 2: Build and push Docker image

```bash
# Build multi-arch (optional — arm64 for M-series Macs)
docker buildx build --platform linux/amd64,linux/arm64 \
  -t tranhoangtu/agentlens-observe:0.6.0 \
  -t tranhoangtu/agentlens-observe:latest \
  --push .

# Or single-arch build + push
docker build -t tranhoangtu/agentlens-observe:0.6.0 .
docker tag tranhoangtu/agentlens-observe:0.6.0 tranhoangtu/agentlens-observe:latest
docker push tranhoangtu/agentlens-observe:0.6.0
docker push tranhoangtu/agentlens-observe:latest
```

### Step 3: Publish Python SDK (if changed)

```bash
cd sdk
# Build to /tmp/ to avoid dist/ hook issues
server/.venv/bin/python3 -m build -o /tmp/agentlens-sdk-dist/
# Upload
server/.venv/bin/python3 -m twine upload /tmp/agentlens-sdk-dist/*
# Verify
pip install agentlens-observe==0.4.0
```

### Step 4: Publish TypeScript SDK (if changed)

```bash
cd sdk-ts
npm run build
npm publish --access public
# Verify
npm info agentlens-observe
```

### Step 5: Create GitHub Release

```bash
gh release create v0.6.0 \
  --title "v0.6.0 — Renamed to agentlens-observe" \
  --notes "$(cat <<'EOF'
## What's New

### Renamed to agentlens-observe
- GitHub repo: `tranhoangtu-it/agentlens-observe`
- Docker: `docker run -p 3000:3000 tranhoangtu/agentlens-observe:0.6.0`
- PyPI/npm package names unchanged

### Security Improvements
- Configurable CORS origins (env: AGENTLENS_CORS_ORIGINS)
- Webhook URL validation (SSRF prevention)
- JWT secret warning on startup

### Test Coverage
- 100% server test coverage
- Comprehensive diff, auth seed, alert evaluator tests

### Install
```bash
docker run -p 3000:3000 tranhoangtu/agentlens-observe:0.6.0
pip install agentlens-observe
npm install agentlens-observe
```
EOF
)"
```

### Step 6: Verify all published packages

```bash
# Docker
docker pull tranhoangtu/agentlens-observe:0.6.0
docker run --rm -p 3000:3000 tranhoangtu/agentlens-observe:0.6.0 &
curl http://localhost:3000/api/health
# Should return {"status":"ok"}

# PyPI
pip install agentlens-observe --upgrade
python -c "import agentlens; print('OK')"

# npm
npm info agentlens-observe version
```

## Todo List

- [ ] Bump version numbers in pyproject.toml and/or package.json
- [ ] Build Docker image with new name
- [ ] Push Docker image (0.6.0 + latest tags)
- [ ] Publish Python SDK to PyPI (if changed)
- [ ] Publish TS SDK to npm (if changed)
- [ ] Create GitHub release v0.6.0
- [ ] Verify Docker image works (pull + health check)
- [ ] Verify PyPI install works
- [ ] Verify npm install works
- [ ] Update README quickstart with new Docker image name

## Success Criteria
- `docker pull tranhoangtu/agentlens-observe:0.6.0` succeeds
- `docker run ... /api/health` returns `{"status":"ok"}`
- GitHub release v0.6.0 visible at repo releases page
- All version numbers consistent across docs

## Risk Assessment
- **Docker Hub namespace**: Must verify `tranhoangtu/agentlens-observe` available
- **Breaking existing users**: Old Docker image still available, old pip/npm still work
- **Build failure**: Test Docker build locally before pushing

## Security Considerations
- Never commit .pypirc or npm tokens
- Docker image must not contain .env, secrets, or dev dependencies
- Use `--no-cache-dir` in Dockerfile pip install (already done)
