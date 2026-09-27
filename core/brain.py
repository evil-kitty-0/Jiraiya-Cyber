#!/usr/bin/env python3

import sys
from pathlib import Path

BASE = Path.home() / "jiraiya"

sys.path.insert(0, str(BASE / "core"))
sys.path.insert(0, str(BASE))

from router import router_decision
from learner import learn


# ============================================================
# JIRAIYA BRAIN
# ============================================================

def brain(question):
    """
    Central decision layer.

    Flow:

        USER QUESTION
             ↓
          ROUTER
             ↓
      ┌──────┼──────┐
      ↓      ↓      ↓
    OFFLINE ONLINE HYBRID
      │      │      │
      │      ↓      ↓
      │    LEARNER  LOCAL FIRST
      │      │      ↓
      │      │      WEB IF NEEDED
      └──────┴──────┘
             ↓
        EXECUTION PLAN
    """

    question = str(question).strip()

    if not question:
        return {
            "ok": False,
            "status": "empty_question",
            "question": question
        }

    # --------------------------------------------------------
    # ROUTER
    # --------------------------------------------------------

    decision = router_decision(
        question
    )

    intent = decision.get(
        "intent",
        "general"
    )

    mode = decision.get(
        "mode",
        "offline"
    )

    handler = decision.get(
        "handler"
    )

    reason = decision.get(
        "reason",
        ""
    )

    # --------------------------------------------------------
    # OFFLINE
    # --------------------------------------------------------

    if mode == "offline":

        return {
            "ok": True,
            "status": "offline_route",
            "question": question,
            "intent": intent,
            "mode": mode,
            "handler": handler,
            "internet": False,
            "learning": False,
            "reason": reason,
            "decision": decision
        }

    # --------------------------------------------------------
    # ONLINE
    # --------------------------------------------------------

    if mode == "online":

        category = intent

        learning = learn(
            question,
            category
        )

        return {
            "ok": learning.get("ok", False),
            "status": "online_route",
            "question": question,
            "intent": intent,
            "mode": mode,
            "handler": handler,
            "internet": True,
            "learning": True,
            "learning_result": learning,
            "reason": reason,
            "decision": decision
        }

    # --------------------------------------------------------
    # HYBRID
    # --------------------------------------------------------

    if mode == "hybrid":

        # Local-first policy.
        #
        # The learner itself checks local knowledge first,
        # then goes online only when required.

        learning = learn(
            question,
            intent
        )

        return {
            "ok": learning.get("ok", False),
            "status": "hybrid_route",
            "question": question,
            "intent": intent,
            "mode": mode,
            "handler": handler,
            "internet": learning.get(
                "web_used",
                False
            ),
            "learning": True,
            "learning_result": learning,
            "reason": reason,
            "decision": decision
        }

    # --------------------------------------------------------
    # UNKNOWN MODE
    # --------------------------------------------------------

    return {
        "ok": False,
        "status": "unknown_mode",
        "question": question,
        "intent": intent,
        "mode": mode,
        "handler": handler,
        "reason": reason,
        "decision": decision
    }


# ============================================================
# HUMAN-READABLE OUTPUT
# ============================================================

def print_brain_result(result):

    print()

    print("🧠 JIRAIYA BRAIN")
    print("=" * 45)

    print(
        f"Question : "
        f"{result.get('question')}"
    )

    print(
        f"Intent   : "
        f"{result.get('intent')}"
    )

    print(
        f"Mode     : "
        f"{result.get('mode')}"
    )

    print(
        f"Handler  : "
        f"{result.get('handler')}"
    )

    print(
        f"Internet : "
        f"{'YES' if result.get('internet') else 'NO'}"
    )

    print(
        f"Reason   : "
        f"{result.get('reason', '')}"
    )

    print()

    learning = result.get(
        "learning_result"
    )

    if learning:

        status = learning.get(
            "status"
        )

        if status == "local_knowledge":

            print(
                "📚 Knowledge source: LOCAL"
            )

            print(
                f"Confidence: "
                f"{learning.get('confidence')}"
            )

            print(
                f"Relevance: "
                f"{learning.get('relevance')}"
            )

        elif status == "learned":

            print(
                "🌐 Knowledge source: WEB"
            )

            print(
                "💾 Knowledge: STORED"
            )

            print(
                f"Confidence: "
                f"{learning.get('confidence')}"
            )

            verification = learning.get(
                "verification",
                {}
            )

            print(
                f"Sources: "
                f"{verification.get('source_count', 0)}"
            )

            print(
                f"Independent domains: "
                f"{verification.get('independent_domains', 0)}"
            )

        elif status == "verification_failed":

            print(
                "⚠️ Web knowledge found, "
                "but verification failed."
            )

            print(
                "💾 Knowledge was NOT stored."
            )

        elif status == "web_unavailable":

            print(
                "🌐 Web was required, "
                "but unavailable."
            )

    print()


# ============================================================
# CLI
# ============================================================

def main():

    if len(sys.argv) < 2:

        print(
            'Usage:\n'
            '  python ~/jiraiya/core/brain.py '
            '"your question"'
        )

        return

    question = " ".join(
        sys.argv[1:]
    )

    result = brain(
        question
    )

    print_brain_result(
        result
    )


if __name__ == "__main__":
    main()
