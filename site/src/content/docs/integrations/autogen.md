---
title: AutoGen
description: Integrate AgentLens with Microsoft AutoGen multi-agent conversations
---

## Installation

```bash
pip install agentlens-observe pyautogen
```

## Setup

```python
import agentlens
from agentlens.integrations.autogen import patch_autogen

agentlens.configure(server_url="http://localhost:3000")
patch_autogen()  # Patches ConversableAgent.generate_reply
```

Call `patch_autogen()` once at startup — before creating any agents.

## Usage

```python
import autogen

config_list = [{"model": "gpt-4o", "api_key": "your-key"}]

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    code_execution_config={"work_dir": "coding"},
)

# All agent messages and LLM calls are automatically traced
user_proxy.initiate_chat(
    assistant,
    message="Write a Python function to calculate Fibonacci numbers",
)
```

## What Gets Traced

- Each `generate_reply` call as a span
- Agent-to-agent message exchanges
- LLM call inputs and outputs
- Code execution results (when applicable)
- Conversation turn boundaries
