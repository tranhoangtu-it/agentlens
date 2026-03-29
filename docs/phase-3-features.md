# AgentLens Phase 3 Features — Replay Sandbox, Go CLI, VS Code Extension

**Status:** Implementation Phase | **Target Release:** v0.9.0 (Q2 2026)

## Overview

Phase 3 introduces three major systems:
1. **Replay Sandbox** — Interactive span editing and trace replay/simulation
2. **Go CLI Tool** — Command-line interface for trace management and inspection
3. **VS Code Extension** — IDE integration for trace discovery and inspection

## 1. Replay Sandbox

### Purpose
Enable users to edit span inputs/outputs, create alternative execution paths, and test "what-if" scenarios without re-running agents.

### Architecture

**Database Model** (`server/replay_models.py`)
```python
class ReplaySession:
    id: str [PK]
    trace_id: str [FK, INDEX]
    user_id: str [INDEX]
    name: str                      # User-given name for this replay
    base_span_id: str [FK]         # Original span being replayed
    edited_spans: dict             # {span_id: modified_input/output}
    created_at: datetime
    updated_at: datetime
    # Index: (trace_id, user_id), (user_id, created_at)
```

**API Endpoints** (`server/replay_routes.py`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/replay-sessions` | POST | JWT/ApiKey | Create replay session from trace |
| `/api/traces/{id}/replay-sessions` | GET | JWT/ApiKey | List all replay sessions for trace |
| `/api/replay-sessions/{id}` | GET | JWT/ApiKey | Fetch replay session details |
| `/api/replay-sessions/{id}` | PUT | JWT/ApiKey | Update span edits in session |
| `/api/replay-sessions/{id}` | DELETE | JWT/ApiKey | Delete replay session |

**Create Replay Session**
```http
POST /api/replay-sessions
Body: {
  "trace_id": "trace_123",
  "name": "Test different search terms",
  "base_span_id": "span_456"  // optional: start from specific span
}
Returns: ReplaySession
```

**Update Edits**
```http
PUT /api/replay-sessions/{id}
Body: {
  "edited_spans": {
    "span_456": {"input": "{\"query\": \"new search term\"}"},
    "span_789": {"output": "{\"result\": \"custom output\"}"}
  }
}
Returns: ReplaySession
```

### Dashboard Integration

**Replay Page** (`dashboard/src/pages/trace-replay-page.tsx`)
- **Sandbox Mode Button** — Toggle between "View" and "Sandbox" mode on trace detail
- **Span Editor Panel** — Click span → edit input/output in drawer
  - JSON input editor (syntax highlighting)
  - Read-only original values for reference
  - Save/Discard buttons
- **Replay Timeline** — Show original vs edited execution path
  - Original spans (gray)
  - Edited spans (blue highlight)
  - Diff indicators (input/output badges)
- **Session Management** — List saved replay sessions
  - Create new
  - Load existing
  - Delete unused

**Components**
- `replay-sandbox-controls.tsx` — Mode toggle, save/load buttons
- `replay-span-editor.tsx` — JSON editor for span input/output
- `replay-timeline-view.tsx` — Visual timeline with edits highlighted
- `replay-session-list.tsx` — Session history management

### Storage Functions (`server/replay_storage.py`)
- `create_replay_session(trace_id, user_id, name, base_span_id)` — Create session
- `get_replay_session(session_id, user_id)` — Fetch with ownership check
- `list_replay_sessions(trace_id, user_id)` — List all for trace
- `update_replay_session_edits(session_id, edited_spans, user_id)` — Update edits
- `delete_replay_session(session_id, user_id)` — Delete session

### Use Cases
- **Debug agent behavior** — Change search terms, API responses to test different paths
- **Scenario testing** — Test "what if" without re-running expensive agents
- **Output verification** — Validate agent would handle different responses correctly
- **Training data generation** — Create variations for fine-tuning datasets

## 2. Go CLI Tool

### Purpose
Provide a lightweight, portable command-line interface for AgentLens operations.

### Package Structure (`cli/`)

```
cli/
├── main.go                 # CLI entry point
├── go.mod                  # Go module definition
├── Makefile                # Build targets
├── config/
│   └── config.go          # Config file management
├── commands/
│   ├── traces.go          # trace list/show/tail/diff commands
│   ├── push.go            # push command (stdin pipe)
│   └── config.go          # config set/show commands
├── api/
│   └── client.go          # API client wrapper
└── tests/
    └── *_test.go          # Unit tests
```

### Build Instructions

```bash
cd cli
go build -o agentlens .
./agentlens --help
```

### Configuration

**Config File** (`~/.agentlens/config.json`)
```json
{
  "server_url": "http://localhost:3000",
  "api_key": "al_xxx...",
  "output_format": "json",
  "default_limit": 10
}
```

**Config Commands**
```bash
# Set configuration
agentlens config set server_url http://localhost:3000
agentlens config set api_key al_xxx...
agentlens config set output_format json

# Show configuration
agentlens config show

# Output: displays config (with redacted API key)
```

### Trace Commands

**List Traces**
```bash
agentlens traces list [--limit=10] [--status=running|completed|error] [--agent=AgentName]

# Output:
# ID                    Agent         Status     Cost     Span Count  Created At
# trace_abc123          SearchAgent   completed  $0.25    8           2026-03-29 14:23:15
# trace_def456          ...           ...        ...      ...         ...
```

**Show Trace Details**
```bash
agentlens traces show <trace_id> [--format=json|table|tree]

# Output (tree format):
# SearchAgent [completed] (cost: $0.25, duration: 2.3s)
# ├── web_search (tool_call)
# │   ├── input: {"query": "..."}
# │   └── output: {...}
# └── summarize (llm_call)
#     ├── input: {...}
#     └── output: {...}
```

**Tail Traces (Real-time)**
```bash
agentlens traces tail [--agent=AgentName] [--status=running]

# Output (streaming):
# [14:25:30] trace_xyz789 SearchAgent RUNNING (2 spans)
# [14:25:31] trace_xyz789 SearchAgent RUNNING (3 spans)
# [14:25:32] trace_xyz789 SearchAgent COMPLETED ($0.18, 8 spans)
```

**Compare Traces**
```bash
agentlens traces diff <trace_1> <trace_2> [--format=json|unified]

# Output (unified format):
# --- trace_1/web_search
# +++ trace_2/web_search
# @@ input @@
# -"query": "old search"
# +"query": "new search"
```

### Push Command (Stdin Pipe)

**From Python**
```bash
python my_agent.py | agentlens push [--name=agent_name]

# Reads JSON trace from stdin, pushes to server
```

**From JSON File**
```bash
cat trace.json | agentlens push
agentlens push < trace.json
```

**Expected Input Format**
```json
{
  "id": "trace_123",
  "agent_name": "MyAgent",
  "created_at": "2026-03-29T14:23:15Z",
  "spans": [
    {"id": "span_1", "name": "web_search", "type": "tool_call", ...},
    ...
  ]
}
```

### Help & Version

```bash
agentlens --version       # v0.9.0
agentlens --help
agentlens traces --help
agentlens traces list --help
```

### Technology Stack

- **Framework:** Cobra (CLI framework)
- **API Client:** stdlib net/http + encoding/json
- **Config:** viper (config file management)
- **Output Formatting:** tablewriter (ASCII tables), json encoder
- **Streaming:** SSE listener for `traces tail` command

## 3. VS Code Extension

### Purpose
Provide IDE integration for discovering, inspecting, and comparing traces without switching to browser.

### Package Structure (`vscode-extension/`)

```
vscode-extension/
├── package.json            # Extension manifest
├── tsconfig.json           # TypeScript config
├── src/
│   ├── extension.ts        # Extension entry point
│   ├── sidebar-provider.ts # TreeView data provider
│   ├── webview-provider.ts # WebView for detail panel
│   ├── status-bar.ts       # Status bar indicator
│   └── api-client.ts       # API calls
├── resources/
│   ├── icons/              # Tree icons
│   └── styles.css          # WebView styling
└── tests/
    └── *.test.ts           # Unit tests
```

### Build Instructions

```bash
cd vscode-extension
npm install
npx tsc                  # Compile TypeScript
code --install-extension dist/
```

### VS Code Configuration

**Settings** (`agentlens.endpoint`, `agentlens.apiKey`)

User can configure in VS Code settings:
```json
{
  "agentlens.endpoint": "http://localhost:3000",
  "agentlens.apiKey": "al_xxx..."
}
```

### Features

**1. Sidebar Trace TreeView** (`sidebar-provider.ts`)
- **Icon:** AgentLens logo in activity bar
- **Contents:**
  - Recent traces (last 10, grouped by agent)
  - Status badges (completed/running/error)
  - Expandable agent groups
  - Right-click context menu (open, compare, delete)
- **Sorting:** by created_at desc (most recent first)
- **Auto-refresh:** Polls server every 5s for new traces

**TreeView Structure:**
```
AgentLens
├── SearchAgent (5 traces)
│   ├── trace_abc123 (completed) ✓
│   │   └── 8 spans
│   ├── trace_def456 (running) ⟳
│   └── ...
├── SummarizeAgent (2 traces)
│   └── ...
└── [Settings] ⚙️
```

**2. Detail WebView Panel** (`webview-provider.ts`)
- **Triggered:** Click trace in sidebar or via context menu
- **Contents:**
  - Trace header (agent, status, cost, duration)
  - Topology graph (React Flow, same as dashboard)
  - Span list (expandable, click to inspect)
  - Span detail (input, output, cost, duration)
  - JSON viewer for spans (syntax highlight)
- **Actions:**
  - Open in browser (dashboard link)
  - Copy trace ID
  - Export as JSON
  - Compare with another trace

**3. Status Bar Indicator** (`status-bar.ts`)
- **Location:** Bottom right of VS Code
- **Display:** "AgentLens: Connected" / "Disconnected" with color
- **Click:** Toggle sidebar visibility or show quick stats
- **Stats:** Total traces, most active agent, total cost today

### Commands

**Registered VS Code Commands**

```javascript
// Sidebar context menu
"agentlens.openTrace"      // Open trace in detail panel
"agentlens.openInBrowser"  // Open in dashboard
"agentlens.compareTraces"  // Compare two traces
"agentlens.deleteTrace"    // Delete trace (with confirm)
"agentlens.copyTraceId"    // Copy ID to clipboard
"agentlens.exportTrace"    // Export as JSON file

// Command palette
"agentlens.refresh"        // Refresh trace list
"agentlens.configure"      // Open settings
"agentlens.connectStatus"  // Show connection status
```

### WebView HTML Structure

```html
<div id="agentlens-detail">
  <div class="header">
    <h2>{agent_name}</h2>
    <span class="status">{status}</span>
    <span class="cost">${cost}</span>
  </div>
  <div class="tabs">
    <button class="tab active">Topology</button>
    <button class="tab">Spans</button>
    <button class="tab">JSON</button>
  </div>
  <div class="tab-content">
    <!-- React Flow topology, or span list, or JSON viewer -->
  </div>
</div>
```

### Configuration Validation

On extension activation:
- Check if `agentlens.endpoint` and `agentlens.apiKey` are set
- Attempt connection to server (GET /api/health)
- Display "Connected" or "Configuration Required" in status bar
- If disconnected, show warning in sidebar: "Click to configure"

### Technology Stack

- **Extension Framework:** Visual Studio Code Extension API
- **UI Components:** WebView (HTML/CSS/JS)
- **Graph Visualization:** React Flow (via WebView)
- **Build:** TypeScript + esbuild
- **Package:** VSIX format (vsce CLI)

## Testing

### Replay Sandbox Tests (`server/tests/test_replay.py`)
- Session creation and ownership validation
- Span edit storage and retrieval
- Concurrent session handling
- Dashboard component rendering

### Go CLI Tests (`cli/commands/*_test.go`)
- Config file parsing and validation
- API client HTTP requests
- Output formatting (JSON, table, tree)
- Stdin pipe handling for `push` command

### VS Code Extension Tests (`vscode-extension/tests/*.test.ts`)
- TreeView data provider refresh logic
- WebView message passing
- API client error handling
- Configuration validation

## Backward Compatibility

- **No Breaking Changes** — All Phase 3 features are additive
- Existing traces, SDKs, server APIs unchanged
- Replay sessions independent of original traces (no mutation)
- CLI and VS Code are optional tools (server functions without them)

## Performance Considerations

- **Replay Sessions** — Stored as JSON blobs (no re-execution cost)
- **CLI Streaming** — Uses SSE for `traces tail` (efficient, real-time)
- **VS Code Sidebar** — Polls server every 5s (configurable)
- **WebView Graph** — Same React Flow component as dashboard (reuses code)

## Deployment

### Docker Integration
- Go CLI binary included in Docker image (optional)
- Build stage: `RUN cd cli && go build -o /usr/local/bin/agentlens .`
- Entrypoint: `agentlens` command available in containers

### VS Code Marketplace
- Published to [VS Code Marketplace](https://marketplace.visualstudio.com/)
- Automatic updates via marketplace
- Public repository on GitHub
- Free, open-source license

### CLI Distribution
- Standalone binary releases (GitHub Releases)
- Platform-specific: darwin-amd64, darwin-arm64, linux-amd64, linux-arm64, windows-amd64
- Installation: `curl | sh` installer script
- Homebrew: `brew install agentlens-cli`

## Success Criteria

- [x] Replay Sandbox API fully functional, tested
- [x] Go CLI buildable and distributable
- [x] VS Code Extension published and reviewable
- [x] Documentation for all three tools
- [x] Integration tests for CLI + server
- [x] VS Code extension tests passing
