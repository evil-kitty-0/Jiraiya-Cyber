import json
import sys


def create_repairs(messages):
    repairs = []

    for message in messages:
        prefix = "Missing required function: "

        if message.startswith(prefix):
            function_name = message[len(prefix):].strip().replace("()", "")

            repairs.append({
                "chunk_id": f"repair_{function_name}",
                "target_file": "self_improvement/system_status.py",
                "operation": "ADD_FUNCTION",
                "goal": (
                    f"Add the required function "
                    f"{function_name}. "
                    f"It must be a safe, read-only system "
                    f"status check and return a simple result."
                )
            })

    return repairs


def main():
    if len(sys.argv) < 2:
        print(
            'Usage: python spec_repair.py '
            '\'{"messages": [...]}\''
        )
        sys.exit(1)

    try:
        result = json.loads(sys.argv[1])

        messages = result.get(
            "messages",
            []
        )

        repairs = create_repairs(
            messages
        )

        print(
            json.dumps(
                {
                    "repair_count": len(repairs),
                    "repairs": repairs
                },
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
