# Data Contract Guardian

**An AI agent that catches breaking data changes between teams before they hit production — auto-fixing safe changes and escalating risky ones to a human.**

## The Problem

At any company where multiple teams share data, a schema change on one side (a renamed field, a changed data type) can silently break a downstream pipeline, dashboard, or ML model. These failures are usually caught hours or days later — by a human, after something has already gone wrong. This is a real, expensive, and common failure mode in production data systems.

## What This Does

Data Contract Guardian sits between a data producer and a data consumer, like an automated contract reviewer:

1. Detects when incoming data violates an agreed-upon schema/contract
2. Uses an LLM (Claude) to reason about *how risky* the change is and what the right fix looks like
3. **Auto-fixes** low-risk changes (e.g., safe field renames)
4. **Escalates high-risk changes to a human** via Slack, with a clear explanation and suggested fix, instead of guessing
5. Logs every decision for observability — how many changes were caught, auto-fixed vs. escalated, and response time

## Why I Built This

At Tech Mahindra, I worked on production banking data pipelines (2TB+/day) where schema and data quality issues were a constant, costly risk — I built the validation and observability frameworks that caught these issues manually. This project automates and extends that experience with an AI reasoning layer, moving from "detect and alert a human" to "detect, reason, and act autonomously with guardrails."

## Architecture

Producer change -> Contract Validator (Pydantic) -> Violation?
-> Claude Agent reasons about risk & fix
-> Low risk -> Auto-apply fix
-> High risk -> Alert human via Slack -> Human approves/rejects
-> Log outcome for metrics

## Agentic AI Patterns Demonstrated

- **ReAct Planning** — observe -> think -> act -> reflect loop for risk assessment
- **Multi-Tool Orchestration** — coordinating validation, reasoning, and remediation tools
- **Human-in-the-Loop** — auto-resolves safe cases, escalates risky ones with full context
- **Event-Triggered Automation** — designed to run on real CI/CD events (GitHub Actions)
- **Production Observability** — logs every decision for auditability and metrics

## Tech Stack

- **Reasoning engine**: Claude API (Anthropic)
- **Agent orchestration**: LangGraph
- **Schema/contract definition**: Pydantic
- **Automation trigger**: GitHub Actions
- **Human alerting**: Slack Webhooks
- **Logging/metrics**: SQLite

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
export SLACK_WEBHOOK_URL="your-slack-webhook-url-here"
python3 contracts/user_contract.py   # test the contract validator
python3 agent.py                     # basic AI agent
python3 graph_agent.py               # full multi-step LangGraph agent
```

## Status

**Live and working:**
- ✅ Contract validation (Pydantic)
- ✅ Multi-step LangGraph agent with tool-calling (downstream impact + incident history lookup)
- ✅ Claude-powered risk reasoning
- ✅ Real Slack human-in-the-loop escalation
- ✅ Real GitHub Actions workflow — triggers and runs automatically on every pull request (see `.github/workflows/data-contract-guardian.yml`)

**Not yet built:**
- ⬜ SQLite logging for historical metrics
- ⬜ Metrics dashboard

## Author

Preethi Dommaraju
