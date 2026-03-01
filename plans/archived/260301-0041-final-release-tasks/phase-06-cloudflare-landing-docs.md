# Phase 6: Cloudflare Pages — Landing Page + Docs Site

## Context Links
- Cloudflare Pages docs: https://developers.cloudflare.com/pages/
- Current docs: `docs/` directory (markdown files)
- GitHub repo: https://github.com/tranhoangtu-it/agentlens-observe

## Overview
- **Priority:** P2
- **Status:** pending
- **Effort:** 4h
- Single-page marketing landing + comprehensive documentation, deployed to Cloudflare Pages

## Key Insights
- Cloudflare Pages: free tier, auto-deploy from GitHub, custom domain support
- Two approaches: (A) single Vite/Astro site with landing + docs, or (B) separate landing + docs subpaths
- **Recommended: Astro + Starlight** — purpose-built for docs, supports landing page, deploys to Cloudflare Pages natively
- Alternative: simple static HTML/CSS landing page + VitePress/Docusaurus for docs

## Architecture

### Option A: Astro + Starlight (Recommended)
```
site/
├── astro.config.mjs
├── package.json
├── src/
│   ├── content/
│   │   └── docs/          # Documentation pages (markdown)
│   │       ├── index.md
│   │       ├── getting-started/
│   │       │   ├── quickstart.md
│   │       │   ├── docker.md
│   │       │   └── configuration.md
│   │       ├── sdks/
│   │       │   ├── python.md
│   │       │   └── typescript.md
│   │       ├── integrations/
│   │       │   ├── langchain.md
│   │       │   ├── crewai.md
│   │       │   ├── autogen.md
│   │       │   ├── llamaindex.md
│   │       │   └── google-adk.md
│   │       ├── features/
│   │       │   ├── trace-comparison.md
│   │       │   ├── replay.md
│   │       │   ├── alerting.md
│   │       │   ├── opentelemetry.md
│   │       │   └── auth.md
│   │       └── api/
│   │           └── rest-api.md
│   └── pages/
│       └── index.astro     # Landing page (custom, not Starlight)
├── public/
│   ├── demo.gif
│   └── screenshots/
└── wrangler.toml            # Cloudflare Pages config (optional)
```

### Option B: Simple static landing (lower effort, less polished)
```
site/
├── index.html              # Single-page landing
├── docs/                   # VitePress or plain HTML docs
└── _redirects              # Cloudflare Pages redirect rules
```

**Decision: Go with Option A (Astro + Starlight)** — better DX, auto-generates nav/search, looks professional.

## Requirements

### Functional — Landing Page
- Hero section: title, tagline, CTA buttons (Get Started, View on GitHub)
- Features grid: 6-8 key features with icons
- Quickstart code snippet (Python + TypeScript tabs)
- Comparison table: AgentLens vs LangSmith vs Langfuse vs Phoenix
- Social proof / stats (if available): test count, GitHub stars, npm downloads
- Footer: links, license

### Functional — Docs Site
- Getting Started: quickstart, Docker setup, configuration
- Python SDK: configure, trace, span, log, cost, exporters
- TypeScript SDK: configure, trace, span, log, transport
- Integrations: LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK, OpenTelemetry
- Features: trace comparison, replay, alerting, auth
- API Reference: REST endpoints (from main.py routes)
- Deployment: Docker, PostgreSQL, environment variables

### Non-functional
- PageSpeed score > 90
- Mobile responsive
- Dark mode (Starlight has built-in)
- Search (Starlight has built-in)

## Implementation Steps

### Step 1: Initialize Astro + Starlight project

```bash
cd /Users/tranhoangtu/Desktop/PET/my-project/agentlens
npm create astro@latest site -- --template starlight
cd site
npm install
```

### Step 2: Configure Astro

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'AgentLens',
      description: 'Debug AI agents visually',
      social: {
        github: 'https://github.com/tranhoangtu-it/agentlens-observe',
      },
      sidebar: [
        { label: 'Getting Started', items: [
          { label: 'Quickstart', link: '/docs/getting-started/quickstart/' },
          { label: 'Docker Setup', link: '/docs/getting-started/docker/' },
          { label: 'Configuration', link: '/docs/getting-started/configuration/' },
        ]},
        { label: 'SDKs', items: [
          { label: 'Python SDK', link: '/docs/sdks/python/' },
          { label: 'TypeScript SDK', link: '/docs/sdks/typescript/' },
        ]},
        { label: 'Integrations', autogenerate: { directory: 'docs/integrations' } },
        { label: 'Features', autogenerate: { directory: 'docs/features' } },
        { label: 'API Reference', items: [
          { label: 'REST API', link: '/docs/api/rest-api/' },
        ]},
      ],
    }),
  ],
});
```

### Step 3: Create landing page (`src/pages/index.astro`)

Key sections:
1. **Hero**: "Debug AI agents visually" + demo.gif + CTA
2. **Features**: 8-card grid (live streaming, topology graph, comparison, replay, alerting, OTel, multi-tenant, self-hosted)
3. **Quickstart**: tabbed Python/TypeScript code
4. **Comparison table**: vs LangSmith, Langfuse, Phoenix
5. **Footer**: MIT license, GitHub link

### Step 4: Create documentation content

Migrate from existing `docs/` and `README.md`:
- Extract quickstart from README
- Extract SDK usage from README + sdk/README.md
- Extract integration examples from README
- Write API reference from main.py + alert_routes.py + auth_routes.py routes
- Write deployment guide from docs/deployment-guide.md
- Write configuration reference (all AGENTLENS_* env vars)

### Step 5: Deploy to Cloudflare Pages

```bash
# Option 1: Cloudflare Pages via GitHub integration
# Connect repo, set build command: cd site && npm run build
# Set build output: site/dist/

# Option 2: Wrangler CLI
cd site
npx wrangler pages deploy dist/ --project-name agentlens
```

### Step 6: Custom domain (optional)

If `agentlens.dev` or similar available:
```bash
npx wrangler pages project create agentlens
# Then add custom domain in Cloudflare dashboard
```

## Environment Variables Reference (for docs)

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTLENS_DB_PATH` | `./agentlens.db` | SQLite database path |
| `DATABASE_URL` | `sqlite:///./agentlens.db` | PostgreSQL connection string |
| `AGENTLENS_JWT_SECRET` | auto-generated | JWT signing secret (set in production!) |
| `AGENTLENS_ADMIN_EMAIL` | `admin@agentlens.local` | Default admin email |
| `AGENTLENS_ADMIN_PASSWORD` | `changeme` | Default admin password |
| `AGENTLENS_CORS_ORIGINS` | `*` (after Phase 2 fix) | Comma-separated allowed origins |

## Todo List

- [ ] Initialize Astro + Starlight project in `site/` directory
- [ ] Configure sidebar navigation
- [ ] Create landing page (hero, features, quickstart, comparison)
- [ ] Write Getting Started docs (quickstart, docker, config)
- [ ] Write Python SDK docs
- [ ] Write TypeScript SDK docs
- [ ] Write Integration docs (5 frameworks + OTel)
- [ ] Write Feature docs (comparison, replay, alerting, auth)
- [ ] Write API Reference (REST endpoints)
- [ ] Write Deployment guide (Docker, PostgreSQL, env vars)
- [ ] Copy screenshots/demo.gif to `site/public/`
- [ ] Test local build: `npm run build && npm run preview`
- [ ] Deploy to Cloudflare Pages
- [ ] Verify deployment works
- [ ] Add site URL to GitHub repo "About" section
- [ ] Add site URL to README

## Success Criteria
- Landing page loads with hero, features, quickstart, comparison
- Docs site has working navigation, search, dark mode
- All 5 integration guides present with code examples
- API reference covers all REST endpoints
- Deployed to Cloudflare Pages with working URL
- PageSpeed > 90 on mobile and desktop

## Risk Assessment
- **Astro/Starlight version**: Use latest stable, avoid pre-release
- **Content accuracy**: All code examples must match actual API
- **Domain availability**: May need to use `agentlens-observe.pages.dev` initially
- **Build time**: Cloudflare Pages has 20-minute build limit — Astro builds are fast (<1 min)

## Security Considerations
- No secrets in static site
- No API calls from landing page (purely static)
- HTTPS enforced by Cloudflare automatically
