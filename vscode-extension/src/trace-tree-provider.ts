/**
 * TreeView data provider for the AgentLens sidebar panel.
 * Lists recent traces with status icons and triggers detail webview on click.
 */
import * as vscode from "vscode";
import { AgentLensApiClient, TraceRecord } from "./api-client";

// ── Tree item ─────────────────────────────────────────────────────────────────

export class TraceItem extends vscode.TreeItem {
  constructor(public readonly trace: TraceRecord) {
    super(TraceItem.buildLabel(trace), vscode.TreeItemCollapsibleState.None);

    this.description = TraceItem.buildDescription(trace);
    this.tooltip = TraceItem.buildTooltip(trace);
    this.iconPath = new vscode.ThemeIcon(TraceItem.statusIcon(trace.status));
    this.contextValue = "traceItem";

    // Clicking a trace fires the openTrace command
    this.command = {
      command: "agentlens.openTrace",
      title: "Open Trace Detail",
      arguments: [trace],
    };
  }

  private static buildLabel(trace: TraceRecord): string {
    return trace.agent_name;
  }

  private static buildDescription(trace: TraceRecord): string {
    const parts: string[] = [trace.status];
    if (trace.duration_ms != null) {
      parts.push(`${(trace.duration_ms / 1000).toFixed(1)}s`);
    }
    if (trace.total_cost_usd != null) {
      parts.push(`$${trace.total_cost_usd.toFixed(4)}`);
    }
    return parts.join(" · ");
  }

  private static buildTooltip(trace: TraceRecord): string {
    const lines = [
      `ID: ${trace.id}`,
      `Agent: ${trace.agent_name}`,
      `Status: ${trace.status}`,
      `Spans: ${trace.span_count}`,
    ];
    if (trace.duration_ms != null) {
      lines.push(`Duration: ${trace.duration_ms}ms`);
    }
    if (trace.total_cost_usd != null) {
      lines.push(`Cost: $${trace.total_cost_usd.toFixed(6)}`);
    }
    if (trace.total_tokens != null) {
      lines.push(`Tokens: ${trace.total_tokens}`);
    }
    lines.push(`Created: ${new Date(trace.created_at).toLocaleString()}`);
    return lines.join("\n");
  }

  /** Maps trace status to a VS Code ThemeIcon id. */
  private static statusIcon(status: TraceRecord["status"]): string {
    switch (status) {
      case "completed": return "check";
      case "running":   return "loading~spin";
      case "error":     return "error";
      default:          return "circle-outline";
    }
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

export class TraceTreeProvider
  implements vscode.TreeDataProvider<TraceItem>
{
  private readonly _onDidChangeTreeData =
    new vscode.EventEmitter<TraceItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private traces: TraceRecord[] = [];
  private refreshTimer: ReturnType<typeof setInterval> | undefined;
  private isLoading = false;
  private lastError: string | null = null;

  constructor(private client: AgentLensApiClient) {}

  // ── vscode.TreeDataProvider ────────────────────────────────────────────────

  getTreeItem(element: TraceItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: TraceItem): Promise<TraceItem[]> {
    // Flat list — no nesting at tree level
    if (element !== undefined) {
      return [];
    }
    if (this.isLoading) {
      return [this.loadingItem()];
    }
    if (this.lastError !== null) {
      return [this.errorItem(this.lastError)];
    }
    return this.traces.map((t) => new TraceItem(t));
  }

  // ── Public methods ─────────────────────────────────────────────────────────

  /** Update the API client (e.g. after config change) and refresh. */
  updateClient(client: AgentLensApiClient): void {
    this.client = client;
    void this.refresh();
  }

  /** Manually trigger a data refresh. */
  async refresh(): Promise<void> {
    this.isLoading = true;
    this.lastError = null;
    this._onDidChangeTreeData.fire();

    try {
      const result = await this.client.listTraces(50);
      this.traces = result.traces ?? [];
    } catch (err) {
      this.lastError = err instanceof Error ? err.message : String(err);
      this.traces = [];
    } finally {
      this.isLoading = false;
      this._onDidChangeTreeData.fire();
    }
  }

  /** Start auto-refresh timer (30 s interval). */
  startAutoRefresh(intervalMs = 30_000): void {
    this.stopAutoRefresh();
    // Kick off an immediate fetch, then schedule repeating
    void this.refresh();
    this.refreshTimer = setInterval(() => {
      void this.refresh();
    }, intervalMs);
  }

  /** Stop auto-refresh timer. */
  stopAutoRefresh(): void {
    if (this.refreshTimer !== undefined) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = undefined;
    }
  }

  /** Return the current trace list for status bar counts. */
  getTraces(): TraceRecord[] {
    return this.traces;
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  private loadingItem(): TraceItem {
    const fake: TraceRecord = {
      id: "__loading__",
      agent_name: "Loading traces…",
      status: "running",
      created_at: new Date().toISOString(),
      duration_ms: null,
      total_cost_usd: null,
      total_tokens: null,
      span_count: 0,
    };
    const item = new TraceItem(fake);
    item.command = undefined;
    return item;
  }

  private errorItem(message: string): TraceItem {
    const fake: TraceRecord = {
      id: "__error__",
      agent_name: `Cannot connect: ${message.slice(0, 60)}`,
      status: "error",
      created_at: new Date().toISOString(),
      duration_ms: null,
      total_cost_usd: null,
      total_tokens: null,
      span_count: 0,
    };
    const item = new TraceItem(fake);
    item.command = undefined;
    return item;
  }
}
