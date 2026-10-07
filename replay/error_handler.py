from enum import Enum

class OutcomeType(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    RECOVERABLE = "recoverable"
    HARD_FAILURE = "hard_failure"

BUSINESS_OUTCOMES = [
    "no member found",
    "not found",
    "account is locked",
    "permission denied",
    "record not found",
    "no results",
]

RECOVERABLE_CONDITIONS = [
    "timeout",
    "slow",
    "loading",
    "please wait",
    "session expired",
    "try again",
]

def classify_error(error_text: str, page_text: str = "") -> dict:
    combined = (error_text + " " + page_text).lower()

    for phrase in BUSINESS_OUTCOMES:
        if phrase in combined:
            return {
                "outcome": OutcomeType.BUSINESS_OUTCOME,
                "message": f"Known business outcome: {phrase}",
                "recoverable": False,
                "details": error_text
            }

    for phrase in RECOVERABLE_CONDITIONS:
        if phrase in combined:
            return {
                "outcome": OutcomeType.RECOVERABLE,
                "message": f"Recoverable condition: {phrase}",
                "recoverable": True,
                "details": error_text
            }

    return {
        "outcome": OutcomeType.HARD_FAILURE,
        "message": "Unrecognized failure - stopping replay",
        "recoverable": False,
        "details": error_text
    }

def handle_error(step_id: int, action: str, error: str, page_text: str = "") -> dict:
    classification = classify_error(error, page_text)
    print(f"[ERROR] Step {step_id} ({action}): {classification['outcome']} - {classification['message']}")
    return {
        "step_id": step_id,
        "action": action,
        "error": error,
        **classification
    }
