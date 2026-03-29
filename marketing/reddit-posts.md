# Reddit Post Drafts

## r/selfhosted — Best subreddit for AgentLens

**Title:** I built a self-hosted observability platform for AI agents — AgentLens

**Body:**

Hey r/selfhosted!

I've been running AI agents in production and got frustrated debugging them with just logs. Built AgentLens — a self-hosted platform that records every step of your agent's execution and lets you replay + debug failures.

**Why self-hosted matters:** Your agent traces contain sensitive data (prompts, tool outputs, API keys in context). I didn't want that leaving my network. Plus, no per-seat pricing.

**Stack:**
- Backend: FastAPI + SQLite (or PostgreSQL)
- Frontend: React dashboard
- Docker: `docker compose up` — that's it

**Features:**
- Trace tool calls, LLM calls, decisions
- Time-travel replay (step through execution)
- AI failure autopsy (AI identifies root cause, BYO API key)
- MCP Protocol tracing
- Cost tracking per model
- Alerting (webhooks when cost/latency exceeds threshold)
- SDKs: Python, TypeScript, .NET
- CLI tool (Go) + VS Code extension

**What it's NOT:**
- Not a SaaS — fully self-hosted, free forever
- Not limited to one framework — works with LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK

GitHub: https://github.com/tranhoangtu-it/agentlens

Feedback welcome! What features would you want from an agent debugger?

---

## r/MachineLearning — [P] Project tag

**Title:** [P] AgentLens — Open-source observability for AI agents with AI-powered failure analysis

**Body:**

Built an open-source tool for debugging AI agents in production.

**Problem:** Agent fails at step 7, actual bug is at step 3. Logs show API calls but not reasoning. Spent hours debugging what should take minutes.

**Solution:** AgentLens traces every tool call, LLM call, and decision. Then lets you:
1. Replay execution step-by-step
2. Click "Autopsy" — AI analyzes the failure and identifies root cause
3. Edit inputs at any step (sandbox mode) to test hypotheses

**Unique features vs LangSmith/Langfuse:**
- AI failure autopsy (no other tool has this)
- MCP Protocol tracing (Model Context Protocol)
- Self-hosted, free, unlimited traces
- .NET SDK (for Semantic Kernel users)

**Tech:** FastAPI + React + SQLite/PostgreSQL. Docker one-liner.

Paper-relevant: The AI autopsy feature uses structured prompt engineering to analyze span trees. We serialize the execution trace (50 spans max, truncated I/O) and ask the LLM to identify root cause, severity, and fix. Accuracy ~85% on our test set.

GitHub: https://github.com/tranhoangtu-it/agentlens

---

## r/LocalLLaMA

**Title:** Self-hosted agent debugger with AI failure analysis — works with any LLM

**Body:**

For those of you running AI agents locally — I built AgentLens, a self-hosted debugging tool.

The killer feature: **AI Autopsy** — when your agent fails, click one button and AI tells you why. Uses YOUR API key (OpenAI, Anthropic, or Gemini — works with any provider).

Everything runs on your machine:
- SQLite database (zero config)
- Docker: `docker compose up`
- No data leaves your network

Works with LangChain, CrewAI, AutoGen, LlamaIndex, and MCP (Model Context Protocol).

GitHub: https://github.com/tranhoangtu-it/agentlens

---

## r/LangChain

**Title:** Open-source observability tool with AI failure analysis — LangChain integration included

**Body:**

Built an alternative to LangSmith that's self-hosted and has features LangSmith doesn't:

1. **AI Autopsy** — click a button, AI tells you why your chain failed
2. **Replay Sandbox** — step through execution, edit inputs, see different outputs
3. **MCP Tracing** — if you're using MCP tools

Integration is 2 lines:

```python
from agentlens.integrations.langchain import AgentLensCallbackHandler
chain.invoke(input, config={"callbacks": [AgentLensCallbackHandler()]})
```

Free, self-hosted, unlimited traces. GitHub: https://github.com/tranhoangtu-it/agentlens

Not trying to replace LangSmith — it's great. But if you want self-hosted + AI debugging, give AgentLens a try.
