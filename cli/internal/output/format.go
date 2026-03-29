// format.go — Table and JSON output formatting utilities
package output

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"text/tabwriter"
)

// Writer wraps stdout/stderr with helpers for table and JSON output.
type Writer struct {
	Out io.Writer
	Err io.Writer
}

// Default is the package-level writer targeting os.Stdout / os.Stderr.
var Default = &Writer{Out: os.Stdout, Err: os.Stderr}

// PrintJSON serialises v as indented JSON to Out.
func (w *Writer) PrintJSON(v interface{}) error {
	enc := json.NewEncoder(w.Out)
	enc.SetIndent("", "  ")
	if err := enc.Encode(v); err != nil {
		return fmt.Errorf("json encode: %w", err)
	}
	return nil
}

// PrintTable writes headers + rows using tabwriter for aligned columns.
// headers and each row must have the same number of columns.
func (w *Writer) PrintTable(headers []string, rows [][]string) {
	tw := tabwriter.NewWriter(w.Out, 0, 0, 2, ' ', 0)
	defer tw.Flush()

	// Print header row
	for i, h := range headers {
		if i > 0 {
			fmt.Fprint(tw, "\t")
		}
		fmt.Fprint(tw, h)
	}
	fmt.Fprintln(tw)

	// Print separator
	for i, h := range headers {
		if i > 0 {
			fmt.Fprint(tw, "\t")
		}
		for range h {
			fmt.Fprint(tw, "-")
		}
	}
	fmt.Fprintln(tw)

	// Print data rows
	for _, row := range rows {
		for i, cell := range row {
			if i > 0 {
				fmt.Fprint(tw, "\t")
			}
			fmt.Fprint(tw, cell)
		}
		fmt.Fprintln(tw)
	}
}

// Errorf prints a formatted error message to Err.
func (w *Writer) Errorf(format string, args ...interface{}) {
	fmt.Fprintf(w.Err, "error: "+format+"\n", args...)
}

// Printf prints a formatted message to Out.
func (w *Writer) Printf(format string, args ...interface{}) {
	fmt.Fprintf(w.Out, format+"\n", args...)
}

// Truncate shortens s to maxLen characters, appending "…" if cut.
func Truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-1] + "…"
}
