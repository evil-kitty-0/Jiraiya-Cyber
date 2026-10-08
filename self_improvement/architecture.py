#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import json


BASE = Path(__file__).resolve().parents[1]
OUTPUT = (
    BASE
    / "self_improvement"
    / "architecture.json"
)

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    "sandbox",
    "backups",
    "versions",
}


def scan():
    files = []
    directories = []

    for path in BASE.rglob("*"):

        relative = path.relative_to(BASE)

        if any(
            part in IGNORE_DIRS
            for part in relative.parts
        ):
            continue

        if path.is_dir():
            directories.append(
                str(relative)
            )

        elif path.is_file():
            files.append(
                str(relative)
            )

    return {
        "generated_at":
            datetime.now()
            .astimezone()
            .isoformat(),

        "root": str(BASE),

        "directories":
            sorted(directories),

        "files":
            sorted(files),
    }


def save(data):
    OUTPUT.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    data = scan()
    save(data)

    print(
        "============================================="
    )
    print(
        "JIRAIYA ARCHITECTURE"
    )
    print(
        "============================================="
    )

    print()
    print(
        f"Directories: "
        f"{len(data['directories'])}"
    )

    print(
        f"Files      : "
        f"{len(data['files'])}"
    )

    print()
    print("Core files:")

    for file in data["files"]:
        if (
            file.endswith(".py")
            and (
                file.startswith("core/")
                or file == "agent.py"
                or file == "learner.py"
                or file == "model_manager.py"
            )
        ):
            print(f"  ✓ {file}")

    print()
    print(
        f"✓ Architecture saved:"
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
