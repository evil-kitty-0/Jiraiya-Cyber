#!/usr/bin/env python3

try:
    from .memory_analyzer import analyze_text
    from .memory import add_memory
except ImportError:
    from memory_analyzer import analyze_text
    from memory import add_memory


def process_message(text, session_id=None):
    """
    Analyze a chat message and store it when appropriate.
    """

    if not text or not text.strip():
        return {
            "store": False,
            "reason": "empty",
            "stored": False
        }

    decision = analyze_text(text)

    if not decision.get("store", False):
        return {
            **decision,
            "stored": False
        }

    content = decision.get(
        "content",
        text
    ).strip()

    category = decision.get(
        "category",
        "user"
    )

    importance = float(
        decision.get(
            "importance",
            0.5
        )
    )

    memory_type = decision.get(
        "memory_type",
        "cache"
    )

    stored = add_memory(
        category=category,
        content=content,
        importance=importance,
        memory_type=memory_type,
        session_id=session_id
    )

    return {
        **decision,
        "stored": bool(stored)
    }


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m memory.auto_memory <message>"
        )
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    result = process_message(message)

    print(result)
