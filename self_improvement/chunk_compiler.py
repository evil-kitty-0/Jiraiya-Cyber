import ast
import json
import sys
from pathlib import Path

from chunk_validator import validate_chunk


def safe_target(sandbox_dir, target_file):
    sandbox = Path(sandbox_dir).resolve()
    target = (sandbox / target_file).resolve()

    try:
        target.relative_to(sandbox)
    except ValueError:
        raise ValueError("Target escapes sandbox")

    return target


def replace_function(source, new_code):
    """
    Replace exactly one function/method anywhere in the AST,
    including functions nested inside classes.
    """

    tree = ast.parse(source)
    new_tree = ast.parse(new_code)

    new_functions = [
        node
        for node in new_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    if len(new_functions) != 1:
        raise ValueError(
            "MODIFY_FUNCTION requires exactly one function"
        )

    new_function = new_functions[0]

    target_node = None

    # Search recursively so class methods are also supported.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == new_function.name:
                target_node = node
                break

    if target_node is None:
        raise ValueError(
            f"Function not found: {new_function.name}"
        )

    lines = source.splitlines(keepends=True)

    start = target_node.lineno - 1
    end = target_node.end_lineno

    # Preserve indentation of the original function/method.
    original_line = lines[start]

    indent = original_line[
        :len(original_line) - len(original_line.lstrip())
    ]

    new_lines = new_code.rstrip().splitlines()

    replacement_lines = []

    for line in new_lines:
        if line.strip():
            replacement_lines.append(indent + line)
        else:
            replacement_lines.append("")

    replacement = "\n".join(replacement_lines) + "\n"

    return (
        "".join(lines[:start])
        + replacement
        + "".join(lines[end:])
    )


def compile_chunk(sandbox_dir, chunk):
    target = safe_target(
        sandbox_dir,
        chunk["target_file"]
    )

    context_source = None

    if (
        chunk["operation"] == "MODIFY_FUNCTION"
        and target.exists()
    ):
        context_source = target.read_text(
            encoding="utf-8"
        )

    valid, message = validate_chunk(
        chunk,
        context_source=context_source
    )

    if not valid:
        raise ValueError(
            f"Chunk rejected: {message}"
        )

    target.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    operation = chunk["operation"]
    code = chunk["code"]

    if operation == "CREATE_FILE":

        if target.exists():
            raise FileExistsError(
                f"File already exists: {target}"
            )

        target.write_text(
            code.rstrip() + "\n",
            encoding="utf-8"
        )

    elif operation == "ADD_IMPORT":

        existing = (
            target.read_text(encoding="utf-8")
            if target.exists()
            else ""
        )

        target.write_text(
            code.rstrip() + "\n\n" + existing,
            encoding="utf-8"
        )

    elif operation == "ADD_FUNCTION":

        with target.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                "\n\n" +
                code.rstrip() +
                "\n"
            )

    elif operation == "ADD_CLASS":

        with target.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                "\n\n" +
                code.rstrip() +
                "\n"
            )

    elif operation == "MODIFY_FUNCTION":

        if not target.exists():
            raise FileNotFoundError(
                f"Target file does not exist: {target}"
            )

        existing = target.read_text(
            encoding="utf-8"
        )

        updated = replace_function(
            existing,
            code
        )

        target.write_text(
            updated,
            encoding="utf-8"
        )

    else:

        raise ValueError(
            f"Unsupported operation: {operation}"
        )

    return target


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python chunk_compiler.py "
            "<sandbox_dir> <chunk.json>"
        )
        sys.exit(1)

    sandbox_dir = sys.argv[1]

    with open(
        sys.argv[2],
        "r",
        encoding="utf-8"
    ) as file:
        chunk = json.load(file)

    target = compile_chunk(
        sandbox_dir,
        chunk
    )

    print(f"✓ Compiled: {target}")


if __name__ == "__main__":
    main()
