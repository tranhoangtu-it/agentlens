/**
 * WebView panel for displaying full trace detail — span tree with timing, cost, I/O.
 * Plain HTML rendering, no React or bundler required.
 */
import * as vscode from "vscode";
import { AgentLensApiClient, TraceDetail, SpanRecord } from "./api-client";

// ── Panel manager (one panel reused across traces) ────────────────────────────

export class TraceDetailWebview {
  private static current: vscode.WebviewPanel | undefined;

  /**
   * Open (or reveal) the trace detail panel for the given trace ID.
   * Reuses the existing panel if already open.
   */
  static async show(
    context: vscode.ExtensionContext,
    client: AgentLensApiClient,
    traceId: string,
    endpoint: string,
  ): Promise<void> {
    const column = vscode.window.activeTextEditor
      ? vscode.ViewColumn.Beside
      : vscode.ViewColumn.One;

    if (TraceDetailWebview.current) {
      TraceDetailWebview.current.reveal(column);
    } else {
      TraceDetailWebview.current = vscode.window.createWebviewPanel(
        "agentlens.traceDetail",
        "AgentLens — Trace Detail",
        column,
        { enableScripts: false, retainContextWhenHidden: true },
      );
      TraceDetailWebview.current.onDidDispose(() => {
        TraceDetailWebview.current = undefined;
      });
    }

    // Show loading state immediately
    TraceDetailWebview.current.webview.html = buildLoadingHtml(traceId);

    try {
      const trace = await client.getTrace(traceId);
      TraceDetailWebview.current.title = `Trace — ${trace.agent_name}`;
      TraceDetailWebview.current.webview.html = buildTraceHtml(trace, endpoint);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      TraceDetailWebview.current.webview.html = buildErrorHtml(traceId, msg);
    }
  }
}

// ── HTML builders ─────────────────────────────────────────────────────────────

function buildLoadingHtml(traceId: string): string {
  return wrapHtml(`<p class="muted">Loading trace <code>${esc(traceId)}</code>…</p>`);
}

function buildErrorHtml(traceId: string, message: string): string {
  return wrapHtml(
    `<p class="error">Failed to load trace <code>${esc(traceId)}</code></p>
     <pre class="error-detail">${esc(message)}</pre>`,
  );
}

function buildTraceHtml(trace: TraceDetail, endpoint: string): string {
  const dashboardUrl = `${endpoint}/traces/${encodeURIComponent(trace.id)}`;
  const created = new Date(trace.created_at).toLocaleString();

  const header = `
    <div class="header">
      <h2>${esc(trace.agent_name)}</h2>
      <span class="badge badge-${esc(trace.status)}">${esc(trace.status)}</span>
    </div>
    <table class="meta">
      <tr><td>ID</td><td><code>${esc(trace.id)}</code></td></tr>
      <tr><td>Created</td><td>${esc(created)}</td></tr>
      ${trace.duration_ms != null ? `<tr><td>Duration</td><td>${trace.duration_ms} ms</td></tr>` : ""}
      ${trace.total_cost_usd != null ? `<tr><td>Cost</td><td>$${trace.total_cost_usd.toFixed(6)}</td></tr>` : ""}
      ${trace.total_tokens != null ? `<tr><td>Tokens</td><td>${trace.total_tokens}</td></tr>` : ""}
      <tr><td>Spans</td><td>${trace.span_count}</td></tr>
    </table>
    <p><a href="${esc(dashboardUrl)}" class="dashboard-link">Open in Dashboard ↗</a></p>
    <hr/>
  `;

  const spanTree = buildSpanTree(trace.spans ?? []);
  return wrapHtml(header + `<h3>Spans</h3>` + spanTree);
}

/** Render spans as a nested list ordered by start_ms. */
function buildSpanTree(spans: SpanRecord[]): string {
  if (spans.length === 0) {
    return `<p class="muted">No spans recorded.</p>`;
  }

  // Build parent→children map
  const childMap = new Map<string | null, SpanRecord[]>();
  for (const span of spans) {
    const key = span.parent_id ?? null;
    if (!childMap.has(key)) { childMap.set(key, []); }
    childMap.get(key)!.push(span);
  }

  // Sort each group by start_ms
  for (const children of childMap.values()) {
    children.sort((a, b) => a.start_ms - b.start_ms);
  }

  function renderSpans(parentId: string | null, depth: number): string {
    const children = childMap.get(parentId) ?? [];
    if (children.length === 0) { return ""; }

    const items = children.map((span) => {
      const duration = span.end_ms != null ? `${span.end_ms - span.start_ms} ms` : "running…";
      const cost = span.cost_usd != null ? ` · $${span.cost_usd.toFixed(6)}` : "";
      const model = span.cost_model ? ` · ${esc(span.cost_model)}` : "";

      let detail = "";
      if (span.input) {
        detail += `<div class="io-block"><span class="io-label">Input</span><pre>${esc(truncate(span.input, 400))}</pre></div>`;
      }
      if (span.output) {
        detail += `<div class="io-block"><span class="io-label">Output</span><pre>${esc(truncate(span.output, 400))}</pre></div>`;
      }

      const nested = renderSpans(span.id, depth + 1);

      return `
        <li class="span-item depth-${Math.min(depth, 5)}">
          <div class="span-header">
            <span class="span-type">${esc(span.type)}</span>
            <span class="span-name">${esc(span.name)}</span>
            <span class="span-meta">${esc(duration)}${cost}${model}</span>
          </div>
          ${detail}
          ${nested ? `<ul class="span-children">${nested}</ul>` : ""}
        </li>`;
    });

    return items.join("");
  }

  return `<ul class="span-list">${renderSpans(null, 0)}</ul>`;
}

/** Escape HTML special characters. */
function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Truncate long strings for display. */
function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + "…" : s;
}

/** Wrap content in a full HTML document with VS Code-compatible styles. */
function wrapHtml(body: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AgentLens Trace</title>
  <style>
    body {
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      color: var(--vscode-foreground);
      background: var(--vscode-editor-background);
      padding: 16px 20px;
      max-width: 900px;
    }
    h2, h3 { margin: 0 0 8px; color: var(--vscode-foreground); }
    hr { border: none; border-top: 1px solid var(--vscode-panel-border); margin: 16px 0; }
    code { font-family: var(--vscode-editor-font-family, monospace); }
    pre {
      background: var(--vscode-textBlockQuote-background);
      border-left: 3px solid var(--vscode-textBlockQuote-border);
      padding: 8px 10px;
      margin: 4px 0;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
    }
    table.meta { border-collapse: collapse; margin-bottom: 12px; }
    table.meta td { padding: 2px 12px 2px 0; vertical-align: top; }
    table.meta td:first-child { color: var(--vscode-descriptionForeground); min-width: 80px; }
    .header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 10px;
      font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px;
    }
    .badge-completed { background: #1a7f1a; color: #d4ffd4; }
    .badge-running   { background: #7a6a00; color: #fff9c4; }
    .badge-error     { background: #7f1a1a; color: #ffd4d4; }
    .dashboard-link { color: var(--vscode-textLink-foreground); }
    .muted { color: var(--vscode-descriptionForeground); }
    .error { color: var(--vscode-errorForeground); }
    .error-detail { font-size: 12px; }
    .span-list, .span-children { list-style: none; padding: 0; margin: 0; }
    .span-item {
      margin: 6px 0;
      border-left: 2px solid var(--vscode-panel-border);
      padding-left: 10px;
    }
    .span-item.depth-0 { border-color: #4a9eff; }
    .span-item.depth-1 { border-color: #9b59b6; }
    .span-item.depth-2 { border-color: #27ae60; }
    .span-item.depth-3 { border-color: #e67e22; }
    .span-item.depth-4, .span-item.depth-5 { border-color: var(--vscode-panel-border); }
    .span-header { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
    .span-type {
      font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px;
      color: var(--vscode-descriptionForeground);
      background: var(--vscode-badge-background);
      padding: 1px 5px; border-radius: 3px;
    }
    .span-name { font-weight: 600; }
    .span-meta { font-size: 11px; color: var(--vscode-descriptionForeground); margin-left: auto; }
    .io-block { margin: 4px 0; }
    .io-label {
      font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px;
      color: var(--vscode-descriptionForeground);
    }
    .span-children { margin-top: 6px; }
  </style>
</head>
<body>
${body}
</body>
</html>`;
}
