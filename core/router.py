#!/usr/bin/env python3

import sys
from pathlib import Path

BASE = Path.home() / "jiraiya"

sys.path.insert(0, str(BASE))

from intent import classify


# ============================================================
# ROUTE DEFINITIONS
# ============================================================

ROUTES = {

    "memory": {
        "mode": "offline",
        "handler": "memory",
        "reason": "Memory operations are local."
    },

    "mathematics": {
        "mode": "offline",
        "handler": "math",
        "reason": "Mathematical problems are local-first."
    },

    "physics": {
        "mode": "hybrid",
        "handler": "physics",
        "reason": (
            "Physics is local-first; "
            "unknown concepts may require online learning."
        )
    },

    "chemistry": {
        "mode": "hybrid",
        "handler": "chemistry",
        "reason": (
            "Chemistry is local-first; "
            "unknown concepts may require online learning."
        )
    },

    "coding": {
        "mode": "offline",
        "handler": "coding",
        "reason": "Coding is handled by the local coder model."
    },

    "gold": {
        "mode": "online",
        "handler": "gold",
        "reason": "Gold rates are dynamic and require fresh data."
    },

    "weather": {
        "mode": "online",
        "handler": "weather",
        "reason": "Weather is dynamic and requires fresh data."
    },

    "stock_market": {
        "mode": "online",
        "handler": "stock_market",
        "reason": "Market data is dynamic and requires fresh data."
    },

    "news": {
        "mode": "online",
        "handler": "news",
        "reason": "News requires current online information."
    },

    "economics": {
        "mode": "online",
        "handler": "economics",
        "reason": "Economic data can change and requires fresh information."
    },

    "history": {
        "mode": "hybrid",
        "handler": "history",
        "reason": (
            "History uses local knowledge first and "
            "online verification when required."
        )
    },

    "knowledge": {
        "mode": "hybrid",
        "handler": "knowledge",
        "reason": (
            "Knowledge uses local knowledge first; "
            "unknown topics can be learned online."
        )
    },

    "web": {
        "mode": "online",
        "handler": "web",
        "reason": "Explicit web requests require internet access."
    },

    "general": {
        "mode": "hybrid",
        "handler": "general",
        "reason": (
            "General questions use local knowledge/model first "
            "and can fall back to the web."
        )
    }
}


# ============================================================
# ROUTER
# ============================================================

def route(question):

    classification = classify(
        question
    )

    intent = classification.get(
        "intent",
        "general"
    )

    route_info = ROUTES.get(
        intent,
        ROUTES["general"]
    )

    return {
        "question": question,
        "intent": intent,
        "mode": route_info["mode"],
        "handler": route_info["handler"],
        "reason": route_info["reason"]
    }


# ============================================================
# EXECUTION POLICY
# ============================================================

def hybrid_policy():

    return {
        "primary": "local",
        "internet_fallback": True,
        "verification": True,
        "max_online_rounds": 2
    }


def router_decision(question):

    result = route(
        question
    )

    mode = result["mode"]

    if mode == "offline":

        result["execution"] = {
            "primary": "local",
            "internet": False,
            "verification": False
        }

    elif mode == "online":

        result["execution"] = {
            "primary": "internet",
            "internet": True,
            "verification": True
        }

    elif mode == "hybrid":

        result["execution"] = {
            "primary": "local",
            "internet": True,
            "verification": True,
            "max_online_rounds": 2
        }

    else:

        result["execution"] = {
            "primary": "local",
            "internet": False,
            "verification": False
        }

    return result


# ============================================================
# CLI
# ============================================================

def main():

    if len(sys.argv) < 2:

        print(
            'Usage:\n'
            '  python router.py "your question"'
        )

        return

    question = " ".join(
        sys.argv[1:]
    )

    result = router_decision(
        question
    )

    print(
        "Intent:",
        result["intent"]
    )

    print(
        "Mode:",
        result["mode"]
    )

    print(
        "Handler:",
        result["handler"]
    )

    print(
        "Reason:",
        result["reason"]
    )

    print(
        "Execution:",
        result["execution"]
    )


if __name__ == "__main__":
    main()
