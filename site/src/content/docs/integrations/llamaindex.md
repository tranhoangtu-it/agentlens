---
title: LlamaIndex
description: Integrate AgentLens with LlamaIndex agents and query engines
---

## Installation

```bash
pip install agentlens-observe llama-index
```

## Setup

```python
import agentlens
from agentlens.integrations.llamaindex import AgentLensCallbackHandler
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager

agentlens.configure(server_url="http://localhost:3000")

handler = AgentLensCallbackHandler()
Settings.callback_manager = CallbackManager([handler])
```

Set `Settings.callback_manager` once at startup — all LlamaIndex operations inherit it automatically.

## Usage with Query Engine

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

# Query is automatically traced
response = query_engine.query("What are the main topics in these documents?")
```

## Usage with Agent

```python
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool

def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

search_tool = FunctionTool.from_defaults(fn=search_web)
agent = ReActAgent.from_tools([search_tool], verbose=True)

# Agent runs are automatically traced
response = agent.chat("Find the latest news about AI")
```

## What Gets Traced

- Query engine retrieval steps
- LLM calls with prompts and responses
- Tool invocations by agents
- Re-ranking and post-processing steps
- Embedding calls
