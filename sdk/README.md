# agentlens-observe

**Debug AI agents visually** — Python SDK for [AgentLens](https://github.com/tranhoangtu-it/agentlens), the self-hosted AI agent observability platform.

## Install

```bash
pip install agentlens-observe
```

## Quick Start

```python
import agentlens

agentlens.configure(server_url="http://localhost:8000")

@agentlens.trace(name="ResearchAgent")
def run_agent(query: str) -> str:
    with agentlens.span("web_search", "tool_call") as s:
        result = search(query)
        s.set_output(result)
        s.set_cost("gpt-4o", input_tokens=500, output_tokens=200)
    return summarize(result)

run_agent("Latest AI research papers")
# → Traces stream to your AgentLens dashboard
```

## Features

- **2-line integration** — `@agentlens.trace` decorator + `agentlens.span()` context manager
- **Fire-and-forget** — never blocks your agent (daemon thread transport)
- **Async-safe** — uses `contextvars.ContextVar` for trace propagation
- **Cost tracking** — built-in pricing for 12+ models (GPT-4o, Claude, etc.)
- **Framework integrations** — LangChain, CrewAI

## Framework Integrations

### LangChain / LangGraph

```python
from agentlens.integrations.langchain import AgentLensCallbackHandler
agent.run("task", callbacks=[AgentLensCallbackHandler()])
```

### CrewAI

```python
from agentlens.integrations.crewai import patch_crewai
patch_crewai()  # Auto-instruments all Crew runs
```

## License

MIT — see [LICENSE](https://github.com/tranhoangtu-it/agentlens/blob/main/LICENSE)
