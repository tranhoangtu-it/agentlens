# Why I Built AgentLens: Chrome DevTools for AI Agents

*Publish on: DEV.to, Hashnode, Medium, Viblo (Vietnamese version)*

---

My AI agent kept failing in production. The error showed up at step 7, but the actual bug was at step 3. I spent 4 hours reading through trace logs before finding it.

That's when I realized: **we need Chrome DevTools for AI agents.**

## The Problem Nobody Talks About

Everyone's building AI agents. LangChain, CrewAI, AutoGen — the frameworks are amazing. But when your agent breaks in production, you're on your own.

Traditional logging gives you API calls and timestamps. But it doesn't answer:
- Why did the agent choose tool A over tool B?
- Where exactly did the reasoning go wrong?
- Was it a context window overflow or a hallucinated tool call?

I've debugged hundreds of AI agent failures. The patterns are always the same:
1. **Context window overflow** — agent stuffs too much into the prompt
2. **Tool selection errors** — wrong tool for the task
3. **Infinite loops** — agent keeps retrying the same failed approach
4. **Hallucinated tool calls** — agent invents tools that don't exist
5. **Missing error handling** — silent failures cascade

## What I Built

AgentLens is an open-source, self-hosted observability platform. Think of it as Chrome DevTools, but for AI agents.

### Trace Everything

Drop in 2 lines of code:

```python
import agentlens

@agentlens.trace
def my_agent(query):
    # Your agent code — every tool call, LLM call, and decision is recorded
    pass
```

### Replay Like a Flight Recorder

Time-travel through your agent's execution step-by-step. See exactly what happened at each point. Edit inputs at any step and see how the output changes.

### AI Autopsy (My Favorite Feature)

Click "Autopsy" on a failed trace. AI analyzes the full execution tree and tells you:
- **Root cause:** "Context window overflow at step 4 caused by accumulating search results without summarization"
- **Severity:** Critical
- **Suggested fix:** "Add a summarization step between search and analysis to keep context under 8K tokens"

This is the feature no one else has. LangSmith doesn't have it. Langfuse doesn't have it.

### MCP Protocol Tracing

If you're using MCP (Model Context Protocol) — which Claude, Cursor, and Windsurf all use — AgentLens is the only tool that traces MCP calls visually.

```python
from agentlens.integrations.mcp import patch_mcp
patch_mcp()  # Auto-instruments all MCP tool calls
```

## Why Self-Hosted?

I believe your agent data should stay on your infrastructure:
- No vendor lock-in
- No data leaving your network
- No per-seat pricing that scales with your team
- Free forever, unlimited traces

## The Tech Stack

- **Backend:** FastAPI + SQLModel (SQLite for dev, PostgreSQL for prod)
- **Dashboard:** React 19 + Vite + Tailwind CSS
- **SDKs:** Python, TypeScript, .NET 8, Go CLI
- **Infrastructure:** Docker one-liner, GitHub Actions CI

## What's Next

I'm working on:
- Conference talks (applying to PyCon, .NET Conf)
- Integration PRs to LangChain, CrewAI, AutoGen docs
- Cloud-hosted version for teams who don't want to self-host

## Try It

```bash
pip install agentlens-observe
docker compose up  # Dashboard at http://localhost:3000
```

GitHub: https://github.com/tranhoangtu-it/agentlens

Star it if you find it useful. Every star helps an open-source developer keep going.

---

*Tags: #ai #agents #observability #opensource #debugging*
