# Docker Image Rename and Registry Push

**Date**: 2026-03-01 09:14
**Severity**: Medium
**Component**: Docker image, DockerHub registry
**Status**: Resolved

## What Happened

Renamed Docker image from `tranhoangtu/agentlens` to `tranhoangtu/agentlens-observe` to align with official project rename. Updated all documentation references and pushed both `0.6.0` and `latest` tags to Docker Hub.

## The Brutal Truth

This should have been a 5-minute task. It wasn't. The pain was finding every reference scattered across the codebase: README, quickstart guide, GitHub workflows, Docker compose examples, issue templates, deployment docs. Each one had to be updated consistently, or users following old docs would get 404s.

The real frustration was realizing we didn't have a single source of truth for Docker image name. It lived in at least 8 different files with slightly different formats. This is the technical debt of ad-hoc documentation.

## Technical Details

**Files Updated**:
- README.md: Quickstart section with full image name
- Dockerfile: Base image references (stayed the same, only comments)
- docker-compose.yml: Service image reference
- docs/: Multiple deployment guides with image tags
- GitHub workflows: Push/build steps referencing old image name
- Issue templates: Example commands with old image reference
- Architecture docs: References in deployment diagrams

**Docker Hub Push**:
```bash
docker build -t tranhoangtu/agentlens-observe:0.6.0 .
docker tag tranhoangtu/agentlens-observe:0.6.0 tranhoangtu/agentlens-observe:latest
docker push tranhoangtu/agentlens-observe:0.6.0
docker push tranhoangtu/agentlens-observe:latest
```

Both tags now live on Docker Hub publicly.

## What We Tried

Initial plan was regex find-and-replace. That caught maybe 60% of references. The remaining 40% were in slightly different contexts:
- `docker run tranhoangtu/agentlens:0.5.0`
- `image: tranhoangtu/agentlens:latest`
- `FROM tranhoangtu/agentlens:base`
- Documentation prose mentioning the image name

Had to do manual review of each file to catch variations.

## Root Cause Analysis

**Why Documentation Was Scattered**:

We didn't follow DRY (Don't Repeat Yourself) for documentation. Image name should be defined once (in a config or constants file) and referenced everywhere. Instead, we copied the name into each doc.

**Why This Happened Late**:

GitHub repo rename came before realizing we needed to update image names everywhere. Should have done this rename holistically: repo name + image name + package names + all docs at once.

## Lessons Learned

1. **Documentation Consistency**: Use variables/templates for repeating values. In markdown/docs, define image name once, reference it elsewhere.

2. **Breaking Changes Need Migration Path**: Old users pulling `tranhoangtu/agentlens` will get 404. Should have either:
   - Kept old image name as mirror (redirects to new name)
   - Created migration doc explaining the change
   - Added deprecation warning to old image

3. **Automation Over Manual Updates**: Could have written a script that updates all refs at once, ensuring consistency.

4. **Single Source of Truth**: Define Docker image name in `Makefile`, `.github/workflows/`, and docs generation uses that value.

## Next Steps

- Consider keeping `tranhoangtu/agentlens:0.5.0` on Docker Hub as legacy reference
- Add migration note to GitHub release for users on old image name
- Document standard for future image names (always `agentlens-observe`, never just `agentlens`)

Commits: 54d3efa, 5a70ba4
