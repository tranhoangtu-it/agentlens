// sse.go — Server-Sent Events client for real-time trace tailing
package stream

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// Event represents a single SSE message from the server.
type Event struct {
	ID    string
	Event string
	Data  string
}

// Handler is called for each received SSE event. Return an error to stop streaming.
type Handler func(e Event) error

// Listen opens an SSE stream at the given URL with auth header and calls handler
// for every complete event until the connection closes or handler returns an error.
func Listen(client *http.Client, rawURL, apiKey string, handler Handler) error {
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return fmt.Errorf("building SSE request: %w", err)
	}

	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("Cache-Control", "no-cache")
	if apiKey != "" {
		req.Header.Set("X-API-Key", apiKey)
	}

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("connecting to SSE stream: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("SSE stream returned %d", resp.StatusCode)
	}

	return parseStream(resp.Body, handler)
}

// parseStream reads SSE lines and fires handler for each complete event.
func parseStream(r io.Reader, handler Handler) error {
	scanner := bufio.NewScanner(r)
	var current Event

	for scanner.Scan() {
		line := scanner.Text()

		switch {
		case line == "":
			// Blank line dispatches the accumulated event.
			if current.Data != "" {
				if err := handler(current); err != nil {
					return err
				}
			}
			current = Event{}

		case strings.HasPrefix(line, "id:"):
			current.ID = strings.TrimSpace(strings.TrimPrefix(line, "id:"))

		case strings.HasPrefix(line, "event:"):
			current.Event = strings.TrimSpace(strings.TrimPrefix(line, "event:"))

		case strings.HasPrefix(line, "data:"):
			data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
			if current.Data == "" {
				current.Data = data
			} else {
				// Multi-line data fields are joined with newline.
				current.Data += "\n" + data
			}

		case strings.HasPrefix(line, ":"):
			// SSE comment — ignore heartbeat lines.
		}
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		return fmt.Errorf("reading SSE stream: %w", err)
	}
	return nil
}
