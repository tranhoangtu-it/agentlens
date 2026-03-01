---
title: Trace Comparison
description: Side-by-side diff of two agent runs with color-coded span matching
---

Trace Comparison lets you diff any two agent runs side-by-side — useful for A/B testing prompts, debugging regressions, and measuring cost/latency improvements.

## How to Compare

1. Go to the **Traces** list in the dashboard
2. Select the checkbox on two traces
3. Click **Compare** — or navigate to `#/traces/compare?a=<id>&b=<id>`

## What You See

### Side-by-side Span Tree

Both traces are rendered as parallel span trees. Matching spans (by name) are aligned and color-coded:

| Color | Meaning |
|-------|---------|
| Green | Span exists in both, similar duration |
| Yellow | Span exists in both, significantly different duration |
| Red | Span only in one trace (added or removed) |

### Diff Metrics Panel

At the top, a summary panel shows aggregate differences:

| Metric | Trace A | Trace B | Delta |
|--------|---------|---------|-------|
| Total duration | 4.2s | 3.1s | -26% |
| Total cost | $0.0042 | $0.0031 | -26% |
| Span count | 8 | 6 | -2 |
| Error spans | 0 | 1 | +1 |

### Span Detail Diff

Click any matched span pair to open a detail panel showing input/output diffs between the two runs.

## Use Cases

- **Prompt optimization** — compare token usage and output quality before/after prompt changes
- **Regression detection** — verify a code change didn't add unexpected tool calls or latency
- **Cost analysis** — measure actual savings from switching models or batching calls
- **Debugging** — find which span diverged when one run succeeded and another failed
