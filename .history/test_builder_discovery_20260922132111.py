import json
import sys

import requests


LEAD_AGENT_URL = "http://127.0.0.1:8000"


def print_json(title: str, data):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def check_health():
    print("\nChecking Lead Agent...")

    response = requests.get(
        f"{LEAD_AGENT_URL}/",
        timeout=10,
    )

    response.raise_for_status()

    print_json(
        "LEAD AGENT HEALTH",
        response.json(),
    )


def check_routes():
    print("\nChecking Builder Discovery route...")

    response = requests.get(
        f"{LEAD_AGENT_URL}/openapi.json",
        timeout=10,
    )

    response.raise_for_status()

    openapi = response.json()

    route = "/api/v1/leads/builder-discovery"

    if route in openapi.get("paths", {}):
        print(f"\nOK: {route}")
    else:
        print(f"\nERROR: {route} is not registered.")

        print("\nAvailable Lead routes:")

        for path in openapi.get("paths", {}):
            if "/leads" in path:
                print(f"  {path}")

        sys.exit(1)


def builder_discovery(
    workspace_id: str,
    location: str,
    target_limit: int,
):
    print("\nStarting Builder Discovery...")

    payload = {
        "workspace_id": workspace_id,
        "location": location,
        "target_limit": target_limit,
    }

    print_json(
        "REQUEST",
        payload,
    )

    response = requests.post(
        f"{LEAD_AGENT_URL}/api/v1/leads/builder-discovery",
        json=payload,
        timeout=180,
    )

    print(f"\nHTTP STATUS: {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        return

    print_json(
        "BUILDER DISCOVERY RESPONSE",
        data,
    )

    if response.ok:
        print("\nBuilder Discovery completed.")
    else:
        print("\nBuilder Discovery failed.")


def main():
    print("=" * 70)
    print("ATREAL - TEMPORARY LEAD AGENT TEST CLIENT")
    print("=" * 70)

    workspace_id = input(
        "\nWorkspace ID: "
    ).strip()

    if not workspace_id:
        print("Workspace ID is required.")
        return

    location = input(
        "Location [Palghar]: "
    ).strip()

    if not location:
        location = "Palghar"

    target_input = input(
        "Target builders [3]: "
    ).strip()

    if not target_input:
        target_limit = 3
    else:
        try:
            target_limit = int(target_input)
        except ValueError:
            print("Target must be an integer.")
            return

    if target_limit < 1:
        print("Target must be at least 1.")
        return

    check_health()

    check_routes()

    builder_discovery(
        workspace_id=workspace_id,
        location=location,
        target_limit=target_limit,
    )


if __name__ == "__main__":
    main()