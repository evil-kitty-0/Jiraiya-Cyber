import json
import sys


REQUIRED_FIELDS = {
    "chunk_id",
    "target_file",
    "operation",
    "description",
    "code",
}


ALLOWED_OPERATIONS = {
    "CREATE_FILE",
    "ADD_FUNCTION",
    "ADD_CLASS",
    "ADD_IMPORT",
    "MODIFY_FUNCTION",
}


def validate_chunk(chunk):
    if not isinstance(chunk, dict):
        return False, "Chunk must be a JSON object"

    missing = REQUIRED_FIELDS - set(chunk.keys())
    if missing:
        return False, f"Missing fields: {sorted(missing)}"

    if not isinstance(chunk["chunk_id"], str) or not chunk["chunk_id"].strip():
        return False, "chunk_id must be a non-empty string"

    if not isinstance(chunk["target_file"], str) or not chunk["target_file"].strip():
        return False, "target_file must be a non-empty string"

    if chunk["operation"] not in ALLOWED_OPERATIONS:
        return False, f"Unsupported operation: {chunk['operation']}"

    if not isinstance(chunk["description"], str):
        return False, "description must be a string"

    if not isinstance(chunk["code"], str):
        return False, "code must be a string"

    return True, "VALID"


def main():
    if len(sys.argv) < 2:
        print("Usage: python chunk_spec.py '<json>'")
        sys.exit(1)

    try:
        chunk = json.loads(sys.argv[1])
        valid, message = validate_chunk(chunk)

        print(json.dumps({
            "valid": valid,
            "message": message
        }, indent=2))

        sys.exit(0 if valid else 1)

    except json.JSONDecodeError as exc:
        print(json.dumps({
            "valid": False,
            "message": f"Invalid JSON: {exc}"
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
