import json
import sys
import urllib.request


LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"
TIMEOUT = 60


def call_llm(prompt, max_tokens=180):
    payload = {
        "model": "local-model",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate tiny Python code only. "
                    "Return Python source code only. "
                    "No JSON. No markdown. No explanation."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        LLM_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    return result["choices"][0]["message"]["content"]


def clean_code(text):
    text = text.strip()

    if "```" in text:
        lines = text.splitlines()

        lines = [
            line for line in lines
            if not line.strip().startswith("```")
        ]

        text = "\n".join(lines).strip()

    return text


def build_prompt(goal, operation, target_file):
    if operation == "CREATE_FILE":
        rule = (
            "Return a complete small Python file."
        )

    elif operation == "ADD_FUNCTION":
        rule = (
            "Return exactly ONE complete Python function. "
            "The function must take no arguments. "
            "Do not use self. "
            "Do not use pass."
        )

    elif operation == "ADD_CLASS":
        rule = (
            "Return exactly ONE complete Python class."
        )

    elif operation == "ADD_IMPORT":
        rule = (
            "Return only Python import statements."
        )

    elif operation == "MODIFY_FUNCTION":
        rule = (
            "Return exactly ONE complete Python function."
        )

    else:
        rule = "Return valid Python code."

    return f"""
Create a tiny Python code chunk.

Goal:
{goal}

Operation:
{operation}

Target:
{target_file}

Rules:
{rule}

IMPORTANT:
Return ONLY Python source code.
Do NOT return JSON.
Do NOT use markdown.
Do NOT explain anything.
"""


def generate_chunk(goal, operation, target_file):
    prompt = build_prompt(
        goal,
        operation,
        target_file
    )

    code = clean_code(
        call_llm(prompt)
    )

    if not code:
        raise ValueError("LLM returned empty code")

    return {
        "chunk_id": "generated",
        "target_file": target_file,
        "operation": operation,
        "description": goal,
        "code": code
    }


def main():
    if len(sys.argv) < 4:
        print(
            'Usage: python chunk_generator.py '
            '"goal" "operation" "target_file"'
        )
        sys.exit(1)

    goal = sys.argv[1]
    operation = sys.argv[2]
    target_file = sys.argv[3]

    try:
        chunk = generate_chunk(
            goal,
            operation,
            target_file
        )

        print(
            json.dumps(
                chunk,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
