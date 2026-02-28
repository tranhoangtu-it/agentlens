"""Seed demo traces into AgentLens server for demo/screenshot purposes."""

import httpx
import uuid
import time

BASE = "http://127.0.0.1:8000/api/traces"


def ms(offset_s: float) -> int:
    return int((time.time() + offset_s) * 1000)


def post_trace(trace_id, agent_name, spans):
    resp = httpx.post(BASE, json={"trace_id": trace_id, "agent_name": agent_name, "spans": spans})
    print(f"  {agent_name}: {resp.status_code}")


# Trace 1: Research Agent — multi-step with tools
t1 = str(uuid.uuid4())
s1_root = str(uuid.uuid4())
s1_arxiv = str(uuid.uuid4())
s1_scholar = str(uuid.uuid4())
s1_summarize = str(uuid.uuid4())
post_trace(t1, "ResearchAgent", [
    {"span_id": s1_root, "name": "research_pipeline", "type": "agent_run",
     "start_ms": ms(-60), "end_ms": ms(-2),
     "input": "Find latest papers on multi-agent systems",
     "output": "Found 12 relevant papers from ArXiv and Semantic Scholar",
     "cost": {"model": "gpt-4o", "input_tokens": 2500, "output_tokens": 800, "usd": 0.0143}},
    {"span_id": s1_arxiv, "parent_id": s1_root, "name": "arxiv_search", "type": "tool_call",
     "start_ms": ms(-55), "end_ms": ms(-40),
     "input": "multi-agent systems 2025-2026", "output": "8 papers found"},
    {"span_id": s1_scholar, "parent_id": s1_root, "name": "semantic_scholar", "type": "tool_call",
     "start_ms": ms(-39), "end_ms": ms(-25),
     "input": "autonomous AI agents collaboration", "output": "4 papers found"},
    {"span_id": s1_summarize, "parent_id": s1_root, "name": "llm:summarize", "type": "llm_call",
     "start_ms": ms(-24), "end_ms": ms(-5),
     "output": "Summary: Multi-agent systems show 40% improvement in complex reasoning tasks...",
     "cost": {"model": "gpt-4o", "input_tokens": 3200, "output_tokens": 600, "usd": 0.014}},
])

# Trace 2: Coding Agent — with handoff
t2 = str(uuid.uuid4())
s2_root = str(uuid.uuid4())
s2_read = str(uuid.uuid4())
s2_plan = str(uuid.uuid4())
s2_write = str(uuid.uuid4())
s2_handoff = str(uuid.uuid4())
post_trace(t2, "CodingAgent", [
    {"span_id": s2_root, "name": "implement_feature", "type": "agent_run",
     "start_ms": ms(-120), "end_ms": ms(-10),
     "input": "Add pagination to /api/users endpoint",
     "output": "Feature implemented with 3 files modified",
     "cost": {"model": "claude-3-5-sonnet", "input_tokens": 8000, "output_tokens": 2500, "usd": 0.0615}},
    {"span_id": s2_read, "parent_id": s2_root, "name": "read_codebase", "type": "tool_call",
     "start_ms": ms(-115), "end_ms": ms(-100), "output": "Read 5 files"},
    {"span_id": s2_plan, "parent_id": s2_root, "name": "llm:plan", "type": "llm_call",
     "start_ms": ms(-99), "end_ms": ms(-80),
     "cost": {"model": "claude-3-5-sonnet", "input_tokens": 5000, "output_tokens": 1200, "usd": 0.033}},
    {"span_id": s2_write, "parent_id": s2_root, "name": "write_code", "type": "tool_call",
     "start_ms": ms(-79), "end_ms": ms(-40), "output": "Modified routes.py, models.py, tests.py"},
    {"span_id": s2_handoff, "parent_id": s2_root, "name": "handoff:reviewer", "type": "handoff",
     "start_ms": ms(-39), "end_ms": ms(-15), "output": "Code review passed"},
])

# Trace 3: Data Analyst Agent
t3 = str(uuid.uuid4())
s3_root = str(uuid.uuid4())
s3_query = str(uuid.uuid4())
s3_analyze = str(uuid.uuid4())
post_trace(t3, "DataAnalystAgent", [
    {"span_id": s3_root, "name": "analyze_sales", "type": "agent_run",
     "start_ms": ms(-200), "end_ms": ms(-150),
     "input": "Analyze Q4 2025 sales trends",
     "output": "Revenue up 23% YoY, top product: Enterprise Plan",
     "cost": {"model": "gpt-4o-mini", "input_tokens": 15000, "output_tokens": 3000, "usd": 0.00405}},
    {"span_id": s3_query, "parent_id": s3_root, "name": "query_database", "type": "tool_call",
     "start_ms": ms(-195), "end_ms": ms(-180), "output": "1.2M rows fetched"},
    {"span_id": s3_analyze, "parent_id": s3_root, "name": "llm:analyze", "type": "llm_call",
     "start_ms": ms(-179), "end_ms": ms(-155),
     "cost": {"model": "gpt-4o-mini", "input_tokens": 12000, "output_tokens": 2000, "usd": 0.003}},
])

# Trace 4: Running agent (no end_ms on root)
t4 = str(uuid.uuid4())
s4_root = str(uuid.uuid4())
s4_ping = str(uuid.uuid4())
post_trace(t4, "MonitoringAgent", [
    {"span_id": s4_root, "name": "health_check", "type": "agent_run",
     "start_ms": ms(0), "input": "Check all services"},
    {"span_id": s4_ping, "parent_id": s4_root, "name": "ping_services", "type": "tool_call",
     "start_ms": ms(1), "end_ms": ms(3), "output": "3/5 services healthy"},
])

print("\nDone! Open http://localhost:5173 to see the dashboard.")
