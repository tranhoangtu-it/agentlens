# Show HN Draft

## Title Options (pick one)

1. Show HN: AgentLens – Chrome DevTools for AI Agents (open-source, self-hosted)
2. Show HN: I built an AI that debugs your AI agents
3. Show HN: AgentLens – Self-hosted alternative to LangSmith with AI failure analysis

## Post Body

Hi HN! I'm Tu, and I built AgentLens — an open-source observability platform for AI agents.

**The problem:** When your AI agent fails in production, you're blind. Logs show API calls, but they don't show you WHY the agent chose tool A over tool B, or WHERE its reasoning went wrong. I spent hours reading through trace logs trying to debug a multi-step agent that kept failing at step 7, when the actual bug was at step 3.

**What AgentLens does:**

- Records every step of your agent's execution (tool calls, LLM calls, handoffs)
- Lets you replay the execution step-by-step, like a flight recorder
- **AI-powered failure autopsy** — click "Autopsy" on a failed trace and AI identifies the root cause and suggests a fix (BYO API key)
- **MCP Protocol tracing** — first tool to trace Model Context Protocol calls visually
- Prompt versioning, LLM-as-Judge evaluations, alerting

**SDKs:** Python, TypeScript, .NET (yes, .NET — no other observability tool has this)

**Developer tools:** Go CLI (`agentlens traces tail` for real-time streaming), VS Code extension

**Why not LangSmith/Langfuse?**
- Self-hosted, free forever (unlimited traces)
- AI autopsy (no one else has this)
- MCP tracing (no one else has this)
- .NET SDK (no one else has this)
- Plugin system for extensibility

**Tech stack:** FastAPI + React + SQLite/PostgreSQL. Docker one-liner: `docker compose up`

**Try it:**
```
pip install agentlens-observe
docker compose up
```

GitHub: https://github.com/tranhoangtu-it/agentlens

I'd love feedback on what features matter most to you. Happy to answer any questions!

---

## Tips for posting
- Post on Tuesday-Wednesday, 8-10 AM EST
- Be online for 8 hours to answer comments
- Have 3-5 friends upvote in first 30 minutes
- Be genuine, answer every comment thoughtfully
