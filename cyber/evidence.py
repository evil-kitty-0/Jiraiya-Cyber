"""Evidence helpers with conservative secret redaction."""

import re
from time import time

_SECRET_PATTERNS = [
    (re.compile(r"(?i)(authorization\\s*:\\s*bearer\\s+)[^\\s]+"), r"\\1[REDACTED]"),
    (re.compile(r"(?i)(cookie\\s*:\\s*)[^\\r\\n]+"), r"\\1[REDACTED]"),
    (re.compile(r"(?i)(set-cookie\\s*:\\s*)[^\\r\\n]+"), r"\\1[REDACTED]"),
    (re.compile(r"(?i)(api[_-]?key\\s*[=:]\\s*)[^\\s,;&]+"), r"\\1[REDACTED]"),
]


def redact(text: str) -> str:
    value = text or ""
    for pattern, replacement in _SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def capture(kind: str, target: str, details: dict) -> dict:
    safe = {k: redact(str(v)) for k, v in details.items()}
    return {"type": kind, "target": target, "timestamp": time(), "details": safe}
