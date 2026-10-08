#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import json
import sys


BASE = Path(__file__).resolve().parents[1]
SI = BASE / "self_improvement"

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

    timestamp = datetime.now().astimezone().isoformat()

    entry = {
        "timestamp": timestamp,
        "event": event,
        "data": data or {},
    }

    log_file = LOGS / "update_manager.log"

    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUPS / f"update_{timestamp}"

    backup_dir.mkdir(parents=True, exist_ok=False)

    copied = []

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

        copied.append(item)

    log_event(
        "backup_created",
        {
            "path": str(backup_dir),
            "files": copied,
        },
    )

    return backup_dir


def restore_backup(backup_dir):
    if not backup_dir.exists():
        raise RuntimeError(f"Backup not found: {backup_dir}")

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

        target.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    log_event(
        "rollback_completed",
        {
            "backup": str(backup_dir),
        },
    )


def run_command(command):
    result = subprocess.run(
        command,
        cwd=BASE,
        capture_output=True,
        text=True,
    )

    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def syntax_check():
    results = []

    python_files = []

    for item in TRACKED:
        path = BASE / item

        if path.is_file() and path.suffix == ".py":
            python_files.append(path)

        elif path.is_dir():
            python_files.extend(path.rglob("*.py"))

    for path in python_files:
        result = run_command(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(path),
            ]
        )

        results.append(result)

        if result["returncode"] != 0:
            return False, results

    return True, results


def health_check():
    result = run_command(
        [
            sys.executable,
            "-c",
            (
                "import urllib.request; "
                "r=urllib.request.urlopen("
                "'http://127.0.0.1:8080/health', timeout=5); "
                "print(r.read().decode())"
            ),
        ]
    )

    return result["returncode"] == 0, result


def dry_run():
    print("=============================================")
    print("JIRAIYA UPDATE MANAGER")
    print("=============================================")
    print("MODE: DRY RUN")
    print()
    print("No production files will be modified.")
    print()

    log_event("dry_run_started")

    syntax_ok, syntax_results = syntax_check()

    print(
        "✓ Syntax check passed"
        if syntax_ok
        else "✗ Syntax check failed"
    )

    if not syntax_ok:
        log_event(
            "dry_run_failed",
            {"reason": "syntax_check"},
        )
        return False

    health_ok, health_result = health_check()

    print(
        "✓ LLM health check passed"
        if health_ok
        else "⚠ LLM health check unavailable"
    )

    log_event(
        "dry_run_completed",
        {
            "syntax_ok": syntax_ok,
            "health_ok": health_ok,
        },
    )

    print()
    print("DRY RUN COMPLETE")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python update_manager.py dry-run")
        print("  python update_manager.py backup")
        return

    command = sys.argv[1].lower()

    if command == "dry-run":
        dry_run()

    elif command == "backup":
        backup = create_backup()

        print("=============================================")
        print("BACKUP CREATED")
        print("=============================================")
        print(backup)

    else:
        print("Unknown command:", command)


if __name__ == "__main__":
    main()
