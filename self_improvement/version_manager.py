#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import shutil
import json
import sys


BASE = Path(__file__).resolve().parents[1]
VERSIONS = BASE / "self_improvement" / "versions"
META_FILE = VERSIONS / "versions.json"

# Files/directories that form the Jiraiya application.
TRACKED = [
    "agent.py",
    "learner.py",
    "model_manager.py",
    "core",
    "memory",
    "knowledge",
    "web",
]


def load_metadata():
    if not META_FILE.exists():
        return []

    try:
        return json.loads(META_FILE.read_text())
    except Exception:
        return []


def save_metadata(data):
    META_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )


def next_version():
    versions = load_metadata()

    if not versions:
        return "v0.1.0"

    numbers = []

    for item in versions:
        version = item.get("version", "v0.0.0")
        try:
            parts = version.lstrip("v").split(".")
            numbers.append(tuple(map(int, parts)))
        except Exception:
            pass

    if not numbers:
        return "v0.1.0"

    major, minor, patch = max(numbers)
    return f"v{major}.{minor}.{patch + 1}"


def snapshot(reason="manual snapshot"):
    version = next_version()
    destination = VERSIONS / version

    destination.mkdir(parents=True, exist_ok=False)

    copied = []

    for item in TRACKED:
        source = BASE / item

        if not source.exists():
            continue

        target = destination / item
        target.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

        copied.append(item)

    metadata = load_metadata()

    entry = {
        "version": version,
        "created_at": datetime.now().astimezone().isoformat(),
        "reason": reason,
        "files": copied,
    }

    metadata.append(entry)
    save_metadata(metadata)

    print("=============================================")
    print("JIRAIYA VERSION MANAGER")
    print("=============================================")
    print(f"Version : {version}")
    print(f"Reason  : {reason}")
    print("Status  : SNAPSHOT CREATED")
    print()
    print("Tracked:")
    for item in copied:
        print(f"  ✓ {item}")


def list_versions():
    versions = load_metadata()

    print("=============================================")
    print("JIRAIYA VERSIONS")
    print("=============================================")

    if not versions:
        print("No versions found.")
        return

    for item in versions:
        print(
            f"{item['version']}  |  "
            f"{item['created_at']}  |  "
            f"{item.get('reason', '')}"
        )


def restore(version):
    versions = load_metadata()

    selected = None

    for item in versions:
        if item.get("version") == version:
            selected = item
            break

    if selected is None:
        print(f"ERROR: Version {version} not found.")
        return False

    source_root = VERSIONS / version

    if not source_root.exists():
        print(f"ERROR: Snapshot directory missing: {source_root}")
        return False

    # Safety backup before restoring an old version.
    backup_dir = (
        BASE
        / "self_improvement"
        / "backups"
        / datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    backup_dir.mkdir(parents=True, exist_ok=False)

    for item in TRACKED:
        source = BASE / item

        if not source.exists():
            continue

        target = backup_dir / item
        target.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    print(f"Current system backed up to:")
    print(backup_dir)

    # Restore selected version.
    for item in TRACKED:
        source = source_root / item
        target = BASE / item

        if not source.exists():
            continue

        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        target.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    print()
    print("=============================================")
    print("ROLLBACK COMPLETE")
    print("=============================================")
    print(f"Restored : {version}")
    print(f"Backup   : {backup_dir}")
    print("Status   : SUCCESS")

    return True


def usage():
    print(
        """
Usage:

  python version_manager.py snapshot "reason"
  python version_manager.py list
  python version_manager.py restore v0.1.0
"""
    )


def main():
    if len(sys.argv) < 2:
        usage()
        return

    command = sys.argv[1].lower()

    if command == "snapshot":
        reason = " ".join(sys.argv[2:]).strip()

        if not reason:
            reason = "manual snapshot"

        snapshot(reason)

    elif command == "list":
        list_versions()

    elif command == "restore":
        if len(sys.argv) < 3:
            print("ERROR: version required.")
            print("Example: python version_manager.py restore v0.1.0")
            return

        restore(sys.argv[2])

    else:
        usage()


if __name__ == "__main__":
    main()
