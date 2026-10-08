import json
import sys


def create_repairs(errors):
    repairs = []

    needs_test_repair = any(
        "test_create_file()" in error
        and (
            "only pass" in error
            or "placeholder text" in error
        )
        for error in errors
    )

    if needs_test_repair:
        repairs.append({
            "chunk_id": "semantic_repair_system_status_test",
            "target_file": (
                "self_improvement/system_status_test.py"
            ),
            "operation": "MODIFY_FUNCTION",
            "description": (
                "Replace test_create_file() with a real "
                "test that imports system_status and verifies "
                "get_system_status() returns a dictionary "
                "containing memory, knowledge, web and llm."
            ),
            "goal": (
                "Replace test_create_file() with a real "
                "test that imports system_status and verifies "
                "get_system_status() returns a dictionary "
                "containing memory, knowledge, web and llm."
            ),
            "code": (
                "def test_create_file():\n"
                "    import system_status\n"
                "    result = system_status.get_system_status()\n"
                "    assert isinstance(result, dict)\n"
                "    assert \"memory\" in result\n"
                "    assert \"knowledge\" in result\n"
                "    assert \"web\" in result\n"
                "    assert \"llm\" in result\n"
            ),
        })

    return repairs


def main():
    if len(sys.argv) < 2:
        print(
            'Usage: python semantic_repair.py "error1" "error2"'
        )
        sys.exit(1)

    repairs = create_repairs(
        sys.argv[1:]
    )

    print(
        json.dumps(
            repairs,
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
