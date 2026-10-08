import ast
import json
import sys
from pathlib import Path


REQUIRED_FUNCTIONS = {
    "check_memory",
    "check_knowledge",
    "check_web",
    "check_llm",
    "get_system_status",
}


def load_spec(spec_path):
    path = Path(spec_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Spec file not found: {spec_path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_tree(file_path):
    source = Path(file_path).read_text(
        encoding="utf-8"
    )

    return ast.parse(source)


def get_functions(tree):
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    }


def match_system_status(sandbox_dir):
    sandbox = Path(sandbox_dir).resolve()

    target = (
        sandbox
        / "self_improvement"
        / "system_status.py"
    )

    errors = []

    if not target.exists():
        return False, [
            "Missing system_status.py"
        ]

    try:
        tree = load_tree(target)
    except SyntaxError as exc:
        return False, [
            f"Invalid Python syntax: {exc}"
        ]

    functions = get_functions(tree)

    missing = REQUIRED_FUNCTIONS - functions

    if missing:
        for name in sorted(missing):
            errors.append(
                f"Missing required function: {name}()"
            )

    if errors:
        return False, errors

    return True, [
        "All required system-status functions exist"
    ]


def match_tests(sandbox_dir):
    sandbox = Path(sandbox_dir).resolve()

    test_file = (
        sandbox
        / "self_improvement"
        / "system_status_test.py"
    )

    if not test_file.exists():
        return False, [
            "Missing system_status_test.py"
        ]

    try:
        tree = load_tree(test_file)
    except SyntaxError as exc:
        return False, [
            f"Test file has invalid syntax: {exc}"
        ]

    test_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and node.name.startswith("test_")
    }

    if not test_functions:
        return False, [
            "No actual test functions found"
        ]

    return True, [
        f"Found {len(test_functions)} test function(s)"
    ]


def match_spec(spec, sandbox_dir):
    errors = []
    messages = []

    matched, result = match_system_status(
        sandbox_dir
    )

    if not matched:
        errors.extend(result)
    else:
        messages.extend(result)

    matched, result = match_tests(
        sandbox_dir
    )

    if not matched:
        errors.extend(result)
    else:
        messages.extend(result)

    if errors:
        return False, errors

    return True, messages


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python spec_matcher.py "
            '"raw_spec.json" "sandbox_dir"'
        )
        sys.exit(1)

    try:
        spec = load_spec(sys.argv[1])

        matched, messages = match_spec(
            spec,
            sys.argv[2]
        )

        print(
            json.dumps(
                {
                    "matched": matched,
                    "messages": messages
                },
                indent=2
            )
        )

        sys.exit(0 if matched else 1)

    except Exception as exc:
        print(
            json.dumps(
                {
                    "matched": False,
                    "messages": [str(exc)]
                },
                indent=2
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
