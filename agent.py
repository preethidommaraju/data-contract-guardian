"""
STEP 3-4: The Reasoning Agent

When contracts/user_contract.py detects a violation, THIS file sends it
to Claude to reason about:
    - how risky is this change?
    - what's a safe fix?
    - should it be auto-applied or sent to a human?

You'll need an Anthropic API key: https://console.anthropic.com/
Set it as an environment variable before running:
    export ANTHROPIC_API_KEY="your-key-here"
"""

import os
import json
import anthropic
from contracts.user_contract import validate_against_contract

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

AGENT_SYSTEM_PROMPT = """You are Data Contract Guardian, an AI agent that protects
downstream data consumers from breaking changes made by upstream producer teams.

You will be given:
1. The original data contract (what fields/types were expected)
2. A record that violates that contract (what actually arrived)

You must respond with ONLY valid JSON, no other text, in this exact shape:
{
  "risk_level": "low" | "medium" | "high",
  "reasoning": "one or two sentences explaining WHY this is risky or safe",
  "suggested_fix": "a concrete, specific fix a backend engineer could apply",
  "safe_to_auto_apply": true | false
}

Guidance for risk_level:
- "low": cosmetic changes, safe renames with an obvious alias fix
- "medium": changes that need a fix but are unlikely to corrupt data
- "high": type changes, removed fields, or anything that could silently
  corrupt downstream calculations (e.g. a number becoming a string)

Only set "safe_to_auto_apply" to true for "low" risk changes.
"""


def analyze_violation(contract_schema: dict, bad_record: dict, violation_details: str) -> dict:
    """
    Sends the violation to Claude and gets back a structured risk assessment.
    """
    user_message = f"""
Expected contract (Pydantic schema): {json.dumps(contract_schema, indent=2)}

Record that violated the contract: {json.dumps(bad_record, indent=2)}

Validation error details: {violation_details}

Analyze this and respond with the JSON format specified in your instructions.
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=AGENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if Claude adds them
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "risk_level": "unknown",
            "reasoning": "Could not parse agent response",
            "suggested_fix": raw_text,
            "safe_to_auto_apply": False
        }


def run_agent_on_record(record: dict):
    """
    Full pipeline for ONE incoming record:
    1. Validate against contract
    2. If it violates, send to Claude for reasoning
    3. Print/return the decision
    """
    is_valid, error = validate_against_contract(record)

    if is_valid:
        print(f"✅ Record passes contract: {record}")
        return {"status": "valid", "record": record}

    print(f"🚨 Contract violation detected: {record}")
    print(f"   Details: {error}")
    print("   Sending to agent for risk assessment...\n")

    contract_schema = {
        "user_id": "string",
        "signup_date": "string (YYYY-MM-DD)",
        "risk_score": "float (0.0 - 1.0)"
    }

    decision = analyze_violation(contract_schema, record, error)

    print(f"   Risk level: {decision['risk_level']}")
    print(f"   Reasoning: {decision['reasoning']}")
    print(f"   Suggested fix: {decision['suggested_fix']}")
    print(f"   Auto-apply safe: {decision['safe_to_auto_apply']}")

    return {"status": "violation", "record": record, "decision": decision}


# --- Quick manual test ---
if __name__ == "__main__":
    bad_record = {
        "user_id": "U123",
        "signup_date": "2026-01-15",
        "risk_score": "high"   # BREAKING CHANGE: was float, now string
    }

    result = run_agent_on_record(bad_record)
