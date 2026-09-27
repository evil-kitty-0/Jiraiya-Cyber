#!/usr/bin/env python3

import sys
import re
from pathlib import Path

BASE = Path.home() / "jiraiya"
MEMORY = BASE / "memory" / "memory.py"


def run_memory(command, *args):

    import subprocess

    result = subprocess.run(
        [
            "python",
            str(MEMORY),
            command,
            *args
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return "Memory error:\n" + result.stderr.strip()

    return result.stdout.strip()


# =================================
# FIND MEMORY ID FROM TEXT
# =================================

def extract_id(text):

    match = re.search(
        r"(?:memory\s*)?(\d+)",
        text.lower()
    )

    if match:
        return int(match.group(1))

    return None


# =================================
# NATURAL MEMORY ACTION
# =================================

def process_action(text):

    original = text.strip()
    lower = original.lower()


    # -----------------------------
    # DELETE
    # -----------------------------

    delete_words = [
        "forget",
        "delete memory",
        "remove memory",
        "bhool jao",
        "bhul jao",
        "yaad se hata"
    ]

    if any(word in lower for word in delete_words):

        memory_id = extract_id(original)

        if memory_id is None:

            return (
                "DELETE_REQUEST\n"
                "Please provide the memory ID."
            )

        return (
            "DELETE\n"
            + run_memory(
                "delete",
                str(memory_id)
            )
        )


    # -----------------------------
    # UPDATE
    # -----------------------------

    update_words = [
        "update",
        "change",
        "replace",
        "modify",
        "badal do",
        "update kar do",
        "change kar do"
    ]

    if any(word in lower for word in update_words):

        memory_id = extract_id(original)

        if memory_id is None:

            return (
                "UPDATE_REQUEST\n"
                "Please provide the memory ID."
            )

        # Try to extract text after ID
        match = re.search(
            r"\b\d+\b\s*(.*)",
            original
        )

        if not match:

            return (
                "UPDATE_REQUEST\n"
                "Please provide the new memory text."
            )

        new_text = match.group(1).strip()

        if not new_text:

            return (
                "UPDATE_REQUEST\n"
                "New memory text is missing."
            )

        return (
            "UPDATE\n"
            + run_memory(
                "update",
                str(memory_id),
                new_text
            )
        )


    # -----------------------------
    # SHOW MEMORIES
    # -----------------------------

    if (
        "show my memories" in lower
        or "show memories" in lower
        or "list memories" in lower
        or "meri memories dikhao" in lower
        or "meri memory dikhao" in lower
    ):

        return (
            "LIST\n"
            + run_memory("list")
        )


    # -----------------------------
    # SEARCH
    # -----------------------------

    if (
        "search memory" in lower
        or "find memory" in lower
        or "memory search" in lower
        or "meri memory dhundo" in lower
    ):

        query = original

        return (
            "SEARCH\n"
            + run_memory(
                "search",
                query
            )
        )


    return (
        "NO_MEMORY_ACTION\n"
        "No memory action detected."
    )


# =================================
# MAIN
# =================================

def main():

    if len(sys.argv) < 2:

        print(
            "Usage: python actions.py <request>"
        )

        return

    text = " ".join(sys.argv[1:])

    print(
        process_action(text)
    )


if __name__ == "__main__":
    main()
