import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from artifact.schema import Capability, ActionType
from artifact.store import load_capability
from replay.locator import find_element
from replay.error_handler import handle_error, OutcomeType
from agent.screenshot import take_screenshot, get_page_state
from guardrails.redactor import safe_log

def replay(artifact_path: str, inputs: dict = {}) -> dict:
    capability = load_capability(artifact_path)
    print(f"\n[REPLAY] Starting: {capability.name}")
    print(f"[REPLAY] Version: {capability.version}")
    print(f"[REPLAY] Steps: {len(capability.steps)}\n")

    log_entries = []
    extracted_outputs = {}
    start_time = datetime.utcnow().isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(capability.target_url)
        page.wait_for_load_state("networkidle", timeout=10000)

        for step in capability.steps:
            state = get_page_state(page)
            print(f"[REPLAY] Step {step.step_id}: {step.action.value} - {step.description[:60]}")

            value = step.value or ""
            if step.param_ref and step.param_ref in inputs:
                value = inputs[step.param_ref]

            try:
                if step.action == ActionType.NAVIGATE:
                    page.goto(value)
                    page.wait_for_load_state("networkidle", timeout=10000)

                elif step.action == ActionType.CLICK:
                    el = find_element(page, step.locator)
                    if not el:
                        raise Exception(f"Element not found: {step.locator.value}")
                    el.click()
                    page.wait_for_timeout(1500)

                elif step.action == ActionType.TYPE:
                    el = find_element(page, step.locator)
                    if not el:
                        raise Exception(f"Element not found: {step.locator.value}")
                    el.fill(value)

                elif step.action == ActionType.SELECT:
                    el = find_element(page, step.locator)
                    if not el:
                        raise Exception(f"Element not found: {step.locator.value}")
                    el.select_option(value)

                elif step.action == ActionType.WAIT:
                    page.wait_for_timeout(2000)

                elif step.action == ActionType.EXTRACT:
                    el = find_element(page, step.locator)
                    if el and step.extract_as:
                        extracted_outputs[step.extract_as] = el.inner_text().strip()
                        print(f"[REPLAY] Extracted {step.extract_as} = {extracted_outputs[step.extract_as]}")

                elif step.action == ActionType.ASSERT:
                    if step.checkpoint:
                        page_text = page.inner_text("body").lower()
                        if step.checkpoint.lower() not in page_text:
                            raise Exception(f"Checkpoint failed: expected '{step.checkpoint}'")

                if step.checkpoint and step.action != ActionType.ASSERT:
                    page.wait_for_timeout(500)
                    current_text = page.inner_text("body").lower()
                    if step.checkpoint and step.checkpoint.lower() not in current_text:
                        page_text = page.inner_text("body")
                        error_result = handle_error(
                            step.step_id, step.action.value,
                            f"Checkpoint failed: '{step.checkpoint}' not found",
                            page_text
                        )
                        log_entries.append(safe_log(error_result))
                        if error_result["outcome"] == OutcomeType.HARD_FAILURE:
                            take_screenshot(page, f"checkpoint_fail_step{step.step_id}")
                            browser.close()
                            return _build_result("failed", capability, log_entries, extracted_outputs, start_time, error_result)
                        elif error_result["outcome"] == OutcomeType.BUSINESS_OUTCOME:
                            browser.close()
                            return _build_result("business_outcome", capability, log_entries, extracted_outputs, start_time, error_result)

                log_entries.append(safe_log({
                    "step_id": step.step_id,
                    "action": step.action.value,
                    "description": step.description,
                    "outcome": "success",
                    "url": state["url"]
                }))
                page.wait_for_timeout(800)

            except Exception as e:
                page_text = page.inner_text("body") if page else ""
                error_result = handle_error(step.step_id, step.action.value, str(e), page_text)
                log_entries.append(safe_log(error_result))
                take_screenshot(page, f"error_step{step.step_id}")

                if error_result["outcome"] == OutcomeType.RECOVERABLE:
                    print(f"[REPLAY] Recoverable - retrying step {step.step_id}")
                    page.wait_for_timeout(3000)
                    continue
                elif error_result["outcome"] == OutcomeType.BUSINESS_OUTCOME:
                    browser.close()
                    return _build_result("business_outcome", capability, log_entries, extracted_outputs, start_time, error_result)
                else:
                    browser.close()
                    return _build_result("failed", capability, log_entries, extracted_outputs, start_time, error_result)

        take_screenshot(page, "replay_success")
        browser.close()
        save_replay_log(log_entries, capability.name)
        return _build_result("success", capability, log_entries, extracted_outputs, start_time)

def _build_result(status: str, capability: Capability, log: list, outputs: dict, start_time: str, error: dict = None) -> dict:
    return {
        "status": status,
        "capability": capability.name,
        "version": capability.version,
        "start_time": start_time,
        "end_time": datetime.utcnow().isoformat(),
        "outputs": outputs,
        "error": error,
        "log": log
    }

def save_replay_log(log_entries: list, name: str):
    os.makedirs("evidence", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"evidence/replay_run_{timestamp}.log"
    with open(filename, "w") as f:
        json.dump({"capability": name, "timestamp": timestamp, "steps": log_entries}, f, indent=2)
    print(f"[REPLAY] Log saved: {filename}")
