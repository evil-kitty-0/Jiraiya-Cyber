#!/usr/bin/env python3

"""
Jiraiya Memory Engine

Handles:
- Long-term memory
- 30-day temporary cache
- Memory metadata
- Expiration
- Duplicate detection
- Robust relevance retrieval
- Legacy memory migration
- Compact searchable index
"""

import re
import time


CACHE_TTL = 30 * 24 * 60 * 60


# =================================
# TIME
# =================================

def now():
    return int(time.time())


# =================================
# TEXT NORMALIZATION
# =================================

def normalize(text):
    text = str(text).strip().lower()

    text = re.sub(
        r"[^a-z0-9\u0900-\u097f]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def tokenize(text):
    return set(
        word
        for word in normalize(text).split()
        if len(word) >= 2
    )


# =================================
# IMPORTANCE
# =================================

def importance_score(value):

    try:
        value = float(value)

    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(1.0, value)
    )


# =================================
# DUPLICATE CHECK
# =================================

def is_duplicate(records, content):

    target = normalize(content)

    if not target:
        return False

    for record in records:

        existing = normalize(
            record.get(
                "content",
                ""
            )
        )

        if existing == target:
            return True

    return False


# =================================
# BUILD MEMORY RECORD
# =================================

def build_memory_record(
    content,
    category="general",
    importance=0.5,
    memory_type="long_term",
    session_id=None
):

    timestamp = now()

    record = {
        "content": str(content).strip(),

        "category": (
            str(category).strip()
            or "general"
        ),

        "importance": importance_score(
            importance
        ),

        "memory_type": memory_type,

        "created_at": timestamp,

        "last_accessed": timestamp
    }

    if session_id:

        record["source_session"] = str(
            session_id
        )

    if memory_type == "cache":

        record["expires_at"] = (
            timestamp + CACHE_TTL
        )

    return record


# =================================
# DECISION VALIDATION
# =================================

def should_store(decision):

    if not isinstance(
        decision,
        dict
    ):
        return False

    if not decision.get(
        "store",
        False
    ):
        return False

    content = str(
        decision.get(
            "content",
            ""
        )
    ).strip()

    if not content:
        return False

    memory_type = decision.get(
        "memory_type",
        "long_term"
    )

    if memory_type not in {
        "long_term",
        "cache"
    }:
        return False

    return True


# =================================
# PREPARE MEMORY
# =================================

def prepare_memory(
    decision,
    session_id=None
):

    if not should_store(
        decision
    ):
        return None

    return build_memory_record(

        content=decision[
            "content"
        ],

        category=decision.get(
            "category",
            "general"
        ),

        importance=decision.get(
            "importance",
            0.5
        ),

        memory_type=decision.get(
            "memory_type",
            "long_term"
        ),

        session_id=session_id
    )


# =================================
# EXPIRATION
# =================================

def expire_cache(records):

    current = now()

    active = []

    removed = 0

    for record in records:

        if record.get(
            "memory_type"
        ) != "cache":

            active.append(
                record
            )

            continue

        expires_at = record.get(
            "expires_at"
        )

        if expires_at is None:

            record["expires_at"] = (
                record.get(
                    "created_at",
                    current
                )
                + CACHE_TTL
            )

            active.append(
                record
            )

            continue

        if current >= expires_at:

            removed += 1

        else:

            active.append(
                record
            )

    return active, removed


# =================================
# LEGACY MIGRATION
# =================================

def migrate_record(record):

    timestamp = now()

    upgraded = dict(
        record
    )

    upgraded.setdefault(
        "category",
        "general"
    )

    upgraded.setdefault(
        "importance",
        0.5
    )

    upgraded.setdefault(
        "memory_type",
        "long_term"
    )

    upgraded.setdefault(
        "created_at",
        timestamp
    )

    upgraded.setdefault(
        "last_accessed",
        timestamp
    )

    if (
        upgraded["memory_type"]
        == "cache"
    ):

        upgraded.setdefault(
            "expires_at",
            upgraded[
                "created_at"
            ] + CACHE_TTL
        )

    return upgraded


def migrate_records(records):

    migrated = []

    for record in records:

        migrated.append(
            migrate_record(
                record
            )
        )

    return migrated


# =================================
# COMPACT INDEX
# =================================

def compact_index(record):

    content = str(
        record.get(
            "content",
            ""
        )
    ).strip()

    keywords = sorted(
        tokenize(content)
    )

    return {
        "memory_id": record.get(
            "id"
        ),

        "keywords": keywords[:30],

        "category": normalize(
            record.get(
                "category",
                "general"
            )
        ),

        "importance": importance_score(
            record.get(
                "importance",
                0.5
            )
        )
    }


def build_index(records):

    return [
        compact_index(record)
        for record in records
    ]


# =================================
# RELEVANCE RETRIEVAL
# =================================

def retrieve_candidates(
    records,
    query,
    limit=5
):

    query_tokens = tokenize(
        query
    )

    if not query_tokens:
        return []

    results = []

    for record in records:

        content_tokens = tokenize(
            record.get(
                "content",
                ""
            )
        )

        category_tokens = tokenize(
            record.get(
                "category",
                ""
            )
        )

        matched_content = (
            query_tokens
            & content_tokens
        )

        matched_category = (
            query_tokens
            & category_tokens
        )

        score = (
            len(matched_content)
            + (
                2
                * len(matched_category)
            )
        )

        if score <= 0:
            continue

        importance = importance_score(
            record.get(
                "importance",
                0.5
            )
        )

        final_score = (
            score
            + importance
        )

        results.append(
            (
                final_score,
                record
            )
        )

    results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        record
        for _, record
        in results[:limit]
    ]


# =================================
# ACTIVE MEMORY VIEW
# =================================

def active_memories(records):

    active, _ = expire_cache(
        records
    )

    return active
