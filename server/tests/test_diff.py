"""Tests for diff.py: build_span_tree, _flatten_tree, match_spans, compute_diff."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from diff import SpanNode, _flatten_tree, build_span_tree, compute_diff, match_spans


# ── Helpers ────────────────────────────────────────────────────────────────────

def _span(sid, name="op", type_="tool_call", parent_id=None, input_=None, output=None,
          start_ms=None, end_ms=None, cost_usd=None, cost_in=None, cost_out=None):
    """Build minimal span dict for testing."""
    d = {
        "id": sid,
        "name": name,
        "type": type_,
        "parent_id": parent_id,
        "input": input_,
        "output": output,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "cost_usd": cost_usd,
        "cost_input_tokens": cost_in,
        "cost_output_tokens": cost_out,
    }
    return d


# ── build_span_tree ────────────────────────────────────────────────────────────

class TestBuildSpanTree:
    def test_single_root(self):
        spans = [_span("root")]
        roots = build_span_tree(spans)
        assert len(roots) == 1
        assert roots[0].span_id == "root"
        assert roots[0].depth == 0

    def test_parent_child(self):
        spans = [
            _span("root"),
            _span("child", parent_id="root"),
        ]
        roots = build_span_tree(spans)
        assert len(roots) == 1
        assert roots[0].span_id == "root"
        assert len(roots[0].children) == 1
        child = roots[0].children[0]
        assert child.span_id == "child"
        assert child.depth == 1
        assert child.sibling_index == 0

    def test_multiple_roots(self):
        spans = [_span("a"), _span("b")]
        roots = build_span_tree(spans)
        root_ids = {r.span_id for r in roots}
        assert "a" in root_ids
        assert "b" in root_ids

    def test_sibling_index_assigned(self):
        spans = [
            _span("root"),
            _span("child1", parent_id="root"),
            _span("child2", parent_id="root"),
        ]
        roots = build_span_tree(spans)
        children = roots[0].children
        assert len(children) == 2
        indexes = {c.sibling_index for c in children}
        assert indexes == {0, 1}

    def test_depth_three_levels(self):
        spans = [
            _span("root"),
            _span("mid", parent_id="root"),
            _span("leaf", parent_id="mid"),
        ]
        roots = build_span_tree(spans)
        mid = roots[0].children[0]
        leaf = mid.children[0]
        assert mid.depth == 1
        assert leaf.depth == 2

    def test_unknown_parent_becomes_root(self):
        """Span referencing non-existent parent should be treated as root."""
        spans = [_span("orphan", parent_id="nonexistent")]
        roots = build_span_tree(spans)
        assert any(r.span_id == "orphan" for r in roots)

    def test_empty_spans(self):
        roots = build_span_tree([])
        assert roots == []

    def test_span_with_all_fields(self):
        spans = [_span("s1", name="llm", type_="llm_call",
                        input_="hello", output="world",
                        start_ms=100, end_ms=200,
                        cost_usd=0.01, cost_in=50, cost_out=30)]
        roots = build_span_tree(spans)
        node = roots[0]
        assert node.input == "hello"
        assert node.output == "world"
        assert node.start_ms == 100
        assert node.end_ms == 200
        assert node.cost_usd == 0.01
        assert node.cost_input_tokens == 50
        assert node.cost_output_tokens == 30

    def test_span_using_span_id_key(self):
        """Spans using 'span_id' key (instead of 'id') should be parsed."""
        spans = [{"span_id": "s99", "name": "op", "type": "tool_call"}]
        roots = build_span_tree(spans)
        assert len(roots) == 1
        assert roots[0].span_id == "s99"


# ── _flatten_tree ─────────────────────────────────────────────────────────────

class TestFlattenTree:
    def test_single_node(self):
        node = SpanNode("r", "op", "tool", 0, 0, None, None, None, None, None, None, None, [])
        result = _flatten_tree([node])
        assert len(result) == 1
        assert result[0].span_id == "r"

    def test_dfs_order(self):
        """DFS: root → child1 → grandchild → child2."""
        grandchild = SpanNode("gc", "op", "t", 2, 0, None, None, None, None, None, None, None, [])
        child1 = SpanNode("c1", "op", "t", 1, 0, None, None, None, None, None, None, None, [grandchild])
        child2 = SpanNode("c2", "op", "t", 1, 1, None, None, None, None, None, None, None, [])
        root = SpanNode("r", "op", "t", 0, 0, None, None, None, None, None, None, None, [child1, child2])
        result = _flatten_tree([root])
        ids = [n.span_id for n in result]
        assert ids == ["r", "c1", "gc", "c2"]

    def test_multiple_roots(self):
        a = SpanNode("a", "op", "t", 0, 0, None, None, None, None, None, None, None, [])
        b = SpanNode("b", "op", "t", 0, 1, None, None, None, None, None, None, None, [])
        result = _flatten_tree([a, b])
        ids = [n.span_id for n in result]
        assert ids == ["a", "b"]

    def test_empty(self):
        assert _flatten_tree([]) == []


# ── match_spans ───────────────────────────────────────────────────────────────

class TestMatchSpans:
    def _make_roots(self, *names):
        """Create flat list of root SpanNodes with given names."""
        return [
            SpanNode(f"s{i}", n, "tool_call", 0, i, None, None, None, None, None, None, None, [])
            for i, n in enumerate(names)
        ]

    def test_perfect_match(self):
        left = self._make_roots("a", "b")
        right = self._make_roots("a", "b")
        matched, left_only, right_only = match_spans(left, right)
        assert len(matched) == 2
        assert left_only == []
        assert right_only == []

    def test_left_only(self):
        left = self._make_roots("a", "extra")
        right = self._make_roots("a")
        matched, left_only, right_only = match_spans(left, right)
        assert len(matched) == 1
        assert len(left_only) == 1
        assert left_only[0].name == "extra"
        assert right_only == []

    def test_right_only(self):
        left = self._make_roots("a")
        right = self._make_roots("a", "new")
        matched, left_only, right_only = match_spans(left, right)
        assert len(matched) == 1
        assert left_only == []
        assert len(right_only) == 1
        assert right_only[0].name == "new"

    def test_no_match(self):
        left = self._make_roots("x")
        right = self._make_roots("y")
        matched, left_only, right_only = match_spans(left, right)
        assert matched == []
        assert len(left_only) == 1
        assert len(right_only) == 1

    def test_empty_both(self):
        matched, left_only, right_only = match_spans([], [])
        assert matched == []
        assert left_only == []
        assert right_only == []

    def test_duplicate_names_matched_in_order(self):
        """Two spans with same name should be matched pairwise."""
        left = [
            SpanNode("l1", "dup", "t", 0, 0, None, None, None, None, None, None, None, []),
            SpanNode("l2", "dup", "t", 0, 1, None, None, None, None, None, None, None, []),
        ]
        right = [
            SpanNode("r1", "dup", "t", 0, 0, None, None, None, None, None, None, None, []),
            SpanNode("r2", "dup", "t", 0, 1, None, None, None, None, None, None, None, []),
        ]
        matched, left_only, right_only = match_spans(left, right)
        assert len(matched) == 2
        assert left_only == []
        assert right_only == []


# ── compute_diff ──────────────────────────────────────────────────────────────

class TestComputeDiff:
    def _span_d(self, sid, name="op", type_="tool_call", parent_id=None,
                input_=None, output=None, start_ms=None, end_ms=None,
                cost_usd=None, cost_in=None, cost_out=None):
        return {
            "id": sid, "name": name, "type": type_,
            "parent_id": parent_id, "input": input_, "output": output,
            "start_ms": start_ms, "end_ms": end_ms,
            "cost_usd": cost_usd,
            "cost_input_tokens": cost_in,
            "cost_output_tokens": cost_out,
        }

    def test_identical_spans(self):
        left = [self._span_d("a", input_="q", output="r")]
        right = [self._span_d("b", input_="q", output="r")]
        result = compute_diff(left, right)
        assert len(result["matched"]) == 1
        assert result["matched"][0]["status"] == "identical"
        assert result["left_only"] == []
        assert result["right_only"] == []

    def test_changed_spans(self):
        left = [self._span_d("a", input_="q", output="old")]
        right = [self._span_d("b", input_="q", output="new")]
        result = compute_diff(left, right)
        assert result["matched"][0]["status"] == "changed"

    def test_left_only_span(self):
        left = [self._span_d("a", name="extra")]
        right = []
        result = compute_diff(left, right)
        assert "a" in result["left_only"]
        assert result["matched"] == []
        assert result["right_only"] == []

    def test_right_only_span(self):
        left = []
        right = [self._span_d("b", name="new")]
        result = compute_diff(left, right)
        assert "b" in result["right_only"]
        assert result["matched"] == []
        assert result["left_only"] == []

    def test_duration_delta_computed(self):
        left = [self._span_d("a", start_ms=0, end_ms=100)]
        right = [self._span_d("b", start_ms=0, end_ms=150)]
        result = compute_diff(left, right)
        m = result["matched"][0]
        assert m["duration_delta_ms"] == 50

    def test_duration_delta_none_when_missing(self):
        """If either span missing start/end, delta should be None."""
        left = [self._span_d("a", start_ms=None, end_ms=None)]
        right = [self._span_d("b", start_ms=0, end_ms=100)]
        result = compute_diff(left, right)
        m = result["matched"][0]
        assert m["duration_delta_ms"] is None

    def test_cost_delta_computed(self):
        left = [self._span_d("a", cost_usd=0.01)]
        right = [self._span_d("b", cost_usd=0.03)]
        result = compute_diff(left, right)
        m = result["matched"][0]
        assert abs(m["cost_delta_usd"] - 0.02) < 1e-9

    def test_cost_delta_none_when_missing(self):
        left = [self._span_d("a", cost_usd=None)]
        right = [self._span_d("b", cost_usd=0.01)]
        result = compute_diff(left, right)
        assert result["matched"][0]["cost_delta_usd"] is None

    def test_token_deltas_computed(self):
        left = [self._span_d("a", cost_in=100, cost_out=50)]
        right = [self._span_d("b", cost_in=200, cost_out=30)]
        result = compute_diff(left, right)
        m = result["matched"][0]
        assert m["input_tokens_delta"] == 100
        assert m["output_tokens_delta"] == -20

    def test_token_deltas_none_when_missing(self):
        left = [self._span_d("a", cost_in=None, cost_out=None)]
        right = [self._span_d("b", cost_in=100, cost_out=50)]
        result = compute_diff(left, right)
        m = result["matched"][0]
        assert m["input_tokens_delta"] is None
        assert m["output_tokens_delta"] is None

    def test_empty_traces(self):
        result = compute_diff([], [])
        assert result == {"matched": [], "left_only": [], "right_only": []}

    def test_left_right_span_ids_in_matched(self):
        left = [self._span_d("L1")]
        right = [self._span_d("R1")]
        result = compute_diff(left, right)
        m = result["matched"][0]
        assert m["left_span_id"] == "L1"
        assert m["right_span_id"] == "R1"
