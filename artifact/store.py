import json
import os
from artifact.schema import Capability, ActionStep, Locator, LocatorStrategy, ActionType

STORE_DIR = "evidence"

def save_capability(capability: Capability) -> str:
    os.makedirs(STORE_DIR, exist_ok=True)
    filename = f"{STORE_DIR}/{capability.name.replace(' ', '_')}_{capability.version}.json"
    with open(filename, "w") as f:
        json.dump(capability.model_dump(), f, indent=2)
    return filename

def load_capability(filepath: str) -> Capability:
    with open(filepath, "r") as f:
        data = json.load(f)
    steps = []
    for s in data.get("steps", []):
        locator = None
        if s.get("locator"):
            loc = s["locator"]
            locator = Locator(
                strategy=LocatorStrategy(loc.get("strategy", "css")),
                value=loc.get("value", ""),
                fallbacks=loc.get("fallbacks", []),
                description=loc.get("description", "")
            )
        steps.append(ActionStep(
            step_id=s["step_id"],
            action=ActionType(s["action"]),
            description=s.get("description", ""),
            locator=locator,
            value=s.get("value"),
            param_ref=s.get("param_ref"),
            extract_as=s.get("extract_as"),
            checkpoint=s.get("checkpoint"),
            timeout_ms=s.get("timeout_ms", 5000),
            on_error=s.get("on_error", "fail")
        ))
    data["steps"] = steps
    return Capability(**data)

def list_capabilities() -> list:
    if not os.path.exists(STORE_DIR):
        return []
    files = [f for f in os.listdir(STORE_DIR) if f.endswith(".json")]
    capabilities = []
    for f in files:
        try:
            cap = load_capability(os.path.join(STORE_DIR, f))
            capabilities.append({"file": f, "name": cap.name, "version": cap.version, "status": cap.status})
        except Exception:
            pass
    return capabilities
