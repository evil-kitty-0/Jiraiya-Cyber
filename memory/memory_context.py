#!/usr/bin/env python3

from pathlib import Path
import importlib.util

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "memory.py"

_spec = importlib.util.spec_from_file_location(
    "jiraiya_memory_backend",
    MEMORY_FILE
)

_memory_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_memory_module)

retrieve_candidates = _memory_module.retrieve_candidates


def get_memory_context(query, limit=3):
    """
    Return a compact context string containing
    only memories relevant to the current query.
    """

    if not query or not query.strip():
        return ""

    try:
        memories = retrieve_candidates(query, limit=limit)
    except Exception:
        return ""

    if not memories:
        return ""

    lines = []

    for memory in memories:
        content = str(
            memory.get("content", "")
        ).strip()

        if content:
            lines.append(f"- {content}")

    if not lines:
        return ""

    return (
        "Relevant memory about the user or project:\n"
        + "\n".join(lines)
        + "\n\n"
        "Use these memories only when relevant. "
        "Do not invent facts beyond them."
    )


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m memory.memory_context <query>"
        )
        raise SystemExit(1)

    query = " ".join(sys.argv[1:])

    print(
        get_memory_context(query)
    )
