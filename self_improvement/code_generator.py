#!/usr/bin/env python3

import json
import sys
import hashlib
import urllib.request
import urllib.error
from pathlib import Path


SERVER_URL = "http://127.0.0.1:8080"
CHAT_URL = SERVER_URL + "/v1/chat/completions"

TIMEOUT = 300
MAX_TOKENS = 350

MODEL_NAME = "local-model"

ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".sh",
}

PROTECTED_EXTENSIONS = {
    ".db",
    ".db.enc",
    ".key",
    ".gguf",
    ".log",
    ".sqlite",
    ".sqlite3",
}

PROTECTED_NAMES = {
    "master.key"
}

PROTECTED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "versions",
}


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def get_plan(data):
    if isinstance(data.get("plan"), dict):
        return data["plan"]

    return data


def normalize_path(value):
    return (
        str(value)
        .strip()
        .replace("\\", "/")
        .lstrip("./")
    )


def extract_paths(plan, key):
    result = []

    for item in plan.get(key, []):
        if isinstance(item, dict):
            value = item.get("path", "")
        else:
            value = item

        value = normalize_path(value)

        if value:
            result.append(value)

    return result


def is_protected(path_value):
    path = Path(
        normalize_path(path_value)
    )

    if path.name in PROTECTED_NAMES:
        return True

    if path.suffix.lower() in PROTECTED_EXTENSIONS:
        return True

    for part in path.parts:
        if part in PROTECTED_DIRS:
            return True

    return False


def allowed_source(path_value):
    return (
        Path(
            normalize_path(path_value)
        ).suffix.lower()
        in ALLOWED_EXTENSIONS
    )


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def read_context(plan, sandbox):
    paths = []

    paths.extend(
        extract_paths(
            plan,
            "related_files"
        )
    )

    paths.extend(
        extract_paths(
            plan,
            "existing_files"
        )
    )

    result = []
    seen = set()

    for path_value in paths:

        if path_value in seen:
            continue

        seen.add(path_value)

        if is_protected(path_value):
            continue

        path = sandbox / path_value

        if not path.is_file():
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace"
            )
        except Exception:
            continue

        result.append({
            "path": path_value,
            "content": text[:1800]
        })

    return result[:4]


def find_change(plan, target):
    for change in plan.get(
        "changes",
        []
    ):

        if not isinstance(change, dict):
            continue

        if normalize_path(
            change.get("file", "")
        ) == target:
            return change

    return {}


def build_prompt(
    plan,
    target,
    action,
    change,
    context,
    repair_error=None
):

    context_text = ""

    for item in context:
        context_text += (
            "\nFILE: "
            + item["path"]
            + "\n"
            + item["content"]
            + "\n"
        )

    repair_text = ""

    if repair_error:
        repair_text = f"""

PREVIOUS CODE FAILED SYNTAX CHECK.

ERROR:
{repair_error}

Repair the code while keeping the same requested functionality.
Return the COMPLETE corrected file.
"""

    return f"""
You are Jiraiya's coding engine.

Generate ONE small source file.

TASK:
{plan.get("title", "System improvement")}

GOAL:
{plan.get("goal", "")}

TARGET:
{target}

ACTION:
{action}

REQUIREMENT:
{change.get("description", "")}

CONSTRAINTS:
{json.dumps(change.get("constraints", []), ensure_ascii=False)}

PROJECT CONTEXT:
{context_text}

RULES:

- Return COMPLETE source code only.
- No JSON.
- No markdown.
- No code fences.
- No explanations.
- No shell commands.
- Do not create another file.
- Do not invent filenames.
- Do not access keys.
- Do not modify databases.
- Do not modify model files.
- Do not modify logs.
- Keep the implementation concise.
- Use Python standard library where possible.
- Make Python code syntactically valid.
- Implement only the requested feature.

The target path is fixed by Jiraiya:
{target}

{repair_text}

RETURN ONLY SOURCE CODE.
""".strip()


def call_llm(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Jiraiya's coding model. "
                    "You are Qwen2.5-Coder 1.5B. "
                    "Generate concise valid source code only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "max_tokens": MAX_TOKENS
    }

    request = urllib.request.Request(
        CHAT_URL,
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT
        ) as response:

            raw = response.read().decode(
                "utf-8",
                errors="replace"
            )

        result = json.loads(raw)

        choices = result.get(
            "choices",
            []
        )

        if not choices:
            raise RuntimeError(
                "LLM returned no choices"
            )

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:
            raise RuntimeError(
                "LLM returned empty content"
            )

        return content.strip()

    except urllib.error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"LLM HTTP error {exc.code}: "
            f"{body[:1000]}"
        )


def clean_code(text):
    text = text.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and (
            lines[-1].strip()
            == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    return text


def validate_code(
    code,
    target
):

    code = clean_code(code)

    if not code:
        raise ValueError(
            "Generated file is empty"
        )

    if is_protected(target):
        raise ValueError(
            f"Protected file: {target}"
        )

    if not allowed_source(target):
        raise ValueError(
            f"Unsupported source: {target}"
        )

    if (
        Path(target).suffix.lower()
        == ".py"
    ):

        compile(
            code,
            target,
            "exec"
        )

    return code


def write_file(
    sandbox,
    target,
    code
):

    destination = (
        sandbox / target
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    destination.write_text(
        code,
        encoding="utf-8"
    )


def generate_file(
    plan,
    sandbox,
    target,
    action,
    context
):

    change = find_change(
        plan,
        target
    )

    last_error = None

    for attempt in range(
        1,
        4
    ):

        print(
            f"  Attempt {attempt}/3"
        )

        prompt = build_prompt(
            plan,
            target,
            action,
            change,
            context,
            last_error
        )

        try:

            code = call_llm(
                prompt
            )

            code = validate_code(
                code,
                target
            )

            write_file(
                sandbox,
                target,
                code
            )

            return {
                "action": action,
                "path": target,
                "sha256": sha256_text(
                    code
                ),
                "bytes": len(
                    code.encode(
                        "utf-8"
                    )
                )
            }

        except Exception as exc:

            last_error = str(exc)

            print(
                f"  ⚠ {last_error}"
            )

    raise RuntimeError(
        f"Unable to generate "
        f"{target}: {last_error}"
    )


def generate(
    plan_path,
    sandbox
):

    print(
        "============================================="
    )
    print(
        "JIRAIYA SANDBOX CODE GENERATOR"
    )
    print(
        "============================================="
    )
    print()

    print(
        f"Plan: {plan_path}"
    )

    print(
        f"Sandbox: {sandbox}"
    )

    print(
        "Model: Qwen2.5-Coder 1.5B"
    )

    print()

    if not plan_path.exists():
        raise FileNotFoundError(
            f"Plan not found: {plan_path}"
        )

    if not sandbox.exists():
        raise FileNotFoundError(
            f"Sandbox not found: {sandbox}"
        )

    raw = load_json(
        plan_path
    )

    plan = get_plan(
        raw
    )

    existing = extract_paths(
        plan,
        "existing_files"
    )

    new = extract_paths(
        plan,
        "new_files"
    )

    targets = []

    for path_value in existing:
        targets.append(
            (
                path_value,
                "replace"
            )
        )

    for path_value in new:
        targets.append(
            (
                path_value,
                "create"
            )
        )

    if not targets:
        raise ValueError(
            "Plan contains no implementation files"
        )

    context = read_context(
        plan,
        sandbox
    )

    generated = []

    for number, (
        target,
        action
    ) in enumerate(
        targets,
        start=1
    ):

        print(
            f"🧠 File {number}/"
            f"{len(targets)}: "
            f"{target}"
        )

        if target not in (
            existing + new
        ):
            raise ValueError(
                f"Unplanned file: {target}"
            )

        if is_protected(target):
            raise ValueError(
                f"Protected target: {target}"
            )

        result = generate_file(
            plan,
            sandbox,
            target,
            action,
            context
        )

        generated.append(
            result
        )

        print(
            f"  ✓ {action.upper()}: "
            f"{target}"
        )

    manifest = {
        "plan": str(plan_path),
        "sandbox": str(sandbox),
        "model": (
            "Qwen2.5-Coder-1.5B"
        ),
        "generated": generated
    }

    manifest_path = (
        sandbox /
        "implementation_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print()
    print(
        "============================================="
    )
    print(
        "✓ CODE GENERATION COMPLETE"
    )
    print(
        "============================================="
    )
    print()

    print(
        f"Generated files: "
        f"{len(generated)}"
    )

    print(
        f"Manifest: "
        f"{manifest_path}"
    )

    print()
    print(
        "Production was NOT modified."
    )


def main():

    if len(sys.argv) != 3:

        print(
            "Usage:"
        )

        print(
            "python code_generator.py "
            "<plan.json> <sandbox>"
        )

        sys.exit(1)

    plan_path = (
        Path(sys.argv[1])
        .expanduser()
        .resolve()
    )

    sandbox = (
        Path(sys.argv[2])
        .expanduser()
        .resolve()
    )

    try:

        generate(
            plan_path,
            sandbox
        )

    except Exception as exc:

        print()
        print(
            "✗ Code generation failed:"
        )

        print(exc)

        sys.exit(1)


if __name__ == "__main__":
    main()
