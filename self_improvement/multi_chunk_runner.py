import json
import sys
from pathlib import Path

from chunk_pipeline import run_chunk
from spec_matcher import match_spec
from behavioral_gate import run_behavioral_test
from behavioral_repair import create_repair
from spec_repair import create_repairs
from semantic_quality_gate import run_quality_gate
from semantic_repair import create_repairs as create_semantic_repairs


MAX_SPEC_REPAIRS = 2
MAX_BEHAVIORAL_REPAIRS = 2
MAX_SEMANTIC_REPAIRS = 2


def run_all_chunks(chunk_plan, raw_spec, sandbox_dir):
    results = []

    chunks = chunk_plan.get("chunks", [])

    if not chunks:
        raise ValueError("Chunk plan contains no chunks")

    print(f"🚀 Running {len(chunks)} chunks")

    for index, chunk in enumerate(chunks, start=1):
        print()
        print(f"━━━ Chunk {index}/{len(chunks)} ━━━")

        result = run_chunk(
            chunk,
            sandbox_dir
        )

        results.append({
            "chunk_id": chunk["chunk_id"],
            "status": "PASS",
            "result": result
        })

    return results


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python multi_chunk_runner.py "
            "<chunk_plan.json> "
            "<raw_spec.json> "
            "<sandbox_dir>"
        )
        sys.exit(1)

    chunk_plan_file = Path(sys.argv[1])
    raw_spec_file = Path(sys.argv[2])
    sandbox_dir = Path(sys.argv[3])

    with chunk_plan_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        chunk_plan = json.load(file)

    with raw_spec_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        raw_spec = json.load(file)

    results = run_all_chunks(
        chunk_plan,
        raw_spec,
        sandbox_dir
    )

    # =========================================================
    # SPECIFICATION GATE
    # =========================================================

    print()
    print("━━━ Final Spec Check ━━━")

    matched, messages = match_spec(
        raw_spec,
        sandbox_dir
    )

    spec_repairs = []
    spec_rounds = 0

    while (
        not matched
        and spec_rounds < MAX_SPEC_REPAIRS
    ):
        print("  ✗ Raw specification NOT matched")

        for message in messages:
            print(f"  - {message}")

        spec_rounds += 1

        print()
        print(
            f"━━━ Spec Repair Round "
            f"{spec_rounds}/{MAX_SPEC_REPAIRS} ━━━"
        )

        try:
            repairs = create_repairs(messages)
        except Exception as exc:
            print(
                f"  ✗ Spec repair generation failed: {exc}"
            )
            break

        if not repairs:
            print(
                "  ✗ No specification repairs available"
            )
            break

        for repair in repairs:
            print(
                f"\n🔧 Repair: {repair['chunk_id']}"
            )

            result = run_chunk(
                repair,
                sandbox_dir
            )

            spec_repairs.append({
                "chunk_id": repair["chunk_id"],
                "status": "PASS",
                "result": result
            })

        matched, messages = match_spec(
            raw_spec,
            sandbox_dir
        )

        if matched:
            print("  ✓ Specification repaired")
        else:
            print(
                "  ✗ Specification still incomplete"
            )

            for message in messages:
                print(f"  - {message}")

    if not matched:
        return {
            "status": "SPEC_FAIL",
            "chunk_count": len(results),
            "results": results,
            "spec_match": {
                "matched": False,
                "messages": messages
            },
            "spec_repairs": spec_repairs
        }

    print("  ✓ Raw specification matched")

    # =========================================================
    # BEHAVIORAL GATE
    # =========================================================

    print()
    print("━━━ Behavioral Check ━━━")

    behavioral = run_behavioral_test(
        sandbox_dir
    )

    behavioral_repairs = []
    behavioral_rounds = 0

    while (
        not behavioral["passed"]
        and behavioral_rounds < MAX_BEHAVIORAL_REPAIRS
    ):
        print("  ✗ Behavioral test FAILED")

        if behavioral["output"]:
            print(behavioral["output"])

        behavioral_rounds += 1

        print()
        print(
            f"━━━ Behavioral Repair Round "
            f"{behavioral_rounds}/"
            f"{MAX_BEHAVIORAL_REPAIRS} ━━━"
        )

        error = behavioral["output"]

        try:
            repair = create_repair(error)
        except Exception as exc:
            print(
                f"  ✗ No behavioral repair available: "
                f"{exc}"
            )
            break

        print(
            f"🔧 Repair: {repair['chunk_id']}"
        )

        result = run_chunk(
            repair,
            sandbox_dir
        )

        behavioral_repairs.append({
            "chunk_id": repair["chunk_id"],
            "status": "PASS",
            "result": result
        })

        behavioral = run_behavioral_test(
            sandbox_dir
        )

    if not behavioral["passed"]:
        print(
            "  ✗ Behavioral repair failed"
        )

        return {
            "status": "BEHAVIOR_FAIL",
            "chunk_count": len(results),
            "results": results,
            "spec_match": {
                "matched": True,
                "messages": messages
            },
            "spec_repairs": spec_repairs,
            "behavioral": behavioral,
            "behavioral_repairs": behavioral_repairs
        }

    print("  ✓ Behavioral test passed")

    # =========================================================
    # SEMANTIC QUALITY GATE
    # =========================================================

    print()
    print("━━━ Semantic Quality Check ━━━")

    quality_errors = run_quality_gate(
        sandbox_dir
    )

    semantic_repairs = []
    semantic_rounds = 0

    while (
        quality_errors
        and semantic_rounds < MAX_SEMANTIC_REPAIRS
    ):
        print("  ✗ Semantic quality FAILED")

        for error in quality_errors:
            print(f"  - {error}")

        semantic_rounds += 1

        print()
        print(
            f"━━━ Semantic Repair Round "
            f"{semantic_rounds}/"
            f"{MAX_SEMANTIC_REPAIRS} ━━━"
        )

        try:
            repairs = create_semantic_repairs(
                quality_errors
            )
        except Exception as exc:
            print(
                f"  ✗ Semantic repair generation failed: "
                f"{exc}"
            )
            break

        if not repairs:
            print(
                "  ✗ No semantic repairs available"
            )
            break

        for repair in repairs:
            print(
                f"\n🔧 Repair: {repair['chunk_id']}"
            )

            result = run_chunk(
                repair,
                sandbox_dir
            )

            semantic_repairs.append({
                "chunk_id": repair["chunk_id"],
                "status": "PASS",
                "result": result
            })

        quality_errors = run_quality_gate(
            sandbox_dir
        )

    if quality_errors:
        print(
            "  ✗ Semantic quality repair failed"
        )

        for error in quality_errors:
            print(f"  - {error}")

        return {
            "status": "QUALITY_FAIL",
            "chunk_count": len(results),
            "results": results,
            "spec_match": {
                "matched": True,
                "messages": messages
            },
            "spec_repairs": spec_repairs,
            "behavioral": behavioral,
            "behavioral_repairs": behavioral_repairs,
            "quality_errors": quality_errors,
            "semantic_repairs": semantic_repairs
        }

    print("  ✓ Semantic quality passed")

    # =========================================================
    # FINAL PASS
    # =========================================================

    print()
    print("╔══════════════════════════════════╗")
    print("║      JIRAIYA PIPELINE: PASS      ║")
    print("╚══════════════════════════════════╝")

    return {
        "status": "PASS",
        "chunk_count": len(results),
        "results": results,
        "spec_match": {
            "matched": True,
            "messages": messages
        },
        "spec_repairs": spec_repairs,
        "behavioral": behavioral,
        "behavioral_repairs": behavioral_repairs,
        "semantic_repairs": semantic_repairs
    }


if __name__ == "__main__":
    try:
        result = main()

        print()
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as exc:
        print()
        print(f"ERROR: {exc}")
        sys.exit(1)
