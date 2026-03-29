# AgentLens VS Code Extension

AI agent observability inside VS Code. Trace tool calls, inspect decision trees, and monitor agent status without leaving the editor.

## Features

- **Sidebar panel** — lists recent traces (agent name, status, duration, cost) with live status icons
- **Trace detail view** — full span tree with timing, token usage, cost, and I/O per span
- **Status bar** — bottom bar shows total traces and error count; click to refresh
- **Auto-refresh** — data updates every 30 seconds automatically

## Requirements

A running [AgentLens](https://github.com/agentlens/agentlens) server (default `http://localhost:8000`).

```bash
docker compose up   # from the agentlens repo root
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `agentlens.endpoint` | `http://localhost:8000` | AgentLens server URL |
| `agentlens.apiKey` | _(empty)_ | API key for authentication |

Set via **File → Preferences → Settings** and search for `AgentLens`.

## Usage

1. Start your AgentLens server
2. Open the AgentLens icon in the VS Code activity bar (telescope icon)
3. Traces appear automatically — click any trace to open the detail panel
4. Use the refresh button (↺) in the panel title to force an immediate update

## Development

```bash
cd vscode-extension
npm install
npm run compile     # one-shot build
npm run watch       # incremental watch build
```

Press **F5** in VS Code to launch an Extension Development Host for live testing.
