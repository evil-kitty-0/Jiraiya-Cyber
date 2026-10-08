import ast
import sys
from pathlib import Path


FORBIDDEN_PLACEHOLDERS = {
    "pass",
    "NotImplemented",
    "TODO",
    "placeholder",
    "implement here",
    "add your code here",
}


REQUIRED_FUNCTIONS = {
    "check_memory",
    "check_knowledge",
    "check_web",
    "check_llm",
    "get_system_status",
}


def load_tree(file_path):
    source = Path(file_path).read_text(encoding="utf-8")
    return source, ast.parse(source)


def function_map(tree):
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def has_placeholder_text(node, source):
    segment = ast.get_source_segment(source, node)

    if not segment:
        return False

    lowered = segment.lower()

    for marker in FORBIDDEN_PLACEHOLDERS:
        if marker.lower() in lowered:
            return True

    return False


def has_only_pass(node):
    body = [
        item
        for item in node.body
        if not (
            isinstance(item, ast.Expr)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        )
    ]

    return len(body) == 1 and isinstance(body[0], ast.Pass)


def calls_function(node, name):
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                if child.func.id == name:
                    return True

    return False


def returns_constant_true(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            value = child.value

            if (
                isinstance(value, ast.Constant)
                and value.value is True
            ):
                return True

    return False


def check_health_function(name, node, source):
    errors = []

    if has_only_pass(node):
        errors.append(
            f"{name}() contains only pass"
        )

    if has_placeholder_text(node, source):
        errors.append(
            f"{name}() contains placeholder text"
        )

    if returns_constant_true(node):
        errors.append(
            f"{name}() returns constant True"
        )

    if len(node.args.args) != 0:
        errors.append(
            f"{name}() must take no arguments"
        )

    return errors


def check_aggregate_function(node):
    errors = []

    required_checks = {
        "check_memory",
        "check_knowledge",
        "check_web",
        "check_llm",
    }

    for check in required_checks:
        if not calls_function(node, check):
            errors.append(
                f"get_system_status() does not call {check}()"
            )

    return errors


def collect_test_functions(tree):
    tests = []

    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            if node.name.startswith("test_"):
                tests.append(node)

        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    if child.name.startswith("test_"):
                        tests.append(child)

    return tests


def check_tests(test_file):
    source, tree = load_tree(test_file)
    errors = []

    tests = collect_test_functions(tree)

    if not tests:
        errors.append(
            "No test_* functions found"
        )
        return errors

    for test in tests:
        if has_only_pass(test):
            errors.append(
                f"{test.name}() contains only pass"
            )

        if has_placeholder_text(test, source):
            errors.append(
                f"{test.name}() contains placeholder text"
            )

    return errors


def check_system_status(file_path):
    source, tree = load_tree(file_path)
    functions = function_map(tree)
    errors = []

    for name in REQUIRED_FUNCTIONS:
        if name not in functions:
            errors.append(
                f"Missing required function: {name}()"
            )

    health_functions = {
        "check_memory",
        "check_knowledge",
        "check_web",
        "check_llm",
    }

    for name in health_functions:
        node = functions.get(name)

        if node:
            errors.extend(
                check_health_function(
                    name,
                    node,
                    source
                )
            )

    aggregate = functions.get(
        "get_system_status"
    )

    if aggregate:
        errors.extend(
            check_aggregate_function(
                aggregate
            )
        )

    return errors


def run_quality_gate(sandbox_dir):
    sandbox = Path(sandbox_dir).resolve()

    status_file = (
        sandbox
        / "self_improvement"
        / "system_status.py"
    )

    test_file = (
        sandbox
        / "self_improvement"
        / "system_status_test.py"
    )

    errors = []

    if not status_file.exists():
        errors.append(
            "system_status.py does not exist"
        )
    else:
        try:
            errors.extend(
                check_system_status(status_file)
            )
        except Exception as exc:
            errors.append(
                f"Unable to analyze system_status.py: {exc}"
            )

    if not test_file.exists():
        errors.append(
            "system_status_test.py does not exist"
        )
    else:
        try:
            errors.extend(
                check_tests(test_file)
            )
        except Exception as exc:
            errors.append(
                f"Unable to analyze system_status_test.py: {exc}"
            )

    return errors


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python semantic_quality_gate.py "
            "<sandbox_dir>"
        )
        sys.exit(1)

    sandbox_dir = sys.argv[1]

    errors = run_quality_gate(
        sandbox_dir
    )

    if errors:
        print("SEMANTIC QUALITY: FAIL")

        for error in errors:
            print(f"  - {error}")

        sys.exit(1)

    print("SEMANTIC QUALITY: PASS")


if __name__ == "__main__":
    main()
