#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import json
import sys


BASE = Path(__file__).resolve().parents[1]
SI = BASE / "self_improvement"

PROPOSALS = SI / "proposals"
BACKUPS = SI / "backups"
LOGS = SI / "logs"
VERSIONS = SI / "versions"

TRACKED = [
    "agent.py",
    "learner.py",
    "model_manager.py",
    "core",
    "memory",
    "knowledge",
    "web",
]


def log_event(event, data=None):
    LOGS.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "event": event,
        "data": data or {},
    }

    with (LOGS / "deployment.log").open(
        "a",
        encoding="utf-8"
    ) as f:
        f.write(
            json.dumps(
                entry,
                ensure_ascii=False
            ) + "\n"
        )


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


def create_backup():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = BACKUPS / f"deploy_{timestamp}"

    backup_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    copied = []

    for item in TRACKED:
        source = BASE / item

        if not source.exists():
            continue

        target = backup_dir / item
        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

        copied.append(item)

    log_event(
        "backup_created",
        {
            "path": str(backup_dir),
            "files": copied,
        }
    )

    return backup_dir


def restore_backup(backup_dir):
    if not backup_dir.exists():
        raise RuntimeError(
            f"Backup does not exist: {backup_dir}"
        )

    for item in TRACKED:
        source = backup_dir / item
        target = BASE / item

        if not source.exists():
            continue

        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    log_event(
        "rollback_completed",
        {
            "backup": str(backup_dir)
        }
    )


def run_command(command, cwd=BASE):
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True
    )

    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout[-5000:],
        "stderr": result.stderr[-5000:]
    }


def syntax_check(root):
    python_files = list(
        root.rglob("*.py")
    )

    failures = []

    for path in python_files:
        result = run_command(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(path)
            ],
            cwd=root
        )

        if result["returncode"] != 0:
            failures.append({
                "file": str(path),
                "stdout": result["stdout"],
                "stderr": result["stderr"]
            })

    return (
        len(failures) == 0,
        failures
    )


def health_check():
    result = run_command(
        [
            sys.executable,
            "-c",
            (
                "import urllib.request; "
                "r=urllib.request.urlopen("
                "'http://127.0.0.1:8080/health', "
                "timeout=5); "
                "print(r.read().decode())"
            )
        ]
    )

    return (
        result["returncode"] == 0,
        result
    )


def get_latest_version():
    metadata_file = VERSIONS / "versions.json"

    if not metadata_file.exists():
        return "v0.0.0"

    try:
        versions = json.loads(
            metadata_file.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return "v0.0.0"

    if not versions:
        return "v0.0.0"

    numbers = []

    for item in versions:
        version = item.get(
            "version",
            "v0.0.0"
        )

        try:
            parts = (
                version
                .lstrip("v")
                .split(".")
            )

            numbers.append(
                tuple(map(int, parts))
            )

        except Exception:
            pass

    if not numbers:
        return "v0.0.0"

    major, minor, patch = max(numbers)

    return (
        f"v{major}.{minor}.{patch + 1}"
    )


def create_version_snapshot(
    reason
):
    version = get_latest_version()

    destination = (
        VERSIONS / version
    )

    destination.mkdir(
        parents=True,
        exist_ok=False
    )

    copied = []

    for item in TRACKED:
        source = BASE / item

        if not source.exists():
            continue

        target = destination / item

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if source.is_dir():
            shutil.copytree(
                source,
                target
            )
        else:
            shutil.copy2(
                source,
                target
            )

        copied.append(item)

    metadata_file = (
        VERSIONS / "versions.json"
    )

    if metadata_file.exists():
        try:
            metadata = json.loads(
                metadata_file.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            metadata = []
    else:
        metadata = []

    metadata.append({
        "version": version,
        "created_at":
            datetime.now()
            .astimezone()
            .isoformat(),
        "reason": reason,
        "files": copied
    })

    metadata_file.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    return version


def deploy(proposal_id):
    proposal = load_proposal(
        proposal_id
    )

    if proposal is None:
        print(
            f"ERROR: Proposal "
            f"{proposal_id} not found."
        )
        return False

    if proposal.get("status") != "APPROVED":
        print(
            "ERROR: Proposal must be "
            "APPROVED before deployment."
        )
        print(
            f"Current status: "
            f"{proposal.get('status')}"
        )
        return False

    print(
        "============================================="
    )
    print(
        "JIRAIYA DEPLOYMENT ENGINE"
    )
    print(
        "============================================="
    )
    print()
    print(
        f"Proposal: {proposal_id}"
    )
    print(
        f"Title   : {proposal.get('title')}"
    )
    print(
        f"Risk    : {proposal.get('risk')}"
    )
    print()

    log_event(
        "deployment_started",
        {
            "proposal": proposal_id
        }
    )

    # Safety backup.
    print("Creating safety backup...")

    try:
        backup_dir = create_backup()
    except Exception as e:
        print(
            f"✗ Backup failed: {e}"
        )

        log_event(
            "deployment_failed",
            {
                "proposal": proposal_id,
                "reason": "backup_failed",
                "error": str(e)
            }
        )

        return False

    print(
        f"✓ Backup created: {backup_dir}"
    )

    # Current production syntax check.
    print()
    print(
        "Checking current production..."
    )

    syntax_ok, failures = syntax_check(
        BASE
    )

    if not syntax_ok:
        print(
            "✗ Current production "
            "syntax check failed."
        )

        log_event(
            "deployment_failed",
            {
                "proposal": proposal_id,
                "reason":
                    "current_syntax_failed",
                "failures": failures
            }
        )

        return False

    print(
        "✓ Current production syntax OK"
    )

    # IMPORTANT:
    # This first version deliberately does
    # NOT modify production automatically.
    #
    # Actual patch application will be added
    # after the sandbox patch format is defined.

    print()
    print(
        "============================================="
    )
    print(
        "SAFE DEPLOYMENT CHECK"
    )
    print(
        "============================================="
    )

    print(
        "✓ Proposal approved"
    )
    print(
        "✓ Safety backup created"
    )
    print(
        "✓ Production syntax valid"
    )
    print()
    print(
        "⚠ Patch application is not enabled yet."
    )
    print(
        "Production files were NOT modified."
    )

    log_event(
        "deployment_stopped_safely",
        {
            "proposal": proposal_id,
            "backup": str(backup_dir),
            "reason":
                "patch_engine_not_enabled"
        }
    )

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python deployer.py "
            "deploy PROP-XXXXXXXX"
        )
        print(
            "  python deployer.py "
            "health"
        )
        return

    command = sys.argv[1].lower()

    if command == "deploy":

        if len(sys.argv) < 3:
            print(
                "ERROR: Proposal ID required."
            )
            return

        deploy(sys.argv[2])

    elif command == "health":

        ok, result = health_check()

        if ok:
            print(
                "✓ Jiraiya LLM health: OK"
            )
        else:
            print(
                "✗ Jiraiya LLM health: FAILED"
            )
            print(
                result["stderr"]
            )

    else:
        print(
            "Unknown command:",
            command
        )


if __name__ == "__main__":
    main()
