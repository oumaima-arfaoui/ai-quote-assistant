import json
from pathlib import Path

from extract import chain, compute_missing

expected = json.loads(Path("data/expected.json").read_text(encoding="utf-8"))

ok_count = 0
total = 0

for filename, checks in expected.items():
    text = Path("data/requests", filename).read_text(encoding="utf-8")
    result = chain.invoke({"request_text": text})
    result.missing_fields = compute_missing(result)
    data = result.model_dump(mode="json")

    print(f"\n{filename}")
    for field, wanted in checks.items():
        got = data[field]
        if isinstance(wanted, list):
            good = sorted(got) == sorted(wanted)
        else:
            good = got == wanted
        total += 1
        ok_count += good
        print(f"  {'OK  ' if good else 'FAIL'} {field}" + ("" if good else f"  wanted={wanted}  got={got}"))

print(f"\nScore: {ok_count}/{total}")