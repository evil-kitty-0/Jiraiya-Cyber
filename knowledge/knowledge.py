#!/usr/bin/env python3

import sys
import json
import time
import hashlib
import sqlite3
from pathlib import Path


# ============================================================
# JIRAIYA KNOWLEDGE STORE
# ============================================================

BASE = Path.home() / "jiraiya"
KNOWLEDGE_DIR = BASE / "knowledge"

DB_FILE = KNOWLEDGE_DIR / "knowledge.db"


# ============================================================
# DATABASE
# ============================================================

def connect():

    KNOWLEDGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def initialize():

    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            topic TEXT NOT NULL,

            category TEXT NOT NULL,

            content TEXT NOT NULL,

            source TEXT,

            source_url TEXT,

            confidence REAL DEFAULT 0.5,

            verified INTEGER DEFAULT 0,

            created_at INTEGER NOT NULL,

            updated_at INTEGER NOT NULL,

            content_hash TEXT NOT NULL UNIQUE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_knowledge_topic
        ON knowledge(topic)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_knowledge_category
        ON knowledge(category)
    """)

    conn.commit()

    conn.close()


# ============================================================
# HELPERS
# ============================================================

def make_hash(
    topic,
    category,
    content
):

    raw = (
        topic.strip()
        + "\n"
        + category.strip()
        + "\n"
        + content.strip()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# ADD KNOWLEDGE
# ============================================================

def add_knowledge(
    topic,
    category,
    content,
    source=None,
    source_url=None,
    confidence=0.5,
    verified=False
):

    initialize()

    topic = topic.strip()
    category = category.strip()
    content = content.strip()

    if not topic:
        raise ValueError(
            "Topic cannot be empty."
        )

    if not category:
        raise ValueError(
            "Category cannot be empty."
        )

    if not content:
        raise ValueError(
            "Content cannot be empty."
        )

    confidence = max(
        0.0,
        min(1.0, float(confidence))
    )

    content_hash = make_hash(
        topic,
        category,
        content
    )

    now = int(time.time())

    conn = connect()

    existing = conn.execute(
        """
        SELECT id
        FROM knowledge
        WHERE content_hash = ?
        """,
        (content_hash,)
    ).fetchone()

    if existing:

        conn.execute(
            """
            UPDATE knowledge
            SET
                confidence = ?,
                verified = ?,
                source = ?,
                source_url = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                confidence,
                1 if verified else 0,
                source,
                source_url,
                now,
                existing["id"]
            )
        )

        conn.commit()

        knowledge_id = existing["id"]

        conn.close()

        return knowledge_id

    cursor = conn.execute(
        """
        INSERT INTO knowledge (
            topic,
            category,
            content,
            source,
            source_url,
            confidence,
            verified,
            created_at,
            updated_at,
            content_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic,
            category,
            content,
            source,
            source_url,
            confidence,
            1 if verified else 0,
            now,
            now,
            content_hash
        )
    )

    conn.commit()

    knowledge_id = cursor.lastrowid

    conn.close()

    return knowledge_id


# ============================================================
# SEARCH KNOWLEDGE
# ============================================================

def search_knowledge(
    query,
    category=None,
    limit=10
):

    initialize()

    query = query.strip()

    if not query:
        return []

    words = [
        word.lower()
        for word in query.split()
        if len(word) >= 2
    ]

    if not words:
        return []

    conn = connect()

    conditions = []
    params = []

    for word in words:

        conditions.append(
            """
            (
                LOWER(topic) LIKE ?
                OR LOWER(content) LIKE ?
                OR LOWER(category) LIKE ?
            )
            """
        )

        pattern = f"%{word}%"

        params.extend([
            pattern,
            pattern,
            pattern
        ])

    where = " OR ".join(
        conditions
    )

    if category:

        where = (
            "("
            + where
            + ") AND category = ?"
        )

        params.append(
            category
        )

    sql = f"""
        SELECT
            id,
            topic,
            category,
            content,
            source,
            source_url,
            confidence,
            verified,
            created_at,
            updated_at
        FROM knowledge
        WHERE {where}
        ORDER BY
            verified DESC,
            confidence DESC,
            updated_at DESC
        LIMIT ?
    """

    params.append(
        int(limit)
    )

    rows = conn.execute(
        sql,
        params
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET ONE
# ============================================================

def get_knowledge(knowledge_id):

    initialize()

    conn = connect()

    row = conn.execute(
        """
        SELECT *
        FROM knowledge
        WHERE id = ?
        """,
        (knowledge_id,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)


# ============================================================
# UPDATE KNOWLEDGE
# ============================================================

def update_knowledge(
    knowledge_id,
    content=None,
    confidence=None,
    verified=None,
    source=None,
    source_url=None
):

    initialize()

    current = get_knowledge(
        knowledge_id
    )

    if not current:
        return False

    new_content = (
        content
        if content is not None
        else current["content"]
    )

    new_confidence = (
        float(confidence)
        if confidence is not None
        else current["confidence"]
    )

    new_verified = (
        bool(verified)
        if verified is not None
        else bool(current["verified"])
    )

    new_source = (
        source
        if source is not None
        else current["source"]
    )

    new_source_url = (
        source_url
        if source_url is not None
        else current["source_url"]
    )

    new_hash = make_hash(
        current["topic"],
        current["category"],
        new_content
    )

    now = int(time.time())

    conn = connect()

    try:

        conn.execute(
            """
            UPDATE knowledge
            SET
                content = ?,
                source = ?,
                source_url = ?,
                confidence = ?,
                verified = ?,
                updated_at = ?,
                content_hash = ?
            WHERE id = ?
            """,
            (
                new_content,
                new_source,
                new_source_url,
                new_confidence,
                1 if new_verified else 0,
                now,
                new_hash,
                knowledge_id
            )
        )

        conn.commit()

    except sqlite3.IntegrityError:

        conn.close()

        return False

    conn.close()

    return True


# ============================================================
# DELETE
# ============================================================

def delete_knowledge(
    knowledge_id
):

    initialize()

    conn = connect()

    cursor = conn.execute(
        """
        DELETE FROM knowledge
        WHERE id = ?
        """,
        (knowledge_id,)
    )

    conn.commit()

    deleted = (
        cursor.rowcount > 0
    )

    conn.close()

    return deleted


# ============================================================
# LIST
# ============================================================

def list_knowledge(
    category=None,
    limit=100
):

    initialize()

    conn = connect()

    if category:

        rows = conn.execute(
            """
            SELECT *
            FROM knowledge
            WHERE category = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (
                category,
                limit
            )
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM knowledge
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# STATISTICS
# ============================================================

def statistics():

    initialize()

    conn = connect()

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM knowledge
        """
    ).fetchone()[0]

    verified = conn.execute(
        """
        SELECT COUNT(*)
        FROM knowledge
        WHERE verified = 1
        """
    ).fetchone()[0]

    categories = conn.execute(
        """
        SELECT
            category,
            COUNT(*) AS count
        FROM knowledge
        GROUP BY category
        ORDER BY count DESC
        """
    ).fetchall()

    conn.close()

    return {
        "total": total,
        "verified": verified,
        "unverified": total - verified,
        "categories": {
            row["category"]: row["count"]
            for row in categories
        }
    }


# ============================================================
# CLI
# ============================================================

def print_json(data):

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )
    )


def main():

    initialize()

    if len(sys.argv) < 2:

        print(
            """
Jiraiya Knowledge Store

Commands:

  add
  search
  get
  update
  delete
  list
  stats
            """
        )

        return

    command = sys.argv[1].lower()

    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    if command == "add":

        if len(sys.argv) < 5:

            print(
                'Usage: '
                'knowledge.py add '
                '"topic" "category" "content"'
            )

            return

        topic = sys.argv[2]
        category = sys.argv[3]
        content = sys.argv[4]

        knowledge_id = add_knowledge(
            topic=topic,
            category=category,
            content=content,
            source="manual",
            confidence=1.0,
            verified=True
        )

        print(
            f"Knowledge saved. ID: "
            f"{knowledge_id}"
        )

        return

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if command == "search":

        if len(sys.argv) < 3:

            print(
                'Usage: knowledge.py search "query"'
            )

            return

        query = " ".join(
            sys.argv[2:]
        )

        print_json(
            search_knowledge(
                query
            )
        )

        return

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if command == "get":

        if len(sys.argv) < 3:

            print(
                "Usage: knowledge.py get <id>"
            )

            return

        item = get_knowledge(
            int(sys.argv[2])
        )

        print_json(
            item
        )

        return

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    if command == "delete":

        if len(sys.argv) < 3:

            print(
                "Usage: knowledge.py delete <id>"
            )

            return

        deleted = delete_knowledge(
            int(sys.argv[2])
        )

        print(
            "Deleted."
            if deleted
            else "Knowledge ID not found."
        )

        return

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if command == "list":

        print_json(
            list_knowledge()
        )

        return

    # --------------------------------------------------------
    # STATS
    # --------------------------------------------------------

    if command == "stats":

        print_json(
            statistics()
        )

        return

    print(
        f"Unknown command: {command}"
    )


if __name__ == "__main__":
    main()
