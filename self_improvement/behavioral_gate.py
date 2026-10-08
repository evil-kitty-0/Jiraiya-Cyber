import subprocess
import sys
from pathlib import Path


def run_behavioral_test(sandbox_dir):
    project_root = Path(__file__).resolve().parent.parent
    test_file = project_root / "self_improvement" / "behavioral_status_test.py"

    command = [
        sys.executable,
        str(test_file),
    ]

    result = subprocess.run(
        command,
        cwd=str(project_root),
        env={
            **__import__("os").environ,
            "JIRAIYA_SANDBOX": str(Path(sandbox_dir).resolve()),
        },
        capture_output=True,
        text=True,
    )

    output = (
        result.stdout.strip()
        + (
            "\n" + result.stderr.strip()
            if result.stderr.strip()
            else ""
        )
    ).strip()

    return {
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "output": output,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            'Usage: python behavioral_gate.py "sandbox_dir"'
        )
        sys.exit(1)

    result = run_behavioral_test(sys.argv[1])

    print(result["output"])

    sys.exit(0 if result["passed"] else 1)
