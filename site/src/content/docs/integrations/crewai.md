---
title: CrewAI
description: Integrate AgentLens with CrewAI multi-agent systems
---

## Installation

```bash
pip install agentlens-observe crewai
```

## Setup

```python
import agentlens
from agentlens.integrations.crewai import patch_crewai

agentlens.configure(server_url="http://localhost:3000")
patch_crewai()  # Auto-instruments all Crew runs
```

Call `patch_crewai()` once at startup — before creating any `Crew` instances.

## Usage

```python
from crewai import Agent, Task, Crew

researcher = Agent(
    role="Researcher",
    goal="Find the latest AI research papers",
    backstory="Expert at finding and summarizing academic papers",
    verbose=True,
)

writer = Agent(
    role="Writer",
    goal="Write a clear summary of research findings",
    backstory="Skilled technical writer",
    verbose=True,
)

research_task = Task(
    description="Research the latest papers on LLM reasoning",
    agent=researcher,
)

write_task = Task(
    description="Write a blog post summarizing the research",
    agent=writer,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    verbose=True,
)

# All agent interactions are automatically traced
result = crew.kickoff()
```

## What Gets Traced

- Each agent's task execution as a span
- Tool calls made by agents
- LLM calls with inputs/outputs
- Agent handoffs between crew members
- Overall crew run as a top-level trace
