"""
TestBench AI — Graph Topology Compilation
====================================================
Component 3 of N. Assembles the three existing nodes into an explicit,
cyclic LangGraph workflow:

                ┌─────────────┐
        ┌──────>│ supervisor  │
        │       └──────┬──────┘
        │              │
        │              v
        │      ┌────────────────┐
        │      │ analyzer_oracle │
        │      └────────┬────────┘
        │               │
        │        [oracle_routing_gateway]
        │         PASSED  │  FAILED / REMEDIATED
        │           │     └──────────┐
        │           v                v
        │          END        ┌─────────────┐
        └───────────────────── │ rca_healer  │
                                └─────────────┘

No LLM call governs any edge transition — routing is a pure function
of `execution_status`, read directly off the deterministic state dict.
"""

from langgraph.graph import StateGraph, END

from graph_state import (
    TestBenchState,
    supervisor_router_node,
    signal_analyzer_oracle_node,
    root_cause_remediator_node,
)


# ---------------------------------------------------------------------------
# Conditional Routing Gateway (evaluated after 'analyzer_oracle')
# ---------------------------------------------------------------------------
def oracle_routing_gateway(state: TestBenchState) -> str:
    """
    Pure, deterministic routing function — no model inference.

    Reads `execution_status` off the state dict and returns one of two
    fixed routing keys ("terminate" / "remediate"), which are mapped to
    concrete graph destinations in the `add_conditional_edges` path_map
    below. Any status outside the known set fails closed into
    remediation rather than silently defaulting to termination.
    """

    status = state.get("execution_status", "")

    if status == "PASSED":
        return "terminate"

    if status in ("FAILED", "REMEDIATED"):
        return "remediate"

    # Unknown/unexpected status — never assume success.
    return "remediate"


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------
builder = StateGraph(TestBenchState)

# --- Register nodes ---------------------------------------------------------
builder.add_node("supervisor", supervisor_router_node)
builder.add_node("analyzer_oracle", signal_analyzer_oracle_node)
builder.add_node("rca_healer", root_cause_remediator_node)

# --- Static edges ------------------------------------------------------------
builder.set_entry_point("supervisor")
builder.add_edge("supervisor", "analyzer_oracle")

# --- Conditional edge out of 'analyzer_oracle' -------------------------------
builder.add_conditional_edges(
    "analyzer_oracle",
    oracle_routing_gateway,
    {
        "terminate": END,
        "remediate": "rca_healer",
    },
)

# --- Cyclic recovery edge: rca_healer loops back into supervisor ------------
builder.add_edge("rca_healer", "supervisor")

# --- Compile ------------------------------------------------------------------
testbench_graph = builder.compile()
