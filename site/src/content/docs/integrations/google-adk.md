---
title: Google ADK
description: Integrate AgentLens with Google Agent Development Kit
---

## Installation

```bash
pip install agentlens-observe google-adk
```

## Setup

```python
import agentlens
from agentlens.integrations.google_adk import patch_google_adk

agentlens.configure(server_url="http://localhost:3000")
patch_google_adk()  # Patches Agent.run and tool invocations
```

Call `patch_google_adk()` once at startup — before creating any agents.

## Usage

```python
from google.adk.agents import Agent
from google.adk.tools import google_search

def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {"city": city, "temperature": 22, "condition": "sunny"}

agent = Agent(
    name="WeatherAgent",
    model="gemini-2.0-flash",
    description="Provides weather information and web search",
    tools=[get_weather, google_search],
)

# All agent interactions are automatically traced
result = await agent.run("What's the weather in Tokyo and any recent news?")
```

## What Gets Traced

- `Agent.run()` calls as top-level traces
- Tool invocations with inputs and outputs
- Gemini model calls with prompt and response
- Multi-turn conversation steps
- Function call → result cycles

## Gemini Cost Tracking

AgentLens automatically tracks token costs for Gemini models:
- `gemini-2.0-flash`
- `gemini-1.5-pro`
- `gemini-1.5-flash`
