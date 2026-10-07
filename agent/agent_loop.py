import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from agent.screenshot import take_screenshot, get_page_state
from artifact.schema import Capability, ActionStep, ActionType, Locator, LocatorStrategy, InputParam, OutputField
from artifact.store import save_capability
from guardrails.allowlist import check_action
from guardrails.redactor import safe_log
from escalation.escalation_manager import check_escalation, create_intervention_request

MAX_STEPS = 20

MOCK_SCRIPTS = {
    "lookup_member": [
        {"thought": "I see a login page. I need to enter credentials.", "action": "type", "locator": {"strategy": "name", "value": "username"}, "value": "officer", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Now I enter the password.", "action": "type", "locator": {"strategy": "name", "value": "password"}, "value": "pass123", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Click the Log On button to submit credentials.", "action": "click", "locator": {"strategy": "css", "value": "input[type=submit]"}, "value": "", "checkpoint": "member id", "done": False, "escalate": False},
        {"thought": "I am on the search page. I will enter the member ID.", "action": "type", "locator": {"strategy": "name", "value": "member_id"}, "value": "MEMBER_ID_PLACEHOLDER", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Click Search to find the member.", "action": "click", "locator": {"strategy": "css", "value": "input[type=submit]"}, "value": "", "checkpoint": "member information", "done": False, "escalate": False},
        {"thought": "I can see the member detail page. Extracting savings balance.", "action": "extract", "locator": {"strategy": "css", "value": "#balance-SAV-001"}, "value": "", "extract_as": "savings_balance", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Goal complete. Member found and balance extracted.", "action": "done", "locator": {}, "value": "", "checkpoint": "", "done": True, "escalate": False},
    ],
    "create_subaccount": [
        {"thought": "I see a login page. Entering credentials.", "action": "type", "locator": {"strategy": "name", "value": "username"}, "value": "officer", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Entering password.", "action": "type", "locator": {"strategy": "name", "value": "password"}, "value": "pass123", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Clicking Log On.", "action": "click", "locator": {"strategy": "css", "value": "input[type=submit]"}, "value": "", "checkpoint": "member id", "done": False, "escalate": False},
        {"thought": "Entering member ID in search.", "action": "type", "locator": {"strategy": "name", "value": "member_id"}, "value": "MEMBER_ID_PLACEHOLDER", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Clicking Search.", "action": "click", "locator": {"strategy": "css", "value": "input[type=submit]"}, "value": "", "checkpoint": "member information", "done": False, "escalate": False},
        {"thought": "On member detail page. Clicking Open New Sub-Account.", "action": "click", "locator": {"strategy": "text", "value": "Open New Sub-Account"}, "value": "", "checkpoint": "account details", "done": False, "escalate": False},
        {"thought": "Selecting account type Savings.", "action": "select", "locator": {"strategy": "name", "value": "account_type"}, "value": "Savings", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Entering initial deposit amount.", "action": "type", "locator": {"strategy": "name", "value": "initial_deposit"}, "value": "100.00", "checkpoint": "", "done": False, "escalate": False},
        {"thought": "Clicking Continue to proceed to confirmation.", "action": "click", "locator": {"strategy": "css", "value": "input[type=submit]"}, "value": "", "checkpoint": "please confirm", "done": False, "escalate": False},
        {"thought": "On confirmation screen. Clicking Confirm.", "action": "click", "locator": {"strategy": "css", "value": "#confirm-btn"}, "value": "", "checkpoint": "successfully created", "done": False, "escalate": False},
        {"thought": "Sub-account successfully created. Goal complete.", "action": "done", "locator": {}, "value": "", "checkpoint": "", "done": True, "escalate": False},
    ]
}

def get_mock_script(goal: str, member_id: str = "12345") -> list:
    goal_lower = goal.lower()
    if "sub-account" in goal_lower or "subaccount" in goal_lower or "new account" in goal_lower:
        script = MOCK_SCRIPTS["create_subaccount"]
    else:
        script = MOCK_SCRIPTS["lookup_member"]
    result = []
    for step in script:
        s = dict(step)
        if s.get("value") == "MEMBER_ID_PLACEHOLDER":
            s["value"] = member_id
        result.append(s)
    return result

def run_agent(goal: str, target_url: str, inputs: dict = {}, tenant_id: str = "default") -> dict:
    member_id = inputs.get("member_id", "12345")
    history = []
    recorded_steps = []
    extracted_outputs = {}
    log_entries = []
    start_time = datetime.utcnow().isoformat()

    print(f"\n[AGENT] Starting: {goal}")
    print(f"[AGENT] Target: {target_url}")
    print(f"[AGENT] Mode: MOCK (LLM responses simulated)\n")

    mock_script = get_mock_script(goal, member_id)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(target_url)
        page.wait_for_load_state("networkidle", timeout=10000)

        for step_num, action_json in enumerate(mock_script, 1):
            state = get_page_state(page)

            thought = action_json.get("thought", "")
            action = action_json.get("action", "")
            locator = action_json.get("locator", {})
            value = action_json.get("value", "")
            extract_as = action_json.get("extract_as", "")
            checkpoint = action_json.get("checkpoint", "")
            done = action_json.get("done", False)

            log_value = "[REDACTED]" if action == "type" and "password" in str(locator) else value
            print(f"[AGENT] Step {step_num}: {action} | {thought[:80]}")

            log_entry = safe_log({
                "step": step_num,
                "action": action,
                "thought": thought,
                "locator": locator,
                "value": log_value,
                "url": state["url"],
                "checkpoint": checkpoint
            })
            log_entries.append(log_entry)
            history.append(log_entry)

            if done:
                print(f"[AGENT] Goal complete at step {step_num}")
                take_screenshot(page, "success")
                break

            try:
                if action == "navigate":
                    page.goto(value)
                    page.wait_for_load_state("networkidle", timeout=10000)
                elif action == "click":
                    el = find_element(page, locator)
                    if el:
                        el.click()
                        page.wait_for_timeout(1500)
                elif action == "type":
                    el = find_element(page, locator)
                    if el:
                        el.fill(value)
                elif action == "select":
                    el = find_element(page, locator)
                    if el:
                        el.select_option(value)
                elif action == "wait":
                    page.wait_for_timeout(2000)
                elif action == "extract":
                    el = find_element(page, locator)
                    if el and extract_as:
                        extracted_outputs[extract_as] = el.inner_text().strip()
                        print(f"[EXTRACT] {extract_as} = {extracted_outputs[extract_as]}")

                if action not in ["navigate", "wait", "done"]:
                    recorded_steps.append(ActionStep(
                        step_id=step_num,
                        action=ActionType(action) if action in [a.value for a in ActionType] else ActionType.WAIT,
                        description=thought,
                        locator=Locator(
                            strategy=LocatorStrategy(locator.get("strategy", "css")),
                            value=locator.get("value", ""),
                            description=thought
                        ) if locator and locator.get("value") else None,
                        value=value,
                        extract_as=extract_as or None,
                        checkpoint=checkpoint or None
                    ))

                page.wait_for_timeout(800)

            except Exception as e:
                print(f"[AGENT] Action error at step {step_num}: {e}")
                take_screenshot(page, f"error_step{step_num}")
                stuck = check_escalation(history)
                if stuck:
                    intervention = create_intervention_request(
                        goal=goal, step=step_num,
                        reason=str(e), state=state,
                        screenshot=take_screenshot(page, "stuck")
                    )
                    browser.close()
                    return {"status": "escalated", "intervention": intervention, "log": log_entries}

        capability = Capability(
            name=goal[:50].replace(" ", "_"),
            description=goal,
            target_url=target_url,
            tenant_id=tenant_id,
            inputs=[InputParam(name=k, type="string", description=k, example=v) for k, v in inputs.items()],
            outputs=[OutputField(name=k, type="string", description=k, extract_from=k) for k in extracted_outputs.keys()],
            steps=recorded_steps,
            success_condition="Goal completed successfully",
            tags=["agent-recorded", "mock"]
        )

        artifact_path = save_capability(capability)
        print(f"\n[AGENT] Artifact saved: {artifact_path}")
        save_log(log_entries, goal)
        browser.close()

        return {
            "status": "success",
            "artifact_path": artifact_path,
            "outputs": extracted_outputs,
            "steps_taken": len(recorded_steps),
            "log": log_entries
        }

def find_element(page, locator: dict):
    strategy = locator.get("strategy", "css")
    value = locator.get("value", "")
    if not value:
        return None
    try:
        if strategy == "css":
            return page.locator(value).first
        elif strategy == "xpath":
            return page.locator(f"xpath={value}").first
        elif strategy == "text":
            return page.get_by_text(value).first
        elif strategy == "name":
            return page.locator(f"[name='{value}']").first
        elif strategy == "label":
            return page.get_by_label(value).first
        elif strategy == "placeholder":
            return page.get_by_placeholder(value).first
    except Exception as e:
        print(f"[LOCATOR] Failed: {e}")
        return None

def save_log(log_entries: list, goal: str):
    os.makedirs("evidence", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"evidence/discovery_run_{timestamp}.log"
    with open(filename, "w") as f:
        json.dump({"goal": goal, "timestamp": timestamp, "mode": "mock", "steps": log_entries}, f, indent=2)
    print(f"[AGENT] Log saved: {filename}")
