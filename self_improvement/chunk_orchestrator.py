import json
import sys


def create_chunk_plan(raw_spec):
    request = raw_spec.get("request", "").lower()

    chunks = []

    if "system status" in request:
        chunks = [
            {
                "chunk_id": "status_core",
                "target_file": "self_improvement/system_status.py",
                "operation": "CREATE_FILE",
                "goal": "Create the system status core and result structure.",
            },
            {
                "chunk_id": "status_memory",
                "target_file": "self_improvement/system_status.py",
                "operation": "ADD_FUNCTION",
                "goal": "Add a safe read-only memory health check.",
            },
            {
                "chunk_id": "status_knowledge",
                "target_file": "self_improvement/system_status.py",
                "operation": "ADD_FUNCTION",
                "goal": "Add a safe read-only knowledge health check.",
            },
            {
                "chunk_id": "status_web",
                "target_file": "self_improvement/system_status.py",
                "operation": "ADD_FUNCTION",
                "goal": "Add a lightweight web health check.",
            },
            {
                "chunk_id": "status_llm",
                "target_file": "self_improvement/system_status.py",
                "operation": "ADD_FUNCTION",
                "goal": "Add a local LLM health check.",
            },
            {
                "chunk_id": "status_cli",
                "target_file": "self_improvement/system_status.py",
                "operation": "ADD_FUNCTION",
                "goal": "Add human-readable CLI output and executable entry point.",
            },
            {
                "chunk_id": "status_tests",
                "target_file": "self_improvement/system_status_test.py",
                "operation": "CREATE_FILE",
                "goal": "Create tests for the system status implementation.",
            },
        ]

    if not chunks:
        raise ValueError(
            "No chunk decomposition rule exists for this request"
        )

    return {
        "chunk_plan_version": 1,
        "request": raw_spec.get("request", ""),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: python chunk_orchestrator.py \'{"raw_spec": "..."}\'')
        sys.exit(1)

    try:
        raw_spec = json.loads(sys.argv[1])
        plan = create_chunk_plan(raw_spec)

        print(json.dumps(
            plan,
            indent=2,
            ensure_ascii=False
        ))

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
