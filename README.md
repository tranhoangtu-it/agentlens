# agentlens

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

Self-hosted observability platform for debugging AI agents. Trace tool calls, inspect decision trees, and monitor agent behavior. An open-source alternative to LangSmith and Langfuse.

## Features

- Tool call tracing and timeline visualization
- Decision tree inspection
- Memory and state monitoring
- Handoff tracking between agents
- Real-time dashboard
- SDKs for Python and TypeScript

## Architecture

```
sdk/           # Python SDK (PyPI)
sdk-ts/        # TypeScript SDK (npm)
server/        # Backend API
dashboard/     # React web UI
```

## Quick Start (Docker)

```bash
docker compose up
```

Dashboard available at `http://localhost:3000`

## SDK Installation

**Python**
```bash
pip install agentlens
```

**TypeScript**
```bash
npm install agentlens
```

## Usage

```python
from agentlens import AgentLens

lens = AgentLens(endpoint="http://localhost:8000")

with lens.trace("my-agent"):
    # Your agent code here
    lens.log_tool_call("search", {"query": "test"})
```

## License

See [LICENSE](./LICENSE) for details.
