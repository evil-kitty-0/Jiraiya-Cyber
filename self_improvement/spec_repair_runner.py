import json
import sys

from chunk_pipeline import run_chunk


def run_repairs(repair_file, sandbox_dir):
    with open(
        repair_file,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    repairs = data.get("repairs", [])

    if not repairs:
        raise ValueError("No repair chunks found")

    results = []

    print(f"🔧 Running {len(repairs)} spec repairs")

    for index, repair in enumerate(repairs, start=1):
        print()
        print(
            f"━━━ Repair {index}/{len(repairs)} "
            f"━━━"
        )

        result = run_chunk(
            repair,
            sandbox_dir
        )

        results.append({
            "chunk_id": repair["chunk_id"],
            "status": "PASS",
            "result": result
        })

    return {
        "status": "PASS",
        "repair_count": len(results),
        "results": results
    }


def main():
    if len(sys.argv) < 3:
        print(
            'Usage: python spec_repair_runner.py '
            '"spec_repairs.json" "sandbox_dir"'
        )
        sys.exit(1)

    try:
        result = run_repairs(
            sys.argv[1],
            sys.argv[2]
        )

        print()
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
