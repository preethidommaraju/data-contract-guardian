"""
STEP 5: The LangGraph Agent

This upgrades agent.py from "one straight-through function call" into a
proper multi-step agent graph. The agent now moves through explicit
states, and can call TOOLS along the way before deciding what to do.

New tools added:
    - check_downstream_consumers(): who depends on this field
    - check_past_incidents(): has this kind of change caused problems before

Run this file the same way you ran agent.py:
    python3 graph_agent.py
"""

import os
import json
import requests
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
import anthropic
from contracts.user_contract import validate_against_contract

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Set this as an environment variable, same way as ANTHROPIC_API_KEY:
#   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def send_slack_alert(record: dict, decision: dict) -> bool:
    """
    Posts a real message to Slack via the Incoming Webhook.
    Returns True if it posted successfully, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        print("[SLACK] No SLACK_WEBHOOK_URL set — skipping real post.")
        return False

    message = {
        "text": (
            f":rotating_light: *Data Contract Violation Detected*\n"
            f"*Risk level:* {decision.get('risk_level', 'unknown')}\n"
            f"*Record:* `{json.dumps(record)}`\n"
            f"*Reasoning:* {decision.get('reasoning', 'n/a')}\n"
            f"*Suggested fix:* {decision.get('suggested_fix', 'n/a')}\n"
            f"*Needs human review — not auto-applied.*"
        )
    }

    response = requests.post(SLACK_WEBHOOK_URL, json=message)
    if response.status_code == 200:
        print("[SLACK] ✅ Alert posted successfully to Slack.")
        return True
    else:
        print(f"[SLACK] ❌ Failed to post — status {response.status_code}: {response.text}")
        return False


# ---------------------------------------------------------------------------
# TOOLS the agent can call (Step: Multi-Tool Orchestration)
# ---------------------------------------------------------------------------

# In a real system these would query a real service catalog / incident log.
# For the portfolio version, these are realistic simulated lookups.

FAKE_DOWNSTREAM_REGISTRY = {
    "risk_score": ["fraud-detection-pipeline", "customer-risk-dashboard"],
    "signup_date": ["user-lifecycle-analytics"],
}

FAKE_INCIDENT_LOG = [
    {"field": "risk_score", "change_type": "type_change", "outcome": "caused fraud model to crash for 3 hours"},
    {"field": "email", "change_type": "rename", "outcome": "auto-resolved with alias, no downtime"},
]


def check_downstream_consumers(field_name: str) -> list:
    """Tool: who depends on this field."""
    return FAKE_DOWNSTREAM_REGISTRY.get(field_name, [])


def check_past_incidents(field_name: str) -> list:
    """Tool: has this field caused problems before."""
    return [i for i in FAKE_INCIDENT_LOG if i["field"] == field_name]


# ---------------------------------------------------------------------------
# AGENT STATE — what gets passed between steps in the graph
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    record: dict
    is_valid: bool
    violation_details: Optional[str]
    downstream_consumers: Optional[list]
    past_incidents: Optional[list]
    decision: Optional[dict]


# ---------------------------------------------------------------------------
# GRAPH NODES — each one is a "step" the agent moves through
# ---------------------------------------------------------------------------

def observe_node(state: AgentState) -> AgentState:
    """Step 1: OBSERVE — check the record against the contract."""
    is_valid, error = validate_against_contract(state["record"])
    print(f"[OBSERVE] Valid? {is_valid}")
    return {**state, "is_valid": is_valid, "violation_details": error}


def gather_context_node(state: AgentState) -> AgentState:
    """Step 2: GATHER CONTEXT — call tools to investigate before deciding."""
    # figure out which field actually broke, roughly, from the error text
    field_name = "risk_score" if "risk_score" in (state["violation_details"] or "") else "unknown"

    consumers = check_downstream_consumers(field_name)
    incidents = check_past_incidents(field_name)

    print(f"[GATHER CONTEXT] Downstream consumers affected: {consumers}")
    print(f"[GATHER CONTEXT] Past incidents on this field: {len(incidents)} found")

    return {**state, "downstream_consumers": consumers, "past_incidents": incidents}


def reason_node(state: AgentState) -> AgentState:
    """Step 3: THINK — ask Claude to reason using all gathered context."""
    prompt = f"""
A data contract violation was detected.

Record that violated the contract: {json.dumps(state['record'], indent=2)}
Violation details: {state['violation_details']}
Downstream systems that depend on this data: {state['downstream_consumers']}
Past incidents involving this field: {json.dumps(state['past_incidents'], indent=2)}

Respond with ONLY valid JSON in this shape:
{{
  "risk_level": "low" | "medium" | "high",
  "reasoning": "explanation using the context above",
  "suggested_fix": "a concrete fix",
  "safe_to_auto_apply": true | false
}}
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()

    try:
        decision = json.loads(raw)
    except json.JSONDecodeError:
        decision = {"risk_level": "unknown", "reasoning": raw, "suggested_fix": "n/a", "safe_to_auto_apply": False}

    print(f"[THINK] Risk level: {decision['risk_level']}")
    return {**state, "decision": decision}


def act_node(state: AgentState) -> AgentState:
    """Step 4: ACT — auto-fix or escalate based on the decision."""
    decision = state["decision"]
    if decision.get("safe_to_auto_apply"):
        print(f"[ACT] ✅ Auto-applying fix: {decision['suggested_fix']}")
    else:
        print(f"[ACT] 🚨 High risk — escalating to human via Slack...")
        send_slack_alert(state["record"], decision)
    return state


def valid_record_node(state: AgentState) -> AgentState:
    """Path when the record is already valid — nothing to do."""
    print("[OBSERVE] ✅ Record passes contract, no action needed.")
    return state


# ---------------------------------------------------------------------------
# BUILD THE GRAPH
# ---------------------------------------------------------------------------

def route_after_observe(state: AgentState) -> str:
    return "gather_context" if not state["is_valid"] else "valid_end"


graph = StateGraph(AgentState)
graph.add_node("observe", observe_node)
graph.add_node("gather_context", gather_context_node)
graph.add_node("reason", reason_node)
graph.add_node("act", act_node)
graph.add_node("valid_end", valid_record_node)

graph.set_entry_point("observe")
graph.add_conditional_edges("observe", route_after_observe, {
    "gather_context": "gather_context",
    "valid_end": "valid_end"
})
graph.add_edge("gather_context", "reason")
graph.add_edge("reason", "act")
graph.add_edge("act", END)
graph.add_edge("valid_end", END)

agent_graph = graph.compile()


# ---------------------------------------------------------------------------
# RUN IT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    bad_record = {
        "user_id": "U123",
        "signup_date": "2026-01-15",
        "risk_score": "high"   # BREAKING CHANGE
    }

    print("=" * 60)
    print("Running Data Contract Guardian (LangGraph agent)")
    print("=" * 60)

    final_state = agent_graph.invoke({"record": bad_record})

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
