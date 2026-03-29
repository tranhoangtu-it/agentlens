// traces.go — traces list / show / tail / diff subcommands
package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"time"

	"github.com/spf13/cobra"
	"github.com/tranhoangtu-it/agentlens/cli/internal/output"
	"github.com/tranhoangtu-it/agentlens/cli/internal/stream"
)

// ---- parent command ---------------------------------------------------------

var tracesCmd = &cobra.Command{
	Use:   "traces",
	Short: "List, inspect, tail, and diff agent traces",
}

func init() {
	tracesCmd.AddCommand(tracesListCmd)
	tracesCmd.AddCommand(tracesShowCmd)
	tracesCmd.AddCommand(tracesTailCmd)
	tracesCmd.AddCommand(tracesDiffCmd)
}

// ---- traces list ------------------------------------------------------------

var (
	listStatus string
	listAgent  string
	listLimit  int
	listJSON   bool
)

var tracesListCmd = &cobra.Command{
	Use:   "list",
	Short: "List traces",
	Args:  cobra.NoArgs,
	RunE:  runTracesList,
}

func init() {
	tracesListCmd.Flags().StringVar(&listStatus, "status", "", "Filter by status (e.g. error, success)")
	tracesListCmd.Flags().StringVar(&listAgent, "agent", "", "Filter by agent name")
	tracesListCmd.Flags().IntVar(&listLimit, "limit", 20, "Maximum number of traces to return")
	tracesListCmd.Flags().BoolVar(&listJSON, "json", false, "Output raw JSON")
}

func runTracesList(cmd *cobra.Command, args []string) error {
	client, err := newClient()
	if err != nil {
		return err
	}

	params := url.Values{}
	if listStatus != "" {
		params.Set("status", listStatus)
	}
	if listAgent != "" {
		params.Set("agent_name", listAgent)
	}
	params.Set("limit", strconv.Itoa(listLimit))

	resp, err := client.Get("/api/traces", params)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading response: %w", err)
	}

	if listJSON {
		var v interface{}
		if err := json.Unmarshal(body, &v); err != nil {
			fmt.Fprintln(os.Stdout, string(body))
			return nil
		}
		return output.Default.PrintJSON(v)
	}

	// Parse as list of trace objects for table display.
	var traces []map[string]interface{}
	if err := json.Unmarshal(body, &traces); err != nil {
		// Server may wrap in {data:[...]}
		var wrapper struct {
			Data []map[string]interface{} `json:"data"`
		}
		if err2 := json.Unmarshal(body, &wrapper); err2 != nil {
			fmt.Fprintln(os.Stdout, string(body))
			return nil
		}
		traces = wrapper.Data
	}

	headers := []string{"TRACE ID", "AGENT", "STATUS", "STARTED", "DURATION"}
	rows := make([][]string, 0, len(traces))
	for _, t := range traces {
		rows = append(rows, []string{
			strVal(t, "trace_id"),
			output.Truncate(strVal(t, "agent_name"), 24),
			strVal(t, "status"),
			formatTime(strVal(t, "started_at")),
			strVal(t, "duration_ms") + "ms",
		})
	}

	output.Default.PrintTable(headers, rows)
	return nil
}

// ---- traces show ------------------------------------------------------------

var showJSON bool

var tracesShowCmd = &cobra.Command{
	Use:   "show <trace-id>",
	Short: "Show full detail of a trace including spans",
	Args:  cobra.ExactArgs(1),
	RunE:  runTracesShow,
}

func init() {
	tracesShowCmd.Flags().BoolVar(&showJSON, "json", false, "Output raw JSON")
}

func runTracesShow(cmd *cobra.Command, args []string) error {
	traceID := args[0]
	if traceID == "" {
		return fmt.Errorf("trace-id must not be empty")
	}

	client, err := newClient()
	if err != nil {
		return err
	}

	resp, err := client.Get("/api/traces/"+traceID, nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading response: %w", err)
	}

	if showJSON {
		var v interface{}
		if err := json.Unmarshal(body, &v); err != nil {
			fmt.Fprintln(os.Stdout, string(body))
			return nil
		}
		return output.Default.PrintJSON(v)
	}

	var trace map[string]interface{}
	if err := json.Unmarshal(body, &trace); err != nil {
		fmt.Fprintln(os.Stdout, string(body))
		return nil
	}

	// Print trace summary.
	fmt.Fprintf(os.Stdout, "Trace ID  : %s\n", strVal(trace, "trace_id"))
	fmt.Fprintf(os.Stdout, "Agent     : %s\n", strVal(trace, "agent_name"))
	fmt.Fprintf(os.Stdout, "Status    : %s\n", strVal(trace, "status"))
	fmt.Fprintf(os.Stdout, "Started   : %s\n", formatTime(strVal(trace, "started_at")))
	fmt.Fprintf(os.Stdout, "Duration  : %sms\n\n", strVal(trace, "duration_ms"))

	// Print spans table if present.
	spansRaw, ok := trace["spans"]
	if !ok {
		return nil
	}
	spans, ok := spansRaw.([]interface{})
	if !ok || len(spans) == 0 {
		fmt.Fprintln(os.Stdout, "No spans recorded.")
		return nil
	}

	headers := []string{"SPAN ID", "NAME", "STATUS", "DURATION"}
	rows := make([][]string, 0, len(spans))
	for _, s := range spans {
		span, _ := s.(map[string]interface{})
		rows = append(rows, []string{
			strVal(span, "span_id"),
			output.Truncate(strVal(span, "name"), 32),
			strVal(span, "status"),
			strVal(span, "duration_ms") + "ms",
		})
	}
	output.Default.PrintTable(headers, rows)
	return nil
}

// ---- traces tail ------------------------------------------------------------

var tailAgent string

var tracesTailCmd = &cobra.Command{
	Use:   "tail",
	Short: "Stream live trace events via SSE",
	Args:  cobra.NoArgs,
	RunE:  runTracesTail,
}

func init() {
	tracesTailCmd.Flags().StringVar(&tailAgent, "agent", "", "Filter events by agent name")
}

func runTracesTail(cmd *cobra.Command, args []string) error {
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if cfg.Endpoint == "" {
		return fmt.Errorf("no endpoint configured — run: agentlens config set endpoint <url>")
	}

	streamURL := cfg.Endpoint + "/api/traces/stream"
	if tailAgent != "" {
		streamURL += "?agent_name=" + url.QueryEscape(tailAgent)
	}

	fmt.Fprintf(os.Stdout, "Tailing traces from %s (Ctrl+C to stop)...\n\n", cfg.Endpoint)

	httpClient := &http.Client{Timeout: 0} // No timeout for long-lived SSE.

	return stream.Listen(httpClient, streamURL, cfg.APIKey, func(e stream.Event) error {
		ts := time.Now().Format("15:04:05")
		eventType := e.Event
		if eventType == "" {
			eventType = "message"
		}
		fmt.Fprintf(os.Stdout, "[%s] (%s) %s\n", ts, eventType, output.Truncate(e.Data, 120))
		return nil
	})
}

// ---- traces diff ------------------------------------------------------------

var diffJSON bool

var tracesDiffCmd = &cobra.Command{
	Use:   "diff <id1> <id2>",
	Short: "Compare two traces side by side",
	Args:  cobra.ExactArgs(2),
	RunE:  runTracesDiff,
}

func init() {
	tracesDiffCmd.Flags().BoolVar(&diffJSON, "json", false, "Output raw JSON")
}

func runTracesDiff(cmd *cobra.Command, args []string) error {
	id1, id2 := args[0], args[1]

	client, err := newClient()
	if err != nil {
		return err
	}

	params := url.Values{}
	params.Set("left", id1)
	params.Set("right", id2)

	resp, err := client.Get("/api/traces/compare", params)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading response: %w", err)
	}

	if diffJSON {
		var v interface{}
		if err := json.Unmarshal(body, &v); err != nil {
			fmt.Fprintln(os.Stdout, string(body))
			return nil
		}
		return output.Default.PrintJSON(v)
	}

	// Pretty-print the diff result as indented JSON by default
	// (diff format is server-defined; we render it readable).
	var v interface{}
	if err := json.Unmarshal(body, &v); err != nil {
		fmt.Fprintln(os.Stdout, string(body))
		return nil
	}
	return output.Default.PrintJSON(v)
}

// ---- helpers ----------------------------------------------------------------

// strVal safely extracts a string field from an untyped map.
func strVal(m map[string]interface{}, key string) string {
	if m == nil {
		return ""
	}
	v, ok := m[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return t
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	default:
		return fmt.Sprintf("%v", v)
	}
}

// formatTime parses an ISO-8601 timestamp and returns HH:MM:SS date string.
func formatTime(s string) string {
	if s == "" {
		return ""
	}
	t, err := time.Parse(time.RFC3339, s)
	if err != nil {
		return s // return raw if unparseable
	}
	return t.Format("2006-01-02 15:04:05")
}
