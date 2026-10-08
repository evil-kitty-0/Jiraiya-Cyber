#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import json
import hashlib
import sys


BASE = Path(__file__).resolve().parents[1]
SI = BASE / "self_improvement"
PATCHES = SI / "proposals"
LOGS = SI / "logs"


def log_event(event, data=None):
    LOGS.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "event": event,
        "data": data or {},
    }

    with (LOGS / "patch_manager.log").open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            json.dumps(
                entry,
                ensure_ascii=False,
            ) + "\n"
        )


def proposal_path(proposal_id):
    return PATCHES / f"{proposal_id}.json"


def load_proposal(proposal_id):
    path = proposal_path(proposal_id)

    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return None


def save_proposal(proposal_id, proposal):
    path = proposal_path(proposal_id)

    path.write_text(
        json.dumps(
            proposal,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def calculate_hash(content):
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def add_patch(
    proposal_id,
    relative_file,
    new_content,
):
    """
    Attach a complete-file replacement patch
    to an existing proposal.

    Production is NOT modified here.
    """

    proposal = load_proposal(proposal_id)

    if proposal is None:
        raise RuntimeError(
            f"Proposal {proposal_id} not found."
        )

    if proposal.get("status") != "PENDING":
        raise RuntimeError(
            "Patch can only be added while "
            "proposal is PENDING."
        )

    relative_file = relative_file.strip("/")

    # Security boundary:
    # patch paths must stay inside Jiraiya.
    target = (BASE / relative_file).resolve()

    try:
        target.relative_to(BASE.resolve())
    except ValueError:
        raise RuntimeError(
            "Invalid patch path."
        )

    patch = {
        "file": relative_file,
        "content": new_content,
        "sha256": calculate_hash(
            new_content
        ),
        "created_at":
            datetime.now()
            .astimezone()
            .isoformat(),
    }

    proposal.setdefault(
        "patches",
        []
    )

    # Replace an existing patch for same file.
    proposal["patches"] = [
        p
        for p in proposal["patches"]
        if p.get("file") != relative_file
    ]

    proposal["patches"].append(patch)

    save_proposal(
        proposal_id,
        proposal
    )

    log_event(
        "patch_added",
        {
            "proposal": proposal_id,
            "file": relative_file,
            "sha256": patch["sha256"],
        }
    )

    print(
        f"✓ Patch added: {relative_file}"
    )

    return True


def inspect_patch(proposal_id):
    proposal = load_proposal(
        proposal_id
    )

    if proposal is None:
        print(
            f"ERROR: Proposal "
            f"{proposal_id} not found."
        )
        return

    patches = proposal.get(
        "patches",
        []
    )

    print(
        "============================================="
    )
    print("JIRAIYA PATCH INSPECTOR")
    print(
        "============================================="
    )

    print(
        f"Proposal: {proposal_id}"
    )
    print(
        f"Status  : {proposal.get('status')}"
    )
    print()

    if not patches:
        print("No patches attached.")
        return

    for index, patch in enumerate(
        patches,
        start=1
    ):
        print(
            f"[{index}] "
            f"{patch.get('file')}"
        )

        print(
            f"SHA256: "
            f"{patch.get('sha256')}"
        )

        print(
            f"Created: "
            f"{patch.get('created_at')}"
        )

        print()


def verify_patch(proposal_id):
    proposal = load_proposal(
        proposal_id
    )

    if proposal is None:
        print(
            f"ERROR: Proposal "
            f"{proposal_id} not found."
        )
        return False

    patches = proposal.get(
        "patches",
        []
    )

    if not patches:
        print(
            "✗ No patches to verify."
        )
        return False

    print(
        "============================================="
    )
    print("JIRAIYA PATCH VERIFICATION")
    print(
        "============================================="
    )

    all_valid = True

    for patch in patches:

        content = patch.get(
            "content",
            ""
        )

        expected = patch.get(
            "sha256"
        )

        actual = calculate_hash(
            content
        )

        if actual != expected:
            print(
                f"✗ Hash mismatch: "
                f"{patch.get('file')}"
            )
            all_valid = False
        else:
            print(
                f"✓ Hash verified: "
                f"{patch.get('file')}"
            )

    if all_valid:
        print()
        print("PATCH INTEGRITY: PASS")

        log_event(
            "patch_integrity_passed",
            {
                "proposal": proposal_id
            }
        )

    else:
        print()
        print("PATCH INTEGRITY: FAILED")

        log_event(
            "patch_integrity_failed",
            {
                "proposal": proposal_id
            }
        )

    return all_valid


def usage():
    print(
        """
Usage:

  python patch_manager.py inspect PROP-XXXXXXXX

  python patch_manager.py verify PROP-XXXXXXXX
"""
    )


def main():
    if len(sys.argv) < 3:
        usage()
        return

    command = sys.argv[1].lower()
    proposal_id = sys.argv[2]

    if command == "inspect":
        inspect_patch(
            proposal_id
        )

    elif command == "verify":
        verify_patch(
            proposal_id
        )

    else:
        usage()


if __name__ == "__main__":
    main()
