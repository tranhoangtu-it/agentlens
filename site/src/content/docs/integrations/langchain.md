---
title: LangChain / LangGraph
description: Integrate AgentLens with LangChain and LangGraph agents
---

## Installation

```bash
pip install agentlens-observe langchain
```

## Setup

```python
import agentlens
from agentlens.integrations.langchain import AgentLensCallbackHandler

agentlens.configure(server_url="http://localhost:3000")

handler = AgentLensCallbackHandler()
```

## Usage with Agent

```python
from langchain.agents import AgentExecutor

agent_executor = AgentExecutor(agent=agent, tools=tools)
result = agent_executor.invoke(
    {"input": "What is the weather in NYC?"},
    config={"callbacks": [handler]}
)
```

## Usage with Chain

```python
from langchain.chains import LLMChain

chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run("Summarize the latest AI news", callbacks=[handler])
```

## Usage with LangGraph

```python
from langgraph.graph import StateGraph

graph = StateGraph(MyState)
# ... add nodes and edges ...
app = graph.compile()

result = app.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"callbacks": [handler]}
)
```

## What Gets Traced

- LLM calls with input/output and token counts
- Tool invocations with name, input, and output
- Chain start/end with overall latency
- Agent iterations and final answers

All spans appear in the AgentLens topology graph automatically.
