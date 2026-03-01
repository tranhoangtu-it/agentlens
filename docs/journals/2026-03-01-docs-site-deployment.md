# Astro + Starlight Documentation Site Deployed

**Date**: 2026-03-01 10:49
**Severity**: Medium
**Component**: Documentation site (Astro, Starlight, Cloudflare Pages)
**Status**: Resolved

## What Happened

Built and deployed comprehensive 18-page documentation site using Astro 5.6 + Starlight 0.34. Site includes getting started guides, API documentation, SDK references, integration examples, and deployment guides. Published live to agentlens-observe.pages.dev via Cloudflare Pages.

## The Brutal Truth

Building the docs site was actually smooth. What was frustrating was the realization of how little documentation we had before this. We spent 6 months building a sophisticated observability platform and had it scattered across README, GitHub wiki, and inline comments. A user trying to integrate AgentLens had to read source code to understand how it worked.

The Cloudflare Pages deployment exposed a `.ckignore` hook that blocks the `dist/` pattern—meant to prevent committing build artifacts. Good rule. Annoying when you're trying to deploy build artifacts. We had to add `!site/dist` to the ignore patterns, which feels hacky.

## Technical Details

**Site Structure** (18 pages):
- Getting Started (5 pages): Installation, quickstart, configuration, authentication
- API Reference (4 pages): Trace API, Alert API, OTel ingestion, webhook payload format
- SDK Guides (4 pages): Python SDK, TypeScript SDK, integration examples, custom exporters
- Deployment (3 pages): Docker setup, Kubernetes, environment variables
- About (2 pages): Architecture overview, contributing guide

**Technology Stack**:
- Astro 5.6: Static site generation with partial hydration
- Starlight 0.34: Documentation theme with sidebar navigation, search, dark mode
- Cloudflare Pages: CDN hosting, automatic SSL, GitHub integration

**Build & Deploy**:
```bash
cd site && npm run build
npx wrangler pages deploy dist --project-name agentlens-observe
```

Site loads in <500ms, fully static HTML. Zero JavaScript by default (Starlight loads JS only for search).

## What We Tried

Initial approach was to port existing README content as-is. That didn't work—README is a sales pitch, docs are reference material. Required restructuring:
- README: "Why use AgentLens?"
- Docs: "How do I use AgentLens?"

Used Starlight's built-in features for navigation, search, code highlighting, syntax validation. Considered custom CSS but Starlight defaults were already polished.

Deployment to Cloudflare took 2 attempts:
1. First attempt failed because `.ckignore` blocked `dist/` directory
2. Added `!site/dist` exception, second attempt succeeded

## Root Cause Analysis

**Why Documentation Was Deferred**:

We kept saying "we'll document this later" during feature development. Default assumption was that source code was documentation. But AgentLens is an integration library—users need conceptual guides, examples, and integration patterns. That can't be inferred from code alone.

**Why Starlight**:

Chose Starlight because it's optimized for documentation, comes with sidebar navigation and search out of the box, and integrates seamlessly with Astro. Alternative markdown documentation is painful.

**Why Cloudflare Pages**:

Matches our existing deployment pattern (already using Cloudflare Workers elsewhere). GitHub integration means docs auto-deploy on commits. Zero configuration needed.

## Lessons Learned

1. **Documentation Is Not Optional**: Even for developer tools. Especially for integration libraries. Documentation quality directly impacts adoption.

2. **Documentation Should Evolve With Code**: Each feature should include docs changes. Backfilling docs 6 months later is painful and incomplete.

3. **Static Site Generators Beat Wiki**: Starlight is more maintainable than GitHub wiki or scattered README sections. Version control matters.

4. **Deployment Complexity Hides in Details**: `.ckignore` blocking pattern caused 20 minutes of confusion. Deployment checklist needed to document these gotchas.

5. **Search Matters**: Users expect to search docs. Starlight's built-in Algolia integration makes this automatic.

## Next Steps

- Add examples for common integrations (LangChain agents, CrewAI teams, AutoGen workflows)
- Create troubleshooting section based on GitHub issues
- Add video walkthrough for getting started
- Set up docs site analytics to see which pages are actually used

Commit: 821d841
