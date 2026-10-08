#!/usr/bin/env python3

import json
import sys
import urllib.request
import urllib.error
import subprocess
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
SELF_DIR = BASE / "self_improvement"

ARCH_FILE = SELF_DIR / "architecture.json"
PROPOSALS_DIR = SELF_DIR / "proposals"
SANDBOX_DIR = SELF_DIR / "sandbox"

VALIDATOR = SELF_DIR / "plan_validator.py"
GENERATOR = SELF_DIR / "code_generator.py"

SERVER_URL = "http://127.0.0.1:8080"
CHAT_URL = f"{SERVER_URL}/v1/chat/completions"

MODEL = "local-model"

TIMEOUT = 180
MAX_REVISIONS = 2
MAX_JSON_RETRIES = 2
MAX_TOKENS = 650


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_architecture():
    if not ARCH_FILE.exists():
        raise FileNotFoundError(
            f"Architecture file not found:\n{ARCH_FILE}"
        )

    return load_json(ARCH_FILE)


def normalize_path(value):
    if isinstance(value, dict):
        for key in (
            "path",
            "file",
            "name",
            "relative_path",
        ):
            candidate = value.get(key)

            if isinstance(candidate, str):
                value = candidate
                break

    if not isinstance(value, str):
        return ""

    value = value.strip().replace("\\", "/")

    while value.startswith("./"):
        value = value[2:]

    while value.startswith("/"):
        value = value[1:]

    return value


def architecture_summary(architecture):
    files = architecture.get("files", [])

    paths = []

    for item in files:
        path = normalize_path(item)

        if path:
            paths.append(path)

    allowed = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".html",
        ".css",
        ".sh",
    }

    source_files = [
        path
        for path in paths
        if Path(path).suffix.lower() in allowed
    ]

    source_files.sort()

    priority = [
        "agent.py",
        "core/",
        "learner.py",
        "model_manager.py",
        "memory/",
        "knowledge/",
        "web/",
        "self_improvement/",
    ]

    important = [
        path
        for path in source_files
        if any(term in path for term in priority)
    ]

    result = []
    seen = set()

    for path in important + source_files:
        if path not in seen:
            result.append(path)
            seen.add(path)

    return "\n".join(result[:100])


def server_healthy():
    try:
        request = urllib.request.Request(
            f"{SERVER_URL}/health",
            method="GET"
        )

        with urllib.request.urlopen(
            request,
            timeout=5
        ) as response:
            return response.status == 200

    except Exception:
        return False


def ask_llm(system_prompt, user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.0,
        "max_tokens": MAX_TOKENS
    }

    data = json.dumps(
        payload,
        separators=(",", ":")
    ).encode("utf-8")

    request = urllib.request.Request(
        CHAT_URL,
        data=data,
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
                "utf-8"
            )

            result = json.loads(raw)

            choices = result.get(
                "choices",
                []
            )

            if not choices:
                raise RuntimeError(
                    "LLM returned no choices."
                )

            content = choices[0].get(
                "message",
                {}
            ).get(
                "content",
                ""
            )

            if not content:
                raise RuntimeError(
                    "LLM returned empty content."
                )

            return content.strip()

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not contact local LLM: {exc}"
        )


def extract_json(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "LLM did not return a JSON object."
        )

    return text[start:end + 1]


def parse_plan_response(response):
    raw = extract_json(response)

    try:
        return json.loads(raw)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Malformed JSON from LLM: "
            f"line {exc.lineno}, "
            f"column {exc.colno}: "
            f"{exc.msg}"
        )


def repair_json(response, error):
    system_prompt = """
You are a strict JSON repair utility.

You are given malformed JSON produced by another model.

Repair it without changing the intended plan.

Rules:
- Return ONLY valid JSON.
- Return exactly one JSON object.
- Do not use markdown.
- Do not add explanations.
- Preserve all meaningful fields.
""".strip()

    user_prompt = f"""
MALFORMED RESPONSE:

{response}

JSON ERROR:

{error}

Return the corrected JSON object only.
""".strip()

    return ask_llm(
        system_prompt,
        user_prompt
    )


def ask_for_plan(
    system_prompt,
    prompt
):
    response = ask_llm(
        system_prompt,
        prompt
    )

    for attempt in range(
        MAX_JSON_RETRIES + 1
    ):
        try:
            return parse_plan_response(
                response
            )

        except ValueError as exc:

            if attempt >= MAX_JSON_RETRIES:
                raise

            print(
                f"⚠ Invalid JSON. "
                f"Repair attempt "
                f"{attempt + 1}/"
                f"{MAX_JSON_RETRIES}"
            )

            response = repair_json(
                response,
                str(exc)
            )

    raise RuntimeError(
        "Could not obtain valid JSON."
    )


def build_system_prompt(
    architecture_text
):
    return f"""
You are Jiraiya's safe improvement planner.

Create ONLY an implementation plan.

Never modify files.
Never execute commands.
Never deploy.

REAL SOURCE FILES:

{architecture_text}

RULES:

- Use real paths only.
- Do not invent existing files.
- Prefer modifying existing source when appropriate.
- New files are allowed when necessary.
- Never modify .db, .db.enc, .key, .gguf or .log.
- Never modify backups/, versions/, sandbox/ or .git/.
- Do not propose shell commands as implementation changes.
- Keep the change minimal.
- Include meaningful executable tests.
- Tests must actually exercise the implementation.
- Production requires approval.

Return ONLY valid JSON.
No markdown.
No comments.
No trailing commas.

Schema:

{{
  "title": "...",
  "goal": "...",
  "reason": "...",
  "existing_files": [],
  "new_files": [],
  "changes": [],
  "tests": [],
  "risk": "LOW",
  "rollback": "..."
}}

Risk must be LOW, MEDIUM or HIGH.
""".strip()


def initial_prompt(request):
    return f"""
Create a minimal safe implementation plan for:

{request}

Use only the real source files supplied above.
""".strip()


def revision_prompt(
    request,
    plan,
    validation
):
    feedback = {
        "status":
            validation.get("status"),

        "severity":
            validation.get("severity"),

        "architecture_check":
            validation.get(
                "architecture_check",
                {}
            ),

        "semantic_problems":
            validation.get(
                "semantic_problems",
                []
            ),

        "sandbox_validation":
            validation.get(
                "sandbox_validation",
                []
            ),
    }

    return f"""
Correct the previous improvement plan.

REQUEST:

{request}

PREVIOUS PLAN:

{json.dumps(
    plan,
    separators=(",", ":")
)}

VALIDATOR FEEDBACK:

{json.dumps(
    feedback,
    separators=(",", ":")
)}

The previous plan failed validation.

Create a corrected minimal plan.

Requirements:

- Fix every validator failure.
- Do not invent paths.
- Do not use protected files or directories.
- Tests must actually execute.
- Tests must exercise the implementation.
- Keep the design minimal.
- Return ONLY valid JSON.
- No markdown.
- No explanations.
""".strip()


def validate_structure(plan):
    required = [
        "title",
        "goal",
        "reason",
        "existing_files",
        "new_files",
        "changes",
        "tests",
        "risk",
        "rollback",
    ]

    for key in required:
        if key not in plan:
            raise ValueError(
                f"Missing field: {key}"
            )

    for key in (
        "existing_files",
        "new_files",
        "changes",
        "tests",
    ):
        if not isinstance(
            plan[key],
            list
        ):
            raise ValueError(
                f"{key} must be a list."
            )

    if plan["risk"] not in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }:
        raise ValueError(
            "Invalid risk level."
        )


def save_plan(
    plan,
    request,
    revision
):
    PROPOSALS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = (
        PROPOSALS_DIR
        / f"plan_{timestamp}.json"
    )

    document = {
        "created_at":
            datetime.now()
            .astimezone()
            .isoformat(),

        "request":
            request,

        "revision":
            revision,

        "plan":
            plan,
    }

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            document,
            f,
            indent=2,
            ensure_ascii=False
        )

    return path


def find_latest_sandbox():
    if not SANDBOX_DIR.exists():
        return None

    candidates = [
        path
        for path in SANDBOX_DIR.iterdir()
        if path.is_dir()
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    return candidates[0]


def create_sandbox(plan_path):
    manager = (
        SELF_DIR
        / "sandbox_manager.py"
    )

    if not manager.exists():
        raise FileNotFoundError(
            f"Sandbox manager not found: {manager}"
        )

    result = subprocess.run(
        [
            sys.executable,
            str(manager),
            "create",
            str(plan_path),
        ],
        capture_output=True,
        text=True
    )

    output = (
        result.stdout
        + result.stderr
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Sandbox creation failed:\n"
            + output
        )

    sandbox = find_latest_sandbox()

    if sandbox is None:
        raise RuntimeError(
            "No sandbox was created."
        )

    print(
        f"✓ Sandbox created: {sandbox}"
    )

    return sandbox


def run_generator(
    plan_path,
    sandbox_path
):
    if not GENERATOR.exists():
        raise FileNotFoundError(
            f"Code generator not found: {GENERATOR}"
        )

    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            str(plan_path),
            str(sandbox_path),
        ],
        capture_output=True,
        text=True
    )

    output = (
        result.stdout
        + result.stderr
    )

    print()
    print(output)

    if result.returncode != 0:
        raise RuntimeError(
            "Code generation failed."
        )


def run_validator(
    plan_path,
    sandbox_path
):
    command = [
        sys.executable,
        str(VALIDATOR),
        str(plan_path),
        str(sandbox_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    output = (
        result.stdout
        + result.stderr
    )

    validation_path = (
        plan_path.parent
        / f"{plan_path.stem}_validation.json"
    )

    validation = None

    if validation_path.exists():
        try:
            validation = load_json(
                validation_path
            )
        except Exception:
            pass

    print()
    print(output)

    return (
        result.returncode,
        validation
    )


def generate_and_validate(
    plan,
    plan_path
):
    sandbox = create_sandbox(
        plan_path
    )

    run_generator(
        plan_path,
        sandbox
    )

    return_code, validation = (
        run_validator(
            plan_path,
            sandbox
        )
    )

    return (
        return_code,
        validation,
        sandbox
    )


def generate_plan(request):
    architecture = load_architecture()

    architecture_text = (
        architecture_summary(
            architecture
        )
    )

    system_prompt = build_system_prompt(
        architecture_text
    )

    plan = None
    validation = None
    final_path = None
    sandbox = None

    for revision in range(
        MAX_REVISIONS + 1
    ):

        if revision == 0:
            print(
                "\n🧠 Generating plan..."
            )

            prompt = initial_prompt(
                request
            )

        else:
            print(
                f"\n🔄 Revising plan "
                f"{revision}/{MAX_REVISIONS}..."
            )

            prompt = revision_prompt(
                request,
                plan,
                validation
            )

        plan = ask_for_plan(
            system_prompt,
            prompt
        )

        validate_structure(
            plan
        )

        final_path = save_plan(
            plan,
            request,
            revision
        )

        print(
            f"✓ Draft saved: {final_path}"
        )

        code, validation, sandbox = (
            generate_and_validate(
                plan,
                final_path
            )
        )

        if (
            code == 0
            and validation
            and validation.get(
                "status"
            ) == "SAFE TO CONTINUE"
        ):
            return (
                plan,
                final_path,
                revision,
                sandbox
            )

        if revision >= MAX_REVISIONS:
            raise RuntimeError(
                "Improvement failed validation "
                f"after {MAX_REVISIONS} "
                "revision rounds."
            )

        print(
            "\n⚠ Generated implementation "
            "was rejected."
        )

    raise RuntimeError(
        "Improvement engine stopped unexpectedly."
    )


def print_final(
    plan,
    path,
    revision,
    sandbox
):
    print()
    print("=" * 45)
    print(
        "JIRAIYA FINAL IMPROVEMENT PLAN"
    )
    print("=" * 45)

    print()
    print(
        f"Revision rounds: {revision}"
    )

    print(
        f"Title: {plan['title']}"
    )

    print(
        f"Risk: {plan['risk']}"
    )

    print()
    print("Goal:")
    print(plan["goal"])

    print()
    print("Existing files:")

    if plan["existing_files"]:
        for item in plan["existing_files"]:
            print(f"  ✓ {item}")
    else:
        print("  None")

    print()
    print("New files:")

    if plan["new_files"]:
        for item in plan["new_files"]:
            print(f"  + {item}")
    else:
        print("  None")

    print()
    print("Tests:")

    for item in plan["tests"]:
        print(f"  ✓ {item}")

    print()
    print("Rollback:")
    print(plan["rollback"])

    print()
    print("Validated sandbox:")
    print(sandbox)

    print()
    print("✓ Final validated plan:")
    print(path)

    print()
    print(
        "🔒 Production was NOT modified."
    )


def main():
    if len(sys.argv) < 2:
        print(
            'Usage:\n'
            'python improvement_engine.py '
            '"request"'
        )
        sys.exit(1)

    request = " ".join(
        sys.argv[1:]
    ).strip()

    if not request:
        print(
            "ERROR: Empty request."
        )
        sys.exit(1)

    if not server_healthy():
        print(
            "ERROR: Local LLM server "
            "is not healthy."
        )
        sys.exit(1)

    try:
        plan, path, revision, sandbox = (
            generate_plan(
                request
            )
        )

        print_final(
            plan,
            path,
            revision,
            sandbox
        )

    except Exception as exc:
        print()
        print(
            "✗ Improvement engine failed:"
        )
        print(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
