#!/usr/bin/env python3

import ast
import json
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
SELF_DIR = BASE / "self_improvement"
ARCH_FILE = SELF_DIR / "architecture.json"

PROTECTED_NAMES = {"master.key"}

PROTECTED_EXTENSIONS = {
    ".db",
    ".db.enc",
    ".key",
    ".gguf",
    ".log",
    ".sqlite",
    ".sqlite3",
}

PROTECTED_DIRS = {
    "backups",
    "versions",
    "sandbox",
    ".git",
    "__pycache__",
}

ALLOWED_SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".sh",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_architecture():
    if not ARCH_FILE.exists():
        raise FileNotFoundError(
            f"Architecture file not found: {ARCH_FILE}"
        )
    return load_json(ARCH_FILE)


def extract_path(value):
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        for key in (
            "path",
            "file",
            "name",
            "relative_path",
        ):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate

    return ""


def normalize_path(value):
    value = extract_path(value)

    if not isinstance(value, str):
        return ""

    path = value.strip().replace("\\", "/")

    while path.startswith("./"):
        path = path[2:]

    while path.startswith("/"):
        path = path[1:]

    return path


def path_is_protected(path):
    normalized = normalize_path(path)

    if not normalized:
        return False, ""

    parts = Path(normalized).parts

    for part in parts:
        if part in PROTECTED_DIRS:
            return True, f"Protected directory: {part}"

    name = Path(normalized).name

    if name in PROTECTED_NAMES:
        return True, f"Protected file: {name}"

    lower_name = name.lower()

    for extension in PROTECTED_EXTENSIONS:
        if lower_name.endswith(extension):
            return True, f"Protected file type: {extension}"

    return False, ""


def is_source_file(path):
    normalized = normalize_path(path)

    if not normalized:
        return False

    return (
        Path(normalized).suffix.lower()
        in ALLOWED_SOURCE_EXTENSIONS
    )


def architecture_files(architecture):
    result = set()

    for item in architecture.get("files", []):
        path = normalize_path(item)

        if path:
            result.add(path)

    return result


def classify_path(path, existing_files):
    normalized = normalize_path(path)

    if not normalized:
        return {
            "path": str(path),
            "status": "BLOCKED",
            "reason": "Invalid or unreadable path.",
        }

    protected, reason = path_is_protected(normalized)

    if protected:
        return {
            "path": normalized,
            "status": "BLOCKED",
            "reason": reason,
        }

    if not is_source_file(normalized):
        return {
            "path": normalized,
            "status": "BLOCKED",
            "reason": "Not an allowed source-code file type.",
        }

    if normalized in existing_files:
        return {
            "path": normalized,
            "status": "EXISTING",
            "reason": "Existing project source file.",
        }

    return {
        "path": normalized,
        "status": "NEW",
        "reason": "New source file.",
    }


def resolve_plan(document):
    plan = document.get("plan", document)

    if not isinstance(plan, dict):
        raise ValueError("Plan section is not a JSON object.")

    return plan


def get_plan_paths(plan, key):
    values = plan.get(key, [])

    if not isinstance(values, list):
        return []

    result = []

    for value in values:
        path = normalize_path(value)

        if path and path not in result:
            result.append(path)

    return result


def collect_implementation_files(plan):
    paths = []

    for key in (
        "existing_files",
        "new_files",
    ):
        for path in get_plan_paths(plan, key):
            if path not in paths:
                paths.append(path)

    return paths


def get_changes(plan):
    changes = plan.get("changes", [])

    if not isinstance(changes, list):
        return []

    return changes


def change_path(change):
    if isinstance(change, str):
        return normalize_path(change)

    if isinstance(change, dict):
        for key in (
            "path",
            "file",
            "target",
            "relative_path",
        ):
            value = change.get(key)

            if isinstance(value, str):
                return normalize_path(value)

    return ""


def validate_architecture(plan, architecture):
    existing_architecture = architecture_files(
        architecture
    )

    proposed_existing = get_plan_paths(
        plan,
        "existing_files"
    )

    proposed_new = get_plan_paths(
        plan,
        "new_files"
    )

    existing_results = [
        classify_path(path, existing_architecture)
        for path in proposed_existing
    ]

    new_results = [
        classify_path(path, existing_architecture)
        for path in proposed_new
    ]

    blocked = []
    valid_existing = []
    valid_new = []
    wrong_existing = []
    wrong_new = []

    for result in existing_results:
        if result["status"] == "BLOCKED":
            blocked.append(result)
        elif result["status"] == "EXISTING":
            valid_existing.append(result)
        else:
            wrong_existing.append(result)

    for result in new_results:
        if result["status"] == "BLOCKED":
            blocked.append(result)
        elif result["status"] == "EXISTING":
            wrong_new.append(result)
        else:
            valid_new.append(result)

    return {
        "existing_files": valid_existing,
        "new_files": valid_new,
        "blocked": blocked,
        "wrong_existing": wrong_existing,
        "wrong_new": wrong_new,
    }


def validate_change_targets(plan):
    planned = set(
        collect_implementation_files(plan)
    )

    problems = []

    for change in get_changes(plan):
        path = change_path(change)

        if not path:
            problems.append({
                "type": "CHANGE_WITHOUT_PATH",
                "reason": (
                    "A change entry has no valid file path."
                ),
            })
            continue

        if path not in planned:
            problems.append({
                "type": "UNPLANNED_CHANGE",
                "path": path,
                "reason": (
                    "Change targets a file that is not "
                    "listed in existing_files or new_files."
                ),
            })

    return problems


def read_source(path):
    try:
        return Path(path).read_text(
            encoding="utf-8"
        )
    except Exception:
        return ""


def validate_python_syntax(path):
    source = read_source(path)

    if not source.strip():
        return {
            "path": str(path),
            "status": "FAIL",
            "reason": "Python file is empty or unreadable.",
        }

    try:
        tree = ast.parse(
            source,
            filename=str(path)
        )

        compile(
            tree,
            str(path),
            "exec"
        )

        return {
            "path": str(path),
            "status": "PASS",
            "reason": "Python syntax is valid.",
        }

    except SyntaxError as exc:
        return {
            "path": str(path),
            "status": "FAIL",
            "reason": (
                f"SyntaxError line {exc.lineno}: "
                f"{exc.msg}"
            ),
        }


def validate_python_names(path):
    source = read_source(path)

    if not source.strip():
        return {
            "path": str(path),
            "status": "FAIL",
            "reason": "Python source is empty.",
        }

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {
            "path": str(path),
            "status": "SKIP",
            "reason": "Skipped because syntax is invalid.",
        }

    imported = set()
    defined = set()
    loaded = set()

    builtin_names = set(
        __builtins__.keys()
        if isinstance(__builtins__, dict)
        else dir(__builtins__)
    )

    class Analyzer(ast.NodeVisitor):

        def visit_Import(self, node):
            for alias in node.names:
                imported.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

        def visit_ImportFrom(self, node):
            for alias in node.names:
                imported.add(
                    alias.asname
                    or alias.name
                )

        def visit_FunctionDef(self, node):
            defined.add(node.name)

            for arg in node.args.posonlyargs:
                defined.add(arg.arg)

            for arg in node.args.args:
                defined.add(arg.arg)

            for arg in node.args.kwonlyargs:
                defined.add(arg.arg)

            if node.args.vararg:
                defined.add(node.args.vararg.arg)

            if node.args.kwarg:
                defined.add(node.args.kwarg.arg)

            for child in node.body:
                self.visit(child)

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_ClassDef(self, node):
            defined.add(node.name)
            self.generic_visit(node)

        def visit_Assign(self, node):
            for target in node.targets:
                self.collect_target(target)
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            self.collect_target(node.target)
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            self.collect_target(node.target)
            self.generic_visit(node)

        def visit_For(self, node):
            self.collect_target(node.target)
            self.generic_visit(node)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                loaded.add(node.id)

        def collect_target(self, node):
            if isinstance(node, ast.Name):
                defined.add(node.id)

            elif isinstance(node, (ast.Tuple, ast.List)):
                for item in node.elts:
                    self.collect_target(item)

    analyzer = Analyzer()
    analyzer.visit(tree)

    available = (
        defined
        | imported
        | builtin_names
        | {"self", "cls"}
    )

    possible = sorted(
        name
        for name in loaded
        if name not in available
    )

    if possible:
        return {
            "path": str(path),
            "status": "FAIL",
            "reason": (
                "Possible undefined names: "
                + ", ".join(possible[:10])
            ),
        }

    return {
        "path": str(path),
        "status": "PASS",
        "reason": "No obvious undefined names detected.",
    }


def test_file_candidates(paths):
    candidates = []

    for path in paths:
        lower = path.lower()

        if (
            lower.endswith("_test.py")
            or lower.endswith("test.py")
            or "/test_" in lower
        ):
            candidates.append(path)

    return candidates


def validate_test_structure(
    test_path,
    implementation_paths
):
    source = read_source(test_path)

    if not source.strip():
        return {
            "path": str(test_path),
            "status": "FAIL",
            "reason": "Test file is empty or unreadable.",
        }

    try:
        tree = ast.parse(
            source,
            filename=str(test_path)
        )
    except SyntaxError as exc:
        return {
            "path": str(test_path),
            "status": "FAIL",
            "reason": (
                f"Test syntax error line "
                f"{exc.lineno}: {exc.msg}"
            ),
        }

    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    }

    has_test_functions = any(
        name.startswith("test")
        for name in functions
    )

    has_main_guard = (
        'if __name__ == "__main__"'
        in source
        or "if __name__ == '__main__'"
        in source
    )

    implementation_stems = {
        Path(path).stem
        for path in implementation_paths
        if path != test_path
    }

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module.split(".")[0]
                )

    linked = bool(
        implementation_stems
        & imported_modules
    )

    problems = []

    if not has_test_functions:
        problems.append(
            "No test_* function found."
        )

    if not has_main_guard:
        problems.append(
            "No executable __main__ entry point."
        )

    if not linked:
        problems.append(
            "Test does not appear to import "
            "the generated implementation."
        )

    if problems:
        return {
            "path": str(test_path),
            "status": "FAIL",
            "reason": " ".join(problems),
        }

    return {
        "path": str(test_path),
        "status": "PASS",
        "reason": (
            "Test contains test functions, "
            "an executable entry point, "
            "and a link to the implementation."
        ),
    }


def validate_plan_semantics(plan):
    problems = []

    planned = collect_implementation_files(plan)

    problems.extend(
        validate_change_targets(plan)
    )

    tests = test_file_candidates(planned)

    for test_path in tests:
        absolute = BASE / test_path

        if absolute.exists():
            result = validate_test_structure(
                absolute,
                planned
            )

            if result["status"] == "FAIL":
                problems.append(result)

    return problems


def validate_generated_files(
    plan,
    sandbox_dir=None
):
    results = []

    if sandbox_dir is None:
        return results

    sandbox = Path(sandbox_dir).expanduser().resolve()

    if not sandbox.exists():
        results.append({
            "path": str(sandbox),
            "status": "FAIL",
            "reason": "Sandbox directory does not exist.",
        })
        return results

    for relative_path in collect_implementation_files(plan):

        if not relative_path.endswith(".py"):
            continue

        absolute = sandbox / relative_path

        if not absolute.exists():
            results.append({
                "path": relative_path,
                "status": "FAIL",
                "reason": (
                    "Planned generated file is missing "
                    "from the sandbox."
                ),
            })
            continue

        syntax = validate_python_syntax(
            absolute
        )

        results.append(syntax)

        if syntax["status"] == "PASS":
            results.append(
                validate_python_names(
                    absolute
                )
            )

    for test_path in test_file_candidates(
        collect_implementation_files(plan)
    ):
        absolute = sandbox / test_path

        if not absolute.exists():
            continue

        test_result = validate_test_structure(
            absolute,
            collect_implementation_files(plan)
        )

        results.append(test_result)

    return results


def calculate_status(
    architecture_result,
    semantic_problems,
    generated_results
):
    if architecture_result["blocked"]:
        return "REVISE", "HIGH"

    if (
        architecture_result["wrong_existing"]
        or architecture_result["wrong_new"]
    ):
        return "REVISE", "MEDIUM"

    failures = [
        item
        for item in generated_results
        if item.get("status") == "FAIL"
    ]

    if semantic_problems or failures:
        return "REVISE", "HIGH"

    if not generated_results:
        return "REVIEW REQUIRED", "MEDIUM"

    return "SAFE TO CONTINUE", "LOW"


def print_result(result, request):
    print("=" * 45)
    print("JIRAIYA PLAN VALIDATOR")
    print("=" * 45)

    print()
    print(f"PLAN STATUS: {result['status']}")
    print(f"Severity: {result['severity']}")

    print()
    print("Request:")
    print(request)

    architecture = result["architecture_check"]

    print()
    print("Architecture check:")

    for item in architecture["existing_files"]:
        print(
            f"  ✓ {item['path']} [EXISTING]"
        )

    for item in architecture["new_files"]:
        print(
            f"  ⚠ {item['path']} [NEW]"
        )

    for item in architecture["wrong_existing"]:
        print(
            f"  ✗ {item['path']} "
            "[ARCHITECTURE MISMATCH]"
        )

    for item in architecture["wrong_new"]:
        print(
            f"  ✗ {item['path']} "
            "[ARCHITECTURE MISMATCH]"
        )

    for item in architecture["blocked"]:
        print(
            f"  🔒 {item['path']} [BLOCKED]"
        )
        print(
            f"      Reason: {item['reason']}"
        )

    print()
    print(
        f"Existing files : "
        f"{len(architecture['existing_files'])}"
    )

    print(
        f"New files      : "
        f"{len(architecture['new_files'])}"
    )

    print(
        f"Blocked paths  : "
        f"{len(architecture['blocked'])}"
    )

    print(
        "Architecture mismatches : "
        f"{len(architecture['wrong_existing']) + len(architecture['wrong_new'])}"
    )

    print()
    print("Functional validation:")

    if not result["semantic_problems"]:
        print(
            "  ✓ No obvious plan-level "
            "functional problems."
        )
    else:
        for problem in result["semantic_problems"]:
            print(
                f"  ✗ {problem.get('type', 'FUNCTIONAL')} "
                f"{problem.get('path', '')}"
            )
            print(
                f"      {problem.get('reason', '')}"
            )

    print()
    print("Sandbox validation:")

    if not result["generated_validation"]:
        print(
            "  - Sandbox validation not performed."
        )
    else:
        for item in result["generated_validation"]:
            symbol = (
                "✓"
                if item["status"] == "PASS"
                else "✗"
            )

            print(
                f"  {symbol} {item['path']} "
                f"[{item['status']}]"
            )
            print(
                f"      {item['reason']}"
            )


def save_validation(
    plan_path,
    document,
    result
):
    output = {
        "plan_file": str(plan_path),
        "status": result["status"],
        "severity": result["severity"],
        "request": document.get(
            "request",
            ""
        ),
        "architecture_check": result[
            "architecture_check"
        ],
        "semantic_problems": result[
            "semantic_problems"
        ],
        "sandbox_validation": result[
            "generated_validation"
        ],
    }

    output_path = (
        plan_path.parent
        / f"{plan_path.stem}_validation.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    return output_path


def main():
    if len(sys.argv) not in (2, 3):
        print(
            "Usage:\n"
            "python plan_validator.py <plan.json> "
            "[sandbox_dir]"
        )
        sys.exit(1)

    plan_path = Path(
        sys.argv[1]
    ).expanduser()

    sandbox_dir = None

    if len(sys.argv) == 3:
        sandbox_dir = Path(
            sys.argv[2]
        ).expanduser()

    if not plan_path.exists():
        print(
            f"ERROR: Plan not found:\n"
            f"{plan_path}"
        )
        sys.exit(1)

    try:
        document = load_json(plan_path)
        architecture = load_architecture()
        plan = resolve_plan(document)

        architecture_result = (
            validate_architecture(
                plan,
                architecture
            )
        )

        semantic_problems = (
            validate_plan_semantics(plan)
        )

        generated_validation = (
            validate_generated_files(
                plan,
                sandbox_dir
            )
        )

        status, severity = calculate_status(
            architecture_result,
            semantic_problems,
            generated_validation
        )

        result = {
            "status": status,
            "severity": severity,
            "architecture_check":
                architecture_result,
            "semantic_problems":
                semantic_problems,
            "generated_validation":
                generated_validation,
        }

        print_result(
            result,
            document.get(
                "request",
                "Unknown request"
            )
        )

        output_path = save_validation(
            plan_path,
            document,
            result
        )

        print()
        print("✓ Validation saved:")
        print(output_path)

        if status == "SAFE TO CONTINUE":
            sys.exit(0)

        sys.exit(2)

    except Exception as exc:
        print()
        print("✗ Validation failed:")
        print(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
