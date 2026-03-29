# agentlens CLI

A Go command-line tool for inspecting and managing AI agent traces on an AgentLens server.

## Installation

```bash
cd cli
go build -o agentlens .
# Move to a directory on your PATH, e.g.:
mv agentlens /usr/local/bin/
```

## Configuration

Before using any command, set your server endpoint (and optionally an API key):

```bash
agentlens config set endpoint http://localhost:8000
agentlens config set api-key al_xxxxx

# Verify
agentlens config show
```

Configuration is stored in `~/.agentlens/config.json`.

## Commands

### List traces

```bash
agentlens traces list
agentlens traces list --status=error
agentlens traces list --agent=my-agent --limit=50
agentlens traces list --json
```

Flags:
- `--status` — filter by status (e.g. `error`, `success`)
- `--agent` — filter by agent name
- `--limit` — max results (default: 20)
- `--json` — raw JSON output

### Show trace detail

```bash
agentlens traces show <trace-id>
agentlens traces show <trace-id> --json
```

Displays trace summary and a table of spans.

### Tail live events

```bash
agentlens traces tail
agentlens traces tail --agent=my-agent
```

Streams real-time trace events from the server via SSE. Press `Ctrl+C` to stop.

### Diff two traces

```bash
agentlens traces diff <id1> <id2>
agentlens traces diff <id1> <id2> --json
```

Calls `GET /api/traces/compare?left=<id1>&right=<id2>` and prints the result.

### Push a trace

```bash
cat trace.json | agentlens push
echo '{"trace_id":"t1","agent_name":"my-agent","spans":[]}' | agentlens push
agentlens push --json   # show server response as JSON
```

Reads a JSON trace document from stdin and `POST`s it to `/api/traces`.

## Output

By default all commands output human-readable tables (using `text/tabwriter`).
Add `--json` to any command to receive raw JSON output instead.

Errors are printed to stderr and the process exits with a non-zero status code.

## Project layout

```
cli/
  main.go                      Entry point
  cmd/
    root.go                    Root command, config helpers
    traces.go                  traces list/show/tail/diff
    push.go                    push from stdin
    config.go                  config set/show
  internal/
    api/client.go              Authenticated HTTP client
    output/format.go           Table + JSON formatting
    stream/sse.go              SSE stream client
```
