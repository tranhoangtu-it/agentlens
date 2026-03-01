---
title: Alerting
description: Detect cost spikes, error rates, latency anomalies, and missing spans
---

The Alerting system monitors your agent traces in real-time and fires alerts when behavior deviates from expected baselines.

## Alert Types

| Type | Description |
|------|-------------|
| **Cost spike** | Total trace cost exceeds threshold |
| **Error rate** | Percentage of failed spans exceeds threshold |
| **Latency** | Trace duration exceeds threshold |
| **Missing span** | Expected span name not found in trace |

## Creating Alert Rules

Navigate to **Alert Rules** in the sidebar, then click **New Rule**.

### Rule Configuration

| Field | Description |
|-------|-------------|
| **Name** | Display name for the rule |
| **Type** | One of the 4 alert types above |
| **Threshold** | Numeric limit (cost in $, rate in %, duration in ms) |
| **Mode** | `absolute` — fixed value, or `relative` — % change from rolling baseline |
| **Baseline window** | Number of recent traces used to compute the rolling average |
| **Webhook URL** | Optional HTTP endpoint to notify when alert fires |
| **Cooldown** | Minimum seconds between repeated alerts (default: 60s) |

### Example: Cost Spike Rule

```
Name: High cost alert
Type: cost_spike
Threshold: 0.10       (10 cents per trace)
Mode: absolute
Cooldown: 60
```

### Example: Error Rate Rule

```
Name: Error rate too high
Type: error_rate
Threshold: 20         (20% of spans failing)
Mode: absolute
Baseline window: 10   (compare against last 10 traces)
```

## Viewing Alerts

Navigate to **Alerts** in the sidebar to see all fired alert events, with:
- Timestamp
- Rule name and type
- Trace that triggered it (click to open)
- Resolved / unresolved status

The sidebar badge shows the count of unresolved alerts.

## Real-time Delivery

Alerts fire instantly via SSE — no polling needed. The dashboard badge updates in real-time when a new alert fires.

## Webhook Integration

When a webhook URL is configured, AgentLens sends a POST request on every alert:

```json
{
  "rule_id": "rule_abc123",
  "rule_name": "High cost alert",
  "type": "cost_spike",
  "trace_id": "trace_xyz",
  "value": 0.142,
  "threshold": 0.10,
  "fired_at": "2026-03-01T10:00:00Z"
}
```

Use this to integrate with Slack, PagerDuty, or any custom notification system.
