import json
import sys
from collections import Counter
from pathlib import Path

from extract import chain, compute_missing
from match import select_lines

EXPECTED = json.loads(Path("data/expected_match.json").read_text(encoding="utf-8"))
GLOBAL_FORBIDDEN = set(EXPECTED["global_must_not_include"])
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 1


def load_record(filename):
    text = Path("data/requests", filename).read_text(encoding="utf-8")
    record = chain.invoke({"request_text": text})
    record.missing_fields = compute_missing(record)
    return record


def check_selection(record, expected):
    selection = select_lines(record)
    selected = {line.item_id for line in selection.lines}
    has_manual = len(selection.unmatched_work) > 0
    failures = []
    checks = 0

    for item_id in expected["must_include"]:
        checks += 1
        if item_id not in selected:
            failures.append(f"manque {item_id}")
    for item_id in sorted(set(expected["must_not_include"]) | GLOBAL_FORBIDDEN):
        checks += 1
        if item_id in selected:
            failures.append(f"ne devrait pas contenir {item_id}")
    checks += 1
    if has_manual != expected["needs_manual_pricing"]:
        failures.append(
            f"chiffrage manuel : attendu {expected['needs_manual_pricing']}, obtenu {has_manual}"
        )
    return checks, failures


if __name__ == "__main__":
    total_checks = total_failures = clean_runs = 0
    for filename, expected in EXPECTED["requests"].items():
        record = load_record(filename)  # extraction once per request
        failure_counter = Counter()
        ok_runs = 0
        for _ in range(RUNS):
            checks, failures = check_selection(record, expected)
            total_checks += checks
            total_failures += len(failures)
            ok_runs += not failures
            failure_counter.update(failures)
        clean_runs += ok_runs

        status = "OK    " if ok_runs == RUNS else "ÉCHEC "
        print(f"\n{status}| {filename} | {ok_runs}/{RUNS} passages sans erreur")
        for failure, count in failure_counter.most_common():
            print(f"      - ({count}/{RUNS}) {failure}")

    all_runs = len(EXPECTED["requests"]) * RUNS
    print(
        f"\nChecks : {total_checks - total_failures}/{total_checks} "
        f"| passages sans erreur : {clean_runs}/{all_runs}"
    )