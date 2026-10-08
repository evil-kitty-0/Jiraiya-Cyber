import json
import sys
from datetime import datetime, timezone


def create_raw_spec(request):
    if not request or not request.strip():
        raise ValueError("Request cannot be empty")

    return {
        "spec_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": request.strip(),
        "goal": request.strip(),
        "constraints": {
            "production_changes": False,
            "sandbox_only": True,
            "protected_files": True,
            "small_chunks": True,
            "validate_each_chunk": True,
            "compile_before_deploy": True,
        },
        "status": "RAW",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python raw_spec.py \"request\"")
        sys.exit(1)

    try:
        spec = create_raw_spec(" ".join(sys.argv[1:]))
        print(json.dumps(spec, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
