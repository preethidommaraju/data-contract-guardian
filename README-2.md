# Data Contract Guardian

An AI agent that catches breaking data changes between two teams before
they hit production — auto-fixing safe changes and escalating risky ones
to a human.

## What's built so far (Steps 1-4)

- `contracts/user_contract.py` — the data contract (Pydantic schema) + validator
- `agent.py` — Claude-powered reasoning agent that assesses risk and suggests fixes

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
```

## Run it

```bash
# Test the contract validator alone
python3 contracts/user_contract.py

# Test the full agent (validator + Claude reasoning)
python3 agent.py
```

## What happens when you run agent.py

1. A record with a broken `risk_score` field (string instead of float) is checked against the contract
2. The contract validator catches the mismatch
3. The violation is sent to Claude, which assesses risk level and suggests a fix
4. You see the agent's full reasoning printed to the console

## Next steps (not yet built)

- [ ] Wrap the logic in LangGraph for a proper multi-step agent loop
- [ ] Add Slack webhook alert for high-risk violations
- [ ] Add GitHub Action to trigger on real PRs
- [ ] Log every decision to SQLite for metrics
- [ ] Build a simple Streamlit dashboard showing changes caught/auto-fixed

## Agentic patterns demonstrated

- **ReAct Planning** — observe (violation) → think (risk assessment) → act (fix or escalate)
- **Multi-Tool Orchestration** — (coming next) checking downstream consumers, past incidents
- **Human-in-the-Loop** — (coming next) Slack escalation for high-risk changes
- **Event-Triggered Automation** — (coming next) GitHub Actions trigger
- **Production Observability** — (coming next) SQLite logging + dashboard
