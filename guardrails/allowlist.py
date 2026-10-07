import yaml
import fnmatch
from typing import Optional

def load_policy(path: str = "config/policy.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def is_domain_allowed(url: str, policy: Optional[dict] = None) -> bool:
    if policy is None:
        policy = load_policy()
    allowed = policy.get("allowlist", {}).get("domains", [])
    return any(domain in url for domain in allowed)

def is_route_allowed(route: str, policy: Optional[dict] = None) -> bool:
    if policy is None:
        policy = load_policy()
    allowed_routes = policy.get("allowlist", {}).get("allowed_routes", [])
    for pattern in allowed_routes:
        if fnmatch.fnmatch(route, pattern):
            return True
    return False

def is_action_allowed(action: str, policy: Optional[dict] = None) -> bool:
    if policy is None:
        policy = load_policy()
    allowed = policy.get("allowlist", {}).get("allowed_actions", [])
    return action in allowed

def is_risky_action(action_type: str, route: str, policy: Optional[dict] = None) -> bool:
    if policy is None:
        policy = load_policy()
    risky = policy.get("safety", {}).get("risky_actions", [])
    for r in risky:
        if r["type"] == action_type:
            for pattern in r.get("routes", []):
                if fnmatch.fnmatch(route, pattern):
                    return True
    return False

def check_action(action: str, url: str) -> dict:
    policy = load_policy()
    from urllib.parse import urlparse
    parsed = urlparse(url)
    route = parsed.path
    result = {
        "allowed": True,
        "risky": False,
        "reason": None
    }
    if not is_domain_allowed(url, policy):
        result["allowed"] = False
        result["reason"] = f"Domain not in allowlist: {parsed.netloc}"
        return result
    if not is_route_allowed(route, policy):
        result["allowed"] = False
        result["reason"] = f"Route not in allowlist: {route}"
        return result
    if not is_action_allowed(action, policy):
        result["allowed"] = False
        result["reason"] = f"Action not permitted: {action}"
        return result
    if is_risky_action(action, route, policy):
        result["risky"] = True
        result["reason"] = f"Risky action on sensitive route: {route}"
    return result
