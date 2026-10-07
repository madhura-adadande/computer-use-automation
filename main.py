import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.agent_loop import run_agent
from replay.executor import replay

def main():
    parser = argparse.ArgumentParser(description="Computer-Use Automation System")
    subparsers = parser.add_subparsers(dest="command")

    discover = subparsers.add_parser("discover", help="Run agent to discover and record a capability")
    discover.add_argument("--goal", required=True, help="Natural language goal")
    discover.add_argument("--url", required=True, help="Target URL")
    discover.add_argument("--tenant", default="default", help="Tenant ID")

    rep = subparsers.add_parser("replay", help="Replay a saved capability")
    rep.add_argument("--artifact", required=True, help="Path to artifact JSON")
    rep.add_argument("--input", action="append", help="Input params as key=value", default=[])

    args = parser.parse_args()

    if args.command == "discover":
        result = run_agent(
            goal=args.goal,
            target_url=args.url,
            tenant_id=args.tenant
        )
        print(f"\n[RESULT] Status: {result['status']}")
        if result.get("artifact_path"):
            print(f"[RESULT] Artifact: {result['artifact_path']}")
        if result.get("outputs"):
            print(f"[RESULT] Outputs: {result['outputs']}")

    elif args.command == "replay":
        inputs = {}
        for item in args.input:
            k, v = item.split("=", 1)
            inputs[k] = v
        result = replay(args.artifact, inputs)
        print(f"\n[RESULT] Status: {result['status']}")
        if result.get("outputs"):
            print(f"[RESULT] Outputs: {result['outputs']}")
        if result.get("error"):
            print(f"[RESULT] Error: {result['error']}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
