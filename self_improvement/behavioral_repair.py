import json
import sys


def create_repair(error):
    if "get_system_status() must return a dict" in error:
        return {
            "chunk_id": "behavior_repair_get_system_status",
            "target_file": "self_improvement/system_status.py",
            "operation": "MODIFY_FUNCTION",
            "goal": (
                "Modify get_system_status() so it calls "
                "check_memory(), check_knowledge(), check_web(), "
                "and check_llm(), then returns a dictionary with "
                "the keys memory, knowledge, web and llm."
            )
        }

    raise ValueError(
        f"No repair rule for error: {error}"
    )


def main():
    if len(sys.argv) < 2:
        print(
            'Usage: python behavioral_repair.py "error message"'
        )
        sys.exit(1)

    try:
        repair = create_repair(
            sys.argv[1]
        )

        print(
            json.dumps(
                repair,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
