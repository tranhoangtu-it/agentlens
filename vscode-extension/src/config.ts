/**
 * Extension configuration helper — reads VS Code settings for AgentLens.
 */
import * as vscode from "vscode";

export interface AgentLensConfig {
  endpoint: string;
  apiKey: string;
}

/**
 * Read current AgentLens configuration from VS Code workspace settings.
 * Strips trailing slash from endpoint to keep URL construction consistent.
 */
export function getConfig(): AgentLensConfig {
  const cfg = vscode.workspace.getConfiguration("agentlens");
  const endpoint = (cfg.get<string>("endpoint") ?? "http://localhost:8000").replace(/\/$/, "");
  const apiKey = cfg.get<string>("apiKey") ?? "";
  return { endpoint, apiKey };
}

/**
 * Listen for configuration changes and invoke callback when agentlens settings change.
 */
export function onConfigChange(callback: () => void): vscode.Disposable {
  return vscode.workspace.onDidChangeConfiguration((e) => {
    if (e.affectsConfiguration("agentlens")) {
      callback();
    }
  });
}
