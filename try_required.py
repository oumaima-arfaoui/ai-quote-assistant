from pathlib import Path

from extract import chain, compute_missing

for path in sorted(Path("data/requests").glob("*.txt")):
    record = chain.invoke({"request_text": path.read_text(encoding="utf-8")})
    record.missing_fields = compute_missing(record)
    types = [w.value for w in record.work_types]
    print(f"{path.name:<26} | {types} | surface={record.surface_m2} | manquant={record.missing_fields}")
