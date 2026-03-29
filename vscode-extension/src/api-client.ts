/**
 * HTTP client for AgentLens server API.
 * Uses Node.js native http/https modules — no external dependencies.
 */
import * as http from "http";
import * as https from "https";
import { URL } from "url";

// ── Types mirroring server models ─────────────────────────────────────────────

export interface TraceRecord {
  id: string;
  agent_name: string;
  status: "running" | "completed" | "error";
  created_at: string;
  duration_ms: number | null;
  total_cost_usd: number | null;
  total_tokens: number | null;
  span_count: number;
}

export interface SpanRecord {
  id: string;
  trace_id: string;
  parent_id: string | null;
  name: string;
  type: string;
  start_ms: number;
  end_ms: number | null;
  input: string | null;
  output: string | null;
  cost_usd: number | null;
  cost_model: string | null;
  cost_input_tokens: number | null;
  cost_output_tokens: number | null;
}

export interface TraceDetail extends TraceRecord {
  spans: SpanRecord[];
}

export interface ListTracesResponse {
  traces: TraceRecord[];
  total: number;
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

/** Perform a GET request and resolve with parsed JSON. */
function get<T>(url: string, apiKey: string): Promise<T> {
  return new Promise((resolve, reject) => {
    let parsed: URL;
    try {
      parsed = new URL(url);
    } catch (err) {
      reject(new Error(`Invalid URL: ${url}`));
      return;
    }

    const lib = parsed.protocol === "https:" ? https : http;
    const options: http.RequestOptions = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: "GET",
      headers: {
        "Accept": "application/json",
        ...(apiKey ? { "X-API-Key": apiKey } : {}),
      },
    };

    const req = lib.request(options, (res: http.IncomingMessage) => {
      const chunks: Buffer[] = [];
      res.on("data", (chunk: Buffer) => chunks.push(chunk));
      res.on("end", () => {
        const body = Buffer.concat(chunks).toString("utf8");
        const status = res.statusCode ?? 0;
        if (status < 200 || status >= 300) {
          reject(new Error(`HTTP ${status}: ${body.slice(0, 200)}`));
          return;
        }
        try {
          resolve(JSON.parse(body) as T);
        } catch {
          reject(new Error(`Failed to parse JSON response from ${url}`));
        }
      });
    });

    req.on("error", (err: Error) => reject(err));
    req.setTimeout(10_000, () => {
      req.destroy(new Error(`Request timed out: ${url}`));
    });
    req.end();
  });
}

// ── Public API ────────────────────────────────────────────────────────────────

export class AgentLensApiClient {
  constructor(
    private readonly endpoint: string,
    private readonly apiKey: string,
  ) {}

  /**
   * Fetch recent traces (newest first, up to 50).
   * Returns empty list on network errors so UI degrades gracefully.
   */
  async listTraces(limit = 50): Promise<ListTracesResponse> {
    const url = `${this.endpoint}/api/traces?limit=${limit}&order=desc`;
    return get<ListTracesResponse>(url, this.apiKey);
  }

  /**
   * Fetch full trace with all spans for the detail webview.
   */
  async getTrace(traceId: string): Promise<TraceDetail> {
    const url = `${this.endpoint}/api/traces/${encodeURIComponent(traceId)}`;
    return get<TraceDetail>(url, this.apiKey);
  }

  /**
   * Check server reachability via health endpoint.
   */
  async healthCheck(): Promise<boolean> {
    try {
      await get<{ status: string }>(`${this.endpoint}/api/health`, this.apiKey);
      return true;
    } catch {
      return false;
    }
  }
}
