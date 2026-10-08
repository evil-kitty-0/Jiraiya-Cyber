#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import json
import sys
import uuid


BASE = Path(__file__).resolve().parents[1]
PROPOSALS = BASE / "self_improvement" / "proposals"


def ensure_dir():
    PROPOSALS.mkdir(parents=True, exist_ok=True)


def create_proposal(
    title,
    description,
    changes,
    tests,
    risk="LOW",
):
    ensure_dir()

    proposal_id = "PROP-" + uuid.uuid4().hex[:8].upper()

    proposal = {
        "id": proposal_id,
        "title": title,
        "description": description,
        "changes": changes,
        "tests": tests,
        "risk": risk,
        "status": "PENDING",
        "created_at": datetime.now().astimezone().isoformat(),
        "approved_at": None,
        "rejected_at": None,
    }

    path = PROPOSALS / f"{proposal_id}.json"

    path.write_text(
        json.dumps(
            proposal,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=============================================")
    print("JIRAIYA IMPROVEMENT PROPOSAL")
    print("=============================================")
    print()
    print(f"ID          : {proposal_id}")
    print(f"Title       : {title}")
    print(f"Risk        : {risk}")
    print(f"Status      : PENDING")
    print()
    print("Description:")
    print(description)
    print()
    print("Changes:")
    for change in changes:
        print(f"  • {change}")
    print()
    print("Tests:")
    for test in tests:
        print(f"  • {test}")
    print()
    print("Waiting for user approval.")
    print()
    print(f"Proposal saved:")
    print(path)

    return proposal_id


def load_proposal(proposal_id):
    path = PROPOSALS / f"{proposal_id}.json"

    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return None


def list_proposals():
    ensure_dir()

    files = sorted(PROPOSALS.glob("PROP-*.json"))

    print("=============================================")
    print("JIRAIYA PROPOSALS")
    print("=============================================")

    if not files:
        print("No proposals found.")
        return

    for path in files:
        try:
            proposal = json.loads(
                path.read_text(encoding="utf-8")
            )

            print(
                f"{proposal['id']} | "
                f"{proposal['status']} | "
                f"{proposal['risk']} | "
                f"{proposal['title']}"
            )

        except Exception:
            print(f"⚠ Invalid proposal: {path.name}")


def update_status(proposal_id, status):
    proposal = load_proposal(proposal_id)

    if proposal is None:
        print(f"ERROR: Proposal {proposal_id} not found.")
        return False

    if proposal["status"] != "PENDING":
        print(
            f"ERROR: Proposal is already "
            f"{proposal['status']}."
        )
        return False

    status = status.upper()

    if status not in ("APPROVED", "REJECTED"):
        print("ERROR: Status must be APPROVED or REJECTED.")
        return False

    proposal["status"] = status

    now = datetime.now().astimezone().isoformat()

    if status == "APPROVED":
        proposal["approved_at"] = now
    else:
        proposal["rejected_at"] = now

    path = PROPOSALS / f"{proposal_id}.json"

    path.write_text(
        json.dumps(
            proposal,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"✓ Proposal {proposal_id} "
        f"marked {status}."
    )

    return True


def usage():
    print(
        """
Usage:

Create:
  python proposal_manager.py create

List:
  python proposal_manager.py list

Approve:
  python proposal_manager.py approve PROP-XXXXXXXX

Reject:
  python proposal_manager.py reject PROP-XXXXXXXX
"""
    )


def demo_proposal():
    return create_proposal(
        title="Sandbox self-test feature",
        description=(
            "Add a harmless internal self-test that "
            "checks whether the Jiraiya sandbox is functioning."
        ),
        changes=[
            "Add a sandbox self-test module",
            "Record test result in the self-improvement log",
        ],
        tests=[
            "Python syntax check",
            "Sandbox import test",
            "Self-test execution",
        ],
        risk="LOW",
    )


def main():
    if len(sys.argv) < 2:
        usage()
        return

    command = sys.argv[1].lower()

    if command == "create":
        demo_proposal()

    elif command == "list":
        list_proposals()

    elif command == "approve":
        if len(sys.argv) < 3:
            print("ERROR: Proposal ID required.")
            return

        update_status(sys.argv[2], "APPROVED")

    elif command == "reject":
        if len(sys.argv) < 3:
            print("ERROR: Proposal ID required.")
            return

        update_status(sys.argv[2], "REJECTED")

    else:
        usage()


if __name__ == "__main__":
    main()
