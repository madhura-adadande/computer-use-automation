import json
import os
from datetime import datetime

ESCALATION_DIR = "evidence/escalations"

def check_escalation(history: list, threshold: int = 3) -> bool:
    if len(history) < threshold:
        return False
    recent = history[-threshold:]
    actions = [h.get("action") for h in recent]
    if len(set(actions)) == 1:
        return True
    urls = [h.get("url") for h in recent]
    if len(set(urls)) == 1:
        return True
    return False

def create_intervention_request(goal: str, step: int, reason: str, state: dict, screenshot: str = None) -> dict:
    os.makedirs(ESCALATION_DIR, exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    intervention = {
        "id": f"intervention_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": timestamp,
        "goal": goal,
        "stuck_at_step": step,
        "reason": reason,
        "current_url": state.get("url", ""),
        "current_page_title": state.get("title", ""),
        "screenshot": screenshot,
        "status": "pending",
        "human_actions": [],
        "resumed_at": None
    }
    filepath = f"{ESCALATION_DIR}/{intervention['id']}.json"
    with open(filepath, "w") as f:
        json.dump(intervention, f, indent=2)
    print(f"[ESCALATION] Intervention request created: {filepath}")
    print(f"[ESCALATION] Reason: {reason}")
    print(f"[ESCALATION] URL: {state.get('url', '')}")
    return intervention

def resolve_intervention(intervention_id: str, human_actions: list) -> dict:
    filepath = f"{ESCALATION_DIR}/{intervention_id}.json"
    with open(filepath, "r") as f:
        intervention = json.load(f)
    intervention["status"] = "resolved"
    intervention["human_actions"] = human_actions
    intervention["resumed_at"] = datetime.utcnow().isoformat()
    with open(filepath, "w") as f:
        json.dump(intervention, f, indent=2)
    return intervention
