"""
STEP 1-2: The Data Contract

This file defines what the "Consumer" (e.g. a fraud detection pipeline)
expects to receive from the "Producer" (e.g. a backend users service).

Think of this as the written agreement between two teams.
If incoming data doesn't match this shape, that's a contract violation.
"""

from pydantic import BaseModel, ValidationError
from typing import Optional


class UserContract(BaseModel):
    """
    This is the CONTRACT.
    Consumer team (fraud pipeline) expects every user record to look like this.
    """
    user_id: str
    signup_date: str          # expected format: "YYYY-MM-DD"
    risk_score: float         # expected: a number between 0.0 and 1.0


def validate_against_contract(raw_record: dict) -> tuple[bool, Optional[str]]:
    """
    Checks if a raw incoming data record still matches the contract.

    Returns:
        (True, None) if it matches
        (False, error_message) if it violates the contract
    """
    try:
        UserContract(**raw_record)
        return True, None
    except ValidationError as e:
        return False, str(e)


# --- Quick manual test ---
if __name__ == "__main__":
    # A GOOD record — matches the contract
    good_record = {
        "user_id": "U123",
        "signup_date": "2026-01-15",
        "risk_score": 0.82
    }

    # A BAD record — risk_score is now a string instead of a float
    # (this simulates "Team A" silently breaking the contract)
    bad_record = {
        "user_id": "U123",
        "signup_date": "2026-01-15",
        "risk_score": "high"   # <-- BREAKING CHANGE
    }

    for label, record in [("GOOD record", good_record), ("BAD record", bad_record)]:
        is_valid, error = validate_against_contract(record)
        print(f"\n{label}: {record}")
        print(f"Valid? {is_valid}")
        if error:
            print(f"Violation details:\n{error}")
