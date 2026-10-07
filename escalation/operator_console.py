import json
import os
from datetime import datetime
from escalation.escalation_manager import resolve_intervention

ESCALATION_DIR = "evidence/escalations"

def list_pending_interventions() -> list:
    if not os.path.exists(ESCALATION_DIR):
        return []
    pending = []
    for f in os.listdir(ESCALATION_DIR):
        if f.endswith(".json"):
            with open(os.path.join(ESCALATION_DIR, f)) as fp:
                data = json.load(fp)
            if data.get("status") == "pending":
                pending.append(data)
    return pending

def show_intervention(intervention: dict):
    print("\n" + "="*60)
    print(f"INTERVENTION REQUEST: {intervention['id']}")
    print("="*60)
    print(f"Goal      : {intervention['goal']}")
    print(f"Stuck at  : Step {intervention['stuck_at_step']}")
    print(f"Reason    : {intervention['reason']}")
    print(f"URL       : {intervention['current_url']}")
    print(f"Screenshot: {intervention.get('screenshot', 'N/A')}")
    print("="*60)

def run_operator_console():
    print("\n[OPERATOR CONSOLE] Checking for pending interventions...")
    pending = list_pending_interventions()
    if not pending:
        print("[OPERATOR CONSOLE] No pending interventions.")
        return
    for intervention in pending:
        show_intervention(intervention)
        print("\nOptions:")
        print("  1. Mark as resolved (human took over manually)")
        print("  2. Skip")
        choice = input("Choice: ").strip()
        if choice == "1":
            note = input("Describe what you did: ").strip()
            human_actions = [{
                "timestamp": datetime.utcnow().isoformat(),
                "action": "manual_intervention",
                "note": note
            }]
            resolve_intervention(intervention["id"], human_actions)
            print(f"[OPERATOR CONSOLE] Intervention {intervention['id']} resolved.")

if __name__ == "__main__":
    run_operator_console()
