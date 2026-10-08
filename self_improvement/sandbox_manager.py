#!/usr/bin/env python3

import json
import shutil
import sys
import subprocess
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

SELF_DIR = BASE / "self_improvement"
SANDBOX_DIR = SELF_DIR / "sandbox"

PROTECTED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "versions",
    "sandbox",
}

PROTECTED_EXTENSIONS = {
    ".db",
    ".db.enc",
    ".key",
    ".gguf",
    ".log",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_path(path):
    path = str(path).strip()
    path = path.replace("\\", "/")

    while path.startswith("./"):
        path = path[2:]

    while path.startswith("/"):
        path = path[1:]

    return path


def is_protected(path):
    normalized = normalize_path(path)

    parts = Path(normalized).parts

    for part in parts:
        if part in PROTECTED_DIRS:
            return True

    name = Path(normalized).name.lower()

    for extension in PROTECTED_EXTENSIONS:
        if name.endswith(extension):
            return True

    return False


def safe_project_files():
    """
    Return project files that are safe to copy into
    the sandbox.

    Secrets, databases, models, logs and production
    safety directories are excluded.
    """

    files = []

    for path in BASE.rglob("*"):

        if not path.is_file():
            continue

        try:
            relative = path.relative_to(BASE)
        except ValueError:
            continue

        relative_string = normalize_path(
            relative
        )

        if is_protected(relative_string):
            continue

        files.append(relative)

    return files


def create_workspace(plan_path):
    """
    Create a fresh isolated sandbox workspace.
    """

    document = load_json(plan_path)

    plan = document.get(
        "plan",
        document
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    name = (
        "improvement_"
        + timestamp
    )

    workspace = (
        SANDBOX_DIR
        / name
    )

    workspace.mkdir(
        parents=True,
        exist_ok=False
    )

    copied = 0

    for relative in safe_project_files():

        source = BASE / relative
        destination = workspace / relative

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source,
            destination
        )

        copied += 1

    new_files = plan.get(
        "new_files",
        []
    )

    for item in new_files:

        relative = normalize_path(
            item
        )

        if not relative:
            continue

        if is_protected(relative):
            raise RuntimeError(
                "Plan contains protected "
                f"new file: {relative}"
            )

        destination = (
            workspace / relative
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    metadata = {
        "created_at":
            datetime.now()
            .astimezone()
            .isoformat(),

        "plan_file":
            str(plan_path),

        "workspace":
            str(workspace),

        "copied_files":
            copied,

        "new_files":
            [
                normalize_path(x)
                for x in new_files
            ],

        "status":
            "READY_FOR_IMPLEMENTATION",
    }

    metadata_path = (
        workspace
        / "sandbox_metadata.json"
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
            ensure_ascii=False
        )

    return workspace, metadata


def python_files(workspace):
    return list(
        workspace.rglob("*.py")
    )


def syntax_check(workspace):
    """
    Compile every Python file in the sandbox.
    """

    files = python_files(workspace)

    checked = 0

    for path in files:

        if path.name == "sandbox_metadata.json":
            continue

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(path),
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            return False, (
                f"Syntax failure:\n"
                f"{path}\n\n"
                f"{result.stdout}\n"
                f"{result.stderr}"
            )

        checked += 1

    return True, (
        f"Syntax check passed "
        f"({checked} Python files)."
    )


def import_check(workspace):
    """
    Basic import check for the core package.

    This does not execute production code.
    """

    core = workspace / "core"

    if not core.exists():
        return True, "No core directory to check."

    test_files = [
        core / "intent.py",
        core / "router.py",
        core / "brain.py",
        core / "answer_engine.py",
    ]

    checked = 0

    for path in test_files:

        if not path.exists():
            continue

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(workspace)!r}); "
                    f"import core.{path.stem}"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(workspace)
        )

        if result.returncode != 0:

            return False, (
                f"Import failure:\n"
                f"{path}\n\n"
                f"{result.stdout}\n"
                f"{result.stderr}"
            )

        checked += 1

    return True, (
        f"Core import check passed "
        f"({checked} modules)."
    )


def test_workspace(workspace):
    """
    Run safe sandbox validation.
    """

    print()
    print("=" * 45)
    print("JIRAIYA SANDBOX TEST")
    print("=" * 45)

    print()
    print("Workspace:")
    print(workspace)

    print()
    print("1. Syntax check...")

    syntax_ok, syntax_message = (
        syntax_check(workspace)
    )

    print(
        ("✓ " if syntax_ok else "✗ ")
        + syntax_message
    )

    if not syntax_ok:
        return False

    print()
    print("2. Core import check...")

    import_ok, import_message = (
        import_check(workspace)
    )

    print(
        ("✓ " if import_ok else "✗ ")
        + import_message
    )

    if not import_ok:
        return False

    print()
    print("3. Sandbox integrity check...")

    metadata = workspace / "sandbox_metadata.json"

    if not metadata.exists():

        print(
            "✗ Sandbox metadata missing."
        )

        return False

    print(
        "✓ Sandbox integrity OK."
    )

    return True


def show_workspace(workspace):
    print()
    print("Sandbox files:")

    files = sorted(
        workspace.rglob("*")
    )

    shown = 0

    for path in files:

        if not path.is_file():
            continue

        relative = path.relative_to(
            workspace
        )

        if str(relative) == "sandbox_metadata.json":
            continue

        print(
            f"  {normalize_path(relative)}"
        )

        shown += 1

    print()
    print(
        f"Total files: {shown}"
    )


def main():

    if len(sys.argv) < 2:

        print(
            "Usage:\n"
            "  Create sandbox:\n"
            "    python sandbox_manager.py "
            "create <plan.json>\n\n"
            "  Test sandbox:\n"
            "    python sandbox_manager.py "
            "test <sandbox_path>\n\n"
            "  Show sandbox:\n"
            "    python sandbox_manager.py "
            "show <sandbox_path>"
        )

        sys.exit(1)

    command = sys.argv[1]

    try:

        if command == "create":

            if len(sys.argv) != 3:
                raise ValueError(
                    "create requires a plan.json"
                )

            plan_path = Path(
                sys.argv[2]
            ).expanduser()

            if not plan_path.exists():
                raise FileNotFoundError(
                    f"Plan not found:\n{plan_path}"
                )

            workspace, metadata = (
                create_workspace(
                    plan_path
                )
            )

            print(
                "============================================="
            )
            print(
                "JIRAIYA SANDBOX CREATED"
            )
            print(
                "============================================="
            )

            print()
            print(
                f"Workspace: {workspace}"
            )

            print(
                f"Copied files: "
                f"{metadata['copied_files']}"
            )

            print(
                f"New files reserved: "
                f"{len(metadata['new_files'])}"
            )

            print()
            print(
                "✓ Production was NOT modified."
            )

            show_workspace(
                workspace
            )

        elif command == "test":

            if len(sys.argv) != 3:
                raise ValueError(
                    "test requires sandbox path"
                )

            workspace = Path(
                sys.argv[2]
            ).expanduser()

            if not workspace.exists():
                raise FileNotFoundError(
                    f"Sandbox not found:\n"
                    f"{workspace}"
                )

            success = test_workspace(
                workspace
            )

            print()

            if success:

                print(
                    "============================================="
                )
                print(
                    "✓ SANDBOX TEST PASSED"
                )
                print(
                    "============================================="
                )

                sys.exit(0)

            else:

                print(
                    "============================================="
                )
                print(
                    "✗ SANDBOX TEST FAILED"
                )
                print(
                    "============================================="
                )

                sys.exit(2)

        elif command == "show":

            if len(sys.argv) != 3:
                raise ValueError(
                    "show requires sandbox path"
                )

            workspace = Path(
                sys.argv[2]
            ).expanduser()

            if not workspace.exists():
                raise FileNotFoundError(
                    f"Sandbox not found:\n"
                    f"{workspace}"
                )

            show_workspace(
                workspace
            )

        else:

            raise ValueError(
                f"Unknown command: {command}"
            )

    except Exception as e:

        print()
        print(
            "✗ Sandbox manager failed:"
        )

        print(str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()
