/**
 * Status bar item showing AgentLens trace count and error count.
 * Updates every 30s in sync with the tree provider refresh cycle.
 */
import * as vscode from "vscode";
import { TraceRecord } from "./api-client";

export class AgentLensStatusBar {
  private readonly item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100,
    );
    this.item.command = "agentlens.refreshTraces";
    this.item.tooltip = "AgentLens — click to refresh traces";
    this.setText("AgentLens: connecting…");
    this.item.show();
  }

  /**
   * Update status bar text from the current trace list.
   * Shows total count and error count; surface the command to open sidebar.
   */
  update(traces: TraceRecord[]): void {
    const errors = traces.filter((t) => t.status === "error").length;
    const running = traces.filter((t) => t.status === "running").length;
    const total = traces.length;

    const parts: string[] = [`$(telescope) AgentLens: ${total} trace${total !== 1 ? "s" : ""}`];
    if (running > 0) {
      parts.push(`$(loading~spin) ${running} running`);
    }
    if (errors > 0) {
      parts.push(`$(error) ${errors} error${errors !== 1 ? "s" : ""}`);
    }

    this.item.text = parts.join("  ");
    this.item.backgroundColor =
      errors > 0
        ? new vscode.ThemeColor("statusBarItem.errorBackground")
        : undefined;
  }

  /** Show a transient connection error state. */
  showError(message: string): void {
    this.item.text = `$(error) AgentLens: ${message.slice(0, 40)}`;
    this.item.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.errorBackground",
    );
  }

  /** Reset to neutral connecting state (e.g. after config change). */
  reset(): void {
    this.setText("AgentLens: connecting…");
    this.item.backgroundColor = undefined;
  }

  dispose(): void {
    this.item.dispose();
  }

  private setText(text: string): void {
    this.item.text = text;
  }
}
