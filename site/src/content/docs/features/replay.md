---
title: Time-Travel Replay
description: Scrub through any agent trace step-by-step at any playback speed
---

Time-Travel Replay lets you re-watch any completed agent trace as an animation — stepping through spans one by one or scrubbing to any point in time.

## Opening Replay

From any trace detail page, click **Enter Replay** in the top-right corner.

Or navigate directly: `#/traces/<id>/replay`

## Controls

| Control | Description |
|---------|-------------|
| Play / Pause | Start or stop automatic playback |
| Speed | 1x–10x playback speed |
| Step Forward | Advance one span at a time |
| Step Back | Go back one span |
| Scrubber | Drag the timeline bar to jump to any point |

## Timeline Scrubber

The scrubber displays a Gantt-style bar chart of all spans, proportional to their real duration. Click or drag anywhere on the bar to jump to that moment in the trace.

The topology graph updates in real-time as you scrub — nodes appear and highlight as their corresponding spans become active.

## Use Cases

- **Debugging** — pause at the exact span where an error occurred and inspect its input/output
- **Understanding** — step through an unfamiliar agent's decision flow at your own pace
- **Demos** — replay a successful run to show stakeholders how the agent thinks
- **Root cause analysis** — compare the timing of parallel spans to find race conditions
