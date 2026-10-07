import re
from typing import Any

SENSITIVE_KEYS = [
    "password", "ssn", "token", "secret", "account_number",
    "credit_card", "cvv", "pin", "api_key", "authorization"
]

SENSITIVE_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
    (r'\b\d{16}\b', '[CARD REDACTED]'),
    (r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b', '[CARD REDACTED]'),
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*\S+', '[PASSWORD REDACTED]'),
    (r'(?i)bearer\s+[a-zA-Z0-9\-_\.]+', '[TOKEN REDACTED]'),
]

def redact_value(value: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        value = re.sub(pattern, replacement, value)
    return value

def redact_dict(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, str):
            result[key] = redact_value(value)
        elif isinstance(value, list):
            result[key] = [redact_dict(i) if isinstance(i, dict) else i for i in value]
        else:
            result[key] = value
    return result

def redact_step_value(step: dict) -> dict:
    step = dict(step)
    if step.get("action") == "type":
        locator_desc = step.get("locator", {}).get("description", "").lower()
        if any(s in locator_desc for s in SENSITIVE_KEYS):
            step["value"] = "[REDACTED]"
    return step

def safe_log(data: Any) -> Any:
    if isinstance(data, dict):
        return redact_dict(data)
    elif isinstance(data, str):
        return redact_value(data)
    return data
