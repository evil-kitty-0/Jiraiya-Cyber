import ast
import json
import sys
from pathlib import Path


ALLOWED_OPERATIONS = {
    "CREATE_FILE",
    "ADD_FUNCTION",
    "ADD_CLASS",
    "ADD_IMPORT",
    "MODIFY_FUNCTION",
}


PROTECTED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "versions",
    "sandbox",
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


FORBIDDEN_CALLS = {
    "exec",
    "eval",
    "compile",
    "__import__",
}


BUILTINS = {
    "print",
    "len",
    "range",
    "str",
    "int",
    "float",
    "bool",
    "dict",
    "list",
    "set",
    "tuple",
    "min",
    "max",
    "sum",
    "abs",
    "open",
    "type",
    "isinstance",
    "issubclass",
    "enumerate",
    "zip",
    "sorted",
    "any",
    "all",
    "True",
    "False",
    "None",
    "__name__",
    "__file__",
    "__package__",
    "__doc__",
    "__all__",
}


def _add_target_names(target, names):
    """
    Collect variable names introduced by an assignment target.
    Handles:
      x = ...
      a, b = ...
      obj.attr = ...   -> does not treat obj.attr as a new name
      arr[i] = ...     -> does not introduce a new name
    """
    if isinstance(target, ast.Name):
        names.add(target.id)

    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            _add_target_names(element, names)


def get_defined_names(tree):
    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            names.add(node.name)

        elif isinstance(node, ast.Import):

            for alias in node.names:
                names.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):

            for alias in node.names:
                if alias.name == "*":
                    continue

                names.add(
                    alias.asname
                    or alias.name
                )

        elif isinstance(node, ast.arg):
            names.add(node.arg)

        elif isinstance(node, ast.Assign):

            for target in node.targets:
                _add_target_names(
                    target,
                    names,
                )

        elif isinstance(node, ast.AnnAssign):

            _add_target_names(
                node.target,
                names,
            )

        elif isinstance(node, ast.AugAssign):

            _add_target_names(
                node.target,
                names,
            )

        elif isinstance(node, ast.NamedExpr):

            _add_target_names(
                node.target,
                names,
            )

        elif isinstance(node, ast.For):

            _add_target_names(
                node.target,
                names,
            )

        elif isinstance(node, ast.comprehension):

            _add_target_names(
                node.target,
                names,
            )

        elif isinstance(node, ast.ExceptHandler):

            if node.name:
                names.add(node.name)

        elif isinstance(node, ast.With):

            for item in node.items:
                if item.optional_vars:
                    _add_target_names(
                        item.optional_vars,
                        names,
                    )

    return names


def find_unknown_names(tree):
    defined = get_defined_names(tree)
    unknown = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Name):

            if isinstance(node.ctx, ast.Load):

                if (
                    node.id not in defined
                    and node.id not in BUILTINS
                ):
                    unknown.add(node.id)

    return unknown


def validate_python(
    code,
    operation,
    context_source=None,
):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"Syntax error: {exc}"

    if operation not in ALLOWED_OPERATIONS:
        return False, f"Unsupported operation: {operation}"

    if not code.strip():
        return False, "Code cannot be empty"

    if operation in {
        "ADD_FUNCTION",
        "MODIFY_FUNCTION",
    }:

        functions = [
            node
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        ]

        if len(functions) != 1:
            return (
                False,
                f"{operation} requires exactly one function",
            )

        function = functions[0]

        if function.args.posonlyargs:
            return False, "Function cannot take arguments"

        if function.args.args:
            return False, "Function cannot take arguments"

        if function.args.kwonlyargs:
            return False, "Function cannot take arguments"

        if function.args.vararg:
            return False, "Function cannot take arguments"

        if function.args.kwarg:
            return False, "Function cannot take arguments"

        body = list(function.body)

        if (
            len(body) == 1
            and isinstance(body[0], ast.Pass)
        ):
            return False, "Function cannot be pass-only"

    elif operation == "ADD_CLASS":

        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        ]

        if len(classes) != 1:
            return (
                False,
                "ADD_CLASS requires exactly one class",
            )

    elif operation == "CREATE_FILE":

        if not tree.body:
            return False, "File cannot be empty"

    # Names already defined by the target file.
    context_defined = set()

    if context_source:

        try:
            context_tree = ast.parse(
                context_source
            )

            context_defined = get_defined_names(
                context_tree
            )

        except SyntaxError:
            pass

    unknown = (
        find_unknown_names(tree)
        - context_defined
    )

    if unknown:
        return (
            False,
            "Unknown names: "
            + ", ".join(sorted(unknown)),
        )

    # Security checks.
    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            if isinstance(
                node.func,
                ast.Name,
            ):

                if node.func.id in FORBIDDEN_CALLS:

                    return (
                        False,
                        f"Forbidden call: "
                        f"{node.func.id}",
                    )

    return True, "Valid"


def validate_target_file(target_file):
    if not target_file:
        return False, "Target file cannot be empty"

    path = Path(target_file)

    if path.is_absolute():
        return (
            False,
            "Absolute target paths are not allowed",
        )

    if ".." in path.parts:
        return (
            False,
            "Parent path traversal is not allowed",
        )

    for part in path.parts:

        if part in PROTECTED_DIRS:
            return (
                False,
                f"Protected directory: {part}",
            )

    if path.suffix.lower() in PROTECTED_EXTENSIONS:
        return (
            False,
            f"Protected file type: {path.suffix}",
        )

    if path.suffix.lower() != ".py":
        return (
            False,
            "Only Python files are allowed",
        )

    return True, "Valid"


def validate_chunk(
    chunk,
    context_source=None,
):
    if not isinstance(chunk, dict):
        return (
            False,
            "Chunk must be a dictionary",
        )

    required = {
        "chunk_id",
        "target_file",
        "operation",
        "code",
    }

    missing = required - set(chunk)

    if missing:
        return (
            False,
            "Missing fields: "
            + ", ".join(sorted(missing)),
        )

    target_ok, target_message = (
        validate_target_file(
            chunk["target_file"]
        )
    )

    if not target_ok:
        return False, target_message

    return validate_python(
        chunk["code"],
        chunk["operation"],
        context_source=context_source,
    )


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python chunk_validator.py "
            "<chunk.json>"
        )
        sys.exit(1)

    with open(
        sys.argv[1],
        "r",
        encoding="utf-8",
    ) as file:
        chunk = json.load(file)

    valid, message = validate_chunk(
        chunk
    )

    if valid:
        print("VALID")
        print(message)
        sys.exit(0)

    print("INVALID")
    print(message)
    sys.exit(1)


if __name__ == "__main__":
    main()
