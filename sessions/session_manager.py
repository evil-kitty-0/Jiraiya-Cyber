#!/usr/bin/env python3

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
SESSION_DIR = BASE / "sessions"
SESSION_FILE = SESSION_DIR / "sessions.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def ensure_storage():
    SESSION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not SESSION_FILE.exists():
        SESSION_FILE.write_text(
            "[]",
            encoding="utf-8"
        )


def load_sessions():
    ensure_storage()

    try:
        data = json.loads(
            SESSION_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_sessions(sessions):
    ensure_storage()

    temp_file = SESSION_FILE.with_suffix(".tmp")

    temp_file.write_text(
        json.dumps(
            sessions,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp_file.replace(
        SESSION_FILE
    )


def create_session(title="New Chat"):
    sessions = load_sessions()

    session = {
        "id": str(uuid.uuid4()),
        "title": title,
        "messages": [],
        "created_at": now(),
        "updated_at": now()
    }

    sessions.append(session)

    save_sessions(sessions)

    return session


def get_session(session_id):
    sessions = load_sessions()

    for session in sessions:
        if session.get("id") == session_id:
            return session

    return None


def list_sessions():
    sessions = load_sessions()

    return sorted(
        sessions,
        key=lambda x: x.get(
            "updated_at",
            ""
        ),
        reverse=True
    )


def add_message(
    session_id,
    role,
    content
):
    sessions = load_sessions()

    for session in sessions:

        if session.get("id") != session_id:
            continue

        session.setdefault(
            "messages",
            []
        ).append(
            {
                "role": role,
                "content": content,
                "created_at": now()
            }
        )

        session["updated_at"] = now()

        save_sessions(sessions)

        return session

    return None


def rename_session(
    session_id,
    title
):
    sessions = load_sessions()

    for session in sessions:

        if session.get("id") == session_id:

            session["title"] = (
                str(title).strip()
                or "New Chat"
            )

            session["updated_at"] = now()

            save_sessions(sessions)

            return session

    return None


def delete_session(session_id):
    sessions = load_sessions()

    new_sessions = [
        session
        for session in sessions
        if session.get("id") != session_id
    ]

    if len(new_sessions) == len(sessions):
        return False

    save_sessions(new_sessions)

    return True


if __name__ == "__main__":

    session = create_session()

    print(
        json.dumps(
            session,
            ensure_ascii=False,
            indent=2
        )
    )
