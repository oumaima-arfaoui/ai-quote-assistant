import json
from pathlib import Path

from extract import chain, compute_missing
from match import select_lines

draft = {}
for path in sorted(Path("data/requests").glob("*.txt")):
    text = path.read_text(encoding="utf-8")
    record = chain.invoke({"request_text": text})
    record.missing_fields = compute_missing(record)
    if not record.is_quote_request:
        continue

    selection = select_lines(record)
    draft[path.name] = {
        "must_include": sorted({line.item_id for line in selection.lines}),
        "must_not_include": [],
        "needs_manual_pricing": len(selection.unmatched_work) > 0,
    }
    print(f"\n===== {path.name} =====")
    print(text.strip()[:500])
    print("-> sélectionné :", draft[path.name]["must_include"])
    print("-> hors catalogue :", selection.unmatched_work)

out = Path("data/expected_match.draft.json")
out.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nÉcrit :", out)