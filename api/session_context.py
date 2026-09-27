#!/usr/bin/env python3


def build_context_message(message, history):
    """
    Build a compact current-conversation context
    for Jiraiya's routing/LLM layer.
    """

    message = str(message or "").strip()

    if not message:
        return ""

    if not isinstance(history, list):
        history = []

    history = history[-20:]

    parts = []

    for item in history:
        if not isinstance(item, dict):
            continue

        role = str(
            item.get("role", "")
        ).strip()

        content = str(
            item.get("content", "")
        ).strip()

        if role in ("user", "assistant") and content:
            parts.append(
                role.capitalize() + ": " + content
            )

    if not parts:
        return message

    return (
        "Current conversation:\n"
        + "\n".join(parts)
        + "\n\nCurrent user message:\n"
        + message
    )
