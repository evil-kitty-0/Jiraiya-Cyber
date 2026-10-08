#!/usr/bin/env python3
"""
FreeLLMAPI backend for Jiraiya.

Uses the local FreeLLMAPI OpenAI-compatible gateway so Jiraiya can
route inference across configured free-tier providers instead of
loading a GGUF model on the device.

Environment:
  JIRAIYA_FREELLMAPI_URL  default: http://127.0.0.1:3001/v1
  JIRAIYA_FREELLMAPI_KEY  unified key from FreeLLMAPI
  JIRAIYA_FREELLMAPI_MODEL default: auto
"""

import json
import os
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://127.0.0.1:3001/v1"
DEFAULT_MODEL = "auto"


def configured():
    return bool(os.getenv("JIRAIYA_FREELLMAPI_KEY", "").strip())


def _base_url():
    return os.getenv(
        "JIRAIYA_FREELLMAPI_URL",
        DEFAULT_BASE_URL,
    ).rstrip("/")


def _model():
    return os.getenv(
        "JIRAIYA_FREELLMAPI_MODEL",
        DEFAULT_MODEL,
    ).strip() or DEFAULT_MODEL


def chat(
    messages,
    max_tokens=400,
    temperature=0.2,
    timeout=300,
):
    if not configured():
        raise RuntimeError(
            "FreeLLMAPI is not configured. Set "
            "JIRAIYA_FREELLMAPI_KEY."
        )

    payload = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    request = urllib.request.Request(
        _base_url() + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": (
                "Bearer "
                + os.environ["JIRAIYA_FREELLMAPI_KEY"].strip()
            ),
            "User-Agent": "Jiraiya-Cyber/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"FreeLLMAPI HTTP {exc.code}: {body[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"FreeLLMAPI connection failed: {exc.reason}"
        ) from exc

    try:
        return (
            result["choices"][0]["message"]["content"]
            .strip()
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Unexpected FreeLLMAPI response: "
            + json.dumps(result)[:800]
        ) from exc
