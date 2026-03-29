// push.go — agentlens push: read trace JSON from stdin and POST to server
package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/spf13/cobra"
	"github.com/tranhoangtu-it/agentlens/cli/internal/output"
)

var pushCmd = &cobra.Command{
	Use:   "push",
	Short: "Push a trace from stdin to AgentLens server",
	Long: `Read a trace JSON document from stdin and send it to the server.

Examples:
  cat trace.json | agentlens push
  echo '{"trace_id":"t1","agent_name":"a","spans":[]}' | agentlens push`,
	Args: cobra.NoArgs,
	RunE: runPush,
}

var pushJSONFlag bool

func init() {
	pushCmd.Flags().BoolVar(&pushJSONFlag, "json", false, "Output response as JSON")
}

func runPush(cmd *cobra.Command, args []string) error {
	// Verify stdin has data (not a TTY with no pipe).
	stat, _ := os.Stdin.Stat()
	if (stat.Mode() & os.ModeCharDevice) != 0 {
		return fmt.Errorf("no input detected — pipe a trace JSON document to stdin")
	}

	data, err := io.ReadAll(os.Stdin)
	if err != nil {
		return fmt.Errorf("reading stdin: %w", err)
	}

	// Validate that input is parseable JSON before sending.
	var raw json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return fmt.Errorf("invalid JSON input: %w", err)
	}

	client, err := newClient()
	if err != nil {
		return err
	}

	resp, err := client.Post("/api/traces", raw)
	if err != nil {
		return fmt.Errorf("push failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading response: %w", err)
	}

	if pushJSONFlag {
		var v interface{}
		if err := json.Unmarshal(body, &v); err != nil {
			// Not JSON — print raw.
			fmt.Fprintln(os.Stdout, string(body))
			return nil
		}
		return output.Default.PrintJSON(v)
	}

	// Human-readable success message.
	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err == nil {
		if id, ok := result["trace_id"].(string); ok {
			fmt.Fprintf(os.Stdout, "Trace pushed successfully. trace_id=%s\n", id)
			return nil
		}
	}

	fmt.Fprintln(os.Stdout, "Trace pushed successfully.")
	return nil
}
