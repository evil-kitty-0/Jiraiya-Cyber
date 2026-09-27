#!/usr/bin/env python3

"""
Jiraiya Memory Analyzer

Classifies information into:
- long_term
- cache
- discard

This module does NOT write to the database.
"""

import re


MIN_MEMORY_LENGTH = 3

SECRET_PATTERNS = [
    r"\bpassword\b",
    r"\bpasswd\b",
    r"\bapi[\s_-]?key\b",
    r"\bsecret[\s_-]?key\b",
    r"\bprivate[\s_-]?key\b",
    r"\bseed phrase\b",
    r"\brecovery phrase\b",
    r"\botp\b",
    r"\bone[-\s]?time password\b",
    r"\baccess token\b",
    r"\bauth token\b",
    r"\bbearer token\b",
]

TEMPORARY_PATTERNS = [
    r"\bwhat did i eat\b",
    r"\bi ate\b",
    r"\bi had lunch\b",
    r"\bi had dinner\b",
    r"\bi had breakfast\b",
    r"\bi am drinking\b",
    r"\bi just drank\b",
]


def clean_text(text):
    return " ".join(
        str(text).strip().split()
    )


def contains_secret(text):

    lowered = clean_text(
        text
    ).lower()

    return any(
        re.search(
            pattern,
            lowered
        )
        for pattern in SECRET_PATTERNS
    )


def looks_temporary(text):

    lowered = clean_text(
        text
    ).lower()

    return any(
        re.search(
            pattern,
            lowered
        )
        for pattern in TEMPORARY_PATTERNS
    )


def project_signal(text):

    lowered = text.lower()

    patterns = [
        "my project",
        "our project",
        "the project",
        "i am building",
        "i'm building",
        "we are building",
        "we're building",
        "in jiraiya",
        "for jiraiya",
        "jiraiya project",
    ]

    return any(
        pattern in lowered
        for pattern in patterns
    )


def identity_signal(text):

    lowered = text.lower()

    patterns = [
        "my name is",
        "i work as",
        "my profession is",
        "my job is",
    ]

    return any(
        pattern in lowered
        for pattern in patterns
    )


def preference_signal(text):

    lowered = text.lower()

    patterns = [
        "i like",
        "i love",
        "i prefer",
        "my favorite",
        "i dislike",
        "i hate",
        "i usually",
        "i always",
        "i never",
    ]

    return any(
        pattern in lowered
        for pattern in patterns
    )


def future_decision_signal(text):

    lowered = text.lower()

    patterns = [
        "from now on",
        "going forward",
        "in the future",
        "remember that",
        "keep in mind",
        "always remember",
        "we will",
        "we should",
        "don't change",
        "do not change",
    ]

    return any(
        pattern in lowered
        for pattern in patterns
    )


def analyze_text(text):

    text = clean_text(text)

    if len(text) < MIN_MEMORY_LENGTH:

        return {
            "store": False,
            "memory_type": "discard",
            "importance": 0.0,
            "category": "none",
            "content": "",
            "reason": "too_short",
        }

    # Security always wins.
    if contains_secret(text):

        return {
            "store": False,
            "memory_type": "discard",
            "importance": 0.0,
            "category": "security",
            "content": "",
            "reason": "possible_secret",
        }

    # Project information must be checked before
    # generic identity patterns such as "I am building".
    if project_signal(text):

        return {
            "store": True,
            "memory_type": "long_term",
            "importance": 0.85,
            "category": "project",
            "content": text,
            "reason": "project_context",
        }

    if identity_signal(text):

        return {
            "store": True,
            "memory_type": "long_term",
            "importance": 0.95,
            "category": "identity",
            "content": text,
            "reason": "identity",
        }

    if preference_signal(text):

        return {
            "store": True,
            "memory_type": "long_term",
            "importance": 0.80,
            "category": "preference",
            "content": text,
            "reason": "preference",
        }

    if future_decision_signal(text):

        return {
            "store": True,
            "memory_type": "long_term",
            "importance": 0.90,
            "category": "decision",
            "content": text,
            "reason": "future_decision",
        }

    if looks_temporary(text):

        return {
            "store": True,
            "memory_type": "cache",
            "importance": 0.20,
            "category": "temporary",
            "content": text,
            "reason": "temporary_information",
        }

    # Unknown information stays temporary.
    # It can later be promoted if the future
    # memory system determines it is important.
    return {
        "store": True,
        "memory_type": "cache",
        "importance": 0.35,
        "category": "temporary",
        "content": text,
        "reason": "uncertain_relevance",
    }
