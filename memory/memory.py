#!/usr/bin/env python3

import sys
import json
import os
import base64
import hashlib
import hmac
import subprocess
import re
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "master.key"
DB_FILE = BASE_DIR / "memory.db.enc"

CACHE_TTL = 30 * 24 * 60 * 60


# =================================
# MASTER KEY
# =================================

def get_master_key():

    if not KEY_FILE.exists():
        raise RuntimeError("master.key not found")

    key = KEY_FILE.read_text().strip()

    if len(key) != 64:
        raise RuntimeError("Invalid master.key")

    return key


def get_hmac_key():

    master = bytes.fromhex(
        get_master_key()
    )

    return hashlib.sha256(
        b"JIRAIYA-MEMORY-HMAC-v1" + master
    ).digest()


# =================================
# ENCRYPTION
# =================================

def encrypt(data):

    result = subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "200000",
            "-salt",
            "-pass",
            f"file:{KEY_FILE}"
        ],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True
    )

    ciphertext = result.stdout

    mac = hmac.new(
        get_hmac_key(),
        ciphertext,
        hashlib.sha256
    ).digest()

    package = {
        "version": 1,
        "cipher": "AES-256-CBC",
        "mac": base64.b64encode(mac).decode(),
        "data": base64.b64encode(ciphertext).decode()
    }

    return json.dumps(package).encode("utf-8")


def decrypt(package_data):

    package = json.loads(
        package_data.decode("utf-8")
    )

    ciphertext = base64.b64decode(
        package["data"]
    )

    stored_mac = base64.b64decode(
        package["mac"]
    )

    calculated_mac = hmac.new(
        get_hmac_key(),
        ciphertext,
        hashlib.sha256
    ).digest()

    if not hmac.compare_digest(
        stored_mac,
        calculated_mac
    ):
        raise RuntimeError(
            "Memory integrity check failed!"
        )

    result = subprocess.run(
        [
            "openssl",
            "enc",
            "-d",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "200000",
            "-pass",
            f"file:{KEY_FILE}"
        ],
        input=ciphertext,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True
    )

    return result.stdout


# =================================
# TIME
# =================================

def now():

    return int(time.time())


# =================================
# TEXT NORMALIZATION
# =================================

def normalize(text):

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\u0900-\u097f]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def tokenize(text):

    normalized = normalize(text)

    return {
        word
        for word in normalized.split()
        if len(word) >= 2
    }


# =================================
# RECORD MIGRATION
# =================================

def migrate_record(record):

    changed = False

    if "category" not in record:
        record["category"] = "user"
        changed = True

    if "importance" not in record:
        record["importance"] = 0.5
        changed = True

    if "memory_type" not in record:
        record["memory_type"] = "long_term"
        changed = True

    if "created_at" not in record:
        record["created_at"] = now()
        changed = True

    if "last_accessed" not in record:
        record["last_accessed"] = record["created_at"]
        changed = True

    if (
        record.get("memory_type") == "cache"
        and
        "expires_at" not in record
    ):
        record["expires_at"] = (
            record["created_at"] + CACHE_TTL
        )
        changed = True

    return changed


def migrate_records(records):

    changed = False

    for record in records:

        if migrate_record(record):
            changed = True

    return records, changed


# =================================
# CACHE EXPIRATION
# =================================

def expire_cache(records):

    current_time = now()

    active = []
    changed = False

    for record in records:

        memory_type = record.get(
            "memory_type",
            "long_term"
        )

        if memory_type != "cache":
            active.append(record)
            continue

        expires_at = record.get(
            "expires_at"
        )

        if expires_at is None:

            created_at = record.get(
                "created_at",
                current_time
            )

            record["expires_at"] = (
                created_at + CACHE_TTL
            )

            expires_at = record["expires_at"]
            changed = True

        if current_time < expires_at:

            active.append(record)

        else:

            changed = True

    return active, changed


# =================================
# LOAD
# =================================

def load_memories():

    if not DB_FILE.exists():
        return []

    memories = json.loads(
        decrypt(
            DB_FILE.read_bytes()
        ).decode("utf-8")
    )

    memories, migration_changed = migrate_records(
        memories
    )

    memories, expiry_changed = expire_cache(
        memories
    )

    if migration_changed or expiry_changed:

        save_memories(memories)

    return memories


# =================================
# SAVE
# =================================

def save_memories(memories):

    data = json.dumps(
        memories,
        ensure_ascii=False
    ).encode("utf-8")

    encrypted = encrypt(data)

    temp_file = DB_FILE.with_suffix(".tmp")

    temp_file.write_bytes(
        encrypted
    )

    os.replace(
        temp_file,
        DB_FILE
    )


# =================================
# MEMORY RECORD
# =================================

def build_memory_record(
    content,
    category="user",
    importance=0.5,
    memory_type="long_term",
    session_id=None
):

    created = now()

    record = {
        "content": content.strip(),
        "category": category,
        "importance": float(importance),
        "memory_type": memory_type,
        "created_at": created,
        "last_accessed": created
    }

    if session_id:
        record["source_session"] = session_id

    if memory_type == "cache":

        record["expires_at"] = (
            created + CACHE_TTL
        )

    return record


# =================================
# ADD
# =================================

def add_memory(
    category,
    content,
    importance=0.5,
    memory_type="long_term",
    session_id=None
):

    memories = load_memories()

    content = content.strip()

    if not content:

        print("Memory cannot be empty.")
        return False

    if memory_type not in {
        "long_term",
        "cache"
    }:

        memory_type = "long_term"

    for memory in memories:

        if (
            memory.get("category", "").lower()
            == category.lower()
            and
            memory.get("content", "").strip().lower()
            == content.lower()
        ):

            memory["last_accessed"] = now()

            save_memories(memories)

            return False

    next_id = 1

    if memories:

        next_id = max(
            int(m.get("id", 0))
            for m in memories
        ) + 1

    record = build_memory_record(
        content=content,
        category=category,
        importance=importance,
        memory_type=memory_type,
        session_id=session_id
    )

    record["id"] = next_id

    memories.append(record)

    save_memories(memories)

    return True


# =================================
# UPDATE
# =================================

def update_memory(memory_id, new_content):

    memories = load_memories()

    new_content = new_content.strip()

    if not new_content:

        print("New memory cannot be empty.")
        return

    for memory in memories:

        if int(memory["id"]) == memory_id:

            old_content = memory["content"]

            memory["content"] = new_content
            memory["last_accessed"] = now()

            save_memories(memories)

            print(
                f"Memory [{memory_id}] updated securely."
            )

            print(
                f"Old: {old_content}"
            )

            print(
                f"New: {new_content}"
            )

            return

    print(
        f"Memory [{memory_id}] not found."
    )


# =================================
# DELETE
# =================================

def delete_memory(memory_id):

    memories = load_memories()

    found = False

    new_memories = []

    for memory in memories:

        if int(memory["id"]) == memory_id:

            found = True

        else:

            new_memories.append(memory)

    if not found:

        print("Memory ID not found.")
        return

    save_memories(new_memories)

    print(
        f"Memory [{memory_id}] deleted securely."
    )


# =================================
# LIST
# =================================

def list_memories():

    memories = load_memories()

    if not memories:

        print("No memories stored.")
        return

    print()
    print("===== JIRAIYA MEMORY =====")
    print()

    for memory in memories:

        memory_type = memory.get(
            "memory_type",
            "long_term"
        )

        importance = memory.get(
            "importance",
            0.5
        )

        print(
            f'[{memory["id"]}] '
            f'{memory["category"]} '
            f'({memory_type}, '
            f'importance={importance}): '
            f'{memory["content"]}'
        )

    print()


# =================================
# SEARCH
# =================================

def search_memory(query):

    memories = load_memories()

    if not memories:

        print("No memory found.")
        return

    stop_words = {
        "what", "is", "my", "your",
        "the", "a", "an", "who",
        "where", "when", "why", "how",
        "do", "does", "did", "tell",
        "me", "about", "please", "can",
        "you", "i", "am", "are",
        "was", "were", "this", "that",
        "and", "or", "of", "to", "in",
        "for", "on", "with"
    }

    words = tokenize(query)

    keywords = [
        word
        for word in words
        if word not in stop_words
    ]

    if not keywords:

        print("No useful search terms.")
        return

    results = []

    for memory in memories:

        text = (
            str(memory.get("category", ""))
            + " "
            + str(memory.get("content", ""))
        )

        memory_words = tokenize(text)

        score = sum(
            1
            for keyword in keywords
            if keyword in memory_words
        )

        if score > 0:

            importance = float(
                memory.get(
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
                    memory
                )
            )

    results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    if not results:

        print("No matching memory.")
        return

    for score, memory in results[:5]:

        memory["last_accessed"] = now()

        print(
            f'[{memory["id"]}] '
            f'{memory["category"]}: '
            f'{memory["content"]}'
        )

    save_memories(memories)


# =================================
# RETRIEVE CANDIDATES
# =================================

def retrieve_candidates(
    query,
    limit=5
):

    memories = load_memories()

    if not memories:
        return []

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    weak_words = {
        "what", "is", "my", "your", "the", "a", "an",
        "who", "where", "when", "why", "how", "do", "does",
        "did", "tell", "me", "about", "please", "can", "you",
        "i", "am", "are", "was", "were", "this", "that",
        "and", "or", "of", "to", "in", "for", "on", "with"
    }

    useful_query_tokens = {
        token for token in query_tokens
        if token not in weak_words
    }

    if not useful_query_tokens:
        useful_query_tokens = query_tokens

    for memory in memories:

        content_tokens = tokenize(
            str(memory.get("content", ""))
        )

        category_tokens = tokenize(
            str(memory.get("category", ""))
        )

        content_overlap = len(
            useful_query_tokens.intersection(
                content_tokens
            )
        )

        category_overlap = len(
            useful_query_tokens.intersection(
                category_tokens
            )
        )

        if content_overlap == 0 and category_overlap == 0:
            continue

        # Require a meaningful content match.
        if content_overlap == 0:
            continue

        importance = float(
            memory.get(
                "importance",
                0.5
            )
        )

        score = (
            content_overlap * 2.0
            + category_overlap * 0.5
            + importance * 0.25
        )

        results.append(
            (score, memory)
        )

    results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    selected = []

    for score, memory in results[:limit]:

        memory["last_accessed"] = now()

        selected.append(memory)

    if selected:
        save_memories(memories)

    return selected


# =================================
# ACTIVE MEMORIES
# =================================

def active_memories():

    memories = load_memories()

    return memories


# =================================
# COMPACT INDEX
# =================================

def compact_index(memory):

    keywords = sorted(
        list(
            tokenize(
                memory.get(
                    "content",
                    ""
                )
            )
        )
    )[:20]

    return {
        "memory_id": memory.get("id"),
        "keywords": keywords,
        "category": memory.get(
            "category",
            "user"
        ),
        "importance": memory.get(
            "importance",
            0.5
        )
    }


def build_index():

    memories = load_memories()

    index = []

    for memory in memories:

        index.append(
            compact_index(memory)
        )

    return index


# =================================
# MEMORY STATS
# =================================

def memory_stats():

    memories = load_memories()

    long_term = 0
    cache = 0

    for memory in memories:

        if memory.get(
            "memory_type"
        ) == "cache":

            cache += 1

        else:

            long_term += 1

    return {
        "total": len(memories),
        "long_term": long_term,
        "cache": cache,
        "index_entries": len(memories)
    }


# =================================
# MAIN
# =================================

def main():

    if len(sys.argv) < 2:

        print("""
Jiraiya Memory Manager

Commands:

  add <category> <memory>
  list
  search <query>
  update <id> <new memory>
  delete <id>
  stats
  index
""")

        return

    command = sys.argv[1]


    # -----------------------------
    # ADD
    # -----------------------------

    if command == "add" and len(sys.argv) >= 4:

        add_memory(
            sys.argv[2],
            " ".join(sys.argv[3:])
        )


    # -----------------------------
    # LIST
    # -----------------------------

    elif command == "list":

        list_memories()


    # -----------------------------
    # SEARCH
    # -----------------------------

    elif command == "search" and len(sys.argv) >= 3:

        search_memory(
            " ".join(sys.argv[2:])
        )


    # -----------------------------
    # UPDATE
    # -----------------------------

    elif command == "update" and len(sys.argv) >= 4:

        try:

            memory_id = int(
                sys.argv[2]
            )

            update_memory(
                memory_id,
                " ".join(sys.argv[3:])
            )

        except ValueError:

            print("Invalid memory ID.")


    # -----------------------------
    # DELETE
    # -----------------------------

    elif command == "delete" and len(sys.argv) >= 3:

        try:

            memory_id = int(
                sys.argv[2]
            )

            delete_memory(
                memory_id
            )

        except ValueError:

            print("Invalid memory ID.")


    # -----------------------------
    # STATS
    # -----------------------------

    elif command == "stats":

        print(
            json.dumps(
                memory_stats(),
                indent=2
            )
        )


    # -----------------------------
    # INDEX
    # -----------------------------

    elif command == "index":

        print(
            json.dumps(
                build_index(),
                ensure_ascii=False,
                indent=2
            )
        )


    else:

        print("Invalid command.")


if __name__ == "__main__":
    main()
