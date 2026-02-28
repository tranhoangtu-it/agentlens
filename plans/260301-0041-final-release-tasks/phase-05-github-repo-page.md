# Phase 5: Improve GitHub Repo Page

## Context Links
- Repo: https://github.com/tranhoangtu-it/agentlens-observe (after rename)
- README.md: `/Users/tranhoangtu/Desktop/PET/my-project/agentlens/README.md`

## Overview
- **Priority:** P2
- **Status:** pending
- **Effort:** 2h
- Professional GitHub repo page: topics, description, badges, social preview

## Key Insights
- First impression matters for open-source adoption
- Badges signal project maturity (CI, coverage, versions)
- Topics improve GitHub search discoverability
- Social preview generates click-through from social media shares

## Implementation Steps

### Step 1: Set repo topics and description via GitHub CLI

```bash
gh repo edit tranhoangtu-it/agentlens-observe \
  --description "Debug AI agents visually — self-hosted, open-source observability for LLM agents" \
  --add-topic ai-agents \
  --add-topic observability \
  --add-topic tracing \
  --add-topic llm \
  --add-topic fastapi \
  --add-topic react \
  --add-topic opentelemetry \
  --add-topic developer-tools \
  --add-topic monitoring \
  --add-topic self-hosted \
  --add-topic langchain \
  --add-topic crewai \
  --add-topic python \
  --add-topic typescript
```

### Step 2: Add badges to README.md

Insert after the `# AgentLens` title, before the description:

```markdown
[![PyPI](https://img.shields.io/pypi/v/agentlens-observe?label=PyPI&color=blue)](https://pypi.org/project/agentlens-observe/)
[![npm](https://img.shields.io/npm/v/agentlens-observe?label=npm&color=red)](https://www.npmjs.com/package/agentlens-observe)
[![Docker](https://img.shields.io/docker/v/tranhoangtu/agentlens-observe?label=Docker&color=2496ED)](https://hub.docker.com/r/tranhoangtu/agentlens-observe)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-116%2B%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()
```

Notes:
- PyPI, npm, Docker badges auto-update from registries
- Tests and Coverage are static badges (update manually or add CI later)
- Keep badges on one or two lines for readability

### Step 3: Create social preview image

Generate a 1280x640 image for GitHub social preview:
- Background: dark (#0d1117 or gradient)
- AgentLens logo/text prominently
- Tagline: "Debug AI agents visually"
- Key visual: simplified agent topology graph
- Tech badges: Python, TypeScript, React, FastAPI

Options:
1. Use Figma/Canva to create
2. Use `ai-multimodal` + `imagemagick` skill if available
3. Simple HTML → screenshot approach

Upload via: GitHub repo settings > Social preview

### Step 4: Enhance README structure

Current README is good but can be improved:
- Add "Why AgentLens?" section comparing to alternatives (brief table)
- Add "Community" section with links
- Ensure demo.gif loads correctly after rename
- Update test count to reflect Phase 1 results

### Step 5: Add .github files

Create community health files:
- `.github/FUNDING.yml` (if applicable)
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`

Bug report template:
```markdown
---
name: Bug Report
about: Report a bug in AgentLens
labels: bug
---

## Description
<!-- What happened? -->

## Steps to Reproduce
1.
2.
3.

## Expected Behavior
<!-- What should happen? -->

## Environment
- AgentLens version:
- Python/Node version:
- OS:
- Docker: Yes/No
```

Feature request template:
```markdown
---
name: Feature Request
about: Suggest an idea for AgentLens
labels: enhancement
---

## Problem
<!-- What problem does this solve? -->

## Proposed Solution
<!-- How would you like it to work? -->

## Alternatives Considered
<!-- Any alternatives? -->
```

## Related Code Files

### Files to MODIFY
- `README.md` — badges, minor structure improvements

### Files to CREATE
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- Social preview image (uploaded via GitHub UI)

## Todo List

- [ ] Set repo description and topics via `gh repo edit`
- [ ] Add badges to README.md header
- [ ] Create social preview image (1280x640)
- [ ] Upload social preview via GitHub settings
- [ ] Add `.github/ISSUE_TEMPLATE/bug_report.md`
- [ ] Add `.github/ISSUE_TEMPLATE/feature_request.md`
- [ ] Update test count in README after Phase 1
- [ ] Verify README renders correctly on GitHub

## Success Criteria
- Repo page shows description, topics, social preview
- README has working badges (PyPI, npm, Docker, license)
- Issue templates available when creating new issues
- Page looks professional and inviting for contributors

## Risk Assessment
- Low risk — cosmetic changes only
- Social preview may need iteration to look good
- Badge URLs must match actual package names post-rename
